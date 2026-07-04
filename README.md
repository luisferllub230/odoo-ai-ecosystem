# Odoo AI Ecosystem

Ecosistema de IA para gestionar el ciclo de vida completo del desarrollo de software (enfocado en Odoo, escalable a otras tecnologías). Un Odoo 19 dedicado actúa como **gestor central**: todo proyecto y tarea nace y muere allí. La IA (Claude Code + gentle-ai) ejecuta el ciclo completo — análisis, diseño, desarrollo, pruebas documentadas y PR — con intervención humana solo en **aprobación de diseño, code review y test funcional**.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│  ODOO GESTOR (contenedor dedicado, Odoo 19 Enterprise)      │
│  Proyectos > Tareas (plantillas, etapas, supervisión humana)│
└──────────────┬──────────────────────────────────────────────┘
               │ XML-RPC / API key (configurable → cualquier Odoo)
┌──────────────▼──────────────────────────────────────────────┐
│  CAPA IA (Claude Code + gentle-ai)                          │
│  · Engram: memoria persistente entre sesiones               │
│  · SDD workflows: análisis → diseño → dev → prueba → PR     │
│  · Skills + subagentes + MCP (conector Odoo)                │
│  · Estándares: git, commits, plantillas de docs             │
└──────────────┬──────────────────────────────────────────────┘
               │ opera sobre
┌──────────────▼──────────────────────────────────────────────┐
│  ENTORNOS DEV (Docker por versión de Odoo: 17, 19, ...)     │
│  Imágenes estandarizadas + BD de prueba + manual-generator  │
│  (capturas y manuales de prueba automatizados)              │
└──────────────┬──────────────────────────────────────────────┘
               │ push rama + PR
┌──────────────▼──────────────────────────────────────────────┐
│  GITHUB (multi-cuenta vía SSH) → humano aprueba y despliega │
└─────────────────────────────────────────────────────────────┘
```

## Ciclo de vida de una tarea

1. **Creación** — Humano crea la tarea en el Odoo gestor siguiendo plantilla (contexto, alcance, repo, versión Odoo).
2. **Análisis y diseño** — IA analiza factibilidad y genera documento de diseño en Markdown. ⛔ **Gate humano: aprobar/rechazar diseño.**
3. **Desarrollo** — IA crea rama (nunca `main`), desarrolla aplicando estándares, commits convencionales sin firma de IA.
4. **Prueba documentada** — IA prueba en BD dedicada y genera manual paso a paso con capturas (manual-generator). ⛔ **Gate humano: test funcional.**
5. **PR** — Si pasa, push de la rama y creación del PR. ⛔ **Gate humano: code review, merge y despliegue.**
6. **Cierre** — Humano cierra la tarea en Odoo; se ordena la siguiente.

## Estado del proyecto

El progreso real vive en [`docs/ROADMAP.md`](docs/ROADMAP.md) — **ese es el documento maestro**: cada fase con sus pasos y estado (✅ hecho / 🔄 en curso / ⬜ pendiente). Cualquier sesión de IA debe leerlo primero y marcarlo al completar pasos.

## Estructura del repo

```
odoo-ai-ecosystem/
├── README.md                     ← este archivo
├── docs/
│   ├── ROADMAP.md                ← documento maestro de progreso
│   ├── 00-arquitectura.md        ← decisiones y diseño global
│   ├── fases/                    ← guía paso a paso de cada fase
│   └── estandares/               ← git, commits, plantillas de tarea/diseño/prueba
├── gestor-odoo/                  ← (F2) compose del Odoo gestor
├── conector-odoo/                ← (F3) MCP/cliente RPC hacia cualquier Odoo
├── entornos/                     ← (F4) imágenes docker por versión de Odoo
└── manual-generator/             ← (F6) herramienta de capturas/manuales standalone
```

## Requisitos

- WSL2 (Ubuntu 24.04) con Docker Desktop **con WSL integration activa** en esta distro.
- Claude Code instalado.
- gentle-ai (`go install github.com/gentleman-programming/gentle-ai/cmd/gentle-ai@latest` o brew).
- Acceso SSH a GitHub (multi-cuenta ya configurado en `~/.ssh/config`).
- Imagen/fuentes de Odoo 19 Enterprise (existentes en `~/repos/odoo_pro_19`).

## Uso de tokens (principio rector)

Toda la arquitectura prioriza eficiencia de tokens: memoria persistente (Engram) en vez de re-explicar contexto, documentos de estado (`ROADMAP.md`) para retomar trabajo entre sesiones, subagentes solo cuando aportan, skills con instrucciones precargadas, y plantillas que evitan regenerar estructura. Ver `docs/00-arquitectura.md#eficiencia-de-tokens`.
