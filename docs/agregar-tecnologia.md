# Agregar otra tecnología (no-Odoo) al ecosistema

El ciclo (análisis → diseño → dev → prueba → PR) es agnóstico de tecnología; solo unas pocas piezas son específicas de Odoo. Decisión original: [00-arquitectura.md#escalado-futuro](00-arquitectura.md#escalado-futuro).

## Qué es genérico (se reutiliza tal cual)

- **Gestor Odoo de tareas** ([../gestor-odoo/](../gestor-odoo/README.md)): proyectos, etapas y supervisión humana sirven para cualquier stack.
- **Conector MCP** ([../conector-odoo/](../conector-odoo/README.md)): habla con el *gestor*, no con la tecnología objetivo; las 5 herramientas y el guard de transiciones no cambian.
- **Skills `tarea-*`** (F5): el flujo diseño → dev → prueba → PR es el mismo.
- **Gates humanos** ([00-arquitectura.md#gates-humanos](00-arquitectura.md#gates-humanos-invariantes-del-sistema)): invariantes del sistema, independientes del stack.
- **Engram**: memoria por proyecto, agnóstica.

## Qué es específico de Odoo (lo que hay que reemplazar/adaptar)

- **`entornos/`** (F4): plantillas Docker parametrizadas por versión de Odoo.
- **Seeds del manual-generator**: se ejecutan vía `odoo shell` contra entornos compose F4 ([../manual-generator/README.md#seeds](../manual-generator/README.md#seeds)).
- **Plantilla de tarea** ([estandares/plantilla-tarea.md](estandares/plantilla-tarea.md)): tiene campos Odoo (versión Odoo, módulo).

## Pasos para incorporar una tecnología X

1. **Proyecto nuevo en el gestor** con las mismas 7 etapas (`Backlog → Análisis/Diseño → Aprobado → Desarrollo → Prueba → PR/Review → Hecho`). El guard del conector funciona sin cambios.
2. **Variante de plantilla-tarea**: misma estructura, reemplazando los campos Odoo por los de la tecnología (repo, versión/runtime de X, criterios de aceptación).
3. **Equivalente de `entornos/` para X**: un contenedor dev estandarizado y reproducible (bootstrap parametrizado, convención de puertos, BD/estado de prueba por tarea). El patrón de [../entornos/README.md](../entornos/README.md) es la referencia.
4. **Skills `tarea-*`**: ya sirven, salvo los pasos de entorno y tests — parametrizarlos por tipo de proyecto (los comandos de bootstrap/BD/tests son lo único que cambia entre stacks).
5. **manual-generator**: sirve para cualquier aplicación web — `capture` es Playwright genérico. Lo único Odoo-specific son los seeds; para X, pre-cargar datos por otra vía o crearlos desde la UI en los `steps` del escenario (ya documentado en su README).
