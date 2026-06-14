"""
Agente con adopción de narrativa por umbral (Linear Threshold).

Mantiene un estado cognitivo mínimo respecto a UNA narrativa rastreada
(la "operación" del run). Un mensaje pertenece a la narrativa si su
veracidad es <= `narrative_veracity_threshold` (desinfo).

Por step:
  - Exposición: por cada mensaje de la narrativa recibido, acumula
    convicción ponderada por la confianza en el emisor y la carga
    emocional. Al cruzar `theta` el agente "adopta" la narrativa y se
    registra el evento en el `DataCollector`.
  - Re-emisión espontánea: un agente adoptado reintenta difundir la última
    narrativa que vio en CADA step (con `forward_probability`), no solo al
    recibirla, para que el contagio sea autosostenido.
  - Ruido ambiental: con `fire_probability` crea un mensaje neutro nuevo
    para que la narrativa no viva en el vacío.

Referencia del diseño y las métricas: ``AI_plans/resistencia_cognitiva.md``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.messages import Layer, Message

if TYPE_CHECKING:
    from src.simulation import NetworkModel


class ResistantAgent(BaseAgent):
    """Agente con convicción, umbral de resistencia y adopción.

    Attributes:
        fire_probability: Probabilidad de crear ruido neutro por step.
        gamma: Ganancia de persuasión por exposición en [0, 1].
        theta: Umbral/resistencia innata en [0, 1]. Adopta al superarlo.
        narrative_veracity_threshold: Veracidad máxima para considerar un
            mensaje como parte de la narrativa rastreada.
        forward_probability: Probabilidad de reenviar la narrativa cuando
            el agente ya está adoptado.
        max_targets: Número máximo de destinatarios por emisión. Acota la
            capacidad humana independientemente del grado del nodo.
        conviction: Convicción acumulada hacia la narrativa en [0, 1].
        adopted: Si el agente ya cruzó el umbral.
        adopted_at: Step en el que adoptó (``None`` si no ha adoptado).
        exposures: Nº de mensajes de la narrativa recibidos.
        is_seed: Si el agente es semilla inyectora de la operación.
    """

    def __init__(
        self,
        model: NetworkModel,
        node_id: int,
        fire_probability: float,
        theta: float,
        gamma: float = 0.5,
        forward_probability: float = 0.30,
        narrative_veracity_threshold: float = 0.30,
        max_targets: int = 50,
    ) -> None:
        """Inicializa el agente resistente.

        Args:
            model: NetworkModel donde se registra el agente.
            node_id: Id del nodo del grafo en el que vive.
            fire_probability: Probabilidad de crear ruido neutro por step.
            theta: Umbral de adopción (resistencia innata) en [0, 1].
            gamma: Ganancia de persuasión por exposición en [0, 1].
            forward_probability: Probabilidad de reenviar la narrativa si
                ya está adoptado.
            narrative_veracity_threshold: Veracidad máxima para que un
                mensaje cuente como narrativa.
            max_targets: Número máximo de destinatarios por emisión.
        """
        super().__init__(model, node_id)
        self.fire_probability = fire_probability
        self.gamma = gamma
        self.theta = theta
        self.narrative_veracity_threshold = narrative_veracity_threshold
        self.forward_probability = forward_probability
        self.max_targets = max_targets

        self.conviction: float = 0.0
        self.adopted: bool = False
        self.adopted_at: int | None = None
        self.exposures: int = 0
        self.is_seed: bool = False
        # Última narrativa vista: la usa el creyente para re-emitir de forma
        # espontánea, aunque no reciba nada nuevo ese step.
        self._last_narrative: Message | None = None

    def _sample_targets(self, followers: list[int], layer: Layer) -> list[int]:
        """Elige un subconjunto aleatorio de seguidores.

        En la capa analógica el tamaño queda acotado por ``max_targets``
        (capacidad humana); en la digital no hay límite de broadcast.
        """
        cap = min(self.max_targets, len(followers)) if layer is Layer.ANALOG else len(followers)
        n = self.random.randint(1, cap)
        targets: list[int] = self.random.sample(followers, n)
        return targets

    def _is_narrative(self, msg: Message) -> bool:
        """Indica si el mensaje pertenece a la narrativa rastreada."""
        return msg.veracity <= self.narrative_veracity_threshold

    def _expose(self, msg: Message) -> None:
        """Actualiza la convicción con una exposición a la narrativa.

        Regla de actualización ponderada por confianza (Linear Threshold):
        ``conviction += (1 - conviction) * trust * emotional_load * gamma``.
        Al cruzar ``theta`` marca la adopción y la registra.
        """
        self.exposures += 1
        trust = self.model.trust(msg.source, self.node_id, msg.layer)
        self.conviction += (
            (1.0 - self.conviction) * trust * msg.emotional_load * self.gamma
        )
        self.conviction = min(1.0, self.conviction)

        if not self.adopted and self.conviction >= self.theta:
            self.adopted = True
            self.adopted_at = self.model.current_step
            self.model.data_collector.record_adoption(
                node=self.node_id,
                timestep=self.model.current_step,
                conviction=self.conviction,
                exposures=self.exposures,
            )

    def step(self) -> None:
        """Observa la narrativa, la reenvía si está adoptado y emite ruido."""
        followers = list(self.model.graph.predecessors(self.node_id))

        # Fase 0: observación. Cada exposición a la narrativa actualiza la
        # convicción y puede disparar la adopción.
        inbox: list[Message] = self.model.consume_inbox(self.node_id)
        narrative_msgs = [m for m in inbox if self._is_narrative(m)]
        for msg in narrative_msgs:
            self._expose(msg)
        if narrative_msgs:
            self._last_narrative = narrative_msgs[-1]

        if not followers:
            return

        # Fase 1: re-emisión espontánea. Un creyente reintenta difundir la
        # última narrativa que vio en CADA step (no solo al recibir), de modo
        # que el periodo "infeccioso" no se reduce a un único paso.
        if (
            self.adopted
            and self._last_narrative is not None
            and self.random.random() < self.forward_probability
        ):
            original = self._last_narrative
            for target in self._sample_targets(followers, original.layer):
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

        # Fase 2: ruido ambiental neutro (igual que StochasticAgent).
        if self.random.random() < self.fire_probability:
            for target in self._sample_targets(followers, Layer.ANALOG):
                msg = self.model.make_message(self.node_id, target)
                self.model.emit_message(msg)
