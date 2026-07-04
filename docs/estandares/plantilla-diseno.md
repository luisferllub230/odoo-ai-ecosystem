# Plantilla de documento de diseño

Generado por la IA en la etapa de análisis (`docs/tareas/<task_id>/design.md`). Es lo que el humano aprueba o rechaza antes de cualquier desarrollo.

```markdown
# Diseño — [task_id] [título de la tarea]

## Factibilidad
**Veredicto**: FACTIBLE | FACTIBLE CON RIESGOS | NO FACTIBLE
[Justificación en 2-4 frases. Si NO FACTIBLE: por qué y alternativas.]

## Análisis
[Qué se encontró al explorar el código: módulos afectados, modelos,
vistas, flujos existentes. Referencias archivo:línea.]

## Diseño propuesto
[Solución técnica: qué modelos/campos/vistas/métodos se crean o
modifican. Diagramas si aportan. Decisiones y por qué.]

## Alcance
- Incluye: [...]
- NO incluye: [...]

## Riesgos e impacto
[Migraciones de datos, módulos dependientes, performance, compatibilidad.]

## Plan de prueba
[Escenarios que probará la etapa de prueba: datos semilla necesarios,
pasos, resultado esperado por escenario. Este plan alimenta el
manual-generator.]

## Estimación
[Tamaño relativo: S/M/L + qué lo hace costoso si aplica.]
```

## Reglas

- El análisis se hace explorando el repo real (no de memoria).
- Si la tarea es NO FACTIBLE o ambigua, el documento lo dice y la tarea vuelve al humano con preguntas concretas.
- Aprobado el diseño, es contrato: cambios de alcance durante el desarrollo se comentan en la tarea antes de implementarse.
