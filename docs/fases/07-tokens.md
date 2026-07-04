# Fase 7 — Consumo de tokens por fase y ajustes

**Objetivo**: dejar registro real del costo en tokens de construir el ecosistema, y la lista de ajustes que lo mantienen bajo control. Principios generales: [../00-arquitectura.md#eficiencia-de-tokens](../00-arquitectura.md#eficiencia-de-tokens).

## Medición — sesión de construcción (F4–F6)

Tokens de subagentes medidos por el orquestador. El hilo del orquestador **no** se midió con precisión; mantenerlo delgado es el ajuste principal.

### F4 — entornos (~400k)

| Subagente | Tokens |
|---|---|
| Auditoría Explore | no medido |
| Writer | 89.6k |
| Verificación E2E | 64.2k |
| review-reliability | 71.7k |
| review-resilience | 48.9k |
| Fixer + re-E2E | 122.8k |

### F5 — skills (~252k)

| Subagente | Tokens |
|---|---|
| Writer | 55.7k |
| review-readability | 49.5k |
| Prueba dummy E2E | 74.9k |
| Fixer | 72.1k |

### F6 — manual-generator (~304k)

| Subagente | Tokens |
|---|---|
| Writer + E2E | 100.6k |
| review-reliability | 80.4k |
| Fixer | ~123k * |

\* El fixer murió por session limit a mitad de trabajo; el orquestador recuperó el estado desde disco y terminó inline (ver lección abajo).

## Ajustes aplicados y recomendados

- **Orquestador delgado**: delega TODO trabajo real a subagentes; el hilo principal solo coordina y sintetiza.
- **Modelos por fase**: writers/tests/reviews en sonnet; orquestación en modelo mayor.
- **Lentes de review proporcionales al riesgo**: 1 lente para docs/texto, 2 (reliability + resilience) para shell/estado, 4R solo en hot paths o diffs >400 líneas.
- **Reutilizar el MISMO subagente writer para fixes** (vía SendMessage): conserva contexto y evita re-lectura del repo.
- **Estado en archivos, no en conversación**: auditorías → `docs/`, decisiones → engram. Nunca re-explorar lo ya documentado.
- **Modo caveman** en las respuestas del orquestador (comunicación comprimida sin perder precisión técnica).
- **Lección session-limit**: los agentes de fixes largos dejan estado recuperable en disco — tras un corte, inspeccionar los archivos antes de relanzar (el trabajo hecho suele estar ahí; relanzar de cero duplica el gasto).

## Ciclo real (pendiente)

Métricas del ciclo completo con una tarea real (F7 ítem 1). Completar al ejecutarlo:

| Workflow | Subagentes | Tokens | Notas |
|---|---|---|---|
| tarea-diseno | | | |
| tarea-dev | | | |
| tarea-prueba | | | |
| tarea-pr | | | |
| Cierre (engram) | | | |
