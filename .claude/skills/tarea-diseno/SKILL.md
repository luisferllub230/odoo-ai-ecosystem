---
name: tarea-diseno
description: "Trigger: /tarea-diseno <task_id>, analizar tarea, diseñar tarea, workflow 5.1. Lee la tarea del gestor Odoo, valida la plantilla, explora el repo objetivo y genera design.md para aprobación humana."
license: Apache-2.0
metadata:
  author: lfernandez
  version: "1.0"
---

# Tarea — Análisis y diseño (workflow 5.1)

## Precondiciones

- `task_id` proporcionado por el humano.
- Si la etapa es `Aprobado`, `Desarrollo`, `Prueba` o `PR/Review`: **ABORTAR** con `comment_task` explicando que el diseño aprobado es contrato ([plantilla-diseno](../../../docs/estandares/plantilla-diseno.md)) y no se re-genera. Re-diseñar solo con orden humana explícita, y en ese caso versionar (`design-v2.md`, `design-v3.md`…), nunca sobrescribir `design.md`.
- Tarea idealmente en etapa `Análisis/Diseño`. Si está en `Backlog`, NO intentar moverla: el guard de `move_task` solo permite `Aprobado→Desarrollo→Prueba→PR/Review` y rechazará cualquier otra transición. NUNCA intentar bypass del guard: comentar en la tarea (`comment_task`) pidiendo al humano moverla a `Análisis/Diseño` y confirmar con él antes de continuar.

## Pasos

1. `get_task(task_id)` (MCP `gestor-odoo`). Anotar etapa, título y descripción. Si vas a analizar (etapa `Análisis/Diseño`, no un caso de abortar), escribir el marcador de tarea activa: `bash .claude/marca-tarea.sh <task_id> "<nombre>" "Análisis/Diseño" diseno` (fichero local `docs/tareas/.current`, gitignored, que lee `.claude/statusline-tarea.sh`; la fuente de verdad para consultas es la herramienta MCP `current_task`).
2. Validar campos obligatorios según [plantilla-tarea](../../../docs/estandares/plantilla-tarea.md): `Contexto`, `Objetivo`, `Repo`, `Rama base`, `Versión Odoo`, ≥1 criterio de aceptación. Si falta alguno: `comment_task` listando exactamente qué falta y **parar aquí**.
3. Explorar el repo objetivo (el de `Alcance técnico → Repo`) con un subagente `Explore` fijado a tier Medio (`sonnet`) — ver [modelos-por-proceso](../../../docs/estandares/modelos-por-proceso.md): módulos afectados, modelos, vistas, flujos existentes, referencias archivo:línea. Objetivo: validar **factibilidad**, no implementar.
4. Generar `docs/tareas/<task_id>/design.md` (en este repo) rellenando [plantilla-diseno](../../../docs/estandares/plantilla-diseno.md): factibilidad, análisis, diseño propuesto, alcance, riesgos, plan de prueba, estimación. Este análisis es trabajo tier Potente (`opus`) — ver [modelos-por-proceso](../../../docs/estandares/modelos-por-proceso.md). Si es NO FACTIBLE o ambigua, decirlo con preguntas concretas para el humano.
5. `attach_doc` con el design.md a la tarea + `comment_task` con resumen: veredicto de factibilidad, alcance y estimación.
6. Registrar en engram (`mem_save`, project `odoo-ai-ecosystem`): decisiones de diseño y gotchas del módulo descubiertos.

## Gate humano

⛔ El humano aprueba moviendo la tarea a `Aprobado` (o rechaza con feedback en la tarea → re-analizar). NO mover la tarea de etapa, NO empezar a implementar, NO crear ramas ni tocar el repo objetivo.
