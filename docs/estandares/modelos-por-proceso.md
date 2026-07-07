# Modelos por proceso

Política **fuente de verdad** para elegir qué tier de modelo Claude usar según el tipo
de proceso. No usar el modelo más potente para todo: un análisis o decisión de
arquitectura necesita más capacidad de razonamiento, pero un paso mecánico o
guionizado (mover una tarea, comentar el chatter, formatear texto) lo resuelve
igual de bien un modelo compacto, a menor coste y latencia.

Convención del repo: **alias cortos** (`opus`, `sonnet`, `haiku`), nunca IDs
completos de modelo (nada de `claude-opus-4-8` ni similares) — ni en esta tabla,
ni en skills, ni en frontmatter de agentes.

## Los tres tiers

| Tier | Alias | Tipo de proceso | Ejemplos en el ecosistema |
|---|---|---|---|
| Potente | `opus` | Análisis, diseño, decisión de arquitectura, juicio adversarial de alto riesgo | `/tarea-diseno` (elaborar `design.md`), `sdd-design`, `sdd-propose`, review de hot paths |
| Medio | `sonnet` | Implementación, exploración de repo, tests, review estándar, verificación | `/tarea-dev`, subagente `Explore`, `sdd-apply`, `jd-*`, `review-*`, `sdd-verify` |
| Compacto | `haiku` | Mecánico/determinista: mover tarea, comentar chatter, formateo, PR admin, archive | `/tarea-pr` (push + PR + mover etapa), `/tarea-prueba` (pasos guionizados), `sdd-archive`, `sdd-onboard` |

## Regla de escalado y de-escalado

**Escalar** (subir un tier) si el proceso, aunque nominalmente simple, presenta
alguna de estas señales:

- Repo o módulo desconocido/no explorado antes.
- Requisitos ambiguos.
- Diseño con trade-offs relevantes (varias opciones válidas, impacto en arquitectura).
- Diff esperado > 400 líneas.

**De-escalar** (bajar un tier) si el proceso es puramente guionizado sobre datos
ya conocidos (pasos deterministas, sin decisiones que tomar).

La decisión de escalar/de-escalar y su motivo deben quedar **trazables**: en el
`design.md` de la tarea o en un comentario de la tarea (`comment_task`). No es una
decisión silenciosa.

## Relación con la asignación estática por rol

La asignación estática modelo↔rol de los subagentes globales ya vive en
`~/.claude/agents/*.md` (campo `model:` del frontmatter) y se sincroniza con
`gentle-ai sync --profile`. Esta política **no la duplica**: es la referencia
humana para entender y auditar esa asignación, y para decidir el tier cuando una
skill delega un subagente o cuando aplica la regla de escalado/de-escalado.

Tras tocar cualquier skill, correr `gentle-ai skill-registry refresh` para que
`.atl/skill-registry.md` quede al día.

## Referencias

- `docs/00-arquitectura.md` — principio "Modelos por fase" (sección Eficiencia de tokens).
- `docs/fases/07-tokens.md` — medición real de tokens por fase y ajustes aplicados.
- `.claude/skills/tarea-diseno/SKILL.md`, `tarea-dev`, `tarea-prueba`, `tarea-pr` — aplicación de esta política en el ciclo de tarea.
