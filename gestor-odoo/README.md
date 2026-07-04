# gestor-odoo — Instancia Odoo 19 Enterprise de gestión

Instancia dedicada donde nacen y mueren todos los proyectos/tareas del ecosistema IA
(fase 2 del ROADMAP, ver `../docs/fases/02-odoo-gestor.md`). Totalmente independiente
de los entornos dev: red propia (`gestor_network`), postgres propio (`postgres:17`) y
puerto propio (`8169`). No se une a `odoo_shared_network` ni monta carpetas del repo dev
en tiempo de ejecución, con una única excepción documentada: las fuentes Enterprise.

## Fuentes Enterprise — decisión

**Opción elegida (por defecto)**: la variable `ENTERPRISE_PATH` del `.env` apunta a
`/home/lfernandez/repos/odoo_pro_19/enterprise` y se monta en **solo lectura**
(`/mnt/enterprise:ro`). Evita duplicar ~760 módulos en disco; el `:ro` garantiza que
esta instancia nunca modifica las fuentes del repo dev.

**Alternativa**: copiar las fuentes a `gestor-odoo/enterprise/` (ya gitignorada) y poner
`ENTERPRISE_PATH=./enterprise` en el `.env`. Útil si se quiere desacoplar del repo dev
o fijar una revisión concreta.

## Levantar la instancia

```bash
cp env.example .env      # editar contraseñas y rutas
# Cambiar también admin_passwd en config/odoo.conf (mismo valor que ODOO_MASTER_PASSWORD)
docker compose build
docker compose run --rm odoo odoo -d gestor -i project --stop-after-init   # inicializa la BD
docker compose up -d
```

Odoo queda disponible en <http://localhost:8169> (login inicial `admin` / `admin`; cambiarlo).

- Para incluir asignación por empleado, añadir `hr`: `-i project,hr`.
- La config vive en `config/odoo.conf` (montada en el contenedor): editar y `docker compose restart odoo`.
- Logs: `docker compose logs -f odoo`.

## Siguientes pasos manuales (fase 2)

1. **Usuario API**: crear usuario `ai-agent` con permisos solo de Proyecto y generar su
   API key en *Ajustes → Seguridad → API Keys*. Guardar la key en el `.env` local, nunca commitearla.
2. **Proyecto plantilla** con etapas:
   `Backlog → Análisis/Diseño → Aprobado → Desarrollo → Prueba → PR/Review → Hecho`
   - La IA solo mueve: Aprobado→Desarrollo→Prueba y Prueba→PR/Review.
   - El humano mueve: Backlog→Análisis, Análisis→Aprobado (gate), PR/Review→Hecho (gate).
3. **Plantilla de tarea**: configurar `../docs/estandares/plantilla-tarea.md` como
   descripción por defecto del proyecto plantilla.
4. Verificar la API key con un cliente `xmlrpc` simple y marcar la fase en el ROADMAP.
