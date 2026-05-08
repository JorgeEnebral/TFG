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
from typing import Callable

import mesa
import networkx as nx

# Importamos por nombre porque los necesitamos en runtime
# (no solo para anotaciones). Los módulos `agents` y `datacollector`
# NO importan a `model`, así que no hay ciclo.
from src.agents.base import BaseAgent
from src.datacollector import DataCollector


# `# type: ignore` -> mesa.Model no tiene stubs completos para mypy.
class NetworkModel(mesa.Model):  # type: ignore
    """
    Modelo Mesa parametrizable.

    Recibe los tres ingredientes ya listos:
      - `graph`          : `nx.Graph` ya construido (vienen de un BaseGraph).
      - `agent_factory`  : callable `(model, node_id) -> BaseAgent`.
                           Inyectar la fábrica permite cambiar el tipo de
                           agente sin tocar el modelo.
      - `data_collector` : opcional. Si se pasa, se reusa; si no, crea uno.

    Atributos resultantes:
      - `graph`            : el grafo (referencia, no copia).
      - `data_collector`   : DataCollector activo.
      - `active_messages`  : lista efímera (src, tgt) del paso actual.
      - `current_step`     : contador de pasos ya ejecutados.
      - `agent_by_node`    : dict node_id -> agente, para acceso rápido.
      - heredados de mesa.Model: `agents`, `random`, `running`, etc.
    """

    def __init__(
        self,
        graph: nx.Graph,
        agent_factory: Callable[["NetworkModel", int], BaseAgent],
        data_collector: DataCollector | None = None,
        seed: int = 42,
    ) -> None:
        # `super().__init__(rng=seed)` inicializa el RNG compartido
        # (`self.random`), el `AgentSet` (`self.agents`) y demás
        # estado interno de Mesa. SIN esta llamada nada funciona.
        super().__init__(rng=seed)

        # Guardamos la referencia al grafo. No lo copiamos: el modelo y
        # el visualizador comparten la misma instancia.
        self.graph = graph

        # Inicialización del DataCollector.
        # OJO: hay que escribir este `if ... is not None else ...` y NO
        # `data_collector or DataCollector()`. Razón: `DataCollector` define
        # `__len__`, así que un colector recién creado (vacío) es "falsy"
        # y `or` lo descartaría creando otro nuevo, perdiendo el que pasó
        # el caller. Bug real que ya nos tropezamos.
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
        """
        API pública que usan los agentes para registrar un mensaje.

        Existe en lugar de que los agentes toquen `active_messages`
        directamente porque desacopla:
          - hoy `active_messages` es una list de tuplas;
          - mañana podría ser una cola con prioridades, un buffer
            con TTL, una estructura por canal, etc.
        Cambiar la representación interna no obligaría a tocar agentes.
        """
        self.active_messages.append((source, target))

    def step(self) -> None:
        """
        Avanza la simulación un paso.

        Estructura del tick:
          1. Vaciamos `active_messages` (los mensajes son por-paso, no acumulan).
          2. Ejecutamos `step()` de TODOS los agentes en orden ALEATORIO.
          3. Volcamos los mensajes emitidos en este paso al DataCollector.
          4. Incrementamos el contador de pasos.
        """
        # 1) Reset del buffer efímero. Si no, los mensajes del paso anterior
        #    se sumarían a los nuevos (bug que tendríamos al renderizar).
        self.active_messages = []

        # 2) `agents.shuffle_do("step")` es el helper de Mesa 3.x para
        #    "aleatoriza el orden y llama .step() a cada agente".
        #    El orden aleatorio importa: si fuera siempre el mismo,
        #    introduciríamos sesgo sistemático (los primeros agentes
        #    siempre actúan antes y "ven" el grafo limpio).
        #    El RNG es el del modelo, así que con la misma seed -> mismo orden.
        self.agents.shuffle_do("step")

        # 3) Persistimos las trazas en el DataCollector. Le pasamos el
        #    paso ACTUAL (current_step), no el siguiente, porque queremos
        #    indexar los mensajes con el step durante el cual ocurrieron.
        for src, tgt in self.active_messages:
            self.data_collector.record(self.current_step, src, tgt)

        # 4) Avanzar el reloj. Tras esto, `current_step` apunta al
        #    siguiente paso a ejecutar.
        self.current_step += 1
