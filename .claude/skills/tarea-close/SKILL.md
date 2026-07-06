---
name: tarea-close
description: "Trigger: /tarea-close <task_id>, cerrar tarea, cierre tras merge, volver a rama principal, workflow 5.5. Tras el merge humano: verifica PR mergeado, cambia el repo local a la rama principal actualizada, borra la rama local y limpia el marcador de tarea activa."
license: Apache-2.0
metadata:
  author: lfernandez
  version: "1.0"
---

# Tarea — Cierre (workflow 5.5)

Limpieza local **tras el merge humano**. Esta skill NO mergea, NO aprueba, NO
mueve a `Hecho`, NO borra la rama remota: todo eso es gate humano. Solo deja el
repo local ordenado en la rama principal para la siguiente tarea.

## Precondiciones

- Tarea en etapa `PR/Review` (o ya en `Hecho` si el humano la movió) con un PR
  abierto para la rama de la tarea.
- El humano dio la orden de cierre **después** de haber hecho el merge del PR.
- Workflow guionizado sobre datos conocidos: tier Compacto (`haiku`) — ver
  [modelos-por-proceso](../../../docs/estandares/modelos-por-proceso.md).

## Pasos

1. `get_task(task_id)` (MCP `gestor-odoo`): leer la etapa. Aceptable `PR/Review`
   o `Hecho`. Si está antes de `PR/Review` (no hay PR que cerrar): **abortar** —
   `comment_task` con el motivo y reportar al humano.
2. Localizar el PR de la rama de la tarea y verificar que está **mergeado**:
   ```bash
   gh pr list --head <tipo>/<task_id>-<slug> --state all \
       --json number,state,mergedAt,mergeCommit
   ```
   Si el PR **no** está `MERGED`: **abortar** — `comment_task` pidiendo al humano
   hacer el merge primero. **NUNCA** mergear ni aprobar el PR desde aquí.
3. Cambiar el repo local a la rama principal actualizada (la rama base de la tarea,
   normalmente `main` — ver [git-commits](../../../docs/estandares/git-commits.md)):
   ```bash
   git checkout <rama-principal>
   git pull --ff-only origin <rama-principal>
   ```
   Si hay cambios sin commitear que bloqueen el `checkout`: **parar** y avisar al
   humano. NO descartar ni stashear trabajo ajeno sin su orden.
4. Borrar la rama **local** de la tarea, ya mergeada, con salvaguarda:
   ```bash
   git branch -d <tipo>/<task_id>-<slug>     # -d, NUNCA -D
   git fetch --prune                          # limpia refs remotas ya borradas por GitHub
   ```
   Usar siempre `-d`: si git responde que la rama "no está mergeada" (típico en
   **merge por squash**, donde los commits difieren del historial de `main`),
   **parar** y confirmar con el humano —comparar contra el `mergeCommit` del paso 2—
   antes de considerar `-D`. El borrado de la rama **remota** es del humano/GitHub.
5. Limpiar el marcador de tarea activa (ya no hay tarea en curso en la terminal):
   ```bash
   rm -f docs/tareas/.current
   ```
6. `comment_task` confirmando el cierre local: PR mergeado, repo en `<rama-principal>`
   actualizada, rama local borrada. Si la tarea sigue en `PR/Review`, recordar que
   moverla a `Hecho` es gate humano — la IA NO lo hace (el guard de `move_task`
   además lo rechaza).
7. Registrar en engram (`mem_save`, project `odoo-ai-ecosystem`): cierre del ciclo,
   decisiones y gotchas aprendidos en la tarea (alimenta futuras tareas).

## Gate humano

⛔ Merge, aprobar el PR, mover a `Hecho`, deploy y borrado de la rama remota son del
humano. La IA solo ejecuta la limpieza local **después** de confirmar el merge.
