# Informe — Siguiente nivel de construcción de la red social multiagente

> Documento maestro del TFG. Estudio comparativo, arquitectura y plan de implementación por fases para evolucionar el simulador `mesa` actual hacia una red social bicapa (analógica + digital) con agentes dotados de cerebro, mensajes con carga semántica/emocional/modal, relaciones con confianza y scoring de superioridad cognitiva basado en bucle OODA.

---

## 1. Resumen ejecutivo y objetivos

El simulador parte de una base sólida: `mesa 3.x`, grafos `networkx` (ER, Barabási-Albert, Watts-Strogatz, hipergrafo por cliques, datasets SNAP), `NetworkModel` con `agents.shuffle_do("step")` y un `DataCollector` ya preparado para causalidad encadenada (`trace_id`, `previous_message_ids`).

El **siguiente nivel** convierte ese motor en una red social realista:

- **Horizonte**: 2 meses · 10 timesteps/día = **600 timesteps**.
- **Bicapa**: capa analógica (pequeño mundo, no dirigido, confianza alta tipo Dunbar) + capa digital (scale-free, dirigido, confianza baja con cola larga). Mismos nodos, sin aristas duplicadas entre capas. Opcionalmente, tercera capa como hipergrafo de grupos.
- **Agentes con cerebro**: interfaz `Brain` con implementación recomendada `BayesianMemoryBrain` (memoria asociativa + Bayesiano). Permite enchufar otros cerebros (reglas, RL, LLM) sin tocar el modelo.
- **Mensajes ricos**: `Message` dataclass con tópico, modalidad, emoción, carga emocional, veracidad, salience, intent, encadenamiento causal.
- **Bucle OODA** (Observar → Decidir → Actuar) por agente y por timestep.
- **Scoring de superioridad cognitiva (CSS)** offline, derivado del paper `Fuentes/Papers/2603.05222v1.pdf`.
- **Visualización**: GIF triple (capa analógica sola, capa digital sola, vista combinada apilada) y replay de trazas existentes.

**Criterios de éxito**:

1. Corrida headless de 600 pasos con `N ≈ 200` agentes en `< 5 min`.
2. Reproducibilidad estricta (misma semilla ⇒ misma traza CSV byte a byte).
3. Trazas exportables con todas las variables semánticas, analizables offline en notebooks.
4. GIF triple correcto y `TraceReplayer` que reproduce una traza pre-grabada sin volver a simular.
5. `mypy --strict`, `ruff`, `pylint ≥ 8.0`, `pytest --cov ≥ 80%` verdes.

---

## 2. Estado actual del repositorio

Inventario relevante (rutas reales del repo):

| Fichero | Estado | Qué se reutiliza |
|---|---|---|
| `src/agents/base.py` | Abstracto `BaseAgent(mesa.Agent)` | Se mantiene; se le añade `self.brain: Brain \| None` y un buffer `self.inbox`. |
| `src/agents/stochastic.py` | `StochasticAgent.step()` con `fire_probability` | Se mantiene como **baseline** para comparar contra agentes con cerebro. |
| `src/graphs/base.py` | `BaseGraph` con `@property graph` lazy + `ensure_connected` | Reutilizado por la nueva capa multilayer. |
| `src/graphs/random.py` | ER, BA, Watts-Strogatz | Reutilizados como *builders* internos de `MultiLayerGraph`. |
| `src/graphs/hypergraph.py` | `HyperGraph` (clique projection, `neighbors_via_hyperedges`) | Reutilizado para la capa de grupos opcional. |
| `src/graphs/snap.py` | `SNAPGraph` con datasets reales | Útil como capa digital empírica alternativa. |
| `src/model.py` | `NetworkModel.step()` con `active_messages: list[tuple[int,int]]` | Se sustituye `tuple` por `Message`; se añade buffer de entrada por nodo y dos sub-fases (tx/rx) si hace falta. |
| `src/datacollector.py` | `Interaction(trace_id, message_id, timestep, source, target, previous_message_ids)` | Se amplían campos. `to_csv` / `to_json` solo añaden columnas. |
| `src/visualizer.py` | `NetworkAnimator`, `DegreeDistributionPlot`, `MessageHeatmap`, `_DarkStyle` | `_DarkStyle` y layout cacheado se reutilizan en el `MultiLayerAnimator`. |
| `src/simulation.py` | CLI completo + `run_headless` / `run_with_animation` | Se añaden flags `--days`, `--steps-per-day`, `--config`, `--brain`. |
| `tests/test_agent.py`, `tests/test_graph.py` | Vacíos | Se rellenan en cada fase. |
| `Fuentes/Papers/2603.05222v1.pdf` | Paper base de CSS | Referencia teórica del scoring. |

**Principio**: no se rompe el API público existente; se extiende. `StochasticAgent` debe seguir funcionando exactamente como ahora tras la migración.

---

## 3. Modelo de mensaje extendido

Nuevo `src/messages.py`:

```python
from dataclasses import dataclass, field
from enum import Enum

class Modality(str, Enum):
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"

class Emotion(str, Enum):
    JOY = "joy"
    FEAR = "fear"
    ANGER = "anger"
    SADNESS = "sadness"
    DISGUST = "disgust"
    SURPRISE = "surprise"
    TRUST = "trust"
    NEUTRAL = "neutral"

class Layer(str, Enum):
    ANALOG = "analog"
    DIGITAL = "digital"

@dataclass(frozen=True, slots=True)
class Message:
    message_id: int
    trace_id: int
    timestep: int
    source: int
    target: int                              # nodo o hyperedge_id si broadcast
    layer: Layer
    topic: str                               # etiqueta semántica ("election", "vaccine", ...)
    modalities: frozenset[Modality]
    emotion: Emotion
    emotional_load: float                    # ∈ [0, 1] intensidad de la emoción
    veracity: float                          # ∈ [0, 1] verdad subjetiva del emisor
    salience: float                          # ∈ [0, 1] qué tan llamativo
    intent: str                              # "inform" | "persuade" | "alert" | "entertain" | ...
    payload: dict = field(default_factory=dict)
    parent_message_id: int | None = None     # mensaje del que es respuesta/forward
```

### Cambios derivados

- `NetworkModel.emit_message(msg: Message)` reemplaza a `emit_message(src, tgt)`.
  Para no romper `StochasticAgent`, se ofrece una *factory* `model.make_message(source, target, **kw)` que rellena `message_id` y `timestep` automáticamente con defaults neutros (`topic="generic"`, `emotion=NEUTRAL`, `emotional_load=0.0`, ...).
- `Interaction` añade columnas: `layer, topic, emotion, emotional_load, modalities, veracity, salience, intent`. `to_csv` amplía `fieldnames`; `modalities` se serializa como cadena separada por `|`.
- El buffer pasa de `list[tuple[int,int]]` a `list[Message]`, manteniendo semántica per-step (se vacía al inicio de cada `step()`).

### Por qué estas variables

- **emoción + carga emocional**: literatura sobre contagio emocional en redes (Kramer et al. 2014; Ferrara & Yang 2015) muestra que el contenido emocional es predictor fuerte de propagación.
- **modalidad**: vídeo y audio tienen mayor persistencia perceptual y se propagan distinto que el texto en redes digitales (informes de Pew Research y Reuters Digital News Report).
- **veracity vs. emotional_load**: separan la dimensión "qué tan cierto cree el emisor que es" de "qué tan visceral lo presenta", clave para modelar desinformación.
- **salience**: permite que el receptor decida atender o ignorar (cuello de botella atencional).
- **intent**: necesaria para CSS — sin distinguir `inform` vs. `persuade` no se puede atribuir cambio de decisión.

---

## 4. Cerebro del agente — estudio comparativo y diseño

### 4.1 Estudio comparativo

| Enfoque | Coste/step | Escala a 600·N | Reproducibilidad | Realismo | Explicabilidad | Encaje OODA |
|---|---|---|---|---|---|---|
| (a) Reglas / autómata finito | muy bajo | excelente | total | bajo | alta | directo |
| (b) **Memoria asociativa + Bayesiano** *(recomendado)* | bajo | excelente | total (semilla) | medio-alto | alta | directo |
| (c) DBN / Kalman simple | bajo-medio | bueno | total | medio-alto | media | directo |
| (d) Mapa cognitivo borroso (FCM) | bajo | bueno | total | medio | media | bueno |
| (e) Bandits contextuales / Q-learning tabular | medio (entrenamiento) | bueno | parcial (exploración) | medio | media | directo |
| (f) NN pequeña entrenada offline | medio | bueno (inferencia) | parcial | medio-alto | baja | directo |
| (g) LLM local pequeño por agente (Phi-3, Llama-3.2 1B) | **alto** | malo (GPU) | parcial | alto | media | costoso |
| (h) LLM remoto (Anthropic Haiku 4.5) por agente | **muy alto** ($, latencia) | inviable a 600·N | parcial (temperature) | muy alto | media | inviable |
| (i) Híbrido (b) + LLM puntual | medio | bueno | parcial | alto donde se aplica | media | bueno |

**Veredicto**: (b) como cerebro por defecto; arquitectura abierta para incorporar (i) en un subconjunto de agentes (p. ej. *influencers* o *adversarios*) en experimentos cualitativos.

### 4.2 Interfaz `Brain` y `BayesianMemoryBrain`

Nuevo `src/agents/brain.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from src.messages import Message, Layer

@dataclass
class Action:
    kind: str                       # "send" | "forward" | "silence"
    target: int
    layer: Layer
    message: Message | None         # None si silence

class Brain(ABC):
    @abstractmethod
    def observe(self, msg: Message, sender_trust: float) -> None: ...

    @abstractmethod
    def decide(
        self,
        neighbors_trust: dict[tuple[int, Layer], float],
        timestep: int,
    ) -> list[Action]: ...
```

`BayesianMemoryBrain` — esquema:

```python
import math
from collections import defaultdict
from src.agents.brain import Brain, Action
from src.messages import Message, Emotion, Layer

class BayesianMemoryBrain(Brain):
    """
    Memoria:
      - beliefs[topic] = (alpha, beta)  → Beta(α, β), media = α/(α+β)
      - mood[emotion]  = float ∈ [0, 1] con decay exponencial por step
      - last_seen[topic] = timestep  → recencia (atención)

    Actualización (observe):
      weight = sender_trust * msg.salience
      evidence = msg.veracity * weight
      beliefs[msg.topic].alpha += evidence
      beliefs[msg.topic].beta  += (1 - msg.veracity) * weight
      mood[msg.emotion] = clamp(mood[msg.emotion] + msg.emotional_load * weight)

    Decisión (decide):
      Para cada vecino (n, layer):
        score = utility(belief_strength, mood, trust(n,layer), affinity_topic_n)
        if score > θ_send:  emit Message con
            topic       = sample_top_belief()
            emotion     = argmax(mood)
            emotional_load = mood[emotion]
            veracity    = belief_mean(topic)             # transmite lo que cree
            salience    = score
            intent      = "persuade" if score > θ_persuade else "inform"
            parent_message_id = último que reforzó esa creencia
    """
    def __init__(self,
                 prior_alpha: float = 1.0,
                 prior_beta: float = 1.0,
                 mood_decay_per_day: float = 0.5,
                 steps_per_day: int = 10,
                 theta_send: float = 0.4,
                 theta_persuade: float = 0.7):
        self.beliefs: dict[str, list[float]] = defaultdict(
            lambda: [prior_alpha, prior_beta]
        )
        self.mood: dict[Emotion, float] = defaultdict(float)
        self.last_seen: dict[str, int] = {}
        self._mood_decay_step = mood_decay_per_day ** (1.0 / steps_per_day)
        self._theta_send = theta_send
        self._theta_persuade = theta_persuade

    def observe(self, msg: Message, sender_trust: float) -> None:
        w = sender_trust * msg.salience
        ab = self.beliefs[msg.topic]
        ab[0] += msg.veracity * w
        ab[1] += (1.0 - msg.veracity) * w
        self.mood[msg.emotion] = min(
            1.0, self.mood[msg.emotion] + msg.emotional_load * w
        )
        self.last_seen[msg.topic] = msg.timestep

    def decide(self, neighbors_trust, timestep):
        # decay de humor
        for e in list(self.mood):
            self.mood[e] *= self._mood_decay_step
        # ... selección de tópico y vecinos (ver pseudo-código arriba)
        return []   # esqueleto
```

### 4.3 Integración con el agente

```python
# src/agents/bayesian.py
from src.agents.base import BaseAgent
from src.agents.brain import Brain

class BayesianAgent(BaseAgent):
    def __init__(self, model, node_id: int, brain: Brain):
        super().__init__(model, node_id)
        self.brain = brain

    def step(self) -> None:
        # OBSERVE
        for msg in self.model.consume_inbox(self.node_id):
            trust = self.model.trust(msg.source, self.node_id, msg.layer)
            self.brain.observe(msg, sender_trust=trust)
        # DECIDE + ACT
        neighbors_trust = self.model.neighbors_trust(self.node_id)
        for action in self.brain.decide(neighbors_trust, self.model.current_step):
            if action.kind in ("send", "forward") and action.message is not None:
                self.model.emit_message(action.message)
```

---

## 5. Grafo multicapa (analógica + digital) e hipergrafo

### 5.1 Nuevo `src/graphs/multilayer.py`

```python
import math
import random
import networkx as nx
from src.graphs.base import BaseGraph
from src.graphs.random import WattsStrogatzGraph, BarabasiAlbertGraph
from src.messages import Layer

class MultiLayerGraph(BaseGraph):
    """
    Capas:
      - analog  : Watts-Strogatz (small world), no dirigido.
      - digital : scale-free dirigido (Barabási-Albert dirigido / Bollobás).
                  Arista A->B  ≡  B sigue a A  (B recibe mensajes de A).

    Invariante: ningún par ordenado (u, v) aparece en ambas capas.
    """

    def __init__(
        self,
        num_nodes: int,
        ws_k: int = 6,
        ws_rewire_prob: float = 0.1,
        ba_m: int = 3,
        seed: int | None = None,
    ):
        super().__init__(seed=seed)
        self.num_nodes = num_nodes
        self.ws_k = ws_k
        self.ws_rewire_prob = ws_rewire_prob
        self.ba_m = ba_m

    def build(self) -> nx.MultiDiGraph:
        rng = random.Random(self.seed)
        analog = WattsStrogatzGraph(
            self.num_nodes, k=self.ws_k,
            rewire_prob=self.ws_rewire_prob, seed=self.seed,
        ).graph
        digital_undirected = BarabasiAlbertGraph(
            self.num_nodes, m=self.ba_m, seed=self.seed,
        ).graph

        g = nx.MultiDiGraph()
        g.add_nodes_from(range(self.num_nodes))

        # capa analógica: no dirigida → 2 aristas dirigidas
        analog_pairs: set[frozenset[int]] = set()
        for u, v in analog.edges():
            analog_pairs.add(frozenset((u, v)))
            trust = self._dunbar_trust(u, v, analog, rng)
            g.add_edge(u, v, layer=Layer.ANALOG, trust=trust)
            g.add_edge(v, u, layer=Layer.ANALOG, trust=trust)

        # capa digital: dirigida; evita pares ya presentes en analógica
        for u, v in digital_undirected.edges():
            for a, b in ((u, v), (v, u)):
                if frozenset((a, b)) in analog_pairs:
                    continue
                if g.has_edge(a, b, key=None):  # ya existe en digital
                    continue
                trust = self._digital_trust(a, b, digital_undirected, rng)
                g.add_edge(a, b, layer=Layer.DIGITAL, trust=trust)
        return g

    # ---- confianza ----
    def _dunbar_trust(self, u, v, analog, rng):
        # rango (5, 15, 50, 150) mapeado por distancia/ranking de proximidad
        dist = nx.shortest_path_length(analog, u, v)
        if dist <= 1:        # núcleo
            return rng.uniform(0.85, 1.00)
        if dist == 2:        # simpatía
            return rng.uniform(0.65, 0.85)
        if dist == 3:        # afinidad
            return rng.uniform(0.40, 0.65)
        return rng.uniform(0.15, 0.40)

    def _digital_trust(self, a, b, digital, rng):
        # log-normal con cola corta de fuentes muy confiables
        base = min(1.0, max(0.0, rng.lognormvariate(mu=-2.0, sigma=0.8)))
        # bonus reputacional si el emisor (a) es hub
        in_deg = digital.degree(a)
        return min(1.0, base + 0.0008 * in_deg)
```

### 5.2 Confianza por capas (Dunbar)

Capa analógica, distribución típica:

| Capa Dunbar | Tamaño aprox | Rango trust | Heurística aproximación |
|---|---|---|---|
| Núcleo de apoyo | 5 | 0.85–1.00 | vecinos directos (dist = 1) |
| Simpatía | 15 | 0.65–0.85 | dist = 2 |
| Afinidad | 50 | 0.40–0.65 | dist = 3 |
| Conocidos activos | 150 | 0.15–0.40 | dist ≥ 4 |

Si `N < 150` la asignación se escala por percentiles de distancia en lugar de números absolutos.

Capa digital — la literatura empírica indica:

- Confianza media en información de redes sociales es baja (Edelman Trust Barometer 2023: ~28% confía en redes sociales como fuente; Pew Research: alrededor del 50% expresa desconfianza en lo que ven en plataformas).
- Distribución asimétrica con cola corta de fuentes muy confiables (cuentas verificadas, medios consolidados): se modela con **log-normal** (`μ = -2.0, σ = 0.8`) acotada a `[0, 1]` (mediana ≈ 0.14) más un pequeño *bonus* por reputación (in-degree).
- Alternativa equivalente: `Beta(2, 8)` (media 0.20, sesgada a valores bajos).

Documentar el modelo elegido en el código y ofrecer ambas opciones por parámetro.

### 5.3 Restricción anti-duplicación entre capas

La construcción primero materializa la capa analógica y guarda `frozenset({u, v})` para cada par. Al añadir aristas digitales se descarta cualquier par ordenado cuya versión no dirigida esté en analógica. Si esto deja la capa digital muy escasa, se compensa generando aristas adicionales por *preferential attachment* sobre los nodos restantes (manteniendo distribución scale-free).

Test asociado: `assert analog_pairs.isdisjoint({frozenset(e) for e in digital_edges})`.

### 5.4 Fusión con hipergrafo

Sí es posible y recomendado como **tercera capa lógica**:

- `HyperGraph` ya existe en `src/graphs/hypergraph.py` con `neighbors_via_hyperedges` y `hyperedges_of`.
- Cada hyperedge representa un *grupo*: chat grupal (digital), familia/asociación (analógica), comunidad detectada por Louvain.
- `Message.target` admite `hyperedge_id`: el modelo expande el broadcast a todos los miembros con un coste atencional reducido (`salience *= 0.7`) — modela publicaciones en muro / mensajes a grupo.
- Implementar como `MultiLayerHyperGraph(MultiLayerGraph)` opcional. Permite además modelar **eventos colectivos** (manifestaciones, reuniones) que afectan al humor de todos los miembros simultáneamente.

Trade-off: añade complejidad de visualización y de scheduling; se deja para Fase 6 (opcional).

---

## 6. Bucle OODA y superioridad cognitiva

### 6.1 OODA reducido en el agente

`Observar → Decidir → Actuar` por step. El paso `Orientar` se omite por simplicidad (se considera implícito en la actualización bayesiana de creencias).

`NetworkModel.step()` pasa a dos sub-fases para evitar acoplar tx y rx en el mismo paso:

```python
def step(self) -> None:
    # sub-fase TX: cada agente decide y emite usando lo aprendido hasta t-1
    self._outbox = []
    self.agents.shuffle_do("step")
    # sub-fase RX: distribuye mensajes a los inboxes y los registra
    for msg in self._outbox:
        self._deliver(msg)
        self.data_collector.record_message(msg)
    self.current_step += 1
```

Esto garantiza que las observaciones de un step se aplican al *decide* del siguiente — coherente con OODA y con el cómputo causal del CSS.

### 6.2 Scoring de Superioridad Cognitiva (CSS)

Lectura operativa del paper `Fuentes/Papers/2603.05222v1.pdf`:

- Un agente `i` *gana* superioridad cognitiva sobre `j` cuando los mensajes de `i` provocan un **cambio en la decisión** (estado de acción) de `j`. La importancia del cambio se pondera por el rol de `j` (especialmente alto si `j` es *defender*).

Variables nuevas en el agente:

- `Agent.role ∈ {"civilian", "influencer", "defender", "adversary"}`.
- `Agent.decision_state: dict[str, float]` (posición/intención por tópico).
- En cada `Action.message` enviada por `j`, registrar `caused_by: list[message_id]` = mensajes que estaban en su `inbox` reciente y cuyo `topic` coincide.

Cálculo offline en `src/analysis/cognitive_superiority.py`:

```
Para cada par (i, j):
    CSS(i, j) = Σ_{a ∈ acciones(j)}  Δdecision_j(a) · w_role(j) · trust(i→j) ,
                 sobre acciones cuyo caused_by contiene mensajes de i.

CSS(i) = Σ_j CSS(i, j)
```

Diferenciar `CSS_attacker(i)` (suma sobre defensores) y `CSS_defender(i)` (resiliencia: 1 − fracción de cambios de decisión causados por adversarios).

`# TODO: refinar coeficientes con la ecuación exacta del paper §X tras lectura final.`

---

## 7. Visualización: GIF triple y reproducción de trazas

### 7.1 `MultiLayerAnimator`

Reutiliza `_DarkStyle` y un `nx.spring_layout` cacheado por capa.

Composición con `GridSpec(2, 2)`:

```
+----------------+----------------------+
|  digital sola  |                      |
+----------------+   vista combinada    |
|  analógica     |   (digital arriba,   |
|  sola          |    analógica abajo)  |
+----------------+----------------------+
```

- Mensajes intra-capa: flecha curva, color por `Emotion`, grosor por `emotional_load`, *linestyle* por `Modality` (sólido = texto, punteado = audio, dash-dot = vídeo, ":" = imagen).
- Mensajes inter-capa (un agente reenvía de analógica a digital o viceversa): flecha vertical entre planos en la vista combinada.
- HUD: `step / total`, mensajes activos por capa, top-3 emociones del step.
- Soporte 3D opcional con `mpl_toolkits.mplot3d` para la vista combinada (planos `z=0` analógica, `z=1` digital).

### 7.2 `TraceReplayer`

```python
class TraceReplayer:
    """Reproduce frames a partir de un CSV/JSON exportado por DataCollector,
    sin volver a ejecutar la simulación."""
    def __init__(self, trace_path: str, graph: MultiLayerGraph): ...
    def save_gif(self, path: str, cumulative: bool = False,
                 fade_alpha: float = 0.85) -> None: ...
```

Modo `--cumulative` mantiene un rastro decayente (alpha exponencial) para ver patrones de propagación en una sola imagen acumulativa al final.

---

## 8. DataCollector extendido y análisis offline

### 8.1 Extensión de `Interaction`

```python
@dataclass
class Interaction:
    trace_id: int
    message_id: int
    timestep: int
    source_node: int
    target_node: int
    previous_message_ids: list[int]
    # nuevos:
    layer: str
    topic: str
    emotion: str
    emotional_load: float
    modalities: str           # "text|video"
    veracity: float
    salience: float
    intent: str
```

Nuevos colectores:

- `record_decision(timestep, agent_id, topic, prev_value, new_value, caused_by)` → `decisions.csv`.
- `snapshot_agents(timestep, every_k=50)` → `agents_snapshot_t{T}.csv` con creencias y humor por agente (para series temporales agregadas).

### 8.2 Carpeta `src/analysis/`

- `cognitive_superiority.py` — CSS por pares y agregado, rankings, gráficos.
- `cascades.py` — árboles de cascada por `trace_id` (profundidad, viralidad, ancho máximo, tiempo de extinción).
- `emotion_dynamics.py` — series temporales por emoción/capa/rol.
- `trust_dynamics.py` — evolución de `trust` si se hace adaptativa.
- `notebooks/analysis_template.ipynb` — plantilla que consume todo lo anterior.

---

## 9. Calibración temporal (2 meses · 10 timesteps/día)

- `Simulation.sim_time = 600` por defecto. Nuevos flags CLI: `--days 60`, `--steps-per-day 10`. `sim_time = days * steps_per_day`.
- Parámetros temporales del cerebro se expresan en *días* y se convierten:

  ```
  decay_per_step = decay_per_day ** (1 / steps_per_day)
  memory_window_steps = memory_window_days * steps_per_day
  ```

- Perfil de actividad por hora del día opcional: `activity_profile[step % steps_per_day]` multiplica la probabilidad/utilidad de emitir (mínimo de madrugada).

---

## 10. Extras necesarios

Marcados como `[extra necesario]` para distinguirlos de lo estrictamente solicitado.

- **[extra necesario] Reproducibilidad estricta**: una sola semilla raíz; sub-semillas derivadas (`seed_graph`, `seed_agents`, `seed_brain`, `seed_animator`). Test que ejecuta dos corridas con misma seed y compara `interactions.csv` byte a byte.
- **[extra necesario] Rendimiento**: con 600 pasos × `N ≥ 200` × Bayesiano hay que evitar copias innecesarias; vectorizar actualización de creencias con `numpy` si `N > 500`. Profilar con `cProfile`.
- **[extra necesario] Configuración**: introducir `configs/*.yaml` (Pydantic settings) para experimentos. CLI mínimo: `--config experimento_base.yaml`. Mantener flags actuales por compatibilidad.
- **[extra necesario] Tests**: rellenar `tests/test_agent.py`, `tests/test_graph.py`; añadir `tests/test_messages.py`, `tests/test_multilayer.py`, `tests/test_brain_bayesian.py`, `tests/test_css.py`, `tests/test_replayer.py`. Cobertura ≥ 80%.
- **[extra necesario] Tipado estricto**: respetar `mypy strict = true` ya activo.
- **[extra necesario] Logging estructurado** (`logging` + JSON) para depurar cascadas largas sin saturar stdout.
- **[extra necesario] Documentación**: actualizar `README.md`, añadir `docs/architecture.md` con diagrama de capas y secuencia OODA.
- **[extra necesario] `tasks/lessons.md`**: crearlo según `CLAUDE.md` (no existe aún).
- **[extra necesario] Detección de comunidades** (Louvain) para auto-poblar el hipergrafo y los roles iniciales.
- **[extra necesario] Sub-fase tx/rx** en el `step()` del modelo (ver §6.1) — crítico para CSS.

---

## 11. Roadmap por fases con verificación

Cada fase tiene criterio de verificación reproducible. Ninguna fase mezcla varias áreas; cada una es un PR autocontenido.

### Fase 0 — Andamiaje (1–2 días)
- Crear `src/messages.py`, `src/agents/brain.py`, `src/analysis/`, `configs/`.
- `pytest -q` verde, `python -m src.simulation --help` muestra nuevos flags.

### Fase 1 — Mensaje rico + DataCollector ampliado
- `Message` dataclass, factory `model.make_message`, migración de `StochasticAgent` (que ahora envía `Message(topic="generic", ...)`).
- `Interaction` ampliada, CSV/JSON con nuevas columnas.
- **Verificación**: corrida headless con `StochasticAgent` genera CSV con nuevas columnas; `summary()` cuadra con `len(active_messages)` acumulado; test que carga el CSV y reconstruye los `Message`.

### Fase 2 — Grafo multicapa
- `MultiLayerGraph` con Dunbar (analógica) y log-normal (digital). Invariante anti-duplicación.
- `NetworkModel` adaptado para `MultiDiGraph` y consulta `neighbors(node, layer=...)`.
- **Verificación**: tests que comprueben (i) mismos N nodos en ambas capas, (ii) digital dirigida, (iii) intersección de pares vacía, (iv) distribución de trust dentro de los rangos esperados (Kolmogorov-Smirnov sobre log-normal), (v) grado medio de la analógica ≈ `ws_k`.

### Fase 3 — Cerebro bayesiano + OODA
- `BayesianMemoryBrain`, `BayesianAgent`, sub-fases tx/rx en `NetworkModel.step()`, buffer `inbox` por nodo.
- **Verificación (test de propiedad)**: un agente que recibe N mensajes positivos sobre tópico T desde fuentes con `trust ≥ 0.8` y `veracity ≥ 0.8` termina con `belief_mean(T) > prior + ε`; con `trust ≤ 0.2` apenas se mueve.

### Fase 4 — Visualización triple y replay
- `MultiLayerAnimator`, `TraceReplayer`, modo `--cumulative`.
- **Verificación**: generar GIF de 60 frames con `N = 50` (`--graph multilayer --time 60`); comprobar tamaño/duración; abrir manualmente; replay produce el mismo GIF que la corrida original.

### Fase 5 — Superioridad cognitiva
- Roles, `decision_state`, `caused_by`, `cognitive_superiority.py`.
- **Verificación (escenario sintético)**: 1 atacante con 5 *defenders* en su vecindad digital; tras 200 pasos, `CSS(atacante)` debe ser estrictamente mayor que el de cualquier civil aislado; test cuantitativo con tolerancia.

### Fase 6 — Hipergrafo opcional + calibración 600 pasos
- Activar `MultiLayerHyperGraph` (opcional). Corrida completa 60 días.
- **Verificación**: 600 pasos con `N = 200` termina headless en `< 5 min` (benchmark en CI); `analysis_template.ipynb` se ejecuta de extremo a extremo y produce las figuras esperadas.

### Fase 7 — Documentación y limpieza
- Actualizar `README.md`, `docs/architecture.md`, `tasks/lessons.md`.
- `mypy --strict`, `ruff check`, `pylint ≥ 8.0`, `pytest --cov ≥ 80%` verdes.

---

## 12. Apéndices

### A. Mapa de ficheros nuevos / modificados

| Ruta | Acción |
|---|---|
| `src/messages.py` | nuevo |
| `src/agents/brain.py` | nuevo |
| `src/agents/bayesian.py` | nuevo |
| `src/agents/base.py` | modificar (añadir `brain`, `inbox`) |
| `src/agents/stochastic.py` | modificar (migrar a `Message`) |
| `src/graphs/multilayer.py` | nuevo |
| `src/graphs/multilayer_hyper.py` | nuevo (opcional, Fase 6) |
| `src/model.py` | modificar (multilayer, tx/rx, inbox, `make_message`) |
| `src/datacollector.py` | modificar (campos nuevos, `record_decision`, `snapshot_agents`) |
| `src/visualizer.py` | modificar (añadir `MultiLayerAnimator`, `TraceReplayer`) |
| `src/simulation.py` | modificar (flags `--days`, `--steps-per-day`, `--config`, `--brain`) |
| `src/analysis/cognitive_superiority.py` | nuevo |
| `src/analysis/cascades.py` | nuevo |
| `src/analysis/emotion_dynamics.py` | nuevo |
| `src/analysis/trust_dynamics.py` | nuevo |
| `src/notebooks/analysis_template.ipynb` | nuevo |
| `configs/experimento_base.yaml` | nuevo |
| `tests/test_messages.py` | nuevo |
| `tests/test_multilayer.py` | nuevo |
| `tests/test_brain_bayesian.py` | nuevo |
| `tests/test_css.py` | nuevo |
| `tests/test_replayer.py` | nuevo |
| `tests/test_agent.py` | rellenar |
| `tests/test_graph.py` | rellenar |
| `docs/architecture.md` | nuevo |
| `tasks/lessons.md` | nuevo |
| `README.md` | actualizar |

### B. Referencias

- `Fuentes/Papers/2603.05222v1.pdf` — base del scoring de superioridad cognitiva.
- `Fuentes/Papers/0106096v1.pdf` — clásico de redes (probablemente Watts-Strogatz / scale-free).
- `Fuentes/Libros/networks-book.pdf` — referencia textbook (Newman/Easley-Kleinberg).
- Dunbar, R. I. M. (1992, 2010) — capas concéntricas y número de Dunbar.
- Edelman Trust Barometer (informe anual) — confianza en redes sociales vs. medios tradicionales.
- Pew Research Center — estudios sobre confianza en plataformas y consumo digital.
- Allcott, H. & Gentzkow, M. (2017) — desinformación en redes sociales.
- Centola, D. (2010) — propagación de comportamientos en redes.
- Ferrara, E. & Yang, Z. (2015) — contagio emocional en Twitter.
- Kramer, A. D. I. et al. (2014) — contagio emocional a escala masiva en redes sociales.

### C. Glosario

- **OODA**: Observe-Orient-Decide-Act (aquí sin Orient).
- **CSS**: Cognitive Superiority Score.
- **Dunbar**: capas concéntricas (5, 15, 50, 150) de relaciones sociales humanas.
- **Scale-free dirigido**: distribución de grado de salida (o entrada) con cola de potencias.
- **Hipergrafo**: generalización del grafo donde una arista (hyperedge) conecta cualquier número de nodos.
- **Traza**: secuencia de `Interaction` (mensajes y decisiones) producida por una corrida, exportable y reproducible.
- **Cascada**: subárbol causal originado por un mensaje semilla a través de `parent_message_id` / `caused_by`.
