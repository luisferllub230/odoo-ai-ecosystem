# Guía para agentes — entornos dev Odoo

Comandos exactos para operar un entorno sin explorar. Contexto de diseño: [`docs/fases/04-auditoria.md`](../docs/fases/04-auditoria.md).

## 0. Seguridad (leer antes de destruir nada)

- Los comandos destructivos de esta guía (`down -v`, `dropdb`) se aplican **SOLO al entorno generado para la tarea actual**. **NUNCA** sobre `odoo_pro_17`, `odoo_pro_19`, `gestor-odoo` ni ningún Postgres compartido del host.
- `docker compose down -v` **solo** desde el directorio del entorno de la tarea. Antes de ejecutarlo, verificar QUÉ se va a destruir con `docker compose ps` (los contenedores listados deben ser los del proyecto de la tarea, ningún otro).
- Antes de cualquier `dropdb`, listar las BDs y verificar el nombre exacto `test_<tarea_id>`:
  ```bash
  docker compose exec db psql -U <db_user> -l          # compose
  PGPASSWORD=<pw> psql -h <db_host> -U <db_user> -l    # external
  ```
  Usar siempre `dropdb --if-exists` y solo con nombres `test_*` de la tarea propia.

## 1. Generar un entorno

```bash
# Autocontenido (Postgres embebido) — recomendado para agentes:
/home/lfernandez/repos/odoo-ai-ecosystem/entornos/bootstrap.sh <proyecto> <version> \
    --db compose --target <dir-destino>

# Contra Postgres externo (host obligatorio, sin defaults de IP):
/home/lfernandez/repos/odoo-ai-ecosystem/entornos/bootstrap.sh <proyecto> <version> \
    --db-host <host> --db-user <user> --db-password <pw> --target <dir-destino>
```

Puertos por defecto (XX = versión, ej. 17 o 19): web `80XX`, longpoll `90XX`, debug `30XX`. Cambiar con `--port/--longpoll-port/--debug-port` si chocan. `--dry-run` muestra sin escribir; `--force` sobreescribe.

## 2. Levantar / observar

Todos los comandos siguientes se ejecutan **dentro del directorio del entorno** (donde está `docker-compose.yml`):

```bash
docker compose up -d --build       # levantar (primera vez compila la imagen)
docker compose ps                  # estado
docker compose logs -f odoo        # logs de Odoo
docker compose logs -f db          # logs de Postgres (solo modo compose)
```

Web: `http://localhost:<ODOO_PORT>` (ver `.env`). Master password: `conf/odoo.conf`.

## 3. BD de prueba por tarea (convención)

Una BD por tarea, nombre `test_<tarea_id>` (ej. `test_1234`). Se crea al empezar la prueba y **se destruye al cerrar la tarea**. Nunca reutilizar BDs de prueba entre tareas.

`<db_user>` es el usuario de BD del entorno (ver `DB_ENV_POSTGRES_USER` en `.env`; por defecto `odoo`).

```bash
# Crear (modo compose — vía contenedor db):
docker compose exec db createdb -U <db_user> test_<tarea_id>

# Crear (modo external — psql/createdb contra el host):
PGPASSWORD=<pw> createdb -h <db_host> -p 5432 -U <db_user> test_<tarea_id>

# Destruir al cerrar la tarea (antes: verificar nombre con psql -l, ver §0):
docker compose exec db dropdb --if-exists -U <db_user> test_<tarea_id>                    # compose
PGPASSWORD=<pw> dropdb --if-exists -h <db_host> -p 5432 -U <db_user> test_<tarea_id>      # external
```

## 4. Ejecutar tests de un módulo

`conf/odoo.conf` ya lleva credenciales de BD, por lo que `odoo` funciona directo dentro del contenedor:

```bash
# Instalar el módulo con tests y salir (crea la BD si no existe):
docker compose exec odoo odoo -d test_<tarea_id> --test-enabled -i <modulo> --stop-after-init

# Re-ejecutar tests tras cambios (actualizar en vez de instalar):
docker compose exec odoo odoo -d test_<tarea_id> --test-enabled -u <modulo> --stop-after-init
```

Código de salida 0 = tests OK. Los fallos aparecen en stdout como `FAIL`/`ERROR` (grep `(FAIL|ERROR)`).

## 5. Destruir

Solo desde el directorio del entorno de la tarea y tras verificar con `docker compose ps` (ver §0):

```bash
docker compose down                # parar contenedores (conserva filestore/BD)
docker compose down -v             # destruir TODO: contenedores + volúmenes (filestore y BD)
```

Antes de `down -v` en modo external, destruir las BDs de prueba creadas (sección 3): el Postgres externo no se borra con el entorno.

## 6. Troubleshooting

- **Contenedor odoo en `Exited` justo tras `up`**: `wait-for-psql.py` agotó su timeout (30 s) esperando Postgres. Revisar `docker compose logs odoo` y `docker compose logs db`, y relanzar con `docker compose up -d` (la BD ya estará lista).
- **Cambiar password con `--db compose`**: regenerar con `--force --db-password <nueva>` NO cambia la password del Postgres ya inicializado (persiste en el volumen `*_pg_data`). Remedio: `docker compose down -v` (DESTRUCTIVO: borra BDs y filestore) y volver a levantar.

## Notas

- `.env` contiene credenciales: **nunca** commitearlo (ya está en `.gitignore`).
- Red compartida opcional `odoo_shared_network`: crearla una vez con `docker network create odoo_shared_network` y generar con `--shared-network`.
- Enterprise: `--enterprise-path <dir>` monta las fuentes en `/mnt/enterprise` (solo lectura) y las antepone al `addons_path`.
- Debug: attach de VS Code al puerto `30XX` (config lista en `.vscode/launch.json`).
