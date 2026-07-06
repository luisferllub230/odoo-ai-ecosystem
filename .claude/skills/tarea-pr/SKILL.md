---
name: tarea-pr
description: "Trigger: /tarea-pr <task_id>, crear PR de tarea, abrir pull request, workflow 5.4. Push de la rama al remoto correcto, PR sin firma de IA y tarea a PR/Review con el enlace."
license: Apache-2.0
metadata:
  author: lfernandez
  version: "1.0"
---

# Tarea — PR (workflow 5.4)

## Precondiciones

- Tarea en etapa `Prueba` y el humano dio la orden de PR (gate de test funcional superado).
- Tests del módulo en verde y `docs/tareas/<task_id>/manual-prueba.md` generado y adjunto a la tarea. Si algo de esto falta: **abortar** — `comment_task` con el motivo además de reportar al humano.

## Pasos

1. `get_task(task_id)` (MCP `gestor-odoo`): confirmar etapa `Prueba` y que el manual está adjunto.
2. Verificar tests verdes (re-ejecutar si hay dudas, comandos en [GUIA-AGENTES](../../../entornos/GUIA-AGENTES.md) §4).
3. Verificar `git remote -v` en el repo objetivo: si no hay remoto configurado, **abortar** (`comment_task` con el motivo) y pedir al humano configurar el remoto/cuenta SSH — no inventar remotos ni hosts. Con remoto OK, push de la rama `<tipo>/<task_id>-<slug>` por ese remoto/host SSH ya configurado (cuentas multi-SSH documentadas en [git-commits](../../../docs/estandares/git-commits.md)).
4. Crear el PR — con `gh pr create` si `gh` está autenticado para esa cuenta; si no, dar al humano la URL de "compare" para crearlo:
   - Título = primera línea del commit principal.
   - Cuerpo = qué/por qué (resumen del design.md) + cómo probar (enlace a `docs/tareas/<task_id>/manual-prueba.md`).
   - **Sin firma de IA**: nada de `Co-Authored-By: Claude` ni `Generated with Claude Code`.
5. `move_task` a `PR/Review` + `comment_task` con la URL del PR. Actualizar el marcador de tarea activa: `bash .claude/marca-tarea.sh <task_id> "<nombre>" "PR/Review" pr` (statusline de terminal; ver `tarea-dev`).
6. Registrar en engram (`mem_save`, project `odoo-ai-ecosystem`): cierre del ciclo, decisiones y gotchas aprendidos en la tarea (alimenta 5.5).

## Gate humano

⛔ Review, merge, deploy y borrado de rama son del humano. NO mergear, NO aprobar el propio PR, NO deploy, NO mover a `Hecho` (el guard de `move_task` además lo rechaza).
