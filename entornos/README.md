# entornos/ — generador de entornos dev Odoo

Genera entornos Docker de desarrollo Odoo parametrizados por versión (16–19+), con debugpy, BD externa o embebida, y convenciones únicas de puertos y BDs de prueba.

```bash
./bootstrap.sh <proyecto> <version> --db compose   # ver --help para todos los flags
```

- **Operación (comandos exactos para agentes)**: [`GUIA-AGENTES.md`](GUIA-AGENTES.md)
- **Auditoría que originó el diseño** (patrón común, difs 17/19, gotchas): [`../docs/fases/04-auditoria.md`](../docs/fases/04-auditoria.md)
- **Objetivo de fase**: [`../docs/fases/04-entornos-dev.md`](../docs/fases/04-entornos-dev.md)
- **Plantillas**: [`templates/`](templates/) — Dockerfile con flags pip condicionados por versión, compose external/embebido, entrypoint con espera de Postgres.
