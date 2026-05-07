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

# Heredar de nuestro `BaseAgent`, no directamente de `mesa.Agent`.
from src.agents.base import BaseAgent

if TYPE_CHECKING:
    from src.model import NetworkModel


class StochasticAgent(BaseAgent):
    """
    Cerebro mínimo: con probabilidad p, dispara un mensaje a un vecino.

    Atributos:
      - heredados de `BaseAgent`:
          * `model`, `unique_id`, `random` (vía mesa.Agent)
          * `node_id`
      - propios:
          * `fire_probability` (float en [0, 1]): probabilidad de disparar
            en cada llamada a `step()`.
    """

    def __init__(
        self,
        model: "NetworkModel",
        node_id: int,
        fire_probability: float,
    ) -> None:
        # Constructor del padre registra al agente en y guardar el `node_id`.
        super().__init__(model, node_id)

        self.fire_probability = fire_probability

    def step(self) -> None:
        """
        Lógica que se ejecuta una vez por agente y por paso de simulación.

        Mesa la invoca desde `model.agents.shuffle_do("step")`, que recorre
        todos los agentes en orden aleatorio y llama a su `step()`.
        """
        # 1) Tirada aleatoria. `self.random` es el RNG del modelo
        #    (compartido y sembrado con `seed`), no el `random` global.
        #    Usar este RNG es lo que permite que la simulación sea reproducible
        
        #    Si el número aleatorio > umbral, el agente no actúa en este paso. 
        if self.random.random() >= self.fire_probability:
            return

        # 2) Recogemos los vecinos del nodo en el grafo subyacente.
        neighbors = list(self.model.graph.neighbors(self.node_id))

        # 3) Si el nodo está aislado, no hay a quién enviar nada.
        if not neighbors:
            return

        # 4) Elegimos un vecino al azar. Distribución uniforme sobre los vecinos.
        target = self.random.choice(neighbors)

        # 5) Notificamos al modelo. No tocamos directamente las listas
        #    internas del modelo: usamos `emit_message` como API pública.
        #    Esto desacopla al agente del cómo se almacenan los mensajes
        self.model.emit_message(self.node_id, target)
