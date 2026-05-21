"""
Modelo Mesa que envuelve un grafo y agentes.

`NetworkModel` es la pieza central de la simulación. Orquesta tres
componentes que viven en sus propios módulos:

    +------------+         +-----------+         +---------------+
    |   graph    |  uses   |   agents  |  emit   | DataCollector |
    | (nx.Graph) |<--------|  (BaseAg.)|-------->|  (trazas)     |
    +------------+         +-----------+         +---------------+
            \\               /                        /
             \\             /                        /
              v           v                        v
              +--------------------------------------+
              |             NetworkModel             |
              +--------------------------------------+

El modelo NO sabe de qué TIPO concreto son ni el grafo ni los agentes.
Recibe una `agent_factory` (callable) que decide cómo construir cada
agente. Eso permite tener simulaciones híbridas de agentes sin tocar esta clase.
"""

from __future__ import annotations

from collections.abc import Callable

import mesa
import networkx as nx

from src.agents import BaseAgent
from src.datacollector import DataCollector
from src.messages import Emotion, Layer, Message, Modality


class NetworkModel(mesa.Model):  # type: ignore
    """Modelo Mesa parametrizable.

    Recibe los tres ingredientes ya listos. Inyectar la fábrica permite
    cambiar el tipo de agente sin tocar el modelo.

    Attributes:
        graph: El grafo subyacente (referencia, no copia).
        data_collector: DataCollector activo donde se vuelcan las trazas.
        active_messages: Lista efímera de tuplas (src, tgt) del paso actual.
        current_step: Contador de pasos ya ejecutados.
        agent_by_node: Diccionario node_id -> agente, para acceso O(1).
        agents: Heredado de `mesa.Model`. AgentSet con todos los agentes.
        random: Heredado de `mesa.Model`. RNG compartido y sembrado.
        running: Heredado de `mesa.Model`. Flag de simulación activa.
    """

    def __init__(
        self,
        graph: nx.Graph,
        agent_factory: Callable[[NetworkModel, int], BaseAgent],
        collector: DataCollector,
        seed: int = 42,
    ) -> None:
        """Inicializa el modelo y crea un agente por cada nodo del grafo.

        Args:
            graph: Grafo de NetworkX ya construido (típicamente proveniente
                de un `BaseGraph`). El modelo NO lo copia.
            agent_factory: Callable `(model, node_id) -> BaseAgent` que
                construye el agente concreto que vive en cada nodo.
            seed: Semilla para el RNG compartido (`self.random`).
        """
        # `super().__init__(rng=seed)` inicializa el RNG compartido
        # (`self.random`), el `AgentSet` (`self.agents`) y demás
        # estado interno de Mesa. SIN esta llamada nada funciona.
        super().__init__(rng=seed)

        # Guarda la referencia al grafo. Sin copia: el modelo y
        # el visualizador comparten la misma instancia.
        self.graph = graph

        self.data_collector = collector

        # Buffer efímero de Messages del paso actual (para el visualizador).
        self.active_messages: list[Message] = []

        # Outbox: se llena durante TX y se vacía en la sub-fase RX.
        self._outbox: list[Message] = []

        # Inboxes por nodo: los agentes consumen su inbox al inicio de step().
        self._inboxes: dict[int, list[Message]] = {n: [] for n in graph.nodes()}

        # Contador autoincremental de message_id.
        self._next_message_id: int = 0
        self.current_step = 0

        self.agent_by_node: dict[int, BaseAgent] = {}
        for node_id in graph.nodes():
            agent = agent_factory(self, node_id)
            self.agent_by_node[node_id] = agent

    def make_message(
        self,
        source: int,
        target: int,
        layer: Layer = Layer.ANALOG,
        emotion: Emotion | None = None,
        emotional_load: float = 0.0,
        veracity: float = 0.5,
        salience: float = 0.5,
        modalities: frozenset[Modality] | None = None,
        parent_message_id: int | None = None,
    ) -> Message:
        """Crea un Message con message_id y timestep asignados automáticamente."""
        mid = self._next_message_id
        self._next_message_id += 1
        trace_id = self.data_collector.new_trace_id()
        return Message(
            message_id=mid,
            trace_id=trace_id,
            timestep=self.current_step,
            source=source,
            target=target,
            layer=layer,
            modalities=modalities if modalities is not None else frozenset({Modality.TEXT}),
            emotion=emotion if emotion is not None else Emotion.NEUTRAL,
            emotional_load=emotional_load,
            veracity=veracity,
            salience=salience,
            parent_message_id=parent_message_id,
        )

    def emit_message(self, msg: Message) -> None:
        """Encola un Message en el outbox del paso actual."""
        self._outbox.append(msg)

    def consume_inbox(self, node_id: int) -> list[Message]:
        """Devuelve y vacía el inbox de un nodo."""
        msgs = self._inboxes.get(node_id, [])
        self._inboxes[node_id] = []
        return msgs

    def trust(self, source: int, target: int, layer: Layer) -> float:
        """Devuelve la confianza de la arista source→target en la capa dada."""
        if isinstance(self.graph, nx.MultiDiGraph):
            for data in self.graph.get_edge_data(source, target, default={}).values():
                if data.get("layer") == layer:
                    return float(data.get("trust", 0.5))
        return 0.5

    def neighbors_trust(self, node_id: int) -> dict[tuple[int, Layer], float]:
        """Devuelve {(vecino, capa): trust} para todos los vecinos salientes."""
        result: dict[tuple[int, Layer], float] = {}
        if isinstance(self.graph, nx.MultiDiGraph):
            for nbr in self.graph.successors(node_id):
                for data in self.graph.get_edge_data(node_id, nbr, default={}).values():
                    lyr = data.get("layer", Layer.ANALOG)
                    result[(nbr, lyr)] = float(data.get("trust", 0.5))
        else:
            for nbr in self.graph.neighbors(node_id):
                result[(nbr, Layer.ANALOG)] = 0.5
        return result

    def step(self) -> None:
        """Avanza la simulación un paso con dos sub-fases TX/RX (OODA).

        Sub-fase TX: los agentes deciden y emiten usando lo aprendido hasta t-1.
        Sub-fase RX: los mensajes se entregan a los inboxes y se registran.
        """
        # Sub-fase TX: reset y ejecución de agentes
        self._outbox = []
        self.agents.shuffle_do("step")

        # Sub-fase RX: entrega y registro
        for msg in self._outbox:
            self._inboxes[msg.target].append(msg)
            self.data_collector.record_message(msg)

        # active_messages mantiene la lista del paso actual para el visualizador
        self.active_messages = list(self._outbox)

        self.current_step += 1
