#!/bin/bash
# odoo_dev_env entrypoint.
# Resolves DB connection params from env, waits for Postgres, then execs Odoo
# under debugpy so the IDE can attach on port 3001.
set -e

if [ -v PASSWORD_FILE ]; then
    PASSWORD="$(< "$PASSWORD_FILE")"
fi

# Precedence: explicit env > DB_PORT_5432_* (link-style) > POSTGRES_* > default.
: "${HOST:=${DB_PORT_5432_TCP_ADDR:='db'}}"
: "${PORT:=${DB_PORT_5432_TCP_PORT:=5432}}"
: "${USER:=${DB_ENV_POSTGRES_USER:=${POSTGRES_USER:='odoo'}}}"
: "${PASSWORD:=${DB_ENV_POSTGRES_PASSWORD:=${POSTGRES_PASSWORD:='odoo'}}}"

DB_ARGS=()
check_config() {
    local param="$1" value="$2"
    if grep -q -E "^\s*\b${param}\b\s*=" "$ODOO_RC" 2>/dev/null; then
        value=$(grep -E "^\s*\b${param}\b\s*=" "$ODOO_RC" | cut -d " " -f3 | sed 's/["\n\r]//g')
    fi
    DB_ARGS+=("--${param}" "${value}")
}
check_config "db_host" "$HOST"
check_config "db_port" "$PORT"
check_config "db_user" "$USER"
check_config "db_password" "$PASSWORD"

case "$1" in
    -- | odoo)
        shift
        if [[ "$1" == "scaffold" ]]; then
            exec /usr/bin/python3 -m debugpy --listen 0.0.0.0:3001 /usr/bin/odoo "$@" "${DB_ARGS[@]}"
        else
            wait-for-psql.py "${DB_ARGS[@]}" --timeout=30
            exec /usr/bin/python3 -m debugpy --listen 0.0.0.0:3001 /usr/bin/odoo "$@" "${DB_ARGS[@]}"
        fi
        ;;
    -*)
        wait-for-psql.py "${DB_ARGS[@]}" --timeout=30
        exec /usr/bin/python3 -m debugpy --listen 0.0.0.0:3001 /usr/bin/odoo "$@" "${DB_ARGS[@]}"
        ;;
    *)
        exec "$@"
        ;;
esac
