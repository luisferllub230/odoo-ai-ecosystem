# odoo-ai-ecosystem

Hub de gobierno del ecosistema IA para desarrollo Odoo. **Antes de trabajar: leer `docs/ROADMAP.md`** (documento maestro de progreso); al completar pasos, marcarlos ahí con fecha.

## Reglas duras

- **Gates humanos** (nunca cruzarlos solo): aprobación de diseño, test funcional, code review/merge/deploy. Detalle: `docs/00-arquitectura.md`.
- **Git**: nunca trabajar en la rama principal; commits SIN firma de IA; formato `tipo(modulo): descripción` + cuerpo técnico. Detalle: `docs/estandares/git-commits.md`.
- No avanzar dos fases del ROADMAP en paralelo.

## Memoria y SDD

- Persistencia SDD: **engram** (proyecto `odoo-ai-ecosystem`). No crear `openspec/`.
- Contexto del proyecto: `engram search sdd-init --project odoo-ai-ecosystem`.
- Decisiones nuevas → `engram save ... --type decision --project odoo-ai-ecosystem`.
- Registry de skills: `.atl/skill-registry.md` (refrescar con `gentle-ai skill-registry refresh` tras tocar skills).

## Plantillas (rellenar, no inventar estructura)

- Tarea Odoo: `docs/estandares/plantilla-tarea.md`
- Diseño: `docs/estandares/plantilla-diseno.md`
- Manual de prueba: `docs/estandares/plantilla-manual-prueba.md`

## Eficiencia de tokens

Estado en archivos/engram, no en conversación. Delegar exploraciones largas a subagentes baratos. Documentos cortos que enlazan, no duplican.
