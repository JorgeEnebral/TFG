"""Cerebro de los agentes: interfaces y lógica de toma de decisiones.

Define la interfaz abstracta Brain y la implementación EmotionalBrain,
que mantiene un vector de humor por emoción con decay exponencial y
decide en función de la carga emocional dominante.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass

from src.messages import Emotion, Layer, Message


@dataclass
class Action:
    """Decisión que un cerebro devuelve para que el agente la ejecute.

    Attributes:
        kind: Tipo de operación:
            ``"send"``    — el agente construye y emite un mensaje nuevo.
            ``"forward"`` — el agente reenvía un mensaje recibido sin modificar.
        target: Nodo destinatario de la acción.
        layer: Capa de red por la que se envía.
        message: Mensaje a enviar; ``None`` si lo construye el agente después.
    """

    kind: str
    target: int
    layer: Layer
    message: Message | None = None


class Brain(ABC):
    """Interfaz que deben implementar todos los cerebros de agente."""

    @abstractmethod
    def observe(self, msg: Message, sender_trust: float) -> None:
        """Actualiza el estado interno con un mensaje recibido.

        Args:
            msg: Mensaje recibido por el agente.
            sender_trust: Nivel de confianza en el emisor en [0, 1].
        """

    @abstractmethod
    def decide(
        self,
        neighbors_trust: dict[tuple[int, Layer], float],
        timestep: int,
    ) -> list[Action]:
        """Decide qué acciones tomar en el paso actual.

        Args:
            neighbors_trust: Mapa ``{(vecino, capa): trust}`` de los
                vecinos salientes del agente.
            timestep: Paso de simulación actual.

        Returns:
            Lista de acciones a ejecutar (puede estar vacía).
        """


class EmotionalBrain(Brain):
    """Cerebro puramente emocional sin modelo de creencias por tópico.

    Mantiene un vector de humor ``mood[emotion] ∈ [0, 1]`` que se
    actualiza al observar mensajes y decae exponencialmente cada paso.
    La decisión de enviar depende solo de la emoción dominante y la
    confianza en el vecino; no hay tópicos ni intenciones explícitas.

    Attributes:
        mood: Intensidad emocional actual por emoción.
    """

    def __init__(
        self,
        mood_decay_per_day: float = 0.5,
        steps_per_day: int = 10,
        theta_send: float = 0.4,
    ) -> None:
        """Inicializa el cerebro emocional.

        Args:
            mood_decay_per_day: Factor de decay diario del humor en (0, 1].
                Por ejemplo, 0.5 significa que el humor se reduce a la mitad
                cada día simulado.
            steps_per_day: Pasos de simulación por día; determina el decay
                por paso como ``mood_decay_per_day ** (1 / steps_per_day)``.
            theta_send: Umbral mínimo de score emocional para generar una
                acción de envío. Score = ``emotional_load x trust``.
        """
        self.mood: dict[Emotion, float] = defaultdict(float)
        self._mood_decay_step: float = mood_decay_per_day ** (1.0 / steps_per_day)
        self._theta_send: float = theta_send
        self._last_msg_id: int | None = None

    def observe(self, msg: Message, sender_trust: float) -> None:
        """Actualiza el humor con la carga emocional del mensaje recibido.

        El impacto en el humor se pondera por ``sender_trust x salience x veracity``:
        mensajes de fuentes confiables, relevantes y creíbles mueven más el estado
        emocional del agente.

        Args:
            msg: Mensaje recibido.
            sender_trust: Confianza en el emisor en [0, 1].
        """
        # AÑADIR QUE EL TIPO DE MENSAJE (TEXTO, VIDEO) INFLUYE EN LA EMOCION
        weight = sender_trust * msg.salience * msg.veracity
        self.mood[msg.emotion] = min(
            1.0, self.mood[msg.emotion] + msg.emotional_load * weight
        ) 
        # VER SI TANTA MULTIPLICACION HACE QUE DISMINUYA MUCHO CARGA EMOCIONAL
        # ESTUDIAR EMBEDING TIPO TIWITEER DE MEMORIA
        self._last_msg_id = msg.message_id

    def decide(
        self,
        neighbors_trust: dict[tuple[int, Layer], float],
        timestep: int,
    ) -> list[Action]:
        """Genera acciones de envío basándose en la emoción dominante.

        Aplica decay al humor, identifica la emoción dominante y genera
        una ``Action`` por cada vecino cuyo score ``emotional_load x trust``
        supera ``theta_send``.

        Args:
            neighbors_trust: Mapa ``{(vecino, capa): trust}``.
            timestep: Paso de simulación actual (disponible para subclases).

        Returns:
            Lista de ``Action`` a ejecutar; vacía si el humor es bajo.
        """
        for e in list(self.mood):
            self.mood[e] *= self._mood_decay_step

        if not self.mood:
            return []

        top_emotion = max(self.mood, key=lambda e: self.mood[e])
        emotional_load = float(self.mood[top_emotion])

        if emotional_load < self._theta_send:
            return []

        actions: list[Action] = []
        for (neighbor, layer), trust in neighbors_trust.items():
            score = emotional_load * trust
            if score < self._theta_send:
                continue
            # SIEMPRE MANDA ACCION SEND
            action = Action(kind="send", target=neighbor, layer=layer)
            action.__dict__.update(
                {
                    "_emotion": top_emotion,
                    "_emotional_load": emotional_load,
                    "_salience": score,
                    "_parent_id": self._last_msg_id,
                }
            )
            actions.append(action)
        return actions
