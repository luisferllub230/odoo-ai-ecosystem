# Fase 2 — Odoo Gestor (contenedor dedicado)

**Objetivo**: Odoo 19 Enterprise propio donde nacen y mueren todos los proyectos/tareas. Independiente de los entornos dev; escalable como proyecto personal.

## Prerrequisito

Docker Desktop con WSL integration activa en esta distro (acción humana; verificar con `docker ps`).

## Pasos

1. **Carpeta `gestor-odoo/`** en este repo con:
   - `docker-compose.yml`: servicio `odoo` (imagen propia) + `db` (postgres dedicado). Red propia (`gestor_network`), NO la `odoo_shared_network` de los entornos dev. Puerto que no choque con dev (p. ej. `8169:8069`).
   - `Dockerfile`: partir del de `~/repos/odoo_pro_19` (parametrizado), copiando lo necesario — no montar carpetas del repo dev.
   - `.env.example` con todas las variables (puertos, credenciales BD, ruta enterprise).
   - Volumen para filestore + volumen/bind para addons enterprise.
2. **Fuentes Enterprise**: montar desde una copia propia (p. ej. `gestor-odoo/enterprise/` en `.gitignore`, o variable `ENTERPRISE_PATH` apuntando a `~/repos/odoo_pro_19/enterprise`). Documentar la opción elegida.
3. **Inicializar BD** (`gestor`) instalando `project` (+ `hr` si se quiere asignación por empleado).
4. **Usuario API**: crear usuario `ai-agent` (permisos solo de Proyecto) y generar API key (Ajustes → Seguridad → API Keys). Guardar en `.env` local, nunca commiteada.
5. **Proyecto plantilla** con etapas:
   `Backlog → Análisis/Diseño → Aprobado → Desarrollo → Prueba → PR/Review → Hecho`
   - La IA solo mueve: Aprobado→Desarrollo→Prueba y Prueba→PR/Review.
   - El humano mueve: Backlog→Análisis, Análisis→Aprobado (gate), PR/Review→Hecho (gate).
6. **Plantilla de tarea**: ver `../estandares/plantilla-tarea.md`. Configurarla como descripción por defecto del proyecto plantilla.

## Criterio de salida

Odoo gestor arriba en su puerto, API key funcionando (probar con `xmlrpc` simple), proyecto de prueba con una tarea creada por el humano. Marcar en ROADMAP.
