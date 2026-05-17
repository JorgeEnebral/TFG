"""
Agente que dispara mensajes a vecinos con probabilidad fija.

Es el agente más sencillo de la simulación y representa el "ciudadano base":
  - En cada paso de simulación tira una moneda sesgada (`fire_probability`).
  - Si sale cara, elige uniformemente uno de sus vecinos en el grafo
    y le envía un mensaje.
  - El "envío" se materializa llamando a `model.emit_message(src, tgt)`,
    que registra el evento en `active_messages` y, al final del step,
    en el `DataCollector`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.base import BaseAgent

if TYPE_CHECKING:
    from src.model import NetworkModel


class StochasticAgent(BaseAgent):
    """Cerebro mínimo: con probabilidad p, dispara un mensaje a un vecino.

    Attributes:
        fire_probability: Probabilidad en [0, 1] de disparar en cada
            llamada a `step()`.
        node_id: Heredado de `BaseAgent`. Nodo del grafo donde vive.
        model: Heredado de `mesa.Agent`. Modelo padre.
        unique_id: Heredado de `mesa.Agent`. Id único del agente.
        random: Heredado de `mesa.Agent`. RNG compartido con el modelo.
    """

    def __init__(
        self,
        model: NetworkModel,
        node_id: int,
        fire_probability: float,
    ) -> None:
        """Inicializa el agente estocástico.

        Args:
            model: NetworkModel donde se registra el agente.
            node_id: Id del nodo del grafo en el que vive este agente.
            fire_probability: Probabilidad en [0, 1] de disparar un mensaje
                en cada paso de simulación.
        """
        # Constructor del padre: registra al agente en el modelo y guarda el `node_id`.
        super().__init__(model, node_id)

        self.fire_probability = fire_probability

    def step(self) -> None:
        """Tira la moneda y, si sale cara, envía un mensaje a un vecino.

        Mesa la invoca desde `model.agents.shuffle_do("step")`, que recorre
        todos los agentes en orden aleatorio y llama a su `step()`. Si el
        nodo está aislado (sin vecinos) o falla la tirada, el agente no
        actúa en este paso.
        """
        # 1) Tirada aleatoria. `self.random` es el RNG del modelo
        #    (compartido y sembrado con `seed`), no el `random` global.
        #    Usar este RNG es lo que permite que la simulación sea reproducible

        #    Si el número aleatorio > umbral, el agente no actúa en este paso.
        if self.random.random() >= self.fire_probability:
            return

        # 2) Recupera los vecinos del nodo en el grafo subyacente.
        neighbors = list(self.model.graph.neighbors(self.node_id))

        # 3) Si el nodo está aislado, no hay a quién enviar nada.
        if not neighbors:
            return

        # 4) Elige un vecino al azar. Distribución uniforme sobre los vecinos.
        target = self.random.choice(neighbors)

        # 5) Notifica al modelo. Sin acceso directo a las listas
        #    internas: usa `emit_message` como API pública.
        #    Desacopla al agente del cómo se almacenan los mensajes
        self.model.emit_message(self.node_id, target)
