# Fase 4 — Auditoría de entornos existentes (2026-07-04)

Comparativa de `~/repos/odoo_dev_env` (generador), `~/repos/odoo_pro_19` y `~/repos/odoo_pro_17` (entornos vivos). Base para diseñar `entornos/`.

## Patrón común (los tres)

- **Dockerfile**: `FROM odoo:<version>` → `USER root` → `pip install -r requirements.txt` → copia `entrypoint.sh` → `mkdir/chown /var/lib/odoo` → `USER odoo`.
- **entrypoint.sh**: prácticamente idéntico. Precedencia de credenciales `HOST/PORT/USER/PASSWORD ← DB_PORT_5432_TCP_* ← POSTGRES_* ← default`, lee `$ODOO_RC` con `check_config()`, espera Postgres con `wait-for-psql.py --timeout=30` y lanza `python3 -m debugpy --listen 0.0.0.0:3001 /usr/bin/odoo`.
- **wait-for-psql.py**: mismo script (la copia de odoo_dev_env corrige bug: inicializa `error=""`).
- **compose**: servicio `odoo` con `build .`, `container_name` por `${ODOO_DEVELOPER}`, `${ODOO_PORT}:8069`, `${ODOO_DEBUG_PORT}:3001`, env `DB_PORT_5432_TCP_*` + `DB_ENV_POSTGRES_*`, `./conf:/etc/odoo`, volumen nombrado en `/var/lib/odoo`. Ninguno define healthcheck (el "wait" es el entrypoint).
- **Puertos**: web `80XX`, debug `30XX` (XX = versión). Generador añade longpoll `90XX` (los pro no lo exponen).

## Diferencias 17 vs 19

| Aspecto | pro_17 | pro_19 |
|---|---|---|
| Base | `odoo:17.0` (Py 3.10) | `odoo:19.0` (Py 3.12) |
| pip | clásico + `--upgrade setuptools pip` | `--break-system-packages --ignore-installed` (PEP 668) |
| Puertos | 8017 / 3017 | 8019 / 3019 |
| conf extra | `limit_time_real=3600` | `db_maxconn=16`, `max_cron_threads=1` (Postgres compartido) |
| OCA | submódulo directo `addons/OCA/...` | embebido en `odoo-pro/OCA/` |
| requirements | set antiguo (`cryptography<37`…) | set moderno pinneado (pydantic 2, httpx…) |

`entrypoint.sh` y `wait-for-psql.py` no varían entre versiones.

## bootstrap.sh (odoo_dev_env)

- Flags: `--target --version(16-19) --port(80XX) --longpoll-port(+1000) --debug-port(30XX) --db external|compose --db-host --db-user --db-password --developer --name --enterprise --force --dry-run`.
- Genera por `sed` sobre placeholders `__DEVELOPER__ __PROJECT__ __VERSION__ __PORT__ __LONGPOLL_PORT__ __DEBUG_PORT__ __DB_HOST__ __DB_USER__ __DB_PASSWORD__`: Dockerfile, compose (variante según `--db`), entrypoint, wait-for-psql, conf, requirements, `.env(.example)`, `.vscode/launch.json`, `.gitignore`.
- Idempotente sin `--force`; modo curl (clona templates a tmpdir).
- **Limitaciones**: no cubre submódulos (enterprise/odoo-pro/OCA/pyazul), no red `odoo_shared_network`, `--enterprise` parcha por `sed` frágil y pone enterprise al final del addons_path (doc dice antes), `admin_passwd` plano, default `--db-host 172.28.57.51` hardcodeado.

## Redes y Postgres

- `odoo_shared_network` (`external: true`) solo en los pro; hay que crearla fuera (`docker network create`).
- Ambos pro comparten Postgres externo `172.28.57.51:5432` user `dev` (de ahí `db_maxconn=16`). Generador ofrece `--db compose` (postgres:15 embebido) o external.

## Gotchas

1. `launch.json` de los pro conecta a puertos 8093/8091 que no existen en el mapeo (debug real: 3019/3017) — attach roto sin editar.
2. Los pro versionan `.env` real con credenciales (sin `.env.example`); mismo hash `admin_passwd` en 17 y 19.
3. Volumen `odoo_pro_ODOO_DATA` con mismo nombre en ambos pro (placeholder sin sustituir); salvado por prefijo de proyecto compose.
4. `user: root` en compose de los pro contradice `USER odoo` del Dockerfile → filestore puede quedar de root.
5. IP `172.28.57.51` (bridge WSL2) hardcodeada; no portable.
6. `debugpy` imprescindible en requirements (entrypoint lo invoca siempre).
7. pyazul se instala desde fuente local (submódulo); el generador no contempla paquetes locales.
8. En los pro `addons_path` incluye `/mnt/extra-addons` que no está montado (ruta vacía en contenedor); montajes `:delegated`/`:cached`, ninguno read-only.
9. `addons_path` con ~25 rutas OCA hardcodeadas → candidato a generación automática escaneando `OCA/*`.
10. Env muertas en compose pro: `ODOO_AUTO_UPDATE_MODULES`, `ODOO_DATABASE_NAME` (el entrypoint no las usa).

## Decisiones derivadas para `entornos/`

- Partir de plantillas de `odoo_dev_env` (las más limpias) y añadir: flags pip condicionados por versión (≥18 → `--break-system-packages`), montajes de submódulos con `addons_path` autogenerado, red `odoo_shared_network` opcional, `.env.example` obligatorio + `.env` gitignored, `launch.json` con puerto = `ODOO_DEBUG_PORT`, coherencia `user`/`USER odoo` (sin `user: root`).
