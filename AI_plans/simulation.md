# Plan: alinear `model`, `datacollector` y `simulation` con el refactor de grafos/agents/visualization

## 1. Estado actual

Tras `graph_layers.md` y `agente_inteligente.md`:

- Todos los grafos devuelven `nx.MultiDiGraph` con `layer`/`trust` en cada arista, y graph-attr `directed` con la direccionalidad original.
- Single-layer: cada `BaseGraph` ya conoce su `layer` (`Layer.ANALOG` o `Layer.DIGITAL`) y `_annotate()` aplica `TRUST_FN[layer]`.
- Multilayer: `MultiLayerGraph.build()` re-anota desde cero usando `digital_trust` / `dunbar_trust`, **ignorando** el `layer`/`trust` que las sub-clases ya pusieron.
- `compute_graph_metrics` colapsa `MultiGraph → DiGraph/Graph` para no romper algoritmos de NetworkX.
- `draw_graph` lee `G.graph["directed"]` para no pintar flechas en grafos conceptualmente no dirigidos.
- `config.py` añade `layer: Literal["analog","digital"]` a `ErdosConfig`, `ScaleFreeConfig`, `WattsConfig`, `SNAPConfig`.

Estado de los tres ficheros objetivo:

| Fichero | Estado | Problemas |
|---|---|---|
| `model.py` | ya recibe `nx.MultiDiGraph`; sin `isinstance` checks | menores: ver §3.1 |
| `datacollector.py` | volca `msg.layer.value` (string), ya es compatible | ninguno |
| `simulation.py` | `build_graph` propaga `layer` a single-layer | varios: ver §3.3 |

## 2. Objetivos

1. `simulation.py > build_graph` propaga `layer` a las sub-capas de `MultiLayerGraph` y respeta el config de cada sub-topología (incluido SNAP-as-digital).
2. `simulation.py > render_graph_analysis` despacha a `analyse_multilayer` cuando el grafo es bicapa, y a `analyse_graph` en otro caso.
3. `simulation.py > save_graph_structure` serializa enums (`Layer`) a string antes del JSON.
4. `simulation.py > main` nombra la carpeta de salida de forma reconocible para `MultiLayerConfig` (incluye sub-topologías).
5. `model.py` queda mínimamente limpio: el invariante "una sola arista por par (u,v,layer)" permite simplificar `followers`/`trust` (`break` ya cumple el rol, pero documentarlo).
6. Cero cambios funcionales en `datacollector.py` salvo verificar headers.

## 3. Diseño

### 3.1. `src/simulation/model.py`

Cambios menores, todos justificados por el invariante actual (una sola arista u→v por capa):

- `followers(node_id, layer)`: dejar igual; el `break` interno ya aprovecha el invariante.
- `trust(source, target, layer)`: idem; bucle de ≤1 iteración por capa.
- `neighbors_trust(node_id)`: cambiar la firma del valor a `dict[tuple[int, Layer], float]` ya existente (OK). Pero el comentario actual no menciona que `layer` viene anotado en la arista; añadir una línea de docstring explicando que confía en `_annotate()` (sin cambios de código).

No hay cambios estructurales en `model.py`. Si tras revisión no aporta nada, se omite.

### 3.2. `src/simulation/datacollector.py`

Sin cambios. Verificación pasiva:

- `record_message` recibe `Message` con `msg.layer: Layer` (Enum) y guarda `msg.layer.value` (string). Compatible con CSV/JSON.
- Headers de `to_csv` ya incluyen `layer`, `emotion`, `modalities`, etc.

### 3.3. `src/simulation/simulation.py`

#### 3.3.1. `build_graph` — propagar `layer` en `MultiLayerConfig`

Hoy las sub-capas se construyen sin pasar `layer`, dependiendo del default de cada `BaseGraph` subclase. Es frágil: si alguien cambia el default, el bicapa se rompe en silencio.

Cambios:

```python
if isinstance(g, MultiLayerConfig):
    if isinstance(g.digital, SNAPConfig):
        digital = SNAPGraph(
            dataset_name=g.digital.dataset_name,
            cache_dir=g.digital.cache_dir,
            directed=True,                       # forzado, capa digital es dirigida
            seed=seed,
            layer=Layer.DIGITAL,                 # explícito
        )
        n = len(digital)
    else:
        digital = ScaleFreeGraph(
            num_nodes=g.digital.num_nodes,
            alpha=g.digital.alpha,
            beta=g.digital.beta,
            gamma=g.digital.gamma,
            delta_in=g.digital.delta_in,
            delta_out=g.digital.delta_out,
            seed=seed,
            layer=Layer.DIGITAL,
        )
        n = g.digital.num_nodes
    analog = WattsStrogatzGraph(
        num_nodes=n,
        k=g.analog.k,
        rewire_prob=g.analog.rewire_prob,
        seed=seed,
        layer=Layer.ANALOG,
    )
    return MultiLayerGraph(digital_graph=digital, analog_graph=analog, seed=seed)
```

Nota: el `layer` aquí se ignorará efectivamente dentro de `MultiLayerGraph.build()` porque éste re-anota. Lo dejamos explícito por legibilidad y para que las sub-capas sean inspeccionables por separado con el `layer` correcto (útil en notebook).

#### 3.3.2. `render_graph_analysis` — despachar multilayer

Hoy llama siempre a `analyse_graph(self.model.graph, …)`. Para `MultiLayerConfig` lo correcto es `analyse_multilayer`, que ya existe en `plots.py` y genera `analog/`, `digital/`, vistas combinadas y `multilayer_metrics.json`.

Diseño: el `Simulation` conserva una referencia al `GraphConfig` (o al `BaseGraph` ya construido, que es `MultiLayerGraph` cuando aplica) y decide en runtime.

```python
def __init__(self, graph: BaseGraph, ..., graph_cfg: GraphConfig | None = None) -> None:
    ...
    self.graph_cfg = graph_cfg  # solo informativo
```

```python
def render_graph_analysis(self, basename: str = "simulation") -> Path:
    from src.visualization.plots import analyse_graph, analyse_multilayer
    from src.visualization.visualizer import MessageHeatmap

    self.graph_dir.mkdir(parents=True, exist_ok=True)
    if isinstance(self.graph, MultiLayerGraph):
        analyse_multilayer(self.model.graph, basename, out_dir=self.graph_dir, seed=self.seed)
    else:
        analyse_graph(self.model.graph, basename, out_dir=self.graph_dir, seed=self.seed)
    heatmap_path = self.graph_dir / f"{basename}_heatmap.png"
    MessageHeatmap(self.collector, num_nodes=len(self.graph)).render(heatmap_path)
    return self.graph_dir
```

Alternativa más simple: detectar bicapa mirando si hay aristas con dos valores distintos de `layer`. Pero `isinstance(self.graph, MultiLayerGraph)` es más barato y directo.

#### 3.3.3. `save_graph_structure` — JSON-safe para `Layer`

`nx.node_link_data` serializa los atributos tal cual; `Layer` es un `Enum` con `value: str`. Con `json.dump` directo lanzará `TypeError: Object of type Layer is not JSON serializable`.

Opciones:

- **(a)** Pasar `default=str` a `json.dump`.
- **(b)** Iterar y reemplazar `data["links"][i]["layer"] = link["layer"].value` antes de volcar.

Recomendado **(a)**: una línea, no requiere conocer la estructura interna:

```python
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, default=lambda o: o.value if hasattr(o, "value") else str(o))
```

#### 3.3.4. `main` — folder name para `MultiLayerConfig`

Hoy:

```python
folder = f"{cfg.GRAPH.type}-{cfg.AGENT.type}"
if isinstance(cfg.GRAPH, SNAPConfig):
    folder += f"-{cfg.GRAPH.dataset_name}"
```

Para `MultiLayerConfig` el `type` es `"multilayer"` pero no se distingue ScaleFree vs SNAP en la capa digital. Añadir:

```python
elif isinstance(cfg.GRAPH, MultiLayerConfig):
    digital_tag = (
        f"snap-{cfg.GRAPH.digital.dataset_name}"
        if isinstance(cfg.GRAPH.digital, SNAPConfig)
        else "scale_free"
    )
    folder += f"-{digital_tag}"
```

#### 3.3.5. Paso de `graph_cfg` al `Simulation`

Mínimo: añadir parámetro opcional `graph_cfg: GraphConfig | None = None` al `__init__` solo si se decide usarlo (§3.3.2). Si la dispatch se hace por `isinstance(self.graph, MultiLayerGraph)` no es necesario y se omite este punto.

## 4. Plan de ejecución

1. **`simulation.py > build_graph`**: añadir `layer=Layer.ANALOG` / `Layer.DIGITAL` explícitos a las sub-capas de `MultiLayerConfig`. Verificación: una corrida con `MultiLayerConfig()` produce el mismo nº de aristas que antes.
2. **`simulation.py > save_graph_structure`**: añadir `default=...` al `json.dump`. Verificación: corrida con `OUTPUT.save_graph=True` y un grafo no-multilayer escribe `graph.json` sin `TypeError`.
3. **`simulation.py > render_graph_analysis`**: dispatch por `isinstance(self.graph, MultiLayerGraph)` → `analyse_multilayer` o `analyse_graph`. Verificación: corrida con `MultiLayerConfig()` crea `analog/`, `digital/`, `multilayer_metrics.json` en `graph/`.
4. **`simulation.py > main`**: extender el nombre de carpeta para `MultiLayerConfig`. Verificación: nombre incluye `scale_free` o `snap-<dataset>`.
5. **`model.py`**: refrescar docstring de `neighbors_trust` para mencionar el invariante "una sola arista por (u,v,layer)". Sin cambios de código.
6. **`datacollector.py`**: sin cambios.

## 5. Riesgos y supuestos

- `MultiLayerGraph` ignora el `layer` que ponemos en las sub-capas y re-anota desde cero. Se mantiene esa duplicación intencionalmente: barato, evita una refactor mayor en `MultiLayerGraph.build()`.
- `nx.node_link_data` mete los atributos enteros en cada link; si en el futuro hay más enums (`Modality`, `Emotion`) en aristas, el `default=lambda` los cubre.
- El dispatch por `isinstance(MultiLayerGraph)` introduce una dependencia explícita de `simulation` sobre `MultiLayerGraph`. Aceptable: ya importa `MultiLayerGraph` para `build_graph`.

## 6. Fuera de alcance

- Reescritura de `MultiLayerGraph.build()` para reutilizar el `layer`/`trust` ya anotado por las sub-capas.
- Cualquier cambio en `agents/`, `graphs/`, `visualization/` o `config.py`.
- Tests.
