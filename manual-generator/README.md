# manual-generator

Genera manuales de usuario de Odoo (capturas PNG + manual markdown) contra **cualquier instancia Odoo accesible**, definidos por escenarios JSON. Extraído de `odoo_pro_19/tools/manual-generator` (F6) y desacoplado: sin URLs, BDs, credenciales ni rutas hardcodeadas.

## Instalación

```bash
cd manual-generator
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install   # si ~/.cache/ms-playwright ya tiene chromium-1208
# Si el navegador no está en caché (falla el launch con "Executable doesn't exist"):
npx playwright install chromium
```

La versión de Playwright está fijada en `~1.58` para coincidir con el Chromium ya cacheado (`chromium-1208`). Se usa el Chromium empaquetado de Playwright; con `--channel chrome` se puede usar el Chrome del sistema (comportamiento de la herramienta original).

## Conexión y credenciales

Tres formas, en orden de precedencia (flags > perfil):

1. **Perfil**: `--profile <nombre>` lee `../conector-odoo/profiles.yml` (o `--profiles-file` / env `MANUAL_GEN_PROFILES`). Se usan `url`, `db`, `user`; los `${VAR}` se expanden desde el entorno.
2. **Flags explícitos**: `--url http://host:puerto --db <bd> --user <login>`.
3. **Password**: **solo por entorno**, nunca por flag ni archivo:
   - `ui_password: ${MI_VAR}` en el perfil (referencia a env), o
   - env `ODOO_UI_PASSWORD`.

> ⚠️ El login web necesita la **password real del usuario**. Una `api_key` XML-RPC (como la del perfil `gestor` del conector) **no sirve** para abrir sesión en la UI.

## Uso

```bash
export ODOO_UI_PASSWORD=...   # password del usuario de la UI

# Seed (si aplica) + capturas:
npx manual-gen capture --config configs/<escenario>.json --profile <perfil>

# Solo render del manual (usa las capturas ya existentes en <out>/img/):
npx manual-gen render --config configs/<escenario>.json --out <dir>

# Ambos:
npx manual-gen run --config configs/<escenario>.json --profile <perfil> --out <dir>
```

- `--out` por defecto: la carpeta del config. Salida: `<out>/manual-<module>.md` + `<out>/img/*.png`. Las imágenes se referencian **relativas** (`img/<id>.png`), así la carpeta completa se puede adjuntar a una tarea de Odoo o a una PR.
- `--headed` muestra el navegador (debug); por defecto headless.
- Ayuda completa: `npx manual-gen help`.

## Seeds

Los seeds son scripts Python (`configs/<escenario>.seed.py`, mismo nombre base que el config) que corren dentro de `odoo shell` con el global `env` disponible y terminan con `env.cr.commit()` — igual que en la herramienta original.

`odoo shell` requiere acceso al proceso Odoo, por lo que el seed **solo se ejecuta contra entornos locales docker compose (F4)**: pásale `--compose-dir <dir-del-entorno>` y el CLI corre `docker compose exec -T odoo odoo shell -d <bd> --no-http < seed.py`. Sin `--compose-dir`, el seed se omite con un warning (usar `--no-seed` para silenciarlo). Para instancias remotas: pre-cargar los datos por otra vía o crear los datos desde la propia UI en los `steps` del escenario.

La preparación de la BD (crear BD e instalar el módulo) queda **fuera** de la herramienta: usar los comandos de [entornos/GUIA-AGENTES.md](../entornos/GUIA-AGENTES.md) §3–4 (p. ej. `docker compose exec odoo odoo -d <bd> -i <modulo> --stop-after-init`).

## Formato del escenario JSON

Compatible con los configs originales de odoo_pro_19 (sin cambios de esquema):

```jsonc
{
  "module": "mi_modulo",              // usado en el nombre del manual: manual-<module>.md
  "title": "Mi Módulo — Manual de usuario",
  "intro": "Texto introductorio (markdown).",
  "requirements": ["Requisito 1"],
  "flows": [
    {
      "id": "01-algo",                // nombre de la captura: img/01-algo.png
      "title": "1. Paso",
      "description": "Texto del paso (markdown).",
      "screenshotEl": ".o_content",   // opcional: capturar solo ese elemento
      "steps": [
        { "goto": "/odoo/action-mi_modulo.mi_accion" },
        { "waitFor": ".o_list_view", "timeout": 30000 },
        { "fill": ".o_searchview_input", "value": "texto" },
        { "type": ".o_searchview_input", "value": "texto" },   // tecleo con delay (autocomplete)
        { "press": "Enter" },
        { "click": ".o_data_row:first-child .o_data_cell" },
        { "selectOption": "select.o_input", "label": "Opción" },
        { "scrollTo": ".o_group" },
        { "hover": ".breadcrumb" },
        { "waitForHidden": ".o_loading" },
        { "wait": 1000 }
      ]
    },
    { "id": "99-final", "title": "Solo texto", "description": "Sin captura.", "image": false }
  ],
  "notes": "Notas finales (markdown)."
}
```

## Convención por tarea (workflow F5)

El workflow `/tarea-prueba` genera el escenario en `docs/tareas/<task_id>/escenario.json` y ejecuta:

```bash
npx manual-gen run --config docs/tareas/<task_id>/escenario.json \
    --url http://localhost:<puerto-F4> --db test_<task_id> --user admin \
    --compose-dir <dir-entorno-F4> --out docs/tareas/<task_id>/
```

Salida: `docs/tareas/<task_id>/manual-<module>.md` + `img/` — listos para `attach_doc`.

## Smoke test

`configs/smoke-f4.json` es el smoke test documentado del pipeline contra un entorno F4 (ver su `intro` para los comandos exactos). Se dejó como criterio de salida E2E de la F6.

## Componentes

| Archivo | Rol |
|---------|-----|
| `bin/manual-gen.mjs` | CLI única (`capture` / `render` / `run`) |
| `lib/profiles.mjs` | Carga de perfiles YAML + expansión `${VAR}` + resolución de conexión |
| `lib/capture.mjs` | Login JSON-RPC + navegación + capturas (Playwright) |
| `lib/render.mjs` | Arma el manual markdown con imágenes relativas |
| `lib/seed.mjs` | Ejecuta seeds vía `docker compose exec odoo odoo shell` |
| `configs/*.json` | Escenarios (copiados de odoo_pro_19, siguen válidos) |
| `configs/*.seed.py` | Seeds de datos (odoo shell) |
