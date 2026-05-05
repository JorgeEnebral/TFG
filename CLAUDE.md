# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**TFG — "Interacciones y Dinámicas en la Aldea Global: Modelado Matemático y Psicosocial de la Guerra Cognitiva en Redes Complejas"**
Bachelor's thesis (IMAT, Comillas). Author: Jorge Enebral. Director: David Martín-Corral.

The project models **cognitive warfare** (information/influence campaigns) using agent-based modelling (ABM) on complex networks, combining a Python simulation with a LaTeX thesis document.

## Environment

- Python 3.13, virtualenv at `.venv/`
- Activate: `.venv\Scripts\Activate.ps1`
- Install dependencies: `pip install -r requirements.txt`
  - Core runtime deps (`mesa`, `matplotlib`, `networkx`) are used in the simulation but not fully listed in `requirements.txt` — install them manually if needed.

## Running the simulation

```powershell
python src/network_simulation.py                        # defaults: 12 nodes, 40 steps, saves simulation.gif
python src/network_simulation.py --nodes 30 --time 60  # custom run
python src/network_simulation.py --show                 # open live window (requires display)
python src/network_simulation.py --no-gif --show        # live only, no file output
```

Full CLI options: `--nodes`, `--edge-prob`, `--fire-prob`, `--time`, `--interval`, `--seed`, `--no-gif`, `--show`, `--out`.

Run the notebook:
```powershell
jupyter notebook src/networkx_grafos.ipynb
```

## Code architecture (`src/network_simulation.py`)

Three-layer design, all in one file:

1. **`MessageAgent` (Mesa agent)** — each agent fires a message to a random neighbor with probability `fire_probability` each step. Fires are recorded on the model.

2. **`NetworkModel` (Mesa model)** — wraps a NetworkX graph. Maintains `active_messages` (current step) and `message_history` (all steps). Agents are indexed by node id in `agent_by_node`.

3. **`run_simulation()` (visualizer)** — builds an Erdős–Rényi graph (swappable with any `nx.*` generator), instantiates the model, and drives a `FuncAnimation` that calls `model.step()` each frame. Node colors: yellow = firing, green = receiving, blue = idle.

The graph topology is intentionally decoupled: swap `nx.erdos_renyi_graph(...)` in `run_simulation()` for any NetworkX generator (Barabási–Albert, Watts–Strogatz, SBM, etc.) to test different network structures.

## Notebook (`src/networkx_grafos.ipynb`)

A reference catalog of NetworkX graph generators — classic, random, lattice, named, directed, and advanced types — each with a dark-themed visualization and a property table. Useful for picking graph topologies to plug into the simulation.

## Thesis document

Written in LaTeX. Source at `Memoria/tfg.tex`, bibliography at `Memoria/ref_memoria.bib`, compiled output at `Memoria/out/tfg.pdf`. Annexes follow the same pattern under `Anexo A/` and `Anexo B/`.

## Research notes

`Fuentes/IA/*.md` — AI-generated research summaries covering cognitive warfare doctrine (NATO, EU, China, Russia), Python tools for ABM/graph analysis, random graph models, and the cybersecurity dynamics framework extrapolated to cognitive warfare.

**Always read `Fuentes/IA/guerra_cognitiva.md` at the start of every session.** It is the primary theoretical document of the thesis — a comprehensive treatment of cognitive warfare covering definitions, history, NATO doctrine, network dynamics, actors, and defensive resilience. All simulation design and thesis writing decisions should be grounded in it.
