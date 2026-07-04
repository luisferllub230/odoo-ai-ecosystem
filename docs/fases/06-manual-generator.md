# Fase 6 — manual-generator standalone

**Objetivo**: extraer `~/repos/odoo_pro_19/tools/manual-generator` como herramienta independiente, reutilizable contra cualquier Odoo.

## Estado actual (auditado 2026-07-03)

- Node + Playwright: `capture.mjs` (capturas navegando Odoo), `render-manual.mjs` (render del manual), `generate-manual.sh` (orquestación), `configs/*.json` + `configs/*.seed.py` (escenarios por módulo con seeds de datos).
- Acoplado al entorno odoo_pro_19 (rutas/credenciales implícitas).

## Pasos

1. **Mover** a `manual-generator/` en este repo (histórico no crítico; si se quiere preservar, `git filter-repo` en repo aparte).
2. **Desacoplar**: toda referencia a URL/BD/credenciales pasa a config (`--profile` reutilizando los perfiles del conector F3, o flags/env).
3. **CLI única** (`manual-gen`):
   - `manual-gen capture --config <escenario.json> --profile <odoo>` — ejecuta seed + capturas.
   - `manual-gen render --config <escenario.json> --out <dir>` — genera manual md/pdf.
   - `manual-gen run ...` — ambos.
4. **Convención de escenarios por tarea**: el workflow de prueba (F5) genera el JSON del escenario en `docs/tareas/<task_id>/` y llama a `manual-gen run`.
5. **Mejoras** (después de que funcione desacoplado, no antes):
   - Reintentos/waits robustos en Playwright.
   - Salida markdown con imágenes relativas (para adjuntar a Odoo/PR).
   - Modo headless configurable.

## Criterio de salida

`manual-gen run` genera un manual con capturas contra el Odoo gestor o un entorno dev, ejecutado desde fuera de odoo_pro_19. Los escenarios existentes en configs/ siguen funcionando. Marcar en ROADMAP.
