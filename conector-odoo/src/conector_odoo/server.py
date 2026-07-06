"""Servidor MCP (stdio) que expone herramientas de gestión de tareas Odoo."""

import base64
import html
import mimetypes
import re
from html.parser import HTMLParser
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .client import OdooClient, OdooError

mcp = FastMCP("conector-odoo")

_CLIENTS = {}

# Transitions the AI is allowed to perform (casefolded stage names).
# Everything else is guarded by a human gate (see docs/estandares/plantilla-tarea.md).
ALLOWED_TRANSITIONS = {
    ("aprobado", "desarrollo"),
    ("desarrollo", "prueba"),
    ("prueba", "pr/review"),
}

# Display name of the single next stage the AI may advance to from each stage.
# Must stay in sync with ALLOWED_TRANSITIONS (keys are normalized stage names).
_AI_NEXT_STAGE = {
    "aprobado": "Desarrollo",
    "desarrollo": "Prueba",
    "prueba": "PR/Review",
}

_HUMAN_GATES_MSG = (
    "Transición no permitida a la IA: '{current}' -> '{target}'. "
    "La IA solo puede mover: Aprobado->Desarrollo, Desarrollo->Prueba, Prueba->PR/Review. "
    "Las demás transiciones son gates humanos: Backlog->Análisis/Diseño (orden de analizar), "
    "Análisis/Diseño->Aprobado (aprobación de diseño) y PR/Review->Hecho (merge + deploy)."
)


def _norm(stage_name):
    """Normalize a stage name for comparison."""
    return (stage_name or "").strip().casefold()


def validate_transition(current_stage, target_stage):
    """Valida el guard de transiciones; lanza OdooError si no está permitida a la IA."""
    if (_norm(current_stage), _norm(target_stage)) not in ALLOWED_TRANSITIONS:
        raise OdooError(_HUMAN_GATES_MSG.format(current=current_stage, target=target_stage))


class _HTMLToText(HTMLParser):
    """Minimal HTML to plain-text converter (stdlib only)."""

    _BREAK_TAGS = {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__()
        self._chunks = []

    def handle_data(self, data):
        self._chunks.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in self._BREAK_TAGS:
            self._chunks.append("\n")

    def text(self):
        raw = "".join(self._chunks)
        lines = [ln.strip() for ln in raw.splitlines()]
        return "\n".join(ln for ln in lines if ln)


def html_to_text(html):
    """Convierte HTML de Odoo a texto plano legible."""
    if not html:
        return ""
    parser = _HTMLToText()
    parser.feed(html)
    return parser.text()


# Known HTML tags that mark a body as already-formatted (passthrough).
_HTML_TAG_RE = re.compile(
    r"<(/?)(p|br|ul|ol|li|b|i|strong|em|h[1-6]|div|a|code|pre)\b", re.I
)


def _is_bullet_line(line):
    """True if a line starts (after indentation) with a simple bullet marker."""
    return line.lstrip()[:2] in ("- ", "* ")


def _block_to_html(block):
    """Render one text block (no blank lines) as a <ul> list or a <p> paragraph."""
    lines = block.split("\n")
    if all(_is_bullet_line(ln) for ln in lines):
        items = "".join(
            f"<li>{html.escape(ln.lstrip()[2:].strip())}</li>" for ln in lines
        )
        return f"<ul>{items}</ul>"
    return "<p>" + "<br>".join(html.escape(ln) for ln in lines) + "</p>"


def text_to_html(body):
    """Convierte texto plano a HTML legible para el chatter de Odoo.

    Odoo renderiza el body del chatter como HTML, así que el texto plano con
    saltos de línea se colapsa y sale "todo junto". Esta función formatea:
    párrafos (separados por líneas en blanco), saltos de línea (``<br>``) y
    listas simples (líneas ``- ``/``* ``). Si el body ya contiene HTML conocido
    se devuelve sin cambios (passthrough) para no doble-escapar.
    """
    if not body:
        return body or ""
    if _HTML_TAG_RE.search(body):
        return body
    normalized = body.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", normalized.strip())
    return "".join(_block_to_html(b) for b in blocks if b.strip())


def _post_message(client, task_id, body, attachment_ids=None):
    """Publica un mensaje HTML en el chatter de una tarea y devuelve su id.

    Odoo 16+ representa los campos HTML con ``markupsafe.Markup``: ``message_post``
    ESCAPA un ``body`` que llega como ``str`` plano (lo que siempre ocurre vía
    XML-RPC, que no puede transportar ``Markup``), y el chatter muestra las
    etiquetas literales. Solución: publicar y luego reescribir el ``body`` del
    mensaje con ``mail.message.write``, que sí acepta HTML como ``str`` sin
    escaparlo. Antes se normaliza el texto plano a HTML con ``text_to_html``.
    """
    html_body = text_to_html(body)
    kwargs = {"body": html_body, "message_type": "comment"}
    if attachment_ids:
        kwargs["attachment_ids"] = attachment_ids
    posted = client.execute_kw("project.task", "message_post", [[task_id]], kwargs)
    ids = posted if isinstance(posted, list) else [posted]
    client.execute_kw("mail.message", "write", [ids, {"body": html_body}])
    return posted


def _get_client(profile):
    """Return a cached authenticated client for the given profile name."""
    if profile not in _CLIENTS:
        _CLIENTS[profile] = OdooClient.from_profile(profile)
    return _CLIENTS[profile]


def _as_int(value):
    """Coerce Odoo selection/int values (e.g. priority '0'/'1') to int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _stage_meta(client, stage_ids):
    """Read name/sequence/fold for the given project.task.type ids."""
    if not stage_ids:
        return {}
    types = client.execute_kw(
        "project.task.type",
        "read",
        [list(stage_ids)],
        {"fields": ["id", "name", "sequence", "fold"]},
    )
    return {
        t["id"]: {
            "name": t["name"],
            "sequence": t.get("sequence") or 0,
            "fold": bool(t.get("fold")),
        }
        for t in types
    }


def _next_ai_transition(stage_name):
    """Return the next stage the AI may move to per the guard, else None (human gate)."""
    return _AI_NEXT_STAGE.get(_norm(stage_name))


def _build_reason(task, stage_meta):
    """Human-readable explanation of why a task ranks where it does."""
    parts = []
    if _as_int(task.get("priority")) > 0:
        parts.append("importante ⭐")
    if task.get("date_deadline"):
        parts.append(f"vence {task['date_deadline']}")
    parts.append(f"etapa {stage_meta['name']}")
    return "; ".join(parts)


@mcp.tool()
def list_tasks(profile: str, project: str | None = None, stage: str | None = None) -> list:
    """Lista tareas del Odoo del perfil indicado.

    Devuelve id, nombre, etapa y proyecto de cada tarea. Se puede filtrar
    opcionalmente por nombre de proyecto y/o nombre de etapa.
    """
    client = _get_client(profile)
    domain = []
    if project:
        domain.append(("project_id.name", "ilike", project))
    if stage:
        domain.append(("stage_id.name", "ilike", stage))
    tasks = client.execute_kw(
        "project.task",
        "search_read",
        [domain],
        {"fields": ["id", "name", "stage_id", "project_id"], "order": "project_id, stage_id, id"},
    )
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "stage": t["stage_id"][1] if t["stage_id"] else None,
            "project": t["project_id"][1] if t["project_id"] else None,
        }
        for t in tasks
    ]


@mcp.tool()
def list_projects(profile: str) -> list:
    """Lista los proyectos disponibles con conteo de tareas.

    Devuelve por proyecto: id, name, task_count (todas) y open_task_count
    (excluye tareas en etapas plegadas fold=True, típicamente Hecho/Cancelado).
    Orden alfabético por nombre.
    """
    client = _get_client(profile)
    projects = client.execute_kw(
        "project.project",
        "search_read",
        [[]],
        {"fields": ["id", "name"], "order": "name"},
    )
    if not projects:
        return []
    project_ids = [p["id"] for p in projects]
    tasks = client.execute_kw(
        "project.task",
        "search_read",
        [[("project_id", "in", project_ids)]],
        {"fields": ["id", "project_id", "stage_id"]},
    )
    stage_ids = sorted({t["stage_id"][0] for t in tasks if t["stage_id"]})
    folded = {sid for sid, m in _stage_meta(client, stage_ids).items() if m["fold"]}
    counts = {pid: [0, 0] for pid in project_ids}  # [total, open]
    for t in tasks:
        pid = t["project_id"][0] if t["project_id"] else None
        if pid not in counts:
            continue
        counts[pid][0] += 1
        sid = t["stage_id"][0] if t["stage_id"] else None
        if sid not in folded:
            counts[pid][1] += 1
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "task_count": counts[p["id"]][0],
            "open_task_count": counts[p["id"]][1],
        }
        for p in projects
    ]


@mcp.tool()
def recommend_tasks(profile: str, project: str, limit: int = 10) -> list:
    """Devuelve las tareas trabajables de un proyecto, priorizadas y explicadas.

    Excluye tareas en etapas plegadas (fold=True). Orden: priority DESC
    (importancia), date_deadline ASC (vencimiento, nulos al final),
    stage.sequence DESC (avanzar lo más adelantado), sequence ASC, id ASC.
    Cada tarea incluye 'reason' legible y 'next_ai_transition' (la etapa a la
    que la IA puede avanzar según el guard, o None si el siguiente paso es un
    gate humano).
    """
    client = _get_client(profile)
    tasks = client.execute_kw(
        "project.task",
        "search_read",
        [[("project_id.name", "ilike", project)]],
        {
            "fields": [
                "id", "name", "priority", "sequence",
                "stage_id", "date_deadline",
            ]
        },
    )
    if not tasks:
        return []
    stage_ids = sorted({t["stage_id"][0] for t in tasks if t["stage_id"]})
    stage_meta = _stage_meta(client, stage_ids)
    workable = [
        t for t in tasks
        if t["stage_id"] and not stage_meta[t["stage_id"][0]]["fold"]
    ]

    def sort_key(t):
        meta = stage_meta[t["stage_id"][0]]
        return (
            -_as_int(t.get("priority")),
            t.get("date_deadline") or "9999-12-31",
            -meta["sequence"],
            t.get("sequence") or 0,
            t["id"],
        )

    workable.sort(key=sort_key)
    result = []
    for t in workable[: max(limit, 0)]:
        meta = stage_meta[t["stage_id"][0]]
        result.append(
            {
                "id": t["id"],
                "name": t["name"],
                "priority": _as_int(t.get("priority")),
                "stage": meta["name"],
                "stage_sequence": meta["sequence"],
                "date_deadline": t.get("date_deadline") or None,
                "reason": _build_reason(t, meta),
                "next_ai_transition": _next_ai_transition(meta["name"]),
            }
        )
    return result


@mcp.tool()
def get_task(profile: str, task_id: int) -> dict:
    """Obtiene el detalle completo de una tarea.

    Incluye descripción (convertida a texto), etapa, asignados, lista de
    adjuntos (id y nombre) y los últimos mensajes/comentarios de la bitácora.
    """
    client = _get_client(profile)
    records = client.execute_kw(
        "project.task",
        "read",
        [[task_id]],
        {"fields": ["id", "name", "description", "stage_id", "project_id", "user_ids"]},
    )
    if not records:
        raise OdooError(f"La tarea {task_id} no existe en el perfil '{profile}'")
    task = records[0]

    assignees = []
    if task.get("user_ids"):
        users = client.execute_kw(
            "res.users", "read", [task["user_ids"]], {"fields": ["name"]}
        )
        assignees = [u["name"] for u in users]

    attachments = client.execute_kw(
        "ir.attachment",
        "search_read",
        [[("res_model", "=", "project.task"), ("res_id", "=", task_id)]],
        {"fields": ["id", "name"]},
    )

    messages = client.execute_kw(
        "mail.message",
        "search_read",
        [[("model", "=", "project.task"), ("res_id", "=", task_id)]],
        {"fields": ["date", "author_id", "body", "message_type"], "order": "date desc", "limit": 10},
    )

    return {
        "id": task["id"],
        "name": task["name"],
        "project": task["project_id"][1] if task["project_id"] else None,
        "stage": task["stage_id"][1] if task["stage_id"] else None,
        "assignees": assignees,
        "description": html_to_text(task.get("description")),
        "attachments": [{"id": a["id"], "name": a["name"]} for a in attachments],
        "messages": [
            {
                "date": m["date"],
                "author": m["author_id"][1] if m["author_id"] else None,
                "type": m["message_type"],
                "body": html_to_text(m["body"]),
            }
            for m in messages
        ],
    }


@mcp.tool()
def move_task(profile: str, task_id: int, stage: str) -> dict:
    """Mueve una tarea a otra etapa, respetando los gates humanos.

    La IA solo puede ejecutar: Aprobado->Desarrollo, Desarrollo->Prueba y
    Prueba->PR/Review. Cualquier otra transición se rechaza con un error que
    indica qué gate humano corresponde. La etapa destino se busca por nombre
    dentro del proyecto de la tarea.
    """
    client = _get_client(profile)
    records = client.execute_kw(
        "project.task",
        "read",
        [[task_id]],
        {"fields": ["name", "stage_id", "project_id"]},
    )
    if not records:
        raise OdooError(f"La tarea {task_id} no existe en el perfil '{profile}'")
    task = records[0]
    current_stage = task["stage_id"][1] if task["stage_id"] else ""
    if not task["project_id"]:
        raise OdooError(f"La tarea {task_id} no pertenece a ningún proyecto")
    project_id, project_name = task["project_id"]

    validate_transition(current_stage, stage)

    stages = client.execute_kw(
        "project.task.type",
        "search_read",
        [[("project_ids", "in", [project_id])]],
        {"fields": ["id", "name"]},
    )
    target = next((s for s in stages if _norm(s["name"]) == _norm(stage)), None)
    if target is None:
        names = ", ".join(s["name"] for s in stages)
        raise OdooError(
            f"La etapa '{stage}' no existe en el proyecto '{project_name}'. Etapas: {names}"
        )

    client.execute_kw("project.task", "write", [[task_id], {"stage_id": target["id"]}])
    return {
        "id": task_id,
        "name": task["name"],
        "from_stage": current_stage,
        "to_stage": target["name"],
    }


@mcp.tool()
def comment_task(profile: str, task_id: int, body: str) -> dict:
    """Agrega un comentario a la bitácora (chatter) de la tarea."""
    client = _get_client(profile)
    message_id = _post_message(client, task_id, body)
    return {"task_id": task_id, "message_id": message_id}


@mcp.tool()
def attach_doc(profile: str, task_id: int, file_path: str) -> dict:
    """Sube un archivo local como adjunto de la tarea y lo referencia en la bitácora.

    Útil para adjuntar design.md, manuales de prueba u otros entregables.
    """
    client = _get_client(profile)
    path = Path(file_path)
    if not path.is_file():
        raise OdooError(f"El archivo '{file_path}' no existe o no es un archivo")
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    mimetype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    attachment_id = client.execute_kw(
        "ir.attachment",
        "create",
        [
            {
                "name": path.name,
                "res_model": "project.task",
                "res_id": task_id,
                "datas": data,
                "mimetype": mimetype,
            }
        ],
    )
    _post_message(
        client,
        task_id,
        f"Documento adjuntado: {path.name}",
        attachment_ids=[attachment_id],
    )
    return {"task_id": task_id, "attachment_id": attachment_id, "name": path.name}


def main():
    """Punto de entrada del servidor MCP por stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
