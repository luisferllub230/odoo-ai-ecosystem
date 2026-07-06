#!/usr/bin/env bash
# Statusline de Claude Code: muestra la tarea con la que la sesión está iterando.
#
# Lee un marcador LOCAL (docs/tareas/.current, JSON {task_id,name,stage,phase})
# escrito por los skills de fase (tarea-diseno/dev/prueba/pr). No llama a Odoo:
# la statusline se refresca en cada prompt y no debe meter latencia de red. La
# fuente de verdad para consultas sigue siendo la herramienta MCP current_task.
#
# Claude Code pasa por stdin un JSON con workspace.project_dir; de ahí se calcula
# la ruta del marcador (independiente del cwd). Sin marcador → no imprime nada.

# Claude pasa el JSON por stdin; se captura ANTES de invocar python, porque el
# heredoc ya ocupa el stdin de python (python3 <<'PY' lee el programa de ahí).
input="$(cat)"

CLAUDE_STATUSLINE_INPUT="$input" python3 <<'PY'
import json
import os
import sys
from pathlib import Path

try:
    payload = json.loads(os.environ.get("CLAUDE_STATUSLINE_INPUT") or "{}")
except (json.JSONDecodeError, ValueError):
    payload = {}

workspace = payload.get("workspace") or {}
project_dir = workspace.get("project_dir") or workspace.get("current_dir") or "."
marker = Path(project_dir) / "docs" / "tareas" / ".current"

try:
    data = json.loads(marker.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError):
    sys.exit(0)  # sin marcador o ilegible: silencio, sin ruido

task_id = data.get("task_id")
name = (data.get("name") or "").strip()
stage = (data.get("stage") or "").strip()
if task_id is None and not name:
    sys.exit(0)

label = f"#{task_id}" if task_id is not None else "#?"
if name:
    label += f" {name}"
if stage:
    label += f" · {stage}"
print(label)
PY
