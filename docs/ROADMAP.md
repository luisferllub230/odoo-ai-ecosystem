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
- ⬜ Reiniciar Claude Code para que cargue los subagentes sdd-* instalados (hoy los skills se ejecutan inline). **Acción humana.**

## Fase 2 — Odoo Gestor

Guía: [fases/02-odoo-gestor.md](fases/02-odoo-gestor.md)

- ⬜ Crear carpeta `gestor-odoo/` con `docker-compose.yml` propio (Odoo 19 Enterprise + Postgres dedicado, red aislada, puerto distinto a los entornos dev).
- ⬜ Reutilizar Dockerfile/fuentes enterprise de `~/repos/odoo_pro_19` sin acoplar (copiar/parametrizar, no montar el repo dev).
- ⬜ Inicializar BD con módulo `project` y crear usuario API con API key.
- ⬜ Configurar proyecto plantilla con etapas del ciclo: `Backlog → Análisis/Diseño → Aprobado → Desarrollo → Prueba → PR/Review → Hecho`.
- ⬜ Documentar plantilla de tarea (campos obligatorios: contexto, repo, versión Odoo, criterios de aceptación) → [estandares/plantilla-tarea.md](estandares/plantilla-tarea.md).
- ⛔ Humano valida: crear proyecto y tarea de prueba end-to-end.

## Fase 3 — Conector Odoo (RPC/API key)

Guía: [fases/03-conector-odoo.md](fases/03-conector-odoo.md)

- ⬜ Crear `conector-odoo/`: cliente XML-RPC/JSON-RPC configurable por perfil (`url`, `db`, `usuario`, `api_key`) — sirve para el gestor local y cualquier Odoo remoto.
- ⬜ Exponerlo como servidor MCP para Claude Code (herramientas: listar tareas, leer tarea, mover etapa, comentar, adjuntar docs).
- ⬜ Configurar el MCP en Claude Code/gentle-ai y probar lectura de la tarea de prueba de F2.

## Fase 4 — Entornos dev estandarizados

Guía: [fases/04-entornos-dev.md](fases/04-entornos-dev.md)

- ⬜ Auditar `odoo_dev_env`, `odoo_pro_17`, `odoo_pro_19` y extraer patrón común.
- ⬜ Crear `entornos/`: Dockerfile base parametrizado por versión de Odoo (17/19/…) + compose template + script bootstrap por proyecto/tarea.
- ⬜ Estandarizar: BD de prueba por tarea, puertos por desarrollador/versión, red compartida, volúmenes de addons.
- ⬜ Documentar cómo un agente levanta/destruye un entorno para una tarea concreta.

## Fase 5 — Flujo de desarrollo IA

Guía: [fases/05-flujo-desarrollo.md](fases/05-flujo-desarrollo.md)

- ⬜ Workflow **análisis/diseño**: skill/comando que toma tarea de Odoo, valida factibilidad y genera `design.md` (plantilla en [estandares/plantilla-diseno.md](estandares/plantilla-diseno.md)). ⛔ Gate humano: aprobación.
- ⬜ Workflow **desarrollo**: crear rama desde plantilla de nombre, aplicar [estandares/git-commits.md](estandares/git-commits.md) (nunca main, sin firma IA, conventional commits estilo Odoo).
- ⬜ Workflow **prueba**: BD de prueba + manual paso a paso con capturas (usa manual-generator, F6). ⛔ Gate humano: test funcional.
- ⬜ Workflow **PR**: push de rama, crear PR con descripción estándar. ⛔ Gate humano: review + merge + deploy.
- ⬜ Workflow **cierre**: actualizar tarea en Odoo (etapa Hecho + enlace a PR/docs).

## Fase 6 — manual-generator standalone

Guía: [fases/06-manual-generator.md](fases/06-manual-generator.md)

- ⬜ Extraer `odoo_pro_19/tools/manual-generator` a `manual-generator/` (o repo propio) desacoplado del entorno dev.
- ⬜ Parametrizar: URL/BD/credenciales del Odoo objetivo por config, no hardcodeado.
- ⬜ Mejorar: CLI única (`capture` + `render`), configs de captura por tarea, salida a carpeta de docs de la tarea.
- ⬜ Integrarlo al workflow de prueba (F5).

## Fase 7 — Cierre de ciclo y escalado

- ⬜ Probar ciclo completo con una tarea real: Odoo → diseño → dev → prueba → PR → cierre.
- ⬜ Medir consumo de tokens por fase y ajustar (subagentes, modelos por fase, compresión de contexto).
- ⬜ Documentar cómo agregar otra tecnología (no-Odoo) al ecosistema.
- ⬜ Documentar instalación en otra máquina (clonar repo + bootstrap).
