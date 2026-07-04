#!/usr/bin/env bash
# odoo-ai-ecosystem / entornos / bootstrap.sh
# Generates a version-parametrized Odoo dev environment (Dockerfile +
# docker-compose + debugpy + VS Code attach config) from templates/.
#
# Evolution of odoo_dev_env/bootstrap.sh — see docs/fases/04-auditoria.md for
# the audit that drove the changes (pip flags per version, namespaced volumes,
# no hardcoded DB IPs, optional shared network / enterprise mount).
#
# USAGE
#   bootstrap.sh <project> <version> [flags]
set -euo pipefail

# --- Defaults ----------------------------------------------------------------
DEFAULT_DB_USER="odoo"
DEFAULT_DB_PASSWORD="odoo"

PROJECT=""
VERSION=""
TARGET=""                 # auto: $PWD/<project>
PORT=""                   # auto: 80<version>
LONGPOLL_PORT=""          # auto: 90<version>
DEBUG_PORT=""             # auto: 30<version>
DB_MODE="external"
DB_HOST=""                # REQUIRED in external mode (no hardcoded IP default)
DB_USER="$DEFAULT_DB_USER"
DB_PASSWORD="$DEFAULT_DB_PASSWORD"
DEVELOPER="$(whoami)"
ENTERPRISE_PATH=""
SHARED_NETWORK=0
FORCE=0
DRY_RUN=0

usage() {
    cat <<EOF
odoo-ai-ecosystem entornos bootstrap

USAGE
  bootstrap.sh <project> <version> [flags]

POSITIONAL
  project                 Slug for container/volume names ([a-zA-Z0-9_-]).
  version                 Odoo major version: 16, 17, 18, 19...

FLAGS
  --target <dir>          Directory to seed (default: \$PWD/<project>; created
                          if missing).
  --port <n>              Host port mapped to 8069 (default: 80<version>).
  --longpoll-port <n>     Host port mapped to 8072 (default: 90<version>).
  --debug-port <n>        Host port for debugpy (default: 30<version>).
  --db external|compose   External Postgres (default, requires --db-host) or
                          compose-bundled postgres:15.
  --db-host <host>        External Postgres host. No default on purpose: pass
                          it explicitly or use --db compose.
  --db-user <user>        Postgres user (default: $DEFAULT_DB_USER).
  --db-password <pw>      Postgres password (default: $DEFAULT_DB_PASSWORD).
  --developer <name>      Container prefix (default: \$USER).
  --enterprise-path <dir> Mount <dir> read-only at /mnt/enterprise and add it
                          to addons_path.
  --shared-network        Join the external network odoo_shared_network
                          (create it once: docker network create odoo_shared_network).
  --force                 Overwrite existing files. Default refuses to clobber.
  --dry-run               Print planned actions, write nothing.
  -h | --help             This help.

PORT TABLE (defaults, XX = version)
  web 80XX   longpoll 90XX   debug 30XX     e.g. v17 -> 8017/9017/3017

EXAMPLES
  # Self-contained Odoo 19 env (bundled Postgres):
  ./bootstrap.sh mi-proyecto 19 --db compose

  # Odoo 17 against an external Postgres:
  ./bootstrap.sh mi-proyecto 17 --db-host 192.168.1.10 --db-user dev --db-password s3cret

  # With Enterprise sources and the shared dev network:
  ./bootstrap.sh mi-proyecto 19 --db compose \\
      --enterprise-path /home/me/repos/enterprise --shared-network
EOF
}

# --- Arg parsing (positionals + flags) ----------------------------------------
# req <flag> <remaining_argc>: fail consistently when a value-taking flag has
# no value (avoids `unbound variable` crashes under set -u).
req() {
    if [[ "$2" -lt 2 ]]; then
        echo "Flag $1 requires a value" >&2
        usage
        exit 2
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)          req "$1" $#; TARGET="$2"; shift 2 ;;
        --port)            req "$1" $#; PORT="$2"; shift 2 ;;
        --longpoll-port)   req "$1" $#; LONGPOLL_PORT="$2"; shift 2 ;;
        --debug-port)      req "$1" $#; DEBUG_PORT="$2"; shift 2 ;;
        --db)              req "$1" $#; DB_MODE="$2"; shift 2 ;;
        --db-host)         req "$1" $#; DB_HOST="$2"; shift 2 ;;
        --db-user)         req "$1" $#; DB_USER="$2"; shift 2 ;;
        --db-password)     req "$1" $#; DB_PASSWORD="$2"; shift 2 ;;
        --developer)       req "$1" $#; DEVELOPER="$2"; shift 2 ;;
        --enterprise-path) req "$1" $#; ENTERPRISE_PATH="$2"; shift 2 ;;
        --shared-network)  SHARED_NETWORK=1; shift ;;
        --force)           FORCE=1; shift ;;
        --dry-run)         DRY_RUN=1; shift ;;
        -h|--help)         usage; exit 0 ;;
        --*)               echo "Unknown flag: $1" >&2; usage; exit 2 ;;
        *)
            if   [[ -z "$PROJECT" ]]; then PROJECT="$1"
            elif [[ -z "$VERSION" ]]; then VERSION="$1"
            else echo "Unexpected argument: $1" >&2; usage; exit 2
            fi
            shift ;;
    esac
done

# --- Validation + derived defaults ---------------------------------------------
[[ -z "$PROJECT" || -z "$VERSION" ]] && { echo "Missing positionals: <project> <version>" >&2; usage; exit 2; }
[[ "$PROJECT" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]] \
    || { echo "Bad project slug: '$PROJECT' (use [a-zA-Z0-9_-], must start alnum)" >&2; exit 2; }
[[ "$VERSION" =~ ^(1[4-9]|2[0-9])$ ]] \
    || { echo "Unsupported version: '$VERSION' (use a major like 16, 17, 18, 19)" >&2; exit 2; }
case "$DB_MODE" in external|compose) ;; *) echo "Bad --db: $DB_MODE (use external|compose)" >&2; exit 2 ;; esac

if [[ "$DB_MODE" == "external" && -z "$DB_HOST" ]]; then
    echo "external DB mode requires --db-host <host> (no hardcoded IP defaults)." >&2
    echo "Alternatively use a self-contained Postgres:  --db compose" >&2
    exit 2
fi
if [[ "$DB_MODE" == "compose" ]]; then
    [[ -n "$DB_HOST" ]] && echo "note: --db-host ignored in compose mode (host = 'db' service)"
    DB_HOST="db"
fi

[[ -z "$PORT"          ]] && PORT="80${VERSION}"
[[ -z "$LONGPOLL_PORT" ]] && LONGPOLL_PORT="90${VERSION}"
[[ -z "$DEBUG_PORT"    ]] && DEBUG_PORT="30${VERSION}"

# Ports must be numeric, in range, and pairwise distinct.
for p in "web:$PORT" "longpoll:$LONGPOLL_PORT" "debug:$DEBUG_PORT"; do
    name="${p%%:*}" value="${p#*:}"
    if ! [[ "$value" =~ ^[0-9]+$ ]] || (( value < 1 || value > 65535 )); then
        echo "Bad $name port: '$value' (must be a number 1-65535)" >&2
        exit 2
    fi
done
if [[ "$PORT" == "$LONGPOLL_PORT" || "$PORT" == "$DEBUG_PORT" || "$LONGPOLL_PORT" == "$DEBUG_PORT" ]]; then
    echo "Ports must be distinct: web=$PORT longpoll=$LONGPOLL_PORT debug=$DEBUG_PORT" >&2
    exit 2
fi

[[ -z "$TARGET" ]] && TARGET="$PWD/$PROJECT"
if [[ $DRY_RUN -eq 0 ]]; then
    mkdir -p "$TARGET"
    TARGET="$(cd "$TARGET" && pwd)"
fi

if [[ -n "$ENTERPRISE_PATH" && ! -d "$ENTERPRISE_PATH" ]]; then
    echo "warning: --enterprise-path '$ENTERPRISE_PATH' does not exist (mount will fail at 'up')" >&2
fi

# --- Locate template dir ---------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/templates"
[[ -d "$TEMPLATES_DIR" ]] || { echo "templates/ not found next to bootstrap.sh" >&2; exit 1; }

# Random per-environment Odoo master password (audit gotcha 2).
ADMIN_PASSWD="$(openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')"

# --- Helpers ---------------------------------------------------------------------
log() { printf "  %s\n" "$*"; }
say() { printf "→ %s\n" "$*"; }

# sed_escape <value>: escape sed replacement metacharacters (\, &) and the
# `|` delimiter used below, so user-supplied values (--db-password, --db-host,
# --developer, --enterprise-path...) can never corrupt the rendered files.
sed_escape() { printf '%s' "$1" | sed -e 's/[&|\\]/\\&/g'; }

# Escaped copies for use as sed replacement text.
E_DEVELOPER="$(sed_escape "$DEVELOPER")"
E_PROJECT="$(sed_escape "$PROJECT")"
E_DB_HOST="$(sed_escape "$DB_HOST")"
E_DB_USER="$(sed_escape "$DB_USER")"

# Files actually written by render() in THIS run. Post-render tweaks
# (--shared-network / --enterprise-path) only apply to these, so existing
# files are never mutated without --force.
declare -A WRITTEN=()
SKIPPED=0

# Remove a half-rendered tmp file if the script dies mid-render.
RENDER_TMP=""
trap '[[ -n "$RENDER_TMP" ]] && rm -f "$RENDER_TMP"' EXIT

# render <src> <dest> [db_password_override]
# Copies src to dest with __PLACEHOLDER__ substitution. Honors --force/--dry-run.
# Writes atomically: renders to <dest>.tmp and mv's into place, so an
# interrupted run never leaves a truncated dest that later runs would skip.
render() {
    local src="$1" dest="$2" password="${3:-$DB_PASSWORD}"
    if [[ -e "$dest" && $FORCE -eq 0 ]]; then
        log "skip (exists): ${dest#"$TARGET"/}"
        SKIPPED=$((SKIPPED + 1))
        return 0
    fi
    if [[ $DRY_RUN -eq 1 ]]; then
        log "would write: ${dest#"$TARGET"/}"
        WRITTEN["$dest"]=1
        return 0
    fi
    mkdir -p "$(dirname "$dest")"
    local tmp="$dest.tmp.$$" password_esc
    password_esc="$(sed_escape "$password")"
    RENDER_TMP="$tmp"
    if ! sed \
        -e "s|__DEVELOPER__|${E_DEVELOPER}|g" \
        -e "s|__PROJECT__|${E_PROJECT}|g" \
        -e "s|__VERSION__|${VERSION}|g" \
        -e "s|__PORT__|${PORT}|g" \
        -e "s|__LONGPOLL_PORT__|${LONGPOLL_PORT}|g" \
        -e "s|__DEBUG_PORT__|${DEBUG_PORT}|g" \
        -e "s|__DB_HOST__|${E_DB_HOST}|g" \
        -e "s|__DB_USER__|${E_DB_USER}|g" \
        -e "s|__DB_PASSWORD__|${password_esc}|g" \
        -e "s|__ADMIN_PASSWD__|${ADMIN_PASSWD}|g" \
        "$src" > "$tmp"; then
        rm -f "$tmp"
        echo "render failed for ${dest#"$TARGET"/}" >&2
        exit 1
    fi
    mv "$tmp" "$dest"
    RENDER_TMP=""
    WRITTEN["$dest"]=1
    log "wrote: ${dest#"$TARGET"/}"
}

# written_this_run <dest>: true if render() created/overwrote dest in this run.
written_this_run() { [[ -n "${WRITTEN[$1]:-}" ]]; }

# --- Banner ------------------------------------------------------------------------
say "entornos bootstrap"
log "project:    $PROJECT"
log "target:     $TARGET"
log "developer:  $DEVELOPER"
log "version:    Odoo $VERSION.0"
log "ports:      web=$PORT longpoll=$LONGPOLL_PORT debug=$DEBUG_PORT"
log "db mode:    $DB_MODE (host=$DB_HOST user=$DB_USER)"
[[ -n "$ENTERPRISE_PATH"    ]] && log "enterprise: $ENTERPRISE_PATH (read-only)"
[[ $SHARED_NETWORK -eq 1    ]] && log "network:    odoo_shared_network (external)"
[[ $FORCE          -eq 1    ]] && log "force:      ON (will overwrite)"
[[ $DRY_RUN        -eq 1    ]] && log "dry-run:    no files will be written"
echo

# --- Render --------------------------------------------------------------------------
render "$TEMPLATES_DIR/Dockerfile"          "$TARGET/Dockerfile"
if [[ "$DB_MODE" == "compose" ]]; then
    render "$TEMPLATES_DIR/docker-compose.compose.yml" "$TARGET/docker-compose.yml"
else
    render "$TEMPLATES_DIR/docker-compose.yml"         "$TARGET/docker-compose.yml"
fi
render "$TEMPLATES_DIR/entrypoint.sh"       "$TARGET/entrypoint.sh"
render "$TEMPLATES_DIR/wait-for-psql.py"    "$TARGET/wait-for-psql.py"
render "$TEMPLATES_DIR/conf/odoo.conf"      "$TARGET/conf/odoo.conf"
render "$TEMPLATES_DIR/requirements.txt"    "$TARGET/requirements.txt"
# .env carries real credentials (gitignored); .env.example masks the password.
render "$TEMPLATES_DIR/env.example"         "$TARGET/.env"
render "$TEMPLATES_DIR/env.example"         "$TARGET/.env.example" "change-me"
render "$TEMPLATES_DIR/.vscode/launch.json" "$TARGET/.vscode/launch.json"

if [[ $DRY_RUN -eq 0 ]]; then
    chmod +x "$TARGET/entrypoint.sh" "$TARGET/wait-for-psql.py" 2>/dev/null || true
fi

# --- Optional blocks (marker-based) ------------------------------------------------------
# Tweaks apply ONLY to files render() wrote in this run: pre-existing files
# (skipped without --force) are never mutated behind the user's back.
if [[ $DRY_RUN -eq 0 && $SHARED_NETWORK -eq 1 ]]; then
    if written_this_run "$TARGET/docker-compose.yml"; then
        sed -i 's|#SHARED_NETWORK#||g' "$TARGET/docker-compose.yml"
        log "enabled odoo_shared_network in docker-compose.yml"
    else
        log "skip shared-network tweak: docker-compose.yml pre-exists (re-run with --force to apply)"
    fi
fi

if [[ $DRY_RUN -eq 0 && -n "$ENTERPRISE_PATH" ]]; then
    E_ENTERPRISE_PATH="$(sed_escape "$ENTERPRISE_PATH")"
    if written_this_run "$TARGET/docker-compose.yml"; then
        sed -i 's|#ENTERPRISE#||g' "$TARGET/docker-compose.yml"
        log "enabled read-only enterprise mount (/mnt/enterprise) in docker-compose.yml"
    else
        log "skip enterprise tweak: docker-compose.yml pre-exists (re-run with --force to apply)"
    fi
    if written_this_run "$TARGET/.env"; then
        sed -i "s|^# ENTERPRISE_PATH=.*|ENTERPRISE_PATH=${E_ENTERPRISE_PATH}|" "$TARGET/.env"
    else
        log "skip enterprise tweak: .env pre-exists (set ENTERPRISE_PATH manually or use --force)"
    fi
    if written_this_run "$TARGET/conf/odoo.conf"; then
        # Enterprise addons must come BEFORE community in addons_path.
        sed -i 's|^addons_path = .*|addons_path = /mnt/enterprise,/mnt/extra-addons|' "$TARGET/conf/odoo.conf"
    else
        log "skip enterprise tweak: conf/odoo.conf pre-exists (edit addons_path manually or use --force)"
    fi
fi

# --- .gitignore augmentation -------------------------------------------------------------
if [[ $DRY_RUN -eq 0 ]]; then
    SNIPPET="$TEMPLATES_DIR/gitignore.snippet"
    GITIGNORE="$TARGET/.gitignore"
    if [[ ! -f "$GITIGNORE" ]]; then
        cp "$SNIPPET" "$GITIGNORE"
        log "wrote: .gitignore"
    elif ! grep -q "entornos (odoo-ai-ecosystem)" "$GITIGNORE"; then
        printf "\n" >> "$GITIGNORE"
        cat "$SNIPPET" >> "$GITIGNORE"
        log "appended to: .gitignore"
    else
        log "skip (already augmented): .gitignore"
    fi
fi

# --- Final tips ----------------------------------------------------------------------------
echo
say "done. Next:"
if [[ $SKIPPED -gt 0 && $FORCE -eq 0 ]]; then
    log "NOTE: $SKIPPED existing file(s) were kept as-is; the values shown below"
    log "      may not reflect the actual environment (re-run with --force to overwrite)."
fi
log "1) Review .env (never commit it) and conf/odoo.conf"
[[ $SHARED_NETWORK -eq 1 ]] && log "1b) Ensure the network exists: docker network create odoo_shared_network"
log "2) cd $TARGET && docker compose up -d --build"
log "3) Open http://localhost:$PORT — master password in conf/odoo.conf"
log "4) F5 in VS Code to attach the debugger on port $DEBUG_PORT"
log "See entornos/GUIA-AGENTES.md for the exact agent commands."
