"""Cerebro de los agentes: interfaces y lógica de toma de decisiones.

Define la interfaz abstracta ``Brain``, el dataclass ``Action`` y la
implementación ``EmotionalBrain``: un cerebro vectorial de 11 dimensiones
(8 emociones de Plutchik + atención + credulidad + autoconfianza) con
genética como amplificador estable, decay por dimensión y modulación
circadiana de la sugestionabilidad.

Referencias del modelo y los hiperparámetros: ver
``agente_inteligente.md`` en la raíz del repo.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np

from src.messages import Emotion, Layer, Message, Modality

# ---------------------------------------------------------------------------
# Dimensiones del embedding/genética
# ---------------------------------------------------------------------------


class Dim(IntEnum):
    """Índices fijos de las 11 dimensiones del vector embedding/genética."""

    JOY = 0
    FEAR = 1
    ANGER = 2
    SADNESS = 3
    DISGUST = 4
    SURPRISE = 5
    TRUST = 6
    ANTICIPATION = 7
    ATTENTION = 8
    CREDULITY = 9
    SELF_CONFIDENCE = 10


N_DIMS: int = 11

_EMOTION_TO_DIM: dict[Emotion, int | None] = {
    Emotion.JOY: Dim.JOY,
    Emotion.FEAR: Dim.FEAR,
    Emotion.ANGER: Dim.ANGER,
    Emotion.SADNESS: Dim.SADNESS,
    Emotion.DISGUST: Dim.DISGUST,
    Emotion.SURPRISE: Dim.SURPRISE,
    Emotion.TRUST: Dim.TRUST,
    # ``Emotion.NEUTRAL`` no entra en el vector; se mapea a ``None``.
    Emotion.NEUTRAL: None,
}

_DIM_TO_EMOTION: dict[int, Emotion] = {
    Dim.JOY: Emotion.JOY,
    Dim.FEAR: Emotion.FEAR,
    Dim.ANGER: Emotion.ANGER,
    Dim.SADNESS: Emotion.SADNESS,
    Dim.DISGUST: Emotion.DISGUST,
    Dim.SURPRISE: Emotion.SURPRISE,
    Dim.TRUST: Emotion.TRUST,
    # ``Dim.ANTICIPATION`` no tiene equivalente directo en ``Emotion`` (Plutchik
    # extiende Ekman); si se elige al componer el mensaje, se traduce a JOY.
    Dim.ANTICIPATION: Emotion.JOY,
}


# ---------------------------------------------------------------------------
# Acción que el cerebro devuelve al agente
# ---------------------------------------------------------------------------


@dataclass
class Action:
    """Decisión que un cerebro devuelve para que el agente la ejecute.

    Attributes:
        kind: ``"send"`` o ``"forward"``.
        target: Nodo destinatario.
        layer: Capa de red por la que se envía.
        emotion: Emoción dominante del mensaje a construir.
        emotional_load: Carga emocional en [0, 1].
        salience: Saliencia subjetiva del emisor en [0, 1].
        modalities: Modalidades del mensaje. Si ``None`` el modelo escoge
            un default según la capa.
        parent_id: ``message_id`` del mensaje que dispara este envío, o
            ``None`` si es un mensaje propio.
    """

    kind: str
    target: int
    layer: Layer
    emotion: Emotion = Emotion.NEUTRAL
    emotional_load: float = 0.0
    salience: float = 0.5
    modalities: frozenset[Modality] | None = None
    parent_id: int | None = None


# ---------------------------------------------------------------------------
# Interfaz Brain
# ---------------------------------------------------------------------------


class Brain(ABC):
    """Interfaz que deben implementar todos los cerebros de agente."""

    @abstractmethod
    def observe(self, msg: Message, sender_trust: float, timestep: int) -> None:
        """Actualiza el estado interno con un mensaje recibido.

        Args:
            msg: Mensaje recibido.
            sender_trust: Confianza en el emisor en [0, 1].
            timestep: Paso de simulación actual.
        """

    @abstractmethod
    def decide(
        self,
        neighbors_trust: dict[tuple[int, Layer], float],
        followers_by_layer: dict[Layer, int],
        timestep: int,
    ) -> list[Action]:
        """Decide qué acciones tomar en el paso actual.

        Args:
            neighbors_trust: Mapa ``{(vecino, capa): trust}``.
            followers_by_layer: Número de followers (predecesores en la
                capa) por capa de red.
            timestep: Paso de simulación actual.

        Returns:
            Lista de ``Action`` a ejecutar (puede estar vacía).
        """


# ---------------------------------------------------------------------------
# Defaults citados (ver agente_inteligente.md, HY-1..HY-11)
# ---------------------------------------------------------------------------


def _default_decay_per_hour() -> np.ndarray:
    """Decay multiplicativo por hora derivado de half-life por dimensión (HY-4).

    Returns:
        Vector ``(11,)`` con ``2 ** (-1 / half_life_h)`` por dimensión.
    """
    half_life_h: np.ndarray = np.array(
        [
            4.0,   # JOY
            6.0,   # FEAR
            6.0,   # ANGER
            12.0,  # SADNESS
            2.0,   # DISGUST
            2.0,   # SURPRISE
            24.0,  # TRUST
            8.0,   # ANTICIPATION
            1.0,   # ATTENTION
            48.0,  # CREDULITY
            24.0,  # SELF_CONFIDENCE
        ],
        dtype=np.float64,
    )
    return np.power(2.0, -1.0 / half_life_h)


def _default_modality_bonus() -> dict[Modality, float]:
    """Bonus aditivo por modalidad (HY-3); ``gain = 1 + Σ bonus`` con techo."""
    return {
        Modality.TEXT: 0.00,
        Modality.IMAGE: 0.10,
        Modality.AUDIO: 0.25,
        Modality.VIDEO: 0.40,
    }


def _default_circadian_params() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Parámetros (base, amp, peak_h) por dimensión para la curva circadiana (HY-6)."""
    base = np.ones(N_DIMS, dtype=np.float64)
    amp = np.zeros(N_DIMS, dtype=np.float64)
    peak = np.zeros(N_DIMS, dtype=np.float64)

    # Cognitivas — pico de procesamiento por la mañana
    amp[Dim.ATTENTION] = amp[Dim.CREDULITY] = 0.30
    peak[Dim.ATTENTION] = peak[Dim.CREDULITY] = 10.0

    # Afecto positivo (Golder & Macy 2011) — pico ~09 h
    amp[Dim.JOY] = amp[Dim.TRUST] = 0.25
    peak[Dim.JOY] = peak[Dim.TRUST] = 8.0

    # Afecto negativo — pico nocturno ~22 h
    amp[Dim.FEAR] = amp[Dim.ANGER] = amp[Dim.SADNESS] = 0.30
    peak[Dim.FEAR] = peak[Dim.ANGER] = peak[Dim.SADNESS] = 22.0

    # Autoconfianza — pico de arousal vespertino
    amp[Dim.SELF_CONFIDENCE] = 0.20
    peak[Dim.SELF_CONFIDENCE] = 16.0

    # Anticipación, disgust, surprise — sin modulación circadiana fuerte
    return base, amp, peak


def _default_target_randomness() -> dict[str, tuple[float, float]]:
    """``(α, ε)`` por banda Dunbar y por capa digital (HY-9)."""
    return {
        "dunbar5":   (2.0, 0.05),
        "dunbar15":  (1.5, 0.10),
        "dunbar50":  (1.0, 0.20),
        "dunbar150": (0.5, 0.30),
        "digital":   (0.7, 0.35),
    }


def _trust_to_dunbar_band(trust: float) -> str:
    """Mapea trust analógico a banda Dunbar (ver ``MultiLayerGraph._dunbar_trust``)."""
    if trust >= 0.85:
        return "dunbar5"
    if trust >= 0.65:
        return "dunbar15"
    if trust >= 0.40:
        return "dunbar50"
    return "dunbar150"


# ---------------------------------------------------------------------------
# EmotionalBrain: refactor vectorial
# ---------------------------------------------------------------------------


@dataclass
class BrainHyperparams:
    """Hiperparámetros del ``EmotionalBrain`` con defaults citados.

    Todos los rangos y referencias están en ``agente_inteligente.md``.
    """

    # HY-1 / HY-2
    p_create_analog: float = 0.05
    p_create_digital_base: float = 0.02
    k_follower: float = 5.0
    # HY-3
    modality_bonus: dict[Modality, float] = field(default_factory=_default_modality_bonus)
    modality_gain_cap: float = 1.75
    # HY-4
    decay_per_hour: np.ndarray = field(default_factory=_default_decay_per_hour)
    # HY-5
    genetics_mu: float = 0.5
    genetics_sigma: float = 0.15
    genetics_min: float = 0.05
    genetics_max: float = 1.0
    # HY-6 — base, amp, peak por dimensión
    circadian_base: np.ndarray = field(default_factory=lambda: _default_circadian_params()[0])
    circadian_amp: np.ndarray = field(default_factory=lambda: _default_circadian_params()[1])
    circadian_peak: np.ndarray = field(default_factory=lambda: _default_circadian_params()[2])
    # HY-7
    theta_send: float = 0.35
    # HY-8
    forward_base: float = 0.08
    forward_boost_anger: float = 0.20
    forward_boost_surprise: float = 0.10
    # HY-9
    target_randomness: dict[str, tuple[float, float]] = field(
        default_factory=_default_target_randomness
    )
    # HY-10
    attention_capacity: int = 7
    attention_decay_extra: float = 0.7
    # HY-11
    self_confidence_floor: float = 0.5
    # Tamaño máximo de cola FIFO para reenvíos
    recent_msgs_capacity: int = 32


class EmotionalBrain(Brain):
    """Cerebro vectorial de 11 dimensiones con genética y memoria.

    Mantiene ``embedding[11]`` como memoria dinámica y ``genetics[11]``
    como amplificador estable por agente. Actualiza el embedding al
    observar mensajes (modulado por modalidad, atención, credulidad,
    confianza en emisor y sugestionabilidad circadiana) y decide
    emisiones/reenvíos sobre el vector entero.

    Attributes:
        hp: Hiperparámetros (defaults citados en literatura).
        genetics: Vector ``(11,)`` fijo por agente.
        embedding: Vector ``(11,)`` dinámico clamp [0, 1].
    """

    def __init__(
        self,
        hp: BrainHyperparams | None = None,
        genetics: np.ndarray | None = None,
        seed: int | None = None,
    ) -> None:
        """Inicializa el cerebro.

        Args:
            hp: Hiperparámetros. Si ``None`` se usan los defaults citados.
            genetics: Vector de genética ``(11,)`` preasignado. Si ``None``
                se muestrea con el RNG local a partir de ``hp.genetics_mu``
                y ``hp.genetics_sigma``.
            seed: Semilla del RNG local del cerebro (muestreo de genética
                y de destinatarios).
        """
        self.hp: BrainHyperparams = hp if hp is not None else BrainHyperparams()
        self._rng: np.random.Generator = np.random.default_rng(seed)

        if genetics is None:
            sampled: np.ndarray = self._rng.normal(
                loc=self.hp.genetics_mu,
                scale=self.hp.genetics_sigma,
                size=N_DIMS,
            )
            genetics = np.clip(sampled, self.hp.genetics_min, self.hp.genetics_max)
        else:
            if genetics.shape != (N_DIMS,):
                raise ValueError(
                    f"genetics debe tener forma ({N_DIMS},), recibido {genetics.shape}"
                )

        self.genetics: np.ndarray = genetics.astype(np.float64, copy=True)
        self.embedding: np.ndarray = np.zeros(N_DIMS, dtype=np.float64)

        self._recent_msgs: deque[Message] = deque(maxlen=self.hp.recent_msgs_capacity)
        self._observed_this_step: int = 0
        self._last_decay_step: int = -1

    # --- Helpers internos --------------------------------------------------

    @staticmethod
    def _hour_of(timestep: int) -> int:
        """Hora simulada del paso (asume ``steps_per_day = 24``)."""
        return timestep % 24

    def _circadian_factor(self, timestep: int) -> np.ndarray:
        """Vector ``(11,)`` de sugestionabilidad horaria (HY-6)."""
        h = self._hour_of(timestep)
        factor: np.ndarray = self.hp.circadian_base + self.hp.circadian_amp * np.cos(
            2.0 * math.pi * (h - self.hp.circadian_peak) / 24.0
        )
        return factor

    def _modality_gain(self, modalities: frozenset[Modality]) -> float:
        """Bonus multiplicativo por combinación de modalidades (HY-3)."""
        bonus = sum(self.hp.modality_bonus.get(m, 0.0) for m in modalities)
        return min(self.hp.modality_gain_cap, 1.0 + bonus)

    @staticmethod
    def _message_to_vector(msg: Message) -> np.ndarray:
        """Construye el vector emocional ``(11,)`` desde un Message.

        Las 3 dimensiones cognitivas reciben 0; sólo se activa la dim de
        ``msg.emotion`` con peso ``msg.emotional_load``. ``Emotion.NEUTRAL``
        produce un vector nulo.
        """
        vec = np.zeros(N_DIMS, dtype=np.float64)
        dim = _EMOTION_TO_DIM.get(msg.emotion)
        if dim is not None:
            vec[dim] = float(msg.emotional_load)
        return vec

    def _apply_decay_once(self, timestep: int) -> None:
        """Aplica el decay del embedding una sola vez por step."""
        if timestep == self._last_decay_step:
            return
        self.embedding *= self.hp.decay_per_hour
        self._last_decay_step = timestep
        self._observed_this_step = 0

    # --- Observe -----------------------------------------------------------

    def observe(self, msg: Message, sender_trust: float, timestep: int) -> None:
        """Actualiza el embedding con la carga emocional del mensaje.

        Pipeline (HY-3, 5, 6, 10):
            ``Δ = m_vec * modality_gain * genetics
                  * embedding[attention] * (sender_trust * embedding[credulity])
                  * circadian(timestep) * attention_decay_k``
        """
        # Capacidad atencional limitada (HY-10): después del k-ésimo mensaje
        # del step, el impacto se atenúa por ``attention_decay_extra ** k``.
        k = self._observed_this_step
        self._observed_this_step += 1
        if k >= self.hp.attention_capacity:
            attn_extra = self.hp.attention_decay_extra ** (k - self.hp.attention_capacity + 1)
        else:
            attn_extra = 1.0

        m_vec = self._message_to_vector(msg)
        if not np.any(m_vec):
            self._recent_msgs.append(msg)
            return

        gain = self._modality_gain(msg.modalities)
        attention = float(self.embedding[Dim.ATTENTION])
        credulity = float(self.embedding[Dim.CREDULITY])

        # Las dimensiones cognitivas tienen un piso para no anular el aprendizaje
        # cuando el agente arranca con embedding=0.
        attention_eff = 0.5 + 0.5 * attention
        credulity_eff = 0.5 + 0.5 * credulity

        circadian = self._circadian_factor(timestep)

        impact = (
            m_vec
            * gain
            * self.genetics
            * attention_eff
            * sender_trust
            * credulity_eff
            * circadian
            * attn_extra
        )
        self.embedding = np.clip(self.embedding + impact, 0.0, 1.0)
        self._recent_msgs.append(msg)

    # --- Decide ------------------------------------------------------------

    def decide(
        self,
        neighbors_trust: dict[tuple[int, Layer], float],
        followers_by_layer: dict[Layer, int],
        timestep: int,
    ) -> list[Action]:
        """Decide emisiones y reenvíos sobre el vector embedding."""
        self._apply_decay_once(timestep)

        if not neighbors_trust:
            return []

        circadian = self._circadian_factor(timestep)
        circadian_send = float(circadian[Dim.SELF_CONFIDENCE])

        # Activación vectorial (HY-7). Se usa como multiplicador, NO como gate
        # duro: el headline knob es ``p_create`` (HY-1/HY-2).
        weighted = self.embedding[: Dim.ATTENTION] * self.genetics[: Dim.ATTENTION]
        score = float(np.linalg.norm(weighted) / math.sqrt(int(Dim.ATTENTION)))
        activation = self.hp.theta_send + score  # piso = theta_send (baseline)

        by_layer: dict[Layer, list[tuple[int, float]]] = {Layer.ANALOG: [], Layer.DIGITAL: []}
        for (nbr, layer), trust in neighbors_trust.items():
            by_layer.setdefault(layer, []).append((nbr, trust))

        actions: list[Action] = []
        for layer, candidates in by_layer.items():
            if not candidates:
                continue
            p_create = self._p_create(layer, followers_by_layer.get(layer, 0))
            p_create *= self.hp.self_confidence_floor + float(self.embedding[Dim.SELF_CONFIDENCE])
            p_create *= circadian_send
            p_create *= activation
            p_create = min(1.0, max(0.0, p_create))

            if self._rng.random() >= p_create:
                continue

            emotion, load = self._compose_emotion()
            modalities = (
                frozenset({Modality.AUDIO})
                if layer is Layer.ANALOG
                else self._sample_digital_modalities()
            )
            targets = self._sample_targets(candidates, layer)
            for tgt in targets:
                actions.append(
                    Action(
                        kind="send",
                        target=tgt,
                        layer=layer,
                        emotion=emotion,
                        emotional_load=load,
                        salience=min(1.0, activation),
                        modalities=modalities,
                        parent_id=None,
                    )
                )

        actions.extend(self._decide_forwards(neighbors_trust, timestep))
        return actions

    # --- Helpers de decisión ----------------------------------------------

    def _p_create(self, layer: Layer, followers: int) -> float:
        """Probabilidad base de emitir en la capa dada (HY-1, HY-2)."""
        if layer is Layer.ANALOG:
            return self.hp.p_create_analog
        # Digital: escala log-sublineal con followers
        return self.hp.p_create_digital_base * (
            1.0 + math.log1p(max(0, followers)) / self.hp.k_follower
        )

    def _compose_emotion(self) -> tuple[Emotion, float]:
        """Muestrea emoción de salida (softmax sobre 8 dims emocionales).

        Combina el estado dinámico (``embedding``) con un baseline derivado
        de la genética para que un agente "frío" (sin estímulos previos)
        siga expresando su predisposición de personalidad (HY-5).

        Returns:
            ``(emotion, emotional_load)``. La carga es la norma euclídea
            del subvector emocional combinado, normalizada a [0, 1].
        """
        baseline = 0.15 * self.genetics[: Dim.ATTENTION]
        emo_vec = self.embedding[: Dim.ATTENTION] + baseline
        if not np.any(emo_vec):
            return Emotion.NEUTRAL, 0.0
        # Softmax con temperatura 1 sobre el vector combinado
        exp = np.exp(emo_vec - emo_vec.max())
        probs = exp / exp.sum()
        idx = int(self._rng.choice(int(Dim.ATTENTION), p=probs))
        emotion = _DIM_TO_EMOTION.get(idx, Emotion.NEUTRAL)
        load = float(np.linalg.norm(emo_vec) / math.sqrt(int(Dim.ATTENTION)))
        return emotion, min(1.0, load)

    def _sample_digital_modalities(self) -> frozenset[Modality]:
        """Modalidades para un mensaje digital, sesgadas por arousal del embedding."""
        arousal = float(np.mean(self.embedding[: Dim.ATTENTION]))
        mods: set[Modality] = {Modality.TEXT}
        if self._rng.random() < 0.3 + 0.4 * arousal:
            mods.add(Modality.IMAGE)
        if self._rng.random() < 0.2 + 0.5 * arousal:
            mods.add(Modality.VIDEO)
        if self._rng.random() < 0.15 + 0.4 * arousal:
            mods.add(Modality.AUDIO)
        return frozenset(mods)

    def _sample_targets(
        self,
        candidates: Sequence[tuple[int, float]],
        layer: Layer,
    ) -> list[int]:
        """Selección estocástica de destinatarios con α/ε por banda Dunbar (HY-9)."""
        if not candidates:
            return []

        # Pesos por destinatario
        weights: list[float] = []
        for _, trust in candidates:
            band = "digital" if layer is Layer.DIGITAL else _trust_to_dunbar_band(trust)
            alpha, eps = self.hp.target_randomness[band]
            weights.append(max(trust, 0.0) ** alpha + eps)

        total = float(sum(weights))
        if total <= 0.0:
            return []
        probs = np.array(weights, dtype=np.float64) / total

        # Muestreamos cuántos destinatarios (1..ceil(score*N)) para evitar
        # broadcast a TODA la vecindad en cada step.
        max_targets = max(1, int(math.ceil(0.05 * len(candidates))))
        n = int(self._rng.integers(1, max_targets + 1))
        n = min(n, len(candidates))

        idxs = self._rng.choice(len(candidates), size=n, replace=False, p=probs)
        return [candidates[int(i)][0] for i in idxs]

    def _decide_forwards(
        self,
        neighbors_trust: dict[tuple[int, Layer], float],
        timestep: int,
    ) -> list[Action]:
        """Decide reenvíos de mensajes recientes (HY-8)."""
        if not self._recent_msgs:
            return []
        p_forward = (
            self.hp.forward_base
            + self.hp.forward_boost_anger * float(self.embedding[Dim.ANGER])
            + self.hp.forward_boost_surprise * float(self.embedding[Dim.SURPRISE])
        )
        p_forward = min(1.0, max(0.0, p_forward))
        if self._rng.random() >= p_forward:
            return []

        msg = self._recent_msgs[-1]
        by_layer: dict[Layer, list[tuple[int, float]]] = {}
        for (nbr, layer), trust in neighbors_trust.items():
            if layer is not msg.layer:
                continue
            by_layer.setdefault(layer, []).append((nbr, trust))
        candidates = by_layer.get(msg.layer, [])
        if not candidates:
            return []

        targets = self._sample_targets(candidates, msg.layer)
        return [
            Action(
                kind="forward",
                target=tgt,
                layer=msg.layer,
                emotion=msg.emotion,
                emotional_load=msg.emotional_load,
                salience=msg.salience,
                modalities=msg.modalities,
                parent_id=msg.message_id,
            )
            for tgt in targets
        ]
