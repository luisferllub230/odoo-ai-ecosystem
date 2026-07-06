# Arquitectura y decisiones

## Contexto de la máquina (relevado 2026-07-03)

- Windows + WSL2 (Ubuntu 24.04). 12 cores, 15 GB RAM asignada a WSL, RTX 5060 8GB, ~1 TB SSD.
- Docker Desktop en Windows; **WSL integration pendiente de activar** en esta distro.
- SSH multi-cuenta GitHub: `github.com-personal` (id_ed25519), `github.com-afinancer`, `github.com-pgs`.
- Repos existentes relevantes:
  - `~/repos/odoo_pro_19` — entorno dev Odoo 19 (compose, Dockerfile, enterprise/, odoo-pro/, tools/manual-generator).
  - `~/repos/odoo_pro_17` — entorno dev Odoo 17.
  - `~/repos/odoo_dev_env` — bootstrap + templates de compose/Dockerfile.

## Decisiones (2026-07-03)

| Decisión | Elección | Motivo |
|---|---|---|
| Orquestador | **gentle-ai** sobre Claude Code | Engram (memoria persistente), SDD workflows, skill registry, modelos por fase, MCP. Reduce tokens re-explicando contexto. |
| Odoo gestor | Contenedor **dedicado y nuevo**, Odoo 19 **Enterprise**, carpeta propia | Aislado de entornos dev; debe poder escalar como proyecto personal independiente. Reutiliza imagen/fuentes enterprise existentes. |
| Conexión al gestor | XML-RPC/JSON-RPC + API key, por **perfiles** | Intercambiable: mismo conector sirve para el gestor local o cualquier Odoo de cliente. |
| Repo del ecosistema | GitHub cuenta **personal** | Portabilidad a otras máquinas. |
| Entornos dev | Docker, imágenes parametrizadas por versión de Odoo | Ya todo funciona por contenedores; patrón existente en odoo_dev_env/odoo_pro_*. |

## Gates humanos (invariantes del sistema)

La IA **nunca** cruza estos puntos sola:

1. **Aprobación de diseño** — tras análisis de factibilidad + design.md.
2. **Test funcional** — el humano ejecuta el manual de prueba generado.
3. **Code review / merge / deploy** — PR lo aprueba y despliega el humano.
4. Creación y cierre de tareas en Odoo gestor: supervisado por humano.

## Eficiencia de tokens

Principios que toda pieza del ecosistema debe respetar:

- **Estado en archivos, no en conversación**: `ROADMAP.md`, `design.md` por tarea, Engram. Una sesión nueva lee estado, no re-deriva.
- **Modelos por fase** (perfil SDD de gentle-ai): potente para diseño/análisis, rápido/económico para implementación mecánica y exploración. Política proceso→tier: [modelos-por-proceso](estandares/modelos-por-proceso.md).
- **Subagentes con propósito**: delegar exploraciones largas de código a agentes de contexto barato; el hilo principal se mantiene delgado (patrón orchestrator-thin de gentle-ai).
- **Plantillas**: tarea, diseño, manual de prueba, PR — la IA rellena, no inventa estructura.
- **Skills precargados** en vez de prompts repetidos.
- **CLAUDE.md corto** y enlazando a docs, no duplicando contenido.

## Escalado futuro

- Otras tecnologías: el ciclo (análisis → diseño → dev → prueba → PR) es agnóstico; lo específico de Odoo vive en `entornos/` (imágenes) y `conector-odoo/`. Nueva tecnología = nueva carpeta de entorno + estándares propios.
- Otras máquinas: clonar este repo + `bootstrap` (F7) reinstala gentle-ai, MCPs y configs.
