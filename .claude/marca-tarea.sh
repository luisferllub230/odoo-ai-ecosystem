#!/usr/bin/env bash
# Escribe el marcador local de tarea activa para la statusline de terminal.
#
# Uso:  bash .claude/marca-tarea.sh <task_id> <name> <stage> <phase>
#   task_id  id de la tarea en el gestor Odoo
#   name     título de la tarea
#   stage    etapa del tablero (Desarrollo/Prueba/PR/Review/Análisis-Diseño)
#   phase    fase del workflow (diseno|dev|prueba|pr)
#
# Lo llaman los skills de fase al empezar a iterar una tarea. El marcador vive en
# docs/tareas/.current (gitignored) para no ensuciar el repo. No hace red: es la
# vista pasiva de terminal; la fuente de verdad es la herramienta MCP current_task.

set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "uso: marca-tarea.sh <task_id> <name> <stage> [phase]" >&2
  exit 2
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dest="$root/docs/tareas/.current"
mkdir -p "$(dirname "$dest")"

TASK_ID="$1" NAME="$2" STAGE="$3" PHASE="${4:-}" python3 - "$dest" <<'PY'
import json
import os
import sys

dest = sys.argv[1]
data = {
    "task_id": int(os.environ["TASK_ID"]) if os.environ["TASK_ID"].isdigit() else os.environ["TASK_ID"],
    "name": os.environ["NAME"],
    "stage": os.environ["STAGE"],
    "phase": os.environ["PHASE"],
}
with open(dest, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False)
    fh.write("\n")
PY

echo "marcador escrito: $dest"
