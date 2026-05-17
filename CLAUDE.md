
# CONTEXTO

TFG: simulador de red social multiagente basado en `mesa 3.x` y `networkx`. Modela la propagación de mensajes entre ciudadanos (agentes) sobre un grafo, con recogida de trazas para análisis offline.

## Código en `src/`

- `agents/` — `BaseAgent` (abstracto, `mesa.Agent`) y `StochasticAgent` (dispara mensaje a un vecino aleatorio con `fire_probability`).
- `graphs/` — `BaseGraph` con construcción lazy; topologías `ErdosRenyiGraph`, `BarabasiAlbertGraph`, `WattsStrogatzGraph`, `HyperGraph` (clique projection) y `SNAPGraph` (datasets reales con caché).
- `model.py` — `NetworkModel(mesa.Model)` une grafo y agentes, mantiene `active_messages` por step y ordena agentes con `agents.shuffle_do("step")`.
- `datacollector.py` — dataclass `Interaction(trace_id, message_id, timestep, source, target, previous_message_ids)` con export CSV/JSON y filtros por traza/timestep.
- `simulation.py` — orquestador y CLI (`--graph`, `--nodes`, `--fire-prob`, `--time`, ...) con modos headless y animado.
- `visualizer.py` — `NetworkAmator` (GIF/live con matplotlib), `DegreeDistributionPlot` y `MessageHeatmap`; estilo oscuro centralizado.

Horizonte objetivo de simulación: 2 meses · 10 timesteps/día = 600 timesteps. Plan de evolución a red bicapa (analógica + digital) con cerebro bayesiano, mensajes con carga semántica/emocional y scoring de superioridad cognitiva en `informe.md`.

---

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution."
- Skip this for simple, obvious fixes — don't over-engineer.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Never mark a task complete without proving it works. Ask yourself: "Would a staff engineer approve this?" Run tests, check logs, demonstrate correctness.

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Workflow & Task Management

**Plan first. Track progress. Capture learnings.**

- Enter plan mode for any non-trivial task (3+ steps or architectural decisions).
- Write plan to `tasks/todo.md` with checkable items; check in before starting implementation.
- If something goes sideways, STOP and re-plan immediately — don't keep pushing.
- Mark items complete as you go; add a review section when done.
- After ANY correction from the user: update `tasks/lessons.md` with the pattern and rules to prevent recurrence.
- Review lessons at session start for the relevant project.

## 6. Subagents & Parallel Work

- Use subagents liberally to keep the main context window clean.
- Offload research, exploration, and parallel analysis to subagents.
- For complex problems, throw more compute at it via subagents.
- One task per subagent for focused execution.

## 7. Autonomous Bug Fixing

- When given a bug report: just fix it. Don't ask for hand-holding.
- Point at logs, errors, failing tests — then resolve them.
- Zero context switching required from the user.
- Go fix failing CI tests without being told how.
