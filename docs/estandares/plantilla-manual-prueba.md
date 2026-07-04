# Plantilla de manual de prueba

Generado por la IA tras el desarrollo (`docs/tareas/<task_id>/manual-prueba.md` + carpeta `img/`). Es lo que el humano ejecuta en el gate de test funcional. Las capturas las produce manual-generator (F6).

```markdown
# Manual de prueba — [task_id] [título]

## Entorno
- Odoo: [versión] en [URL entorno de prueba]
- Base de datos: test_[task_id]
- Usuario de prueba: [login / rol]
- Rama: [nombre de la rama]
- Preparación: [comando para levantar entorno + cargar seed, ej.
  `./bootstrap.sh ... && manual-gen run --config ...`]

## Datos semilla
[Qué datos precarga el seed y por qué existen: empleados, facturas,
productos, etc.]

## Escenario 1: [nombre]
**Objetivo**: [qué valida, ligado a un criterio de aceptación]

1. [Paso exacto: menú, botón, valor a ingresar]
   ![captura](img/e1-p1.png)
2. [...]

**Resultado esperado**: [qué debe verse/calcularse exactamente]

## Escenario 2: ...

## Casos borde probados por la IA
[Lo que la IA ya verificó (tests automáticos/manuales) y no requiere
repetición humana, con evidencia.]
```

## Reglas

- Cada criterio de aceptación de la tarea debe estar cubierto por al menos un escenario.
- Pasos reproducibles desde cero: un humano sin contexto debe poder ejecutarlos.
- Toda pantalla relevante lleva captura.
- Si el humano reporta fallo, el feedback se registra en la tarea Odoo y el ciclo vuelve a desarrollo; el manual se regenera.
