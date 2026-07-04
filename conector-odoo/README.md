# conector-odoo

Puente entre la capa IA y cualquier Odoo, configurable por perfiles. Cliente XML-RPC mínimo (stdlib) expuesto como servidor MCP por stdio con 5 herramientas de gestión de tareas.

## Perfiles

La conexión se define en `profiles.yml`. Los secretos nunca se escriben en el archivo: se referencian con `${VAR}` y se leen del entorno.

```yaml
gestor:
  url: http://localhost:8169
  db: gestor
  user: ai-agent
  api_key: ${GESTOR_API_KEY}
```

Cambiar de Odoo = agregar un perfil y pasar su nombre en cada herramienta. El archivo se busca en: `CONECTOR_ODOO_PROFILES` (ruta explícita), el directorio de trabajo, o la raíz de este paquete.

## Herramientas MCP

| Herramienta | Descripción |
|---|---|
| `list_tasks(profile, project?, stage?)` | Lista tareas (id, nombre, etapa, proyecto), con filtros opcionales |
| `get_task(profile, task_id)` | Detalle completo: descripción, etapa, asignados, adjuntos, últimos mensajes |
| `move_task(profile, task_id, stage)` | Mueve la tarea de etapa (solo transiciones permitidas a la IA) |
| `comment_task(profile, task_id, body)` | Comentario en la bitácora (chatter) |
| `attach_doc(profile, task_id, file_path)` | Sube un archivo local como adjunto y lo referencia en la bitácora |

### Transiciones permitidas a la IA

| Transición | Permitida |
|---|---|
| Aprobado → Desarrollo | Sí |
| Desarrollo → Prueba | Sí |
| Prueba → PR/Review | Sí |
| Cualquier otra | No — gate humano (ver `docs/estandares/plantilla-tarea.md`) |

Los gates humanos (orden de analizar, aprobación de diseño, merge + deploy) nunca los cruza la IA: `move_task` rechaza esas transiciones con un error explicativo.

## Instalación

```bash
cd conector-odoo
python3 -m venv .venv
.venv/bin/pip install -e .
```

Para desarrollo (tests): `.venv/bin/pip install -e '.[dev]'` y `.venv/bin/pytest`.

## Registro en Claude Code

```bash
claude mcp add gestor-odoo --scope user \
  -e GESTOR_API_KEY=<api_key_del_usuario_ai-agent> \
  -- /home/lfernandez/repos/odoo-ai-ecosystem/conector-odoo/.venv/bin/conector-odoo-mcp
```

El servidor corre desde cualquier directorio: si no encuentra `profiles.yml` en el cwd, usa el de la raíz del paquete.

## Solución de problemas

- **"API key inválida o expirada"**: regenerar la clave en Odoo (Preferencias → Seguridad de la cuenta → Claves API) y actualizar `GESTOR_API_KEY`. Las claves pueden tener fecha de caducidad.
- **"Autenticación fallida ... verifique que la base de datos exista"**: el campo `db` del perfil no coincide con una base real, o el `user` (login) es incorrecto. El login del gestor local es exactamente `ai-agent`.
- **"Variable de entorno 'X' no definida"**: el perfil referencia `${X}` y no está exportada; pasarla con `-e` al registrar el MCP o exportarla en el shell.
- **"No se pudo conectar"**: el contenedor de Odoo no está arriba o el puerto del perfil es incorrecto.
