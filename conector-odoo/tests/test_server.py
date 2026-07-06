"""Pruebas offline del servidor: guard de transiciones y move_task con cliente simulado."""

import pytest

from conector_odoo import server
from conector_odoo.client import OdooError

STAGES = ["Backlog", "Análisis/Diseño", "Aprobado", "Desarrollo", "Prueba", "PR/Review", "Hecho"]

ALLOWED = [
    ("Aprobado", "Desarrollo"),
    ("Desarrollo", "Prueba"),
    ("Prueba", "PR/Review"),
]


@pytest.mark.parametrize("current,target", ALLOWED)
def test_guard_allows_ai_transitions(current, target):
    server.validate_transition(current, target)  # must not raise


@pytest.mark.parametrize(
    "current,target",
    [(c, t) for c in STAGES for t in STAGES if (c, t) not in ALLOWED],
)
def test_guard_rejects_everything_else(current, target):
    with pytest.raises(OdooError, match="gates humanos"):
        server.validate_transition(current, target)


def test_guard_is_case_insensitive():
    server.validate_transition("aprobado", "DESARROLLO")
    with pytest.raises(OdooError):
        server.validate_transition("BACKLOG", "desarrollo")


class _FakeOdoo:
    """Simulates execute_kw for the move_task flow."""

    def __init__(self, current_stage):
        self.current_stage = current_stage
        self.written_stage_id = None

    def execute_kw(self, model, method, args, kwargs=None):
        if (model, method) == ("project.task", "read"):
            return [
                {
                    "id": args[0][0],
                    "name": "tarea",
                    "stage_id": [10, self.current_stage],
                    "project_id": [1, "Plantilla"],
                }
            ]
        if (model, method) == ("project.task.type", "search_read"):
            return [{"id": 100 + i, "name": n} for i, n in enumerate(STAGES)]
        if (model, method) == ("project.task", "write"):
            self.written_stage_id = args[1]["stage_id"]
            return True
        raise AssertionError(f"unexpected call {model}.{method}")


@pytest.fixture
def fake_odoo(monkeypatch):
    holder = {}

    def factory(stage):
        fake = _FakeOdoo(stage)
        holder["fake"] = fake
        monkeypatch.setitem(server._CLIENTS, "test", fake)
        return fake

    yield factory
    server._CLIENTS.pop("test", None)


def test_move_task_allowed_writes_stage(fake_odoo):
    fake = fake_odoo("Aprobado")
    result = server.move_task("test", 42, "Desarrollo")
    assert result["from_stage"] == "Aprobado"
    assert result["to_stage"] == "Desarrollo"
    assert fake.written_stage_id == 100 + STAGES.index("Desarrollo")


def test_move_task_rejected_does_not_write(fake_odoo):
    fake = fake_odoo("Backlog")
    with pytest.raises(OdooError, match="gates humanos"):
        server.move_task("test", 42, "Desarrollo")
    assert fake.written_stage_id is None


def test_move_task_unknown_target_stage(fake_odoo):
    fake = _FakeOdoo("Aprobado")

    def execute_kw(model, method, args, kwargs=None):
        if (model, method) == ("project.task.type", "search_read"):
            return [{"id": 1, "name": "Aprobado"}]
        return _FakeOdoo.execute_kw(fake, model, method, args, kwargs)

    fake.execute_kw = execute_kw
    server._CLIENTS["test"] = fake
    with pytest.raises(OdooError, match="no existe en el proyecto"):
        server.move_task("test", 42, "Desarrollo")


def test_html_to_text():
    html = "<p>Hola <b>mundo</b></p><ul><li>uno</li><li>dos</li></ul>"
    assert server.html_to_text(html) == "Hola mundo\nuno\ndos"


# --- text_to_html --------------------------------------------------------


def test_text_to_html_paragraphs():
    assert server.text_to_html("Hola\n\nMundo") == "<p>Hola</p><p>Mundo</p>"


def test_text_to_html_linebreaks_within_paragraph():
    assert server.text_to_html("a\nb") == "<p>a<br>b</p>"


def test_text_to_html_simple_list():
    assert server.text_to_html("- uno\n- dos") == "<ul><li>uno</li><li>dos</li></ul>"
    assert server.text_to_html("* uno\n* dos") == "<ul><li>uno</li><li>dos</li></ul>"


def test_text_to_html_passthrough_when_already_html():
    body = "<p>ya <b>html</b></p>"
    assert server.text_to_html(body) == body


def test_text_to_html_escapes_special_chars():
    out = server.text_to_html("a < b & c")
    assert "&lt;" in out and "&amp;" in out
    assert out == "<p>a &lt; b &amp; c</p>"


def test_text_to_html_empty():
    assert server.text_to_html("") == ""
    assert server.text_to_html(None) == ""


def test_text_to_html_roundtrip_recovers_lines():
    # html_to_text colapsa el límite de párrafo a un solo \n, así que el
    # round-trip recupera las líneas lógicas (no las líneas en blanco).
    text = "Hola\nMundo\n\notra linea"
    assert server.html_to_text(server.text_to_html(text)) == "Hola\nMundo\notra linea"


def test_comment_task_posts_html_and_rewrites_body():
    # message_post escapa un body str plano (Odoo 16+), así que comment_task
    # publica y luego reescribe el body con mail.message.write (sin escapar).
    captured = {}

    class _FakeComment:
        def execute_kw(self, model, method, args, kwargs=None):
            if (model, method) == ("project.task", "message_post"):
                captured["post_body"] = kwargs["body"]
                return [7]
            if (model, method) == ("mail.message", "write"):
                captured["write_ids"] = args[0]
                captured["write_body"] = args[1]["body"]
                return True
            raise AssertionError(f"unexpected call {model}.{method}")

    server._CLIENTS["test"] = _FakeComment()
    try:
        result = server.comment_task("test", 42, "linea uno\n\nlinea dos")
    finally:
        server._CLIENTS.pop("test", None)
    assert result == {"task_id": 42, "message_id": [7]}
    # el body ya viaja como HTML y se reescribe sobre el mensaje recién creado
    assert captured["post_body"] == "<p>linea uno</p><p>linea dos</p>"
    assert captured["write_ids"] == [7]
    assert captured["write_body"] == "<p>linea uno</p><p>linea dos</p>"


# --- list_projects / recommend_tasks -------------------------------------

# Stage catalog shared by the recommendation fakes: id -> (name, sequence, fold).
_STAGE_TYPES = {
    10: ("Desarrollo", 3, False),
    11: ("Hecho", 9, True),
    12: ("Aprobado", 2, False),
    13: ("Análisis/Diseño", 1, False),
}


def _stage_type_read(ids):
    return [
        {"id": i, "name": _STAGE_TYPES[i][0], "sequence": _STAGE_TYPES[i][1], "fold": _STAGE_TYPES[i][2]}
        for i in ids
    ]


class _FakeProjects:
    """execute_kw fake for list_projects."""

    def __init__(self, projects, tasks):
        self._projects = projects  # [{"id","name"}] already name-sorted
        self._tasks = tasks        # [{"id","project_id":[id,name],"stage_id":[id,name]}]

    def execute_kw(self, model, method, args, kwargs=None):
        if (model, method) == ("project.project", "search_read"):
            return self._projects
        if (model, method) == ("project.task", "search_read"):
            return self._tasks
        if (model, method) == ("project.task.type", "read"):
            return _stage_type_read(args[0])
        raise AssertionError(f"unexpected call {model}.{method}")


def _install(fake):
    server._CLIENTS["test"] = fake


def _uninstall():
    server._CLIENTS.pop("test", None)


def test_list_projects_counts_and_excludes_folded():
    projects = [{"id": 1, "name": "Alpha"}, {"id": 2, "name": "Beta"}]
    tasks = [
        {"id": 1, "project_id": [1, "Alpha"], "stage_id": [10, "Desarrollo"]},
        {"id": 2, "project_id": [1, "Alpha"], "stage_id": [11, "Hecho"]},  # folded
        {"id": 3, "project_id": [2, "Beta"], "stage_id": [12, "Aprobado"]},
    ]
    _install(_FakeProjects(projects, tasks))
    try:
        result = server.list_projects("test")
    finally:
        _uninstall()
    assert [p["name"] for p in result] == ["Alpha", "Beta"]  # order preserved
    alpha = result[0]
    assert alpha["task_count"] == 2 and alpha["open_task_count"] == 1  # Hecho excluded
    beta = result[1]
    assert beta["task_count"] == 1 and beta["open_task_count"] == 1


def test_list_projects_empty():
    _install(_FakeProjects([], []))
    try:
        assert server.list_projects("test") == []
    finally:
        _uninstall()


class _FakeRecommend:
    """execute_kw fake for recommend_tasks."""

    def __init__(self, tasks):
        self._tasks = tasks

    def execute_kw(self, model, method, args, kwargs=None):
        if (model, method) == ("project.task", "search_read"):
            return self._tasks
        if (model, method) == ("project.task.type", "read"):
            return _stage_type_read(args[0])
        raise AssertionError(f"unexpected call {model}.{method}")


def _recommend_tasks_fixture():
    return [
        # id, priority, sequence, stage, kanban, deadline
        {"id": 1, "name": "aprobada normal", "priority": "0", "sequence": 5,
         "stage_id": [12, "Aprobado"], "date_deadline": False},
        {"id": 2, "name": "importante en dev", "priority": "1", "sequence": 1,
         "stage_id": [10, "Desarrollo"], "date_deadline": False},
        {"id": 3, "name": "con deadline", "priority": "0", "sequence": 1,
         "stage_id": [10, "Desarrollo"], "date_deadline": "2026-07-10"},
        {"id": 4, "name": "ya hecha", "priority": "1", "sequence": 1,
         "stage_id": [11, "Hecho"], "date_deadline": False},
    ]


def test_recommend_tasks_order_and_excludes_folded():
    _install(_FakeRecommend(_recommend_tasks_fixture()))
    try:
        result = server.recommend_tasks("test", "Alpha")
    finally:
        _uninstall()
    # folded task 4 excluded; order: priority>deadline>stage.seq
    assert [t["id"] for t in result] == [2, 3, 1]


def test_recommend_tasks_reason_and_next_transition():
    _install(_FakeRecommend(_recommend_tasks_fixture()))
    try:
        result = server.recommend_tasks("test", "Alpha")
    finally:
        _uninstall()
    by_id = {t["id"]: t for t in result}
    assert "importante ⭐" in by_id[2]["reason"]
    assert by_id[2]["next_ai_transition"] == "Prueba"  # Desarrollo -> Prueba
    assert "vence 2026-07-10" in by_id[3]["reason"]
    assert by_id[1]["next_ai_transition"] == "Desarrollo"  # Aprobado -> Desarrollo


def test_recommend_tasks_next_transition_none_on_human_gate():
    tasks = [
        {"id": 9, "name": "en analisis", "priority": "0", "sequence": 1,
         "stage_id": [13, "Análisis/Diseño"], "date_deadline": False},
    ]
    _install(_FakeRecommend(tasks))
    try:
        result = server.recommend_tasks("test", "Alpha")
    finally:
        _uninstall()
    assert result[0]["next_ai_transition"] is None  # human gate


def test_recommend_tasks_limit():
    _install(_FakeRecommend(_recommend_tasks_fixture()))
    try:
        result = server.recommend_tasks("test", "Alpha", limit=2)
    finally:
        _uninstall()
    assert [t["id"] for t in result] == [2, 3]


def test_recommend_tasks_empty():
    _install(_FakeRecommend([]))
    try:
        assert server.recommend_tasks("test", "Nada") == []
    finally:
        _uninstall()


# --- current_task --------------------------------------------------------

# Stage catalog for current_task: adds the AI in-flight stages with sequences.
_CT_STAGE_TYPES = {
    20: ("Aprobado", 2, False),
    21: ("Desarrollo", 3, False),
    22: ("Prueba", 4, False),
    23: ("PR/Review", 5, False),
    24: ("Hecho", 9, True),
    25: ("Análisis/Diseño", 1, False),
}


def _ct_stage_type_read(ids):
    return [
        {"id": i, "name": _CT_STAGE_TYPES[i][0], "sequence": _CT_STAGE_TYPES[i][1],
         "fold": _CT_STAGE_TYPES[i][2]}
        for i in ids
    ]


class _FakeCurrent:
    """execute_kw fake for current_task."""

    def __init__(self, tasks):
        self._tasks = tasks

    def execute_kw(self, model, method, args, kwargs=None):
        if (model, method) == ("project.task", "search_read"):
            return self._tasks
        if (model, method) == ("project.task.type", "read"):
            return _ct_stage_type_read(args[0])
        raise AssertionError(f"unexpected call {model}.{method}")


def _current_tasks_fixture():
    return [
        {"id": 1, "name": "en dev", "priority": "0", "stage_id": [21, "Desarrollo"],
         "project_id": [1, "Plantilla"], "date_deadline": False,
         "write_date": "2026-07-06 10:00:00"},
        {"id": 2, "name": "en prueba vieja", "priority": "1", "stage_id": [22, "Prueba"],
         "project_id": [1, "Plantilla"], "date_deadline": False,
         "write_date": "2026-07-01 09:00:00"},
        {"id": 3, "name": "en pr", "priority": "0", "stage_id": [23, "PR/Review"],
         "project_id": [1, "Plantilla"], "date_deadline": "2026-07-10",
         "write_date": "2026-07-05 08:00:00"},
        {"id": 4, "name": "aprobada, aún no en curso", "priority": "0",
         "stage_id": [20, "Aprobado"], "project_id": [1, "Plantilla"],
         "date_deadline": False, "write_date": "2026-07-06 11:00:00"},
        {"id": 5, "name": "ya hecha", "priority": "0", "stage_id": [24, "Hecho"],
         "project_id": [1, "Plantilla"], "date_deadline": False,
         "write_date": "2026-07-06 12:00:00"},
    ]


def test_current_task_only_inflight_stages_ordered():
    _install(_FakeCurrent(_current_tasks_fixture()))
    try:
        result = server.current_task("test")
    finally:
        _uninstall()
    # Excludes Aprobado (4) and Hecho (5); order by stage.sequence DESC:
    # PR/Review(5) > Prueba(4) > Desarrollo(3).
    assert [t["id"] for t in result] == [3, 2, 1]


def test_current_task_write_date_tiebreak_within_stage():
    tasks = [
        {"id": 10, "name": "dev vieja", "priority": "0", "stage_id": [21, "Desarrollo"],
         "project_id": [1, "P"], "date_deadline": False, "write_date": "2026-07-01 00:00:00"},
        {"id": 11, "name": "dev reciente", "priority": "0", "stage_id": [21, "Desarrollo"],
         "project_id": [1, "P"], "date_deadline": False, "write_date": "2026-07-06 00:00:00"},
    ]
    _install(_FakeCurrent(tasks))
    try:
        result = server.current_task("test")
    finally:
        _uninstall()
    # same stage.sequence -> write_date DESC (most recent first)
    assert [t["id"] for t in result] == [11, 10]


def test_current_task_reason_and_next_transition():
    _install(_FakeCurrent(_current_tasks_fixture()))
    try:
        result = server.current_task("test")
    finally:
        _uninstall()
    by_id = {t["id"]: t for t in result}
    assert by_id[3]["stage"] == "PR/Review"
    assert by_id[3]["next_ai_transition"] is None  # PR/Review -> human gate (merge)
    assert "vence 2026-07-10" in by_id[3]["reason"]
    assert by_id[2]["next_ai_transition"] == "PR/Review"  # Prueba -> PR/Review
    assert "importante ⭐" in by_id[2]["reason"]
    assert by_id[1]["next_ai_transition"] == "Prueba"  # Desarrollo -> Prueba
    assert by_id[1]["project"] == "Plantilla"


def test_current_task_empty_when_no_tasks():
    _install(_FakeCurrent([]))
    try:
        assert server.current_task("test") == []
    finally:
        _uninstall()


def test_current_task_empty_when_none_inflight():
    tasks = [
        {"id": 1, "name": "aprobada", "priority": "0", "stage_id": [20, "Aprobado"],
         "project_id": [1, "P"], "date_deadline": False, "write_date": "2026-07-06 00:00:00"},
    ]
    _install(_FakeCurrent(tasks))
    try:
        assert server.current_task("test") == []
    finally:
        _uninstall()
