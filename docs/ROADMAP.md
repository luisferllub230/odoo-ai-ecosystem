# ROADMAP — Documento maestro de progreso

> **Instrucción para cualquier sesión de IA**: leer este archivo ANTES de trabajar. Al completar un paso, marcarlo ✅ con fecha. No avanzar dos fases en paralelo. Si una sesión se corta, la siguiente retoma desde aquí.

**Leyenda**: ✅ hecho · 🔄 en curso · ⬜ pendiente · ⛔ gate humano

---

## Fase 0 — Fundación

- ✅ (2026-07-03) Relevar contexto de la máquina (12 cores, 15GB RAM WSL, RTX 5060, Ubuntu 24.04 WSL2, 3 cuentas SSH GitHub).
- ✅ (2026-07-03) Decisiones de arquitectura: gentle-ai como orquestador, Odoo gestor Enterprise en contenedor dedicado y carpeta nueva (proyecto independiente escalable), repo en cuenta GitHub personal.
- ✅ (2026-07-03) Crear este repo con README + documentación por fases.
- ✅ (2026-07-04) Activar Docker Desktop WSL integration en esta distro (verificado con `docker ps`).
- ✅ (2026-07-04) Repo en GitHub personal: `git@github.com-personal:luisferllub230/odoo-ai-ecosystem-.git`, push inicial hecho.

## Fase 1 — Base gentle-ai + Claude Code

Guía: [fases/01-gentle-ai.md](fases/01-gentle-ai.md)

- ✅ (2026-07-04) Instalar gentle-ai v1.43.3 (binario release → `~/.local/bin`) con componentes engram, gga, sdd, skills, permissions, context7 (sin persona/theme). `gentle-ai doctor`: solo quedan avisos no bloqueantes (opencode no instalado — no se usa; engram HTTP 7437 apagado — el MCP stdio sí funciona; binario `claude` duplicado en PATH).
- ✅ (2026-07-04) SDD inicializado en modo engram (sin openspec/): contexto y capacidades de testing persistidos (observaciones #2, #3, proyecto `odoo-ai-ecosystem`).
- ✅ (2026-07-04) Engram v1.17.0 operativo (`~/go/bin`, agregado a PATH en .zshrc) y conectado como MCP en Claude Code; save/search probados.
- ✅ (2026-07-04) `gentle-ai skill-registry refresh` → `.atl/skill-registry.md` (11 skills).
- ✅ (2026-07-04) `CLAUDE.md` del repo creado (reglas, gates, engram, plantillas).
- ✅ (2026-07-04) Modelos por fase ya asignados por gentle-ai en `~/.claude/agents/sdd-*.md`: diseño=opus, implementación/exploración=sonnet.
- ✅ (2026-07-04) Reiniciar Claude Code para que cargue los subagentes sdd-* instalados (confirmado por el humano; agentes sdd-* visibles en la sesión).

## Fase 2 — Odoo Gestor

Guía: [fases/02-odoo-gestor.md](fases/02-odoo-gestor.md)

- ✅ (2026-07-04) Crear carpeta `gestor-odoo/` con `docker-compose.yml` propio (Odoo 19 Enterprise + Postgres 17 dedicado, red `gestor_network`, puerto 8169; websocket 8172).
- ✅ (2026-07-04) Reutilizar Dockerfile/fuentes enterprise de `~/repos/odoo_pro_19` sin acoplar: entrypoint/wait-for-psql/conf copiados y adaptados (sin debugpy ni deps dev); enterprise montado read-only vía `ENTERPRISE_PATH`.
- ✅ (2026-07-04) Inicializar BD `gestor` con `project` (53 módulos, incluye project_enterprise). Usuario `ai-agent` (uid 7, solo permisos Proyecto) con API key XML-RPC verificada (authenticate + read OK; boundary check: AccessError en res.users, correcto). Key entregada al humano para `.env` local.
- ✅ (2026-07-04) Proyecto `Plantilla` (id 1) con etapas `Backlog → Análisis/Diseño → Aprobado → Desarrollo → Prueba → PR/Review → Hecho` (verificadas por XML-RPC) y descripción apuntando a la plantilla de tarea.
- ✅ (2026-07-04) Documentar plantilla de tarea (campos obligatorios: contexto, repo, versión Odoo, criterios de aceptación) → [estandares/plantilla-tarea.md](estandares/plantilla-tarea.md) (existía desde F0; verificada completa).
- ✅ (2026-07-04) ⛔ Humano validó end-to-end: proyecto `Odoo addons` (id 2) + tarea `azul_wepages` (id 5, etapa Análisis/Diseño) creados vía UI y leídos por XML-RPC con `ai-agent`. Nota: es tarea REAL, no de prueba — no trabajarla hasta que exista el conector (F3) y el humano lo ordene.

## Fase 3 — Conector Odoo (RPC/API key)

Guía: [fases/03-conector-odoo.md](fases/03-conector-odoo.md)

- ✅ (2026-07-04) Crear `conector-odoo/`: cliente XML-RPC por perfiles (`profiles.yml` con expansión `${VAR}`; perfil `gestor`; key solo por env `GESTOR_API_KEY`). Python 3.12, venv local, 65 unit tests offline.
- ✅ (2026-07-04) Servidor MCP stdio (SDK oficial `mcp` 1.28.1, FastMCP) con las 5 herramientas; guard duro de transiciones: la IA solo mueve Aprobado→Desarrollo→Prueba→PR/Review, el resto rechaza nombrando los gates humanos (matriz 7×7 testeada).
- ✅ (2026-07-04) MCP registrado en Claude Code scope user (`claude mcp add`, ✔ Connected). E2E real por stdio: list/get sobre `azul_wepages` (solo lectura), comment/attach/move sobre tarea desechable en `Plantilla` (creada y borrada vía xmlrpc). Nota: las herramientas quedan disponibles en sesión tras reiniciar Claude Code.
- ✅ (2026-07-04) Criterio de salida verificado en sesión: tras reiniciar Claude Code, `list_tasks`/`get_task` usadas desde la sesión sobre `azul_wepages` (solo lectura, tarea intacta).

## Fase 4 — Entornos dev estandarizados

Guía: [fases/04-entornos-dev.md](fases/04-entornos-dev.md)

- ✅ (2026-07-04) Auditar `odoo_dev_env`, `odoo_pro_17`, `odoo_pro_19` y extraer patrón común → [fases/04-auditoria.md](fases/04-auditoria.md) (patrón común, difs 17/19, gotchas, decisiones para `entornos/`).
- ✅ (2026-07-04) Crear `entornos/`: `templates/` (Dockerfile con `ARG ODOO_VERSION` y flags pip por versión, compose external/embebido, entrypoint/wait-for-psql, conf, env.example, launch.json) + `bootstrap.sh <proyecto> <version>` (placeholders sed escapados, render atómico, validación de flags/puertos, sin IP hardcodeada — exige `--db-host` o `--db compose`).
- ✅ (2026-07-04) Estandarizar: puertos web 80XX / longpoll 90XX / debug 30XX por versión, BD de prueba `test_<tarea_id>`, red `odoo_shared_network` opcional (`--shared-network`), enterprise read-only vía `--enterprise-path`, volúmenes namespaced por proyecto.
- ✅ (2026-07-04) Documentar operación por agentes → [../entornos/GUIA-AGENTES.md](../../entornos/GUIA-AGENTES.md) (§0 seguridad: `down -v`/`dropdb` solo sobre el entorno de la tarea; troubleshooting). Criterio de salida verificado: bootstrap generó Odoo 19 y 17 funcionales desde cero (build+up, HTTP 200, no-root, debugpy, BD test creada/borrada); reviews reliability+resilience pasadas con fixes aplicados y re-verificados.

## Fase 5 — Flujo de desarrollo IA

Guía: [fases/05-flujo-desarrollo.md](fases/05-flujo-desarrollo.md)

- ✅ (2026-07-04) Workflow **análisis/diseño** → skill `.claude/skills/tarea-diseno/` (valida plantilla-tarea, explora repo con subagente, genera `docs/tareas/<id>/design.md`, adjunta+comenta; guarda de re-ejecución: diseño aprobado = contrato, versionar en vez de sobrescribir). ⛔ Gate humano: aprobación (mueve a `Aprobado`).
- ✅ (2026-07-04) Workflow **desarrollo** → skill `tarea-dev` (verifica `Aprobado`, mueve a `Desarrollo`, rama `<tipo>/<id>-<slug>` con remoto verificado, entorno F4 sin `--force`, commits según git-commits.md sin firma IA, aborts auditables vía comment_task).
- ✅ (2026-07-04) Workflow **prueba** → skill `tarea-prueba` (recrea BD `test_<id>` limpia con semilla, ejecuta plan del design, manual según plantilla — TODO integrar manual-generator F6, adjunta y mueve a `Prueba`). ⛔ Gate humano: test funcional.
- ✅ (2026-07-04) Workflow **PR** → skill `tarea-pr` (verifica tests+manual, push por remoto SSH ya configurado, PR sin firma IA, mueve a `PR/Review` + enlace). ⛔ Gate humano: review + merge + deploy.
- ✅ (2026-07-04) Workflow **cierre**: sin skill — `PR/Review→Hecho` es gate humano (guard lo rechaza a la IA); la IA registra lo aprendido en engram (documentado en 5.5).
- ✅ (2026-07-04) Criterio de salida: 4 skills probadas E2E con tarea dummy real (id 7 en Plantilla, borrada): flujos positivos OK vía MCP, negativos del guard rechazados citando gates, commit dummy sin firma IA verificado, `azul_wepages` intacta. Review readability + fixes aplicados (guarda re-ejecución, colisión BD dev/prueba, aborts auditables, specs 5.1/plantilla-tarea alineadas con el guard). Registry refrescado (15 skills). Nota: reiniciar Claude Code para invocar `/tarea-*` en sesión.

## Fase 6 — manual-generator standalone

Guía: [fases/06-manual-generator.md](fases/06-manual-generator.md)

- ✅ (2026-07-04) Extraer `odoo_pro_19/tools/manual-generator` a `manual-generator/` (copia refactorizada; histórico no migrado, origen intacto).
- ✅ (2026-07-04) Parametrizar: conexión por `--profile` (reutiliza `conector-odoo/profiles.yml`, expansión `${VAR}`) o flags `--url --db --user`; password SOLO por env (`ODOO_UI_PASSWORD` o `ui_password` del perfil). Seeds vía `odoo shell` solo contra entornos compose F4 (`--compose-dir`), documentado.
- ✅ (2026-07-04) CLI única `manual-gen` (`capture`/`render`/`run`), `--out` por defecto la carpeta del config (para tareas: `docs/tareas/<task_id>/`), manual md con imágenes relativas, headless por defecto (`--headed` debug), Chromium empaquetado (Playwright ~1.58, coincide con caché local). Configs originales copiados sin cambios de esquema.
- ✅ (2026-07-04) Integrado al workflow de prueba (F5): `tarea-prueba` §4 ahora genera `escenario.json` y corre `manual-gen run`. Criterio de salida verificado E2E con `configs/smoke-f4.json` contra entorno F4 efímero (bootstrap mg-test, BD `test_mg` base+web, 3 capturas PNG + manual con rutas relativas, exit 0; entorno destruido tras la prueba).
- ✅ (2026-07-04) Review reliability + fixes: `ui_password` en profiles.yml debe ser `${VAR}` (rechaza literales), seed con fallback `.before/.after` y estado siempre logueado, validación de esquema del escenario antes de lanzar browser (ids únicos, títulos), exit ≠ 0 si cualquier flow falla (`--allow-partial` para laxo), rutas de imagen calculadas con `path.relative`. Suite `npm test`: 31 tests (args/profiles/seed/config/render, incluye validación de los 11 configs incluidos).

## Fase 7 — Cierre de ciclo y escalado

- 🔄 (2026-07-04) Probar ciclo completo con tarea real (`azul_wepages`, id 5): `/tarea-diseno` iniciado — validación de plantilla detectó campos faltantes y comentó en la tarea (msg 78). ⛔ Gate humano: completar `Repo` (URL destino + cuenta GitHub) y `Rama base` en la descripción, luego ordenar re-ejecutar `/tarea-diseno 5`. Métricas del ciclo → tabla en [fases/07-tokens.md](fases/07-tokens.md).
- ✅ (2026-07-04) Medir consumo de tokens por fase y ajustar → [fases/07-tokens.md](fases/07-tokens.md) (F4 ~400k, F5 ~252k, F6 ~304k en subagentes; 7 ajustes: orquestador delgado, sonnet en writers/reviews, lentes proporcionales al riesgo, reutilizar writer vía SendMessage, estado en archivos, caveman, recuperación post session-limit). Sección "ciclo real" pendiente del ítem anterior.
- ✅ (2026-07-04) Documentar cómo agregar otra tecnología → [agregar-tecnologia.md](agregar-tecnologia.md) (qué es agnóstico: gestor+conector+skills+gates+engram; qué es Odoo-specific: entornos/, seeds, campos de plantilla).
- ✅ (2026-07-04) Documentar instalación en otra máquina → [instalacion-otra-maquina.md](instalacion-otra-maquina.md). Fixes derivados: `gestor-odoo/env.example` creado (README lo citaba pero no existía) y `conector-odoo/README.md` con `--scope user` explícito (gotcha F3: sin scope cae en local por cwd).
