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
