# Fase 5 — Flujo de desarrollo IA (workflows por etapa)

**Objetivo**: automatizar el ciclo de una tarea con gates humanos. Cada workflow = skill/comando SDD que la IA ejecuta al recibir la orden.

## 5.1 Análisis y diseño (`/tarea-diseno <task_id>`)

1. Leer tarea vía MCP conector (F3).
2. Explorar el repo objetivo (subagente barato) y validar **factibilidad**.
3. Generar `docs/tareas/<task_id>/design.md` según `../estandares/plantilla-diseno.md`: factibilidad, alcance, diseño técnico, riesgos, plan de prueba.
4. Adjuntar/comentar el diseño en la tarea Odoo. (La tarea debe estar ya en `Análisis/Diseño` — moverla desde `Backlog` es acción humana.)
5. ⛔ **Gate humano**: aprueba → humano mueve a `Aprobado`; rechaza → feedback en la tarea, la IA re-analiza.

## 5.2 Desarrollo (`/tarea-dev <task_id>`)

1. Verificar etapa = `Aprobado` (si no, abortar).
2. Rama desde la principal actualizada: `<tipo>/<task_id>-<slug>` (ej. `fix/1234-ir3-descuadre`). **Nunca trabajar en main/master** — ver `../estandares/git-commits.md`.
3. Implementar según design.md. Commits convencionales estilo Odoo, **sin firma de IA**.
4. Levantar entorno de la versión correspondiente (F4) y verificar que arranca sin errores + tests del módulo.
5. Mover tarea a `Desarrollo` al iniciar; comentar avances relevantes.

## 5.3 Prueba documentada (`/tarea-prueba <task_id>`)

1. Crear BD de prueba `test_<task_id>` con datos semilla necesarios.
2. Ejecutar el plan de prueba del design.md.
3. Generar manual paso a paso con capturas usando manual-generator (F6), según `../estandares/plantilla-manual-prueba.md`. Salida: `docs/tareas/<task_id>/manual-prueba.md` + imágenes.
4. Adjuntar manual a la tarea; mover a `Prueba`.
5. ⛔ **Gate humano**: test funcional. Falla → feedback, la IA vuelve a 5.2. Pasa → orden de PR.

## 5.4 PR (`/tarea-pr <task_id>`)

1. Push de la rama al remoto correcto (cuenta SSH según el repo).
2. Crear PR: título = primera línea del commit principal; cuerpo = resumen del design + enlace al manual de prueba. Sin firma de IA.
3. Mover tarea a `PR/Review` con enlace al PR.
4. ⛔ **Gate humano**: review, merge y deploy.

## 5.5 Cierre (`/tarea-close <task_id>`)

1. Tras el **merge humano** del PR, verificar que el PR está mergeado (`gh pr list --head <rama>`); si no, abortar y pedir el merge.
2. Cambiar el repo local a la rama principal actualizada (`git checkout <principal> && git pull --ff-only`) y borrar la rama local de la tarea con salvaguarda (`git branch -d`, nunca `-D`; el squash-merge requiere confirmación humana).
3. Limpiar el marcador de tarea activa (`docs/tareas/.current`) y comentar el cierre en la tarea.
4. Registrar en Engram lo aprendido (decisiones, gotchas del módulo) para futuras tareas.
5. ⛔ **Gate humano**: mover a `Hecho`, deploy y borrado de la rama remota. La IA solo hace limpieza local tras confirmar el merge.

## Criterio de salida de la fase

Los 4 workflows implementados como skills/comandos y probados con una tarea dummy. Marcar en ROADMAP.
