# Plan: capa configurable y función de confianza por grafo single-layer

## 1. Estado actual

| Componente | Aplica `layer` a aristas | Aplica `trust` a aristas | Tipo nx |
|---|---|---|---|
| `MultiLayerGraph` | sí (`ANALOG` / `DIGITAL`) | sí (Dunbar / log-normal por grado) | `MultiDiGraph` |
| `ErdosRenyiGraph` | no | no | `Graph` |
| `WattsStrogatzGraph` | no | no | `Graph` |
| `ScaleFreeGraph` | no | no | `DiGraph` |
| `SNAPGraph` | no | no | `Graph` o `DiGraph` |

- Las funciones de confianza viven como **métodos privados** de `MultiLayerGraph` (`_dunbar_trust`, `_digital_trust`). Nadie más puede invocarlas.
- `NetworkModel.trust()` y `neighbors_trust()` solo leen `layer`/`trust` si el grafo es `MultiDiGraph`; en cualquier otro caso devuelven 0.5 por defecto y todo se etiqueta como `ANALOG`.
- El config tiene una clase por topología (`ErdosConfig`, `WattsConfig`, …) sin campo de capa.

**Problema:** los grafos single-layer no llevan información de capa ni confianza realista. El brain bayesiano consume `trust` y `layer`, así que con esos grafos opera siempre sobre el fallback (0.5, ANALOG), perdiendo dinámica.

## 2. Objetivo

- Los cuatro grafos single-layer (`ErdosRenyi`, `Watts`, `ScaleFree`, `SNAP`) aceptan un parámetro `layer: "analog" | "digital"` en config.
- Cada arista del grafo se anota con `layer` y `trust`, usando la **misma función** que aplica `MultiLayerGraph` para esa capa.
- Cero duplicación: las dos funciones de confianza se definen una sola vez y todos los grafos las consumen.
- `NetworkModel` lee `trust`/`layer` con el mismo código sea single-layer o multilayer (sin `if isinstance(..., MultiDiGraph)`).

## 3. Diseño

### 3.1. Funciones de confianza centralizadas

Nuevo módulo `src/graphs/trust.py`:

```python
def dunbar_trust(u: int, v: int, graph: nx.Graph, rng: random.Random) -> float: ...
def digital_trust(u: int, v: int, graph: nx.Graph, rng: random.Random) -> float: ...

TRUST_FN: dict[Layer, Callable[..., float]] = {
    Layer.ANALOG: dunbar_trust,
    Layer.DIGITAL: digital_trust,
}
```

- Movidas tal cual desde `MultiLayerGraph` (firma idéntica, salvo que ya no son métodos).
- El diccionario `TRUST_FN` es el punto de despacho único — quien necesite trust por capa lo resuelve por aquí.

### 3.2. Anotación de aristas en `BaseGraph`

`BaseGraph` gana:

```python
def __init__(self, seed=None, layer: Layer = Layer.ANALOG):
    self.layer = layer
    ...

def _annotate(self, g: nx.Graph) -> nx.MultiDiGraph:
    """Convierte g a MultiDiGraph y añade layer+trust a cada arista
    usando TRUST_FN[self.layer]. Único punto que toca aristas."""
```

- `_annotate` es el **único** lugar que escribe `layer`/`trust` en grafos single-layer.
- Convierte siempre a `MultiDiGraph` (ver §3.4).
- Para grafos no dirigidos añade las dos direcciones u→v y v→u con el mismo trust (mismo patrón que la capa analógica de multilayer).

### 3.3. `build()` como template method

`BaseGraph.build()` deja de ser abstracto. El método abstracto pasa a ser `_build_topology()`:

```python
@abstractmethod
def _build_topology(self) -> nx.Graph: ...   # subclases: topología desnuda

def build(self) -> nx.MultiDiGraph:
    raw = self._build_topology()
    return self._annotate(raw)
```

- Las subclases single-layer solo escriben la lógica de topología (lo que ya tenían en `build()`, renombrado).
- La anotación ocurre una vez y vive en `BaseGraph`.

### 3.4. Tipo de retorno unificado: `MultiDiGraph`

**Decisión:** todos los grafos devuelven `nx.MultiDiGraph` tras `build()`.

| | Pros | Contras |
|---|---|---|
| **A: todos → MultiDiGraph** | El model lee trust/layer con un único path, sin isinstance ni fallback 0.5 | Pequeño overhead de memoria en single-layer (no se usan multi-edges) |
| B: single-layer mantiene Graph/DiGraph con atributos | Sin conversión | Bifurca `NetworkModel.trust()`; el fallback 0.5 actual queda inconsistente y poco útil |

→ Elegimos A. La unificación elimina los `if isinstance(self.graph, nx.MultiDiGraph)` en `model.py:150`, `:172`, `:181`.

### 3.5. `MultiLayerGraph` se mantiene aparte

- Sigue gestionando la prioridad digital > analog y la unión de dos topologías → su lógica no encaja en `_build_topology()`/`_annotate()`.
- Cambia solo en una cosa: importa `dunbar_trust`/`digital_trust` desde `trust.py` y borra los métodos privados.
- Heredera de `BaseGraph` pero **sobrescribe `build()`** directamente (no usa el template). Documentado como excepción explícita.

### 3.6. Config

A cada clase de config single-layer:

```python
@dataclass
class ErdosConfig:
    type: Literal["erdos"] = ...
    num_nodes: int = 10_000
    edge_prob: float = 0.25
    directed: bool = False
    layer: Literal["analog", "digital"] = "analog"   # ← nuevo
```

Idem en `WattsConfig`, `ScaleFreeConfig` (default `"digital"` por ser dirigido), `SNAPConfig`.

`MultiLayerConfig` no necesita el campo: ya define las dos capas implícitamente.

### 3.7. `build_graph()` en `simulation.py`

Cada rama lee `g.layer` del config y lo pasa al constructor:

```python
if isinstance(g, ErdosConfig):
    return ErdosRenyiGraph(num_nodes=g.num_nodes, edge_prob=g.edge_prob,
                           seed=seed, layer=Layer(g.layer))
```

Igual para los otros tres. La de `MultiLayerConfig` no cambia.

### 3.8. Simplificación de `NetworkModel`

Como todos los grafos son `MultiDiGraph` con `layer`/`trust`, se eliminan los chequeos `isinstance` en:

- `followers()` → siempre cuenta predecesores filtrados por layer.
- `trust()` → siempre busca la arista con `data.get("layer") == layer`.
- `neighbors_trust()` → siempre itera `successors`.

El fallback de 0.5 desaparece.

## 4. Cambios concretos por archivo

| Archivo | Tipo de cambio | Notas |
|---|---|---|
| `src/graphs/trust.py` (nuevo) | crear | Dos funciones puras + dict `TRUST_FN` |
| `src/graphs/base.py` | modificar | `__init__(layer)`, `_annotate(g)`, `build()` template, `_build_topology()` abstracto |
| `src/graphs/random.py` | modificar | Las 3 clases: renombrar `build` → `_build_topology`, aceptar `layer` en `__init__` (delegado a super) |
| `src/graphs/snap.py` | modificar | Idem `SNAPGraph` |
| `src/graphs/multilayer.py` | modificar | Borrar `_dunbar_trust`/`_digital_trust`; importar de `trust.py`. Sigue sobrescribiendo `build()` |
| `src/config.py` | modificar | Añadir `layer: Literal["analog","digital"]` a las 4 configs single-layer |
| `src/simulation/simulation.py` | modificar | `build_graph()` propaga `layer` |
| `src/simulation/model.py` | modificar | Eliminar chequeos `isinstance(MultiDiGraph)` y el fallback 0.5 |
| `src/notebooks/grafos.ipynb` | revisar | Si las celdas asumen `.is_directed()`, comprobar que el cambio a MultiDiGraph no rompe nada |

## 5. Garantías de no-repetición

- **Funciones de confianza:** definidas exactamente una vez en `trust.py`. `MultiLayerGraph` y `BaseGraph._annotate` las consumen.
- **Anotación de aristas:** centralizada en `BaseGraph._annotate`. Las cuatro subclases single-layer no escriben `layer` ni `trust` directamente.
- **Despacho por capa:** el dict `TRUST_FN[Layer]` es el único `if layer == ANALOG / DIGITAL` del sistema (en `trust.py`).

## 6. Test mínimo de validación

```python
g = ErdosRenyiGraph(num_nodes=10, edge_prob=0.5, seed=42, layer=Layer.DIGITAL).graph
assert isinstance(g, nx.MultiDiGraph)
for _, _, data in g.edges(data=True):
    assert data["layer"] == Layer.DIGITAL
    assert 0.0 <= data["trust"] <= 1.0
```

Repetir para los otros tres con `Layer.ANALOG`. Y un test que confirme que `NetworkModel.trust()` ya no devuelve siempre 0.5 con un Erdős.

## 7. Riesgos / preguntas abiertas

- **Grafos no dirigidos con capa digital:** ¿tiene sentido? La función `digital_trust` usa grado total para grafos no dirigidos (ya está implementado), pero conceptualmente lo digital implica direccionalidad. Decisión por defecto: lo permitimos (los defaults del config son coherentes con la naturaleza del grafo) y dejamos al usuario la responsabilidad.
- **Coste de convertir a MultiDiGraph:** despreciable para los tamaños típicos (≤100k nodos). No hay alternativa más limpia.
- **Notebook `grafos.ipynb`:** las funciones `graph_stats`, `draw_graph`, etc. siguen funcionando sobre `MultiDiGraph` (networkx soporta `degree`, `nodes`, etc.). Pero alguna métrica (transitividad, asortatividad) puede comportarse distinto sobre multigrafos — habrá que verificar y, si chirría, llamar a `nx.DiGraph(g)` dentro de las funciones de métricas para descartar multi-aristas.
