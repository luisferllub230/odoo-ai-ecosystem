# Fase 3 — Conector Odoo (RPC / API key / MCP)

**Objetivo**: puente entre la capa IA y **cualquier** Odoo (el gestor local u otros), configurable por perfiles.

## Diseño

- Carpeta `conector-odoo/`. Python (xmlrpc está en stdlib; JSON-RPC como alternativa).
- Config por perfiles en `profiles.yml` (o `.env`):
  ```yaml
  gestor:
    url: http://localhost:8169
    db: gestor
    user: ai-agent@local
    api_key: ${GESTOR_API_KEY}   # desde entorno, nunca en git
  cliente_x:
    url: https://odoo.clientex.com
    ...
  ```
- **Servidor MCP** (stdio) que expone herramientas al agente:
  - `list_projects(profile)` — proyectos con conteo de tareas (total y abiertas).
  - `list_tasks(profile, project, stage)` — tareas por etapa.
  - `recommend_tasks(profile, project, limit)` — tareas trabajables priorizadas y explicadas.
  - `get_task(profile, task_id)` — descripción completa + adjuntos.
  - `move_task(profile, task_id, stage)` — solo etapas permitidas a la IA (ver F2).
  - `comment_task(profile, task_id, body)` — bitácora de avances.
  - `attach_doc(profile, task_id, file)` — subir design.md / manual de prueba.

## Pasos

1. Cliente RPC mínimo + perfiles (probar `common.authenticate` y `execute_kw` sobre `project.task`).
2. Envolver como MCP server (SDK oficial MCP Python) con las herramientas.
3. Registrar el MCP en Claude Code (`claude mcp add`) / config gentle-ai.
4. Prueba end-to-end: el agente lee la tarea de prueba creada en F2 y le agrega un comentario.

## Criterio de salida

Agente lee/comenta/mueve tareas del gestor vía MCP usando solo la API key. Cambiar de Odoo = cambiar perfil. Marcar en ROADMAP.
