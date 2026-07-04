# Instalación en otra máquina (desde cero)

Orden recomendado: capa IA → gestor → conector → entornos → manual-generator. Cada sección enlaza al doc que ya tiene el detalle; aquí solo va la secuencia y lo que no está escrito en otro lado.

## Requisitos

- WSL2 (Ubuntu 24.04) o Linux, con Docker operativo (`docker ps` responde). En WSL: Docker Desktop con **WSL integration activa** en la distro.
- Git con acceso SSH a GitHub (multi-cuenta en `~/.ssh/config` si aplica; ver [00-arquitectura.md](00-arquitectura.md#contexto-de-la-máquina-relevado-2026-07-03)).
- Node 20+ (manual-generator), Python 3.10+ — se usa 3.12 — (conector), Go (engram).
- **Fuentes Odoo 19 Enterprise en disco local**: NO están en este repo (licencia). El gestor las monta por ruta vía `ENTERPRISE_PATH`.

## 1. Clonar el repo

```bash
git clone git@github.com-personal:luisferllub230/odoo-ai-ecosystem-.git ~/repos/odoo-ai-ecosystem
```

## 2. gentle-ai + Claude Code

Guía completa: [fases/01-gentle-ai.md](fases/01-gentle-ai.md). Resumen de lo que quedó instalado en la máquina original:

- Binario de release → `~/.local/bin` (alternativas brew/`go install` en la guía).
- Componentes: engram, gga, sdd, skills, permissions, context7 (sin persona/theme).
- Verificar con `gentle-ai doctor`.

## 3. Engram

- Binario en `~/go/bin`; agregarlo al PATH (`.zshrc`).
- Se conecta como MCP stdio en Claude Code (lo configura gentle-ai); probar `mem_save`/`mem_search` en sesión.

## 4. gestor-odoo

Detalle: [../gestor-odoo/README.md](../gestor-odoo/README.md).

1. Crear `gestor-odoo/.env` (no está versionado). Variables que consume el compose: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `ENTERPRISE_PATH`, y opcionales `ODOO_VERSION`, `ODOO_PORT` (8169), `ODOO_GEVENT_PORT` (8172). `ENTERPRISE_PATH` apunta a las fuentes Enterprise locales (montadas `:ro`).
2. Alinear `admin_passwd` de `config/odoo.conf` con la master password elegida.
3. `docker compose build`, inicializar la BD `gestor` con `project` e iniciar (comandos exactos en el README).
4. Crear usuario `ai-agent` (permisos solo Proyecto) y su API key; guardarla fuera del repo (README, «Siguientes pasos manuales»).
5. Crear proyecto `Plantilla` con las 7 etapas `Backlog → Análisis/Diseño → Aprobado → Desarrollo → Prueba → PR/Review → Hecho`, con [estandares/plantilla-tarea.md](estandares/plantilla-tarea.md) como descripción por defecto.

## 5. conector-odoo

Detalle: [../conector-odoo/README.md](../conector-odoo/README.md) (instalación, registro y troubleshooting).

```bash
cd conector-odoo && python3 -m venv .venv && .venv/bin/pip install -e .
claude mcp add gestor-odoo --scope user \
  -e GESTOR_API_KEY=<api_key_del_usuario_ai-agent> \
  -- $PWD/.venv/bin/conector-odoo-mcp
```

Se registró en scope `user` (F3); las herramientas aparecen en sesión tras reiniciar Claude Code.

## 6. entornos/

Nada que instalar: `bootstrap.sh` genera cada entorno bajo demanda. Operación: [../entornos/GUIA-AGENTES.md](../entornos/GUIA-AGENTES.md).

## 7. manual-generator

Detalle: [../manual-generator/README.md](../manual-generator/README.md).

```bash
cd manual-generator && npm install
npx playwright install chromium   # solo si la caché ~/.cache/ms-playwright no tiene chromium-1208
```

Playwright está fijado en `~1.58`; en máquina nueva lo normal es que el navegador NO esté en caché y haya que instalarlo.

## Verificación final

- `docker ps` — contenedores `gestor_odoo` y `gestor_db` arriba; Odoo responde en `http://localhost:8169`.
- Reiniciar Claude Code y comprobar en sesión las tools MCP `gestor-odoo` (`list_tasks` de solo lectura) y engram.
- `conector-odoo`: `.venv/bin/pip install -e '.[dev]' && .venv/bin/pytest` (65 tests offline).
- `manual-generator`: `npm test` (31 tests, sin red ni navegador).
