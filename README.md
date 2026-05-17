# Trabajo Final de Grado

## Interacciones y Dinámicas en la Aldea Global: Modelado Matemático y Psicosocial de la Guerra Cognitiva en Redes Complejas

Autor: Jorge Enebral

Director: David Martín-Corral

---

## Puesta en marcha

### 1. Instalar `uv`

El proyecto usa [uv](https://docs.astral.sh/uv/) como gestor de entornos y dependencias.

**Linux / macOS**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell)**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Reinicia el terminal tras la instalación para que `uv` esté en el PATH.

### 2. Instalar dependencias

```bash
make install
```

Esto ejecuta `uv sync`, que crea el entorno virtual en `.venv/` e instala todas las dependencias definidas en `pyproject.toml`.

### 3. Ejecutar la simulación

```bash
# Ejecución por defecto: Erdős–Rényi de 12 nodos, 40 pasos, GIF + CSV/JSON + plots
uv run python -m src.simulation

# Cambiar topología
uv run python -m src.simulation --graph barabasi --nodes 50 --m 3
uv run python -m src.simulation --graph watts --nodes 30 --k 4 --rewire-prob 0.1
uv run python -m src.simulation --graph hyper --nodes 20 --hyperedges 15
uv run python -m src.simulation --graph snap --snap-dataset ca-GrQc

# Solo headless (sin GIF, sin ventana) — más rápido para experimentos
uv run python -m src.simulation --no-gif --time 200

# Ver ventana en vivo
uv run python -m src.simulation --show
```

Las salidas (GIF, CSV de trazas, JSON, histograma de grado, heatmap de mensajes) se guardan en `src/data/`. Los datasets SNAP descargados se cachean en `src/data/snap/`.

### 4. Comandos útiles del Makefile

| Comando | Descripción |
|---|---|
| `make install` | Crea el entorno e instala dependencias |
| `make clean` | Elimina cachés y archivos temporales |
| `make remove_venv` | Elimina el entorno virtual (incluye `clean`) |

---

## Estructura del proyecto

```
src/
├── agents/             # Tipos de agentes (BaseAgent + StochasticAgent)
├── graphs/             # Topologías: random, hipergrafo, datasets SNAP
├── data/               # Outputs (GIFs, CSVs, JSONs, plots) y caché SNAP
├── model.py            # NetworkModel (orquesta agentes + grafo + collector)
├── datacollector.py    # Recoge trazas (trace_id, timestep, src, tgt)
├── visualizer.py       # NetworkAnimator, DegreeDistributionPlot, MessageHeatmap
└── simulation.py       # Entry-point + CLI
```

### Diseño

- **Agentes** (`src/agents/`): cada agente vive en un nodo. `BaseAgent` provee la integración con Mesa; las subclases concretas (`StochasticAgent`, futuros bots/trolls/ciudadanos) reimplementan `step()`.
- **Grafos** (`src/graphs/`): `BaseGraph` define la interfaz; subclases para Erdős–Rényi, Barabási–Albert, Watts–Strogatz, hipergrafos y datasets reales de SNAP. El resto del código solo ve `g.graph` (un `nx.Graph`), así que cambiar topología es una línea.
- **Modelo** (`model.py`): recibe grafo, factoría de agentes y `DataCollector`. En cada `step()`, dispara `step()` de los agentes en orden aleatorio y vuelca los mensajes emitidos al collector.
- **DataCollector** (`datacollector.py`): acumula `Trace(trace_id, timestep, source_node, target_node)` y exporta a CSV/JSON.
- **Visualizador** (`visualizer.py`): tres clases independientes. `NetworkAnimator` anima paso a paso; `DegreeDistributionPlot` y `MessageHeatmap` generan gráficas estáticas.

### CLI

| Argumento | Default | Descripción |
|---|---|---|
| `--graph` | `erdos` | `erdos` \| `barabasi` \| `watts` \| `hyper` \| `snap` |
| `--nodes` | `12` | Nº de nodos (no aplica a `snap`) |
| `--edge-prob` | `0.25` | p para Erdős–Rényi |
| `--m` | `2` | Aristas/nodo nuevo en Barabási–Albert |
| `--k` | `4` | Vecinos en Watts–Strogatz |
| `--rewire-prob` | `0.1` | p de recableo en Watts–Strogatz |
| `--hyperedges` | `10` | Hiperaristas en `hyper` |
| `--he-min` / `--he-max` | `2` / `4` | Rango de tamaño por hiperarista |
| `--snap-dataset` | `ca-GrQc` | Dataset del catálogo SNAP |
| `--fire-prob` | `0.20` | Probabilidad de disparo por paso |
| `--time` | `40` | Pasos de simulación |
| `--interval` | `500` | Intervalo entre frames (ms) |
| `--seed` | `42` | Semilla |
| `--no-gif` | flag | No guardar GIF |
| `--show` | flag | Mostrar ventana en vivo |
| `--out` | `simulation` | Basename de los ficheros de salida |
| `--no-export` | flag | No exportar CSV/JSON |
| `--no-plots` | flag | No generar histograma/heatmap |
