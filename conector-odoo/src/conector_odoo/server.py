"""Servidor MCP (stdio) que expone herramientas de gestión de tareas Odoo."""

import base64
import mimetypes
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


def _get_client(profile):
    """Return a cached authenticated client for the given profile name."""
    if profile not in _CLIENTS:
        _CLIENTS[profile] = OdooClient.from_profile(profile)
    return _CLIENTS[profile]


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
    message_id = client.execute_kw(
        "project.task",
        "message_post",
        [[task_id]],
        {"body": body, "message_type": "comment"},
    )
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
    client.execute_kw(
        "project.task",
        "message_post",
        [[task_id]],
        {
            "body": f"Documento adjuntado: {path.name}",
            "message_type": "comment",
            "attachment_ids": [attachment_id],
        },
    )
    return {"task_id": task_id, "attachment_id": attachment_id, "name": path.name}


def main():
    """Punto de entrada del servidor MCP por stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
