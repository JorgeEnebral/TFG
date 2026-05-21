# Arquitectura del simulador — TFG

Simulador multiagente de propagación de mensajes en redes sociales.  
Stack: `mesa 3.x` + `networkx` + `matplotlib`.

---

## Mapa de módulos

```
src/
├── messages.py          ← tipos de datos compartidos (Message, Emotion, Layer…)
├── config.py            ← configuración editable (grafo, simulación, salida)
├── model.py             ← NetworkModel (orquestador Mesa)
├── datacollector.py     ← DataCollector + Interaction (trazas)
├── simulation.py        ← Simulation (pegamento) + main()
├── visualizer.py        ← NetworkAnimator, DegreeDistributionPlot, MessageHeatmap
├── agents/
│   ├── base.py          ← BaseAgent (abstracto)
│   ├── stochastic.py    ← StochasticAgent (lanzar moneda → enviar)
│   ├── bayesian.py      ← BayesianAgent (bucle OODA)
│   └── brain.py         ← Brain (interfaz) + BayesianMemoryBrain
└── graphs/
    ├── base.py          ← BaseGraph (lazy construction)
    ├── random.py        ← ErdosRenyi, BarabasiAlbert, WattsStrogatz
    ├── hypergraph.py    ← HyperGraph (hiperaristas + proyección clique)
    ├── multilayer.py    ← MultiLayerGraph (analógica + digital)
    └── snap.py          ← SNAPDownloader + SNAPGraph (datasets reales)
```

---

## 1. `messages.py` — tipos de datos centrales

Todos los módulos importan de aquí. No tiene lógica propia.

### Enums

| Tipo | Valores |
|---|---|
| `Modality` | `TEXT`, `AUDIO`, `VIDEO`, `IMAGE` |
| `Emotion` | `JOY`, `FEAR`, `ANGER`, `SADNESS`, `DISGUST`, `SURPRISE`, `TRUST`, `NEUTRAL` |
| `Layer` | `ANALOG`, `DIGITAL` |

### `Message` (dataclass frozen, slots)

Objeto inmutable que viaja por la red en cada paso.

| Campo | Tipo | Significado |
|---|---|---|
| `message_id` | `int` | Identificador único global (autoincremental) |
| `trace_id` | `int` | Agrupa mensajes de la misma cadena causal |
| `timestep` | `int` | Paso de simulación en el que se emite |
| `source` / `target` | `int` | Nodos emisor y receptor |
| `layer` | `Layer` | Capa de red por la que viaja |
| `topic` | `str` | Asunto del mensaje (p.ej. `"política"`) |
| `modalities` | `frozenset[Modality]` | Cómo se transmite (texto, audio…) |
| `emotion` | `Emotion` | Emoción dominante del mensaje |
| `emotional_load` | `float [0,1]` | Intensidad emocional |
| `veracity` | `float [0,1]` | Verdad percibida del contenido |
| `salience` | `float [0,1]` | Relevancia subjetiva para el emisor |
| `intent` | `str` | `"inform"` \| `"persuade"` \| `"alert"` \| `"entertain"` |
| `parent_message_id` | `int \| None` | Mensaje que desencadenó éste (para trazas) |

---

## 2. `graphs/` — topologías de red

### `BaseGraph` (base.py)

Clase abstracta con patrón **lazy construction**: el grafo NetworkX no se construye hasta que alguien accede a `.graph` por primera vez.

```
BaseGraph.__init__()      # guarda seed, _graph = None
BaseGraph.graph           # @property: si _graph es None → llama build()
BaseGraph.build()         # abstractmethod: cada subclase lo implementa
BaseGraph.ensure_connected()  # añade aristas mínimas para conectar componentes
```

### Grafos sintéticos (random.py)

| Clase | Modelo | Parámetros clave |
|---|---|---|
| `ErdosRenyiGraph` | Erdős-Rényi G(n,p) | `num_nodes`, `edge_prob` |
| `BarabasiAlbertGraph` | Barabási-Albert (libre de escala) | `num_nodes`, `m` |
| `WattsStrogatzGraph` | Watts-Strogatz (mundo pequeño) | `num_nodes`, `k`, `rewire_prob` |

### `MultiLayerGraph` (multilayer.py)

Grafo bicapa sobre `nx.MultiDiGraph`:

- **Capa `ANALOG`** (Watts-Strogatz): representa relaciones cara a cara. No dirigida → se añaden 2 aristas dirigidas por cada par. Confianza modelada con la regla de Dunbar: cuanto mayor la distancia en el grafo, menor la confianza.
- **Capa `DIGITAL`** (Barabási-Albert): representa relaciones online. Dirigida. Confianza basada en distribución log-normal + corrección por grado.

**Invariante**: ningún par ordenado (u,v) aparece en las dos capas a la vez.

```python
# Confianza analógica (Dunbar)
dist == 1  → trust ∈ [0.85, 1.00]   # amigos directos
dist == 2  → trust ∈ [0.65, 0.85]   # amigos de amigos
dist == 3  → trust ∈ [0.40, 0.65]   # conocidos
dist >= 4  → trust ∈ [0.15, 0.40]   # desconocidos

# Confianza digital (log-normal + grado)
trust = clip(lognormal(μ=-2, σ=0.8) + 0.0008 * in_degree, 0, 1)
```

### `SNAPGraph` + `SNAPDownloader` (snap.py)

Carga datasets reales del repositorio Stanford SNAP.

**`SNAPDownloader`**: descarga el `.txt.gz`, lo descomprime a `.txt` y lo carga como `nx.Graph` / `nx.DiGraph`. Cachea en `data/snap/raw/` y `data/snap/processed/` para no re-descargar.

**`SNAPGraph`**: adaptador que envuelve `SNAPDownloader` implementando la interfaz `BaseGraph`.

Catálogo disponible:

| Dataset | Tipo | Nodos | Aristas |
|---|---|---|---|
| `ego-Facebook` | no dirigido | 4k | 88k |
| `loc-Gowalla` | no dirigido | 196k | 950k |
| `loc-Brightkite` | no dirigido | 58k | 214k |
| `soc-Epinions1` | dirigido | 75k | 508k |
| `soc-sign-epinions` | dirigido | 131k | 841k |
| `ego-Twitter` | dirigido | 81k | 1.7M |

---

## 3. `agents/` — comportamiento de los nodos

### `BaseAgent` (base.py)

Hereda de `mesa.Agent`. Solo guarda `node_id` y declara `step()` como método abstracto. El constructor llama a `super().__init__(model)` que:
1. Asigna `self.model`.
2. Asigna `unique_id` autoincremental.
3. Registra el agente en `model.agents` (AgentSet de Mesa).

### `StochasticAgent` (stochastic.py)

El agente más simple. "Lanza una moneda" cada step:

```
step():
  si random() >= fire_probability → no hace nada
  vecinos = grafo.neighbors(node_id)
  si vacío → no hace nada
  target = choice(vecinos)
  msg = model.make_message(self.node_id, target)   # valores neutros
  model.emit_message(msg)
```

No tiene memoria ni estado interno más allá de `fire_probability`.

### `BayesianAgent` (bayesian.py)

Agente con cerebro. Implementa el bucle **OODA** (Observe → Orient → Decide → Act):

```
step():
  # OBSERVE
  para cada msg en model.consume_inbox(node_id):
      trust = model.trust(msg.source, node_id, msg.layer)
      brain.observe(msg, trust)

  # DECIDE + ACT
  neighbors_trust = model.neighbors_trust(node_id)
  para cada action en brain.decide(neighbors_trust, timestep):
      msg = model.make_message(...)   # con parámetros semánticos del action
      model.emit_message(msg)
```

### `Brain` + `BayesianMemoryBrain` (brain.py)

`Brain` es la interfaz abstracta con dos métodos:
- `observe(msg, sender_trust)` — actualiza el estado interno con un mensaje recibido.
- `decide(neighbors_trust, timestep)` — devuelve lista de `Action`.

`BayesianMemoryBrain` implementa:

#### Estado interno

| Atributo | Tipo | Significado |
|---|---|---|
| `beliefs[topic]` | `[α, β]` | Distribución Beta sobre veracidad del tópico |
| `mood[emotion]` | `float [0,1]` | Intensidad emocional actual (decae cada step) |
| `last_seen[topic]` | `int` | Último timestep en que se vio el tópico |
| `_last_reinforcing[topic]` | `int \| None` | `message_id` del último refuerzo por tópico |

#### `observe(msg, sender_trust)`

Actualiza las creencias y el humor con el peso `w = sender_trust × msg.salience`:

```
α += msg.veracity × w
β += (1 - msg.veracity) × w
mood[emotion] = min(1, mood[emotion] + emotional_load × w)
```

#### `decide(neighbors_trust, timestep)`

1. Aplica **decay** al humor: `mood[e] *= decay_step` (exponencial por step).
2. Selecciona el tópico con mayor **creencia media** `α/(α+β)`.
3. Identifica la emoción dominante.
4. Para cada vecino `(neighbor, layer)` calcula un **score**:
   ```
   score = belief_strength × trust × (1 + emotional_load × 0.5)
   ```
5. Si `score < θ_send` → silencio.  
   Si `score >= θ_send` → genera una `Action(kind="send", ...)`.  
   Si `score >= θ_persuade` → `intent = "persuade"`, si no `"inform"`.

#### `Action` (dataclass)

| Campo | Tipo | Significado |
|---|---|---|
| `kind` | `str` | `"send"` \| `"forward"` \| `"silence"` |
| `target` | `int` | Nodo destinatario |
| `layer` | `Layer` | Capa por la que enviar |
| `message` | `Message \| None` | El modelo lo rellena vía `make_message` |
| `_topic`, `_emotion`, `_veracity`… | (extras) | Parámetros semánticos para construir el `Message` |

---

## 4. `model.py` — `NetworkModel`

Hereda de `mesa.Model`. Es el corazón de la simulación: une grafo, agentes y recolector.

### Atributos principales

| Atributo | Tipo | Rol |
|---|---|---|
| `graph` | `nx.Graph` | Topología (referencia directa, sin copia) |
| `data_collector` | `DataCollector` | Registro de trazas |
| `active_messages` | `list[Message]` | Mensajes del último step (para visualizador) |
| `_outbox` | `list[Message]` | Buffer TX del step en curso |
| `_inboxes` | `dict[int, list[Message]]` | Un inbox por nodo (entrega RX) |
| `agent_by_node` | `dict[int, BaseAgent]` | Acceso O(1) a agente por nodo |
| `current_step` | `int` | Contador de pasos ejecutados |

### Constructor

Recibe un `agent_factory: Callable[[NetworkModel, int], BaseAgent]`. Esto desacopla el modelo del tipo concreto de agente: se puede tener una simulación con agentes mixtos sin modificar `NetworkModel`.

### Métodos de mensajería

```python
make_message(source, target, layer, topic, emotion, ...)  # crea Message con IDs automáticos
emit_message(msg)          # añade msg al _outbox
consume_inbox(node_id)     # devuelve y vacía el inbox del nodo
trust(source, target, layer)          # lee peso de confianza de la arista
neighbors_trust(node_id)   # devuelve {(vecino, layer): trust} para todos los salientes
```

### `step()` — dos sub-fases TX/RX

```
Sub-fase TX:
  _outbox = []
  agents.shuffle_do("step")        # cada agente decide y llama emit_message()

Sub-fase RX:
  para cada msg en _outbox:
      _inboxes[msg.target].append(msg)
      data_collector.record_message(msg)

active_messages = list(_outbox)    # snapshot para el visualizador
current_step += 1
```

La separación TX/RX es crucial para el OODA: todos los agentes **deciden con información de t-1** y **reciben en t**.

---

## 5. `datacollector.py` — trazas

### `Interaction` (dataclass)

Un registro por cada mensaje emitido. Campos semánticos completos (igual que `Message`).

La diferencia clave entre identificadores:
- `message_id`: siempre único y autoincremental — una entrada en el log = un `message_id`.
- `trace_id`: agrupa mensajes de la misma cadena causal. Si un agente responde a un mensaje heredado, reutiliza el `trace_id`; si es una decisión espontánea, se reserva uno nuevo.

### `DataCollector` (dataclass)

| Método | Qué hace |
|---|---|
| `new_trace_id()` | Reserva y devuelve un `trace_id` nuevo (para decisiones espontáneas) |
| `record(...)` | Crea un `Interaction` y lo añade a `self.interactions` |
| `record_message(msg)` | Wrapper de `record()` que extrae los campos de un `Message` |
| `to_csv(path)` | Exporta todas las interacciones a CSV |
| `to_json(path)` | Exporta todas las interacciones a JSON (lista de objetos) |
| `__len__()` | Número de interacciones acumuladas |

---

## 6. `simulation.py` — orquestador

### `Simulation`

Clase que configura y ejecuta una simulación completa. Crea el `DataCollector`, el `NetworkModel` y expone los modos de ejecución.

| Método | Qué hace |
|---|---|
| `run_headless()` | Ejecuta `sim_time` steps sin visualización |
| `run_with_animation(gif_path, show)` | Ejecuta con `NetworkAnimator`; opcionalmente guarda GIF |
| `export_data(basename)` | Vuelca trazas a CSV y JSON |
| `render_static_plots(basename)` | Genera PNG de distribución de grado y heatmap de mensajes |

### `build_graph(g, seed)`

Función que traduce el diccionario de configuración al objeto `BaseGraph` correcto:

```python
"erdos"      → ErdosRenyiGraph
"barabasi"   → BarabasiAlbertGraph
"watts"      → WattsStrogatzGraph
"hyper"      → HyperGraph
"snap"       → SNAPGraph
"multilayer" → MultiLayerGraph
```

### `main()`

Lee `configs/config.py`, construye el grafo, crea la `Simulation` y ejecuta según los flags de `OUTPUT`.

---

## 7. `config.py` — configuración

Tres diccionarios editables sin tocar código:

```python
GRAPH = {
    "type": "erdos",        # tipo de grafo
    "num_nodes": 100,
    "edge_prob": 0.25,      # erdos
    "ws_k": 6,              # watts / multilayer
    "ws_rewire_prob": 0.1,
    "ba_m": 3,              # barabasi / multilayer
    "snap_dataset": "ego-Facebook",
}

SIMULATION = {
    "days": 60,
    "steps_per_day": 10,    # total: 600 steps
    "fire_probability": 0.20,
    "seed": 42,
    "interval_ms": 500,
}

OUTPUT = {
    "basename": "simulation",
    "export_csv": True,
    "export_json": True,
    "render_plots": True,
    "render_gif": False,
    "show": False,
}
```

---

## 8. Flujo completo de una simulación

```
main()
  │
  ├─ build_graph(cfg.GRAPH)          → BaseGraph (lazy)
  │
  ├─ Simulation(graph, ...)
  │     ├─ DataCollector()
  │     └─ NetworkModel(graph, agent_factory)
  │           └─ por cada nodo → agent_factory(model, node_id) → agente
  │
  ├─ sim.run_headless()  ─────────────────────────────────────────────────┐
  │     └─ para t en range(sim_time):                                     │
  │           model.step()                                                │
  │             ├─ TX: agents.shuffle_do("step")                         │
  │             │       └─ cada agente → emit_message(msg)               │
  │             └─ RX: para msg en _outbox:                              │
  │                       _inboxes[target].append(msg)                   │
  │                       data_collector.record_message(msg)             │
  │                                                                       │
  ├─ sim.export_data()   → CSV + JSON con todas las Interaction           │
  └─ sim.render_static_plots()  → degree.png + heatmap.png               │
                                                                          │
                          (BayesianAgent en detalle)                      │
                          step t:                                         │
                            OBSERVE: consume_inbox → brain.observe()     │
                            DECIDE:  brain.decide() → [Action, ...]      │
                            ACT:     make_message() + emit_message()     │
```

---

## 9. Relaciones entre clases

```
BaseGraph (ABC)
  ├─ ErdosRenyiGraph
  ├─ BarabasiAlbertGraph
  ├─ WattsStrogatzGraph
  ├─ HyperGraph
  ├─ MultiLayerGraph
  └─ SNAPGraph ──uses──► SNAPDownloader

BaseAgent (ABC, mesa.Agent)
  ├─ StochasticAgent
  └─ BayesianAgent ──has──► Brain (ABC)
                               └─ BayesianMemoryBrain

NetworkModel (mesa.Model)
  ├─ has ──► nx.Graph          (via BaseGraph.graph)
  ├─ has ──► DataCollector
  └─ creates ──► [BaseAgent]   (via agent_factory)

DataCollector
  └─ has ──► [Interaction]

Message ◄── emitido por agentes, registrado como Interaction
```

---

## 10. Diseño y decisiones clave

**Lazy construction en grafos**: `BaseGraph.graph` como `@property` con caché interna. Permite instanciar configuraciones baratas y retrasar la descarga/generación hasta que sea necesaria.

**Inyección de fábrica en `NetworkModel`**: el modelo no conoce el tipo concreto de agente. Recibe un `Callable[[NetworkModel, int], BaseAgent]`. Esto permite simulaciones híbridas (mezcla de tipos de agentes) sin modificar `NetworkModel`.

**Separación TX/RX en `model.step()`**: todos los agentes leen su inbox del paso anterior (`t-1`) y emiten mensajes que se entregan al final del step (`t`). Elimina el sesgo de orden de ejecución.

**`trace_id` vs `message_id`**: `message_id` identifica cada evento de envío; `trace_id` conecta mensajes causalmente relacionados. Un agente que responde a un mensaje heredado pasa el mismo `trace_id`.

**`BayesianMemoryBrain` desacoplado del agente**: `Brain` solo conoce `Message` y valores de confianza. El `BayesianAgent` actúa de intermediario entre el modelo y el cerebro. Permite intercambiar implementaciones de cerebro sin tocar el agente.

**`MultiLayerGraph` con invariante de capas**: se garantiza que un par (u,v) no aparece en ambas capas a la vez. La capa analógica usa confianza basada en distancia de grafo (Dunbar); la digital usa distribución log-normal sesgada por popularidad (grado de entrada).
