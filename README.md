# Trabajo Final de Grado

## Interacciones y Dinámicas en la Aldea Global: Modelado Matemático y Psicosocial de la Guerra Cognitiva en Redes Complejas

**Autor:** Jorge Enebral  
**Director:** David Martín-Corral

La memoria del trabajo se encuentra en [`Burocracia/Memoria/memoria.tex`](Burocracia/Memoria/memoria.tex).

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

Crea el entorno virtual en `.venv/` e instala todas las dependencias de `pyproject.toml`.

### 3. Ejecutar la simulación

La simulación se configura íntegramente en `src/config.py` (sin CLI). Edita ese fichero para cambiar topología, tipo de agente y parámetros, y luego:

```bash
uv run python -m src.simulation.simulation
```

Los resultados se guardan en `data/results/{tipo_grafo}-{tipo_agente}/`.

### 4. Ejecutar el sweep de experimentos

```bash
uv run python -m src.experiments.sweep
```

Lanza un barrido OFAT (one-factor-at-a-time) sobre cinco palancas de la narrativa, en dos topologías (scale-free y small-world), con réplicas Monte Carlo. Resultados en `data/results/sweep_v2/`.

### 5. Comandos del Makefile

| Comando | Descripción |
|---|---|
| `make install` | Crea el entorno e instala dependencias |
| `make format` | Formatea con ruff |
| `make check` | Ruff + mypy + pylint + complexipy |
| `make clean` | Elimina cachés y archivos temporales |
| `make remove_venv` | Elimina el entorno virtual |

---

## Estructura del proyecto

```
src/
├── agents/
│   ├── base.py           # BaseAgent: interfaz común + integración Mesa
│   ├── stochastic.py     # StochasticAgent: disparo aleatorio de mensajes
│   ├── resistant.py      # ResistantAgent: modelo Linear Threshold
│   ├── bayesian.py       # BayesianAgent: bucle OODA con Brain inyectado
│   └── brain.py          # EmotionalBrain: implementación emocional del Brain
├── graphs/
│   ├── base.py           # BaseGraph: interfaz común
│   ├── random.py         # ErdosRenyiGraph, ScaleFreeGraph, WattsStrogatzGraph
│   ├── snap.py           # SNAPGraph: datasets reales de Stanford SNAP
│   ├── multilayer.py     # MultiLayerGraph: capa analógica (WS) + digital (SF/SNAP)
│   └── trust.py          # Grafo de confianza entre nodos
├── simulation/
│   ├── model.py          # NetworkModel: orquesta agentes + grafo + collector
│   ├── datacollector.py  # Recoge trazas de mensajes y eventos de adopción
│   └── simulation.py     # Simulation: punto de entrada + exportación
├── visualization/
│   ├── visualizer.py     # PostSimAnimator, MessageHeatmap
│   ├── plots.py          # analyse_graph / analyse_multilayer (métricas + figuras)
│   └── metrics.py        # Cálculo de métricas de red
├── experiments/
│   └── sweep.py          # Sweep OFAT multi-topología (escenario resistente)
├── notebooks/
│   ├── analisis_nodo_resistente.ipynb  # Métricas de resistencia cognitiva por run
│   ├── analisis_sweep.ipynb            # Análisis del sweep OFAT
│   └── grafos.ipynb                    # Exploración de topologías
├── messages.py           # Dataclass Message + enum Layer (ANALOG / DIGITAL)
└── config.py             # Configuración centralizada (editar aquí)
```

---

## Configuración (`src/config.py`)

Toda la configuración se define mediante dataclasses. Las instancias activas al final del fichero son las que usa la simulación:

```python
SIMULATION: SimulationConfig = SimulationConfig(days=3, steps_per_day=15, seed=42)
GRAPH: GraphConfig = WattsConfig()          # o ScaleFreeConfig(), MultiLayerConfig()…
AGENT: AgentConfig = AgentConfig(type="resistant")
OUTPUT: OutputConfig = OutputConfig(export_format="json")
```

### Topologías disponibles

| Clase | Tipo de grafo |
|---|---|
| `ErdosConfig` | Erdős–Rényi G(n, p) |
| `ScaleFreeConfig` | Libre de escala (dirigido) |
| `WattsConfig` | Pequeño mundo Watts–Strogatz |
| `SNAPConfig` | Dataset real del catálogo SNAP de Stanford |
| `MultiLayerConfig` | Bicapa: capa digital (SF/SNAP) + analógica (WS) |

### Tipos de agente

| Tipo | Descripción |
|---|---|
| `"stochastic"` | Dispara mensajes con probabilidad `fire_probability` a un vecino aleatorio |
| `"resistant"` | Linear Threshold: acumula convicción por exposición a la narrativa hasta superar el umbral θ |

El escenario principal del TFG es `"resistant"`. Permite estudiar la tasa de ataque de una campaña de desinformación en función de la topología de la red, la distribución bimodal de θ y los parámetros de la narrativa (`NarrativeConfig`).

### Salida

```
data/results/{tipo_grafo}-{tipo_agente}/
    sim/
        graph.json                      # estructura del grafo (node-link)
        simulation.json / .csv          # trazas de mensajes
        simulation_adoptions.csv        # eventos de conversión (solo resistant)
        simulation_agent_states.csv     # estado cognitivo final (solo resistant)
    graph/
        graph.png / histograms.png      # visualizaciones del grafo
        metrics.json                    # métricas escalares de red
        simulation_heatmap.png          # calor de mensajes por par nodo
    simulation.gif                      # replay animado (si render_gif=True)
```
