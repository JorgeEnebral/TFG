"""Tipos de datos compartidos por todos los módulos de la simulación.

Define los enums de dominio (Modality, Emotion, Layer) y el dataclass
inmutable Message que viaja por la red en cada paso de simulación.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Modality(str, Enum):
    """Modalidad de transmisión de un mensaje."""

    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"


class Emotion(str, Enum):
    """Emoción dominante asociada a un mensaje."""

    JOY = "joy"
    FEAR = "fear"
    ANGER = "anger"
    SADNESS = "sadness"
    DISGUST = "disgust"
    SURPRISE = "surprise"
    TRUST = "trust"
    NEUTRAL = "neutral"


class Layer(str, Enum):
    """Capa de red por la que viaja un mensaje."""

    ANALOG = "analog"
    DIGITAL = "digital"


@dataclass(frozen=True, slots=True)
class Message:
    """Mensaje inmutable que viaja entre agentes durante la simulación.

    Attributes:
        message_id: Identificador único global (autoincremental).
        trace_id: Agrupa mensajes de la misma cadena causal.
        timestep: Paso de simulación en el que se emite.
        source: Nodo emisor.
        target: Nodo receptor.
        layer: Capa de red por la que viaja.
        modalities: Conjunto de modalidades del mensaje.
        emotion: Emoción dominante.
        emotional_load: Intensidad emocional en [0, 1].
        veracity: Verdad percibida del contenido en [0, 1].
        salience: Relevancia subjetiva para el emisor en [0, 1].
        parent_message_id: Mensaje que desencadenó éste, o None.
    """

    message_id: int
    trace_id: int
    timestep: int
    source: int
    target: int
    layer: Layer
    modalities: frozenset[Modality]
    emotion: Emotion
    emotional_load: float           # [0, 1]
    veracity: float                 # [0, 1]
    salience: float                 # [0, 1]
    parent_message_id: int | None = None
