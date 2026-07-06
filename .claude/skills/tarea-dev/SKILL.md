---
name: tarea-dev
description: "Trigger: /tarea-dev <task_id>, desarrollar tarea, implementar tarea aprobada, workflow 5.2. Implementa el design.md en rama propia, levanta entorno F4 y pasa tests del módulo."
license: Apache-2.0
metadata:
  author: lfernandez
  version: "1.0"
---

# Tarea — Desarrollo (workflow 5.2)

## Precondiciones

- Tarea en etapa `Aprobado` (gate de diseño superado por el humano).
- `docs/tareas/<task_id>/design.md` existe y está aprobado — es contrato: cambios de alcance se comentan en la tarea ANTES de implementarse.

## Pasos

1. `get_task(task_id)` (MCP `gestor-odoo`). Si la etapa NO es `Aprobado`: **abortar** — `comment_task` con el motivo ("la tarea está en `<etapa>`; este workflow requiere `Aprobado`") además de reportar al humano. No mover nada.
2. `move_task` a `Desarrollo`. Escribir el marcador de tarea activa (vista pasiva de la statusline de terminal): `bash .claude/marca-tarea.sh <task_id> "<nombre>" Desarrollo dev`. Es un fichero local `docs/tareas/.current` (gitignored) que lee `.claude/statusline-tarea.sh`; no llama a Odoo. La fuente de verdad para consultas sigue siendo la herramienta MCP `current_task`.
3. En el repo objetivo (según `Alcance técnico` de la tarea), verificar primero `git remote -v`: si no hay remoto configurado, **abortar** (`comment_task` con el motivo) y pedir al humano configurar el remoto/cuenta SSH. Con remoto OK, crear rama desde la principal actualizada — nunca `main`/`master`/`17.0`/`19.0` directo; ver [git-commits](../../../docs/estandares/git-commits.md):
   ```bash
   git fetch && git checkout -b <tipo>/<task_id>-<slug> origin/<rama-base>
   ```
   Ej.: `fix/1234-ir3-descuadre`.
4. Implementar según design.md. Trabajo tier Medio (`sonnet`) — ver [modelos-por-proceso](../../../docs/estandares/modelos-por-proceso.md). Escalar a tier Potente (`opus`) si el design.md marca alta complejidad (repo/módulo desconocido, trade-offs, diff esperado > 400 líneas); dejar la decisión trazable en la tarea.
5. Entorno de la versión correspondiente ([GUIA-AGENTES](../../../entornos/GUIA-AGENTES.md)): si el entorno del repo/versión ya existe → solo §2 (up/logs); si no existe → generarlo con §1 **SIN `--force`**. NUNCA `--force` sobre un entorno existente. Verificar arranque sin errores + tests del módulo (§4). Respetar salvaguardas §0. Nota: §4 puede dejar creada la BD `test_<task_id>`; `/tarea-prueba` la recreará limpia.
6. Commits convencionales estilo Odoo (`tipo(modulo): descripción` + cuerpo técnico), **sin firma de IA**. Para formato y límite de asunto manda [git-commits](../../../docs/estandares/git-commits.md) del repo (≤ ~72 chars); el skill global `commit` es dependencia opcional para reforzar "sin firma IA" — regla ya garantizada por git-commits.md. Un commit = un cambio lógico.
7. `comment_task` con avance relevante: rama creada, qué se implementó, resultado de tests.
8. Registrar en engram (`mem_save`, project `odoo-ai-ecosystem`): decisiones de implementación y gotchas del módulo.

## Gate humano

⛔ NO mover a `Prueba` desde aquí (eso lo hace `/tarea-prueba`), NO push ni PR, NO mergear, NO deploy. Si el design.md resulta inviable durante el desarrollo, comentar en la tarea y esperar decisión humana.
