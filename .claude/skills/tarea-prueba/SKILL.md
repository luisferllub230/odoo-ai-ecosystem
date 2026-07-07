---
name: tarea-prueba
description: "Trigger: /tarea-prueba <task_id>, probar tarea, manual de prueba, workflow 5.3. Crea BD test_<task_id>, ejecuta el plan de prueba del design.md y genera el manual para el gate de test funcional."
license: Apache-2.0
metadata:
  author: lfernandez
  version: "1.0"
---

# Tarea — Prueba documentada (workflow 5.3)

## Precondiciones

- Tarea en etapa `Desarrollo` con implementación terminada y tests del módulo en verde (`/tarea-dev` completado).
- `docs/tareas/<task_id>/design.md` con sección "Plan de prueba".
- Entorno de la tarea operativo (F4).
- Workflow guionizado sobre datos conocidos: tier Compacto (`haiku`) — ver [modelos-por-proceso](../../../docs/estandares/modelos-por-proceso.md).

## Pasos

1. `get_task(task_id)` (MCP `gestor-odoo`) y verificar etapa `Desarrollo`; si no, **abortar** — `comment_task` con el motivo además de reportar al humano.
2. BD de prueba `test_<task_id>` con los comandos exactos de [GUIA-AGENTES](../../../entornos/GUIA-AGENTES.md) §3. Si ya existe (los tests de `/tarea-dev` §4 pueden haberla creado), recrearla limpia: `dropdb --if-exists` + `createdb`, luego cargar los datos semilla. Respetar salvaguardas §0: nada destructivo fuera del entorno de la tarea; `dropdb` solo `--if-exists` sobre `test_*` propios tras verificar con `psql -l`.
3. Ejecutar el plan de prueba del design.md escenario por escenario, registrando resultados y evidencia.
4. Generar `docs/tareas/<task_id>/manual-prueba.md` + carpeta `img/` rellenando [plantilla-manual-prueba](../../../docs/estandares/plantilla-manual-prueba.md). Cada criterio de aceptación cubierto por ≥1 escenario; pasos reproducibles desde cero. Capturas automáticas con [manual-generator](../../../manual-generator/README.md) (F6):
   1. Escribir el escenario `docs/tareas/<task_id>/escenario.json` (formato en el README de manual-generator; opcional `escenario.seed.py` para datos semilla vía odoo shell) con un flujo por pantalla del plan de prueba.
   2. Ejecutar (password de la UI SOLO por env, nunca en el JSON ni en flags):
      ```bash
      cd /home/lfernandez/repos/odoo-ai-ecosystem/manual-generator
      export ODOO_UI_PASSWORD=<password_ui>   # admin/admin si la BD la creó el CLI
      npx manual-gen run --config <repo>/docs/tareas/<task_id>/escenario.json \
          --url http://localhost:<puerto_F4> --db test_<task_id> --user admin \
          --compose-dir <dir_entorno_F4> --out <repo>/docs/tareas/<task_id>/
      ```
      (o `--profile <perfil>` si la instancia está en `conector-odoo/profiles.yml`). Salida: `manual-<module>.md` + `img/*.png` con rutas relativas.
   3. Verificar exit 0 y que cada PNG referenciado existe; integrar las capturas/las secciones generadas en `manual-prueba.md`. Si alguna pantalla no se puede automatizar, capturarla manualmente o dejar placeholder `img/eN-pM.png` anotado en el manual.
5. `attach_doc` con el manual a la tarea.
6. `move_task` a `Prueba` + `comment_task` con resumen de escenarios ejecutados y resultado. Actualizar el marcador de tarea activa: `bash .claude/marca-tarea.sh <task_id> "<nombre>" Prueba prueba` (statusline de terminal; ver `tarea-dev`).
7. Registrar en engram (`mem_save`, project `odoo-ai-ecosystem`): gotchas de la prueba, datos semilla no obvios, casos borde.

## Gate humano

⛔ El humano ejecuta el test funcional. Si falla → feedback en la tarea y el ciclo vuelve a `/tarea-dev`; si pasa → el humano da la orden de PR. NO mover a `PR/Review`, NO push, NO crear PR sin esa orden.
