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

# `Callable` para tipar la factoría de agentes.
# Forma `Callable[[args...], retorno]`.
from collections.abc import Callable

import mesa
import networkx as nx

from src.agents import BaseAgent
from src.datacollector import DataCollector


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
        data_collector: DataCollector | None = None,
        seed: int = 42,
    ) -> None:
        """Inicializa el modelo y crea un agente por cada nodo del grafo.

        Args:
            graph: Grafo de NetworkX ya construido (típicamente proveniente
                de un `BaseGraph`). El modelo NO lo copia.
            agent_factory: Callable `(model, node_id) -> BaseAgent` que
                construye el agente concreto que vive en cada nodo.
            data_collector: DataCollector preexistente para reusar. Si es
                None se crea uno nuevo.
            seed: Semilla para el RNG compartido (`self.random`).
        """
        # `super().__init__(rng=seed)` inicializa el RNG compartido
        # (`self.random`), el `AgentSet` (`self.agents`) y demás
        # estado interno de Mesa. SIN esta llamada nada funciona.
        super().__init__(rng=seed)

        # Guarda la referencia al grafo. Sin copia: el modelo y
        # el visualizador comparten la misma instancia.
        self.graph = graph

        # Inicialización del DataCollector.
        self.data_collector = (
            data_collector if data_collector is not None else DataCollector()
        )

        # Buffer efímero. Se vacía al principio de cada `step()` y se llena
        # cuando los agentes llaman a `emit_message()`. Al final del step
        # se vuelca al DataCollector y se descarta.
        # Tupla `(src, tgt)` -> ligero, suficiente para la animación.
        self.active_messages: list[tuple[int, int]] = []

        # Contador de pasos. El primero es 0, así casa con `range(sim_time)`.
        self.current_step = 0

        # Mapa node_id -> agente. Mesa ya guarda los agentes en `self.agents`
        # (un AgentSet), pero esa colección está indexada por unique_id, no
        # por node_id. Mantener este dict aparte permite buscar al agente
        # de un nodo en O(1) sin recorrer todos los agentes.
        self.agent_by_node: dict[int, BaseAgent] = {}
        for node_id in graph.nodes():
            # La factoría se encarga de construir el agente concreto.
            # Cuando el agente llama a `super().__init__(model)` en su
            # constructor, Mesa lo registra automáticamente en `self.agents`.
            agent = agent_factory(self, node_id)
            self.agent_by_node[node_id] = agent

    def emit_message(self, source: int, target: int) -> None:
        """Registra el envío de un mensaje en el buffer del paso actual.

        API pública que usan los agentes para registrar un mensaje sin
        tocar directamente `active_messages`. Desacopla a los agentes
        de la representación interna del buffer (hoy lista de tuplas,
        mañana podría ser una cola con prioridades, buffer con TTL,
        estructuras por canal, etc.).

        Args:
            source: Node id del agente emisor.
            target: Node id del receptor.
        """
        self.active_messages.append((source, target))

    def step(self) -> None:
        """Avanza la simulación un paso.

        Estructura del tick:
          1. Vacía `active_messages` (los mensajes son por-paso, no acumulan).
          2. Ejecuta `step()` de todos los agentes en orden aleatorio.
          3. Vuelca los mensajes emitidos en este paso al DataCollector.
          4. Incrementa el contador de pasos.
        """
        # 1) Reset del buffer efímero. Si no, los mensajes del paso anterior
        #    se sumarían a los nuevos (bug al renderizar).
        self.active_messages = []

        # 2) `agents.shuffle_do("step")` es el helper de Mesa 3.x para
        #    "aleatoriza el orden y llama .step() a cada agente".
        #    El orden aleatorio importa: si fuera siempre el mismo,
        #    introduce sesgo sistemático (los primeros agentes
        #    siempre actúan antes y "ven" el grafo limpio).
        #    El RNG es el del modelo, así que con la misma seed -> mismo orden.
        self.agents.shuffle_do("step")

        # 3) Persiste las trazas en el DataCollector. El paso ACTUAL
        #    (current_step) indexa los mensajes con el step en que ocurrieron.
        for src, tgt in self.active_messages:
            self.data_collector.record(self.current_step, src, tgt)

        # 4) Avanzar el reloj. Tras esto, `current_step` apunta al
        #    siguiente paso a ejecutar.
        self.current_step += 1
