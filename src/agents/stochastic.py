"""
Agente que dispara mensajes a seguidores con probabilidad fija.

Dos fases por step:
  - Reenvío: si tiene mensajes en el inbox y sale cara en
    `trace_continue_probability`, reenvía el último mensaje recibido
    a un subconjunto aleatorio de sus seguidores.
  - Creación: si sale cara en `fire_probability`, crea un mensaje nuevo
    y lo envía a un subconjunto aleatorio de sus seguidores.

El tamaño del subconjunto se elige uniformemente entre 1 y el total
de seguidores disponibles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.messages import Message

if TYPE_CHECKING:
    from src.simulation import NetworkModel


class StochasticAgent(BaseAgent):
    """Cerebro mínimo con reenvío y emisión multidestino.

    Attributes:
        fire_probability: Probabilidad en [0, 1] de crear un mensaje nuevo.
        trace_continue_probability: Probabilidad en [0, 1] de reenviar un
            mensaje del inbox al inicio del step.
    """

    def __init__(
        self,
        model: NetworkModel,
        node_id: int,
        fire_probability: float,
        trace_continue_probability: float = 0.10,
    ) -> None:
        """Inicializa el agente estocástico.

        Args:
            model: NetworkModel donde se registra el agente.
            node_id: Id del nodo del grafo en el que vive este agente.
            fire_probability: Probabilidad en [0, 1] de crear un mensaje nuevo.
            trace_continue_probability: Probabilidad en [0, 1] de reenviar
                el último mensaje recibido a los seguidores.
        """
        super().__init__(model, node_id)
        self.fire_probability = fire_probability
        self.trace_continue_probability = trace_continue_probability

    def _sample_targets(self, followers: list[int]) -> list[int]:
        """Elige un subconjunto aleatorio de seguidores de tamaño 1..N."""
        n = self.random.randint(1, len(followers))
        return self.random.sample(followers, n)

    def step(self) -> None:
        """Ejecuta reenvío y creación de mensajes según probabilidades."""
        followers = list(self.model.graph.predecessors(self.node_id))
        if not followers:
            return

        # Fase 1: reenvío de mensajes del inbox
        inbox: list[Message] = self.model.consume_inbox(self.node_id)
        if inbox and self.random.random() < self.trace_continue_probability:
            original = inbox[-1]
            for target in self._sample_targets(followers):
                msg = self.model.make_message(
                    source=self.node_id,
                    target=target,
                    layer=original.layer,
                    emotion=original.emotion,
                    emotional_load=original.emotional_load,
                    veracity=original.veracity,
                    salience=original.salience,
                    modalities=original.modalities,
                    parent_message_id=original.message_id,
                    trace_id=original.trace_id,
                )
                self.model.emit_message(msg)

        # Fase 2: creación de mensaje nuevo
        if self.random.random() < self.fire_probability:
            for target in self._sample_targets(followers):
                msg = self.model.make_message(self.node_id, target)
                self.model.emit_message(msg)
