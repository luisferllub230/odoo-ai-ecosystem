# Estándar Git y Commits

Reglas **obligatorias** para toda IA y humano del ecosistema. Basado en las [Odoo Git Guidelines](https://www.odoo.com/documentation/19.0/contributing/development/git_guidelines.html) + conventional commits.

## Ramas

- **NUNCA** trabajar ni commitear directo en la rama principal (`main`, `master`, `17.0`, `19.0`…).
- Nombre de rama: `<tipo>/<task_id>-<slug-corto>` — ej. `fix/1234-ir3-descuadre`, `feat/1301-payroll-bpd`.
- Rama siempre creada desde la principal actualizada (`git fetch && git checkout -b ... origin/<principal>`).

## Commits

- **NUNCA firmar como IA**: prohibido `Co-Authored-By: Claude`, `Generated with Claude Code` o similar. El autor es el usuario configurado en git.
- Formato:
  ```
  <tipo>(<modulo>): descripción corta de qué hace y a qué impacta

  Descripción técnica de lo que se hizo: qué se cambió, por qué,
  y cualquier detalle que el diff no explica solo.
  ```
- Tipos (tags Odoo): `fix`, `feat` (equivale a ADD/IMP), `ref` (refactor), `rem` (remove), `rev` (revert), `mov`, `imp`, `test`, `doc`, `i18n`, `perf`, `ci`.
- `<modulo>` = nombre técnico del módulo Odoo afectado (`l10n_do_hr_payroll`, no "nómina").
- Primera línea ≤ ~72 caracteres, imperativo, sin punto final. Línea en blanco antes del cuerpo.
- Un commit = un cambio lógico. No mezclar fix + refactor en un commit.

### Ejemplo

```
fix(l10n_do_hr_payroll): corrige doble conteo en reporte IR3

El cálculo de otros ingresos sumaba las entradas de tipo ALLOW dos
veces porque el dominio no excluía las líneas ya agregadas por la
regla salarial. Se filtra por code y se agrega test de regresión.
```

## PRs

- Título = primera línea del commit principal.
- Cuerpo: qué/por qué (del design.md) + cómo probar (enlace al manual de prueba). Sin firma de IA.
- Merge, deploy y borrado de rama: responsabilidad del humano.
