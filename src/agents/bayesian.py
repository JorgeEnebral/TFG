"""Agente con cerebro bayesiano: bucle OODA (Observe-Orient-Decide-Act)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.agents.brain import Brain

if TYPE_CHECKING:
    from src.model import NetworkModel


class BayesianAgent(BaseAgent):
    """Agente con cerebro bayesiano. Bucle OODA por step."""

    def __init__(self, model: NetworkModel, node_id: int, brain: Brain) -> None:
        """Inicializa el agente con el cerebro inyectado.

        Args:
            model: NetworkModel donde se registra el agente.
            node_id: Id del nodo del grafo en el que vive.
            brain: Implementación de ``Brain`` que toma las decisiones.
        """
        super().__init__(model, node_id)
        self.brain = brain

    def step(self) -> None:
        """Ejecuta un ciclo OODA completo.

        Primero consume el inbox del paso anterior (Observe) y actualiza
        el cerebro. Después pide al cerebro las acciones (Decide) y emite
        los mensajes correspondientes (Act).
        """
        # OBSERVE: procesa mensajes recibidos el paso anterior
        for msg in self.model.consume_inbox(self.node_id):
            trust = self.model.trust(msg.source, self.node_id, msg.layer)
            self.brain.observe(msg, sender_trust=trust)

        # DECIDE + ACT
        neighbors_trust = self.model.neighbors_trust(self.node_id)
        for action in self.brain.decide(neighbors_trust, self.model.current_step):
            if action.kind not in ("send", "forward"):
                continue
            msg = self.model.make_message(
                source=self.node_id,
                target=action.target,
                layer=action.layer,
                emotion=getattr(action, "_emotion", None),
                emotional_load=getattr(action, "_emotional_load", 0.0),
                veracity=0.5,
                salience=getattr(action, "_salience", 0.5),
                parent_message_id=getattr(action, "_parent_id", None),
            )
            self.model.emit_message(msg)
