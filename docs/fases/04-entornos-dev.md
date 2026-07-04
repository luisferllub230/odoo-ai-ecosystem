# Fase 4 — Entornos dev estandarizados (Docker)

**Objetivo**: que un agente pueda levantar/operar/destruir un entorno de la versión de Odoo que la tarea requiera, con un patrón único.

## Punto de partida (auditar primero)

- `~/repos/odoo_dev_env`: `bootstrap.sh` + `templates/` (Dockerfile, docker-compose) — patrón generador ya existente.
- `~/repos/odoo_pro_19` y `odoo_pro_17`: entornos vivos; compose con `${ODOO_DEVELOPER}`, `${ODOO_PORT}`, red externa `odoo_shared_network`, volúmenes enterprise/odoo-pro/conf.

## Pasos

1. **Auditoría**: comparar los tres repos; extraer qué es común (estructura compose, entrypoint, wait-for-psql, conf) y qué varía por versión (imagen base, requirements, rutas addons).
2. **`entornos/` en este repo**:
   - `base/Dockerfile` parametrizado (`ARG ODOO_VERSION`), o un Dockerfile por versión si divergen mucho.
   - `templates/docker-compose.yml` con variables: versión, puerto, nombre BD, rutas de addons del proyecto.
   - `bootstrap.sh <proyecto> <version>` — genera el entorno de un proyecto/tarea (evolución del de odoo_dev_env).
3. **Convenciones**:
   - Puertos: rango por versión (17→81xx, 19→82xx… definir tabla).
   - BD de prueba **por tarea**: `test_<tarea_id>` — se crea al iniciar prueba, se destruye al cerrar.
   - Red compartida `odoo_shared_network` para reutilizar un Postgres común en dev si conviene.
4. **Guía para agentes**: doc corto con los comandos exactos (levantar, logs, ejecutar tests, crear BD de prueba, destruir) para que cualquier sesión opere sin explorar.

## Criterio de salida

`bootstrap.sh` genera un entorno funcional de Odoo 19 y otro de 17 desde cero. Guía para agentes escrita. Marcar en ROADMAP.
