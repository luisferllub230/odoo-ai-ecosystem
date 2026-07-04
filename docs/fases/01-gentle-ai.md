# Fase 1 — Base gentle-ai + Claude Code

**Objetivo**: dejar el orquestador operativo con memoria persistente y reglas del ecosistema.

## Pasos

1. **Instalar gentle-ai** (binario Go):
   ```bash
   brew tap Gentleman-Programming/homebrew-tap && brew install gentle-ai
   # o sin brew:
   go install github.com/gentleman-programming/gentle-ai/cmd/gentle-ai@latest
   ```
   Verificar: `gentle-ai doctor`.

2. **Inicializar SDD en este repo**: ejecutar `/sdd-init` desde el agente (detecta stack, crea estructura openspec/SDD).

3. **Engram (memoria persistente)**:
   - Validar que quedó activo: `engram projects list`.
   - Uso: decisiones, bugs conocidos y contexto de cada proyecto quedan en memoria entre sesiones — evita re-explicar.
   - Para replicar en otra máquina: `engram sync`.

4. **Skill registry**: `gentle-ai skill-registry refresh` tras agregar/editar skills en el repo.

5. **CLAUDE.md del repo** (crear en la raíz), contenido mínimo:
   - Leer `docs/ROADMAP.md` antes de trabajar; marcar avances allí.
   - Respetar gates humanos (ver `docs/00-arquitectura.md`).
   - Estándares de git/commits: `docs/estandares/git-commits.md` (nunca main, sin firma IA).
   - Enlaces a plantillas, no contenido duplicado.

6. **Perfil SDD (modelos por fase)**: configurar perfil con `gentle-ai sync --profile <nombre>`:
   - Diseño/análisis → modelo potente.
   - Implementación → modelo rápido.
   - Exploración/búsqueda → modelo económico.

## Criterio de salida

`gentle-ai doctor` limpio, Engram registrando, CLAUDE.md creado, perfil SDD activo. Marcar en ROADMAP.
