# Plantilla de tarea (Odoo gestor)

Toda tarea creada en el Odoo gestor debe seguir esta estructura en su descripción. La IA rechaza (comenta y devuelve a Backlog) tareas sin los campos obligatorios.

```markdown
## Contexto
[Qué problema/necesidad existe. Comportamiento actual vs esperado.]

## Objetivo
[Qué debe existir/funcionar al terminar. Una frase medible.]

## Alcance técnico
- Repo: [ej. git@github.com-afinancer:org/repo.git]
- Rama base: [ej. 19.0]
- Versión Odoo: [17 | 19 | ...]
- Módulo(s): [nombre técnico, o "nuevo: <nombre_propuesto>"]

## Criterios de aceptación
- [ ] [Criterio verificable 1]
- [ ] [Criterio verificable 2]

## Referencias (opcional)
[Capturas, tickets, docs, normativa DGII, etc.]
```

## Campos obligatorios

`Contexto`, `Objetivo`, `Repo`, `Rama base`, `Versión Odoo`, al menos 1 criterio de aceptación.

## Etapas y quién mueve

| Transición | Responsable |
|---|---|
| Backlog → Análisis/Diseño | Humano (orden de analizar) |
| Análisis/Diseño → Aprobado | **Humano (gate: aprueba diseño)** |
| Aprobado → Desarrollo → Prueba | IA |
| Prueba → PR/Review | IA (tras OK del humano en test funcional) |
| PR/Review → Hecho | **Humano (gate: merge + deploy)** |
