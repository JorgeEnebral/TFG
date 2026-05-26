"""
Recolector de datos de la simulación.

Cada vez que un agente dispara un mensaje, el modelo lo registra.
Al final de la simulación, el conjunto de trazas es la fuente de verdad para:
  - exportar a CSV/JSON (análisis posterior, plots, replay).
  - alimentar visualizaciones agregadas (heatmaps, series temporales).

Esquema de cada registro:
  - trace_id     : agrupa una "traza" lógica (decisiones encadenadas).
  - message_id   : identificador único del envío (autoincremental, único siempre).
  - timestep     : paso de simulación en el que ocurre.
  - source_node  : nodo emisor.
  - target_node  : nodo receptor.

Diferencia trace_id vs message_id:
  - `message_id` : SIEMPRE único y autoincremental. Una entrada en el log
                   = un message_id. No se reutiliza nunca.
  - `trace_id`   : agrupa varios mensajes que pertenecen a la misma "traza"
                   de decisión. Cuando los agentes tengan memoria y un
                   envío sea consecuencia de uno previo (responder, reenviar,
                   reaccionar a algo recibido), el agente debe pasar el
                   trace_id heredado para que las dos entradas queden
                   ligadas. Si no se pasa, se reserva un trace_id nuevo
                   (caso "decisión espontánea, sin antecedente").
"""

from __future__ import annotations

import csv
import json

# `dataclass` ahorra escribir __init__/__repr__/__eq__ a mano.
# `asdict` convierte un dataclass en dict (útil para CSV y JSON).
# `field` permite valores por defecto "no triviales" (listas, dicts).
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Interaction:
    """Una interacción = un evento de envío individual."""

    trace_id: int
    message_id: int
    timestep: int
    source_node: int
    target_node: int
    previous_message_ids: list[int] = field(default_factory=list)
    # Campos semánticos (Fase 1)
    layer: str = "analog"
    emotion: str = "neutral"
    emotional_load: float = 0.0
    modalities: str = "text"   # valores separados por "|"
    veracity: float = 0.5
    salience: float = 0.5
    parent_message_id: int | None = None


@dataclass
class DataCollector:
    """Acumula registros y los exporta.

    Attributes:
        interactions: Lista cronológica de interacciones. Se rellena vía `record()`.
            `field(default_factory=list)` evita el bug de "default mutable":
            si pusiéramos `interactions: list = []`, todas las instancias
            compartirían la misma lista.
        _next_message_id: Contador autoincremental para `message_id`.
            Garantiza unicidad global.
        _next_trace_id: Contador autoincremental para `trace_id`. Se usa
            cuando alguien llama a `record()` sin pasar trace_id (la decisión
            es "espontánea") o cuando un agente pide explícitamente empezar
            una nueva traza con `new_trace_id()`.
    """

    interactions: list[Interaction] = field(default_factory=list)
    _next_message_id: int = 0
    _next_trace_id: int = 0

    def new_trace_id(self) -> int:
        """Reserva y devuelve un trace_id nuevo.

        Lo usa quien INICIA una traza lógica (el agente que toma una
        decisión sin antecedentes). Un agente que reacciona a un mensaje
        previo NO debe llamar a este método: debe heredar el trace_id
        del mensaje al que responde.

        Returns:
            Un nuevo trace_id entero, único e irrepetible.
        """
        tid = self._next_trace_id
        self._next_trace_id += 1
        return tid

    def record_message(self, msg: object) -> Interaction:
        """Registra un Message rico (Fase 1+). Delega en record()."""
        from src.messages import Message  # import local para evitar circular

        assert isinstance(msg, Message)
        modalities_str = "|".join(sorted(m.value for m in msg.modalities)) or "text"
        return self.record(
            timestep=msg.timestep,
            source=msg.source,
            target=msg.target,
            trace_id=msg.trace_id,
            previous_message_ids=[msg.parent_message_id] if msg.parent_message_id is not None else [],
            layer=msg.layer.value,
            emotion=msg.emotion.value,
            emotional_load=msg.emotional_load,
            modalities=modalities_str,
            veracity=msg.veracity,
            salience=msg.salience,
            parent_message_id=msg.parent_message_id,
        )

    def record(
        self,
        timestep: int,
        source: int,
        target: int,
        trace_id: int | None = None,
        previous_message_ids: list[int] | None = None,
        layer: str = "analog",
        emotion: str = "neutral",
        emotional_load: float = 0.0,
        modalities: str = "text",
        veracity: float = 0.5,
        salience: float = 0.5,
        parent_message_id: int | None = None,
    ) -> Interaction:
        """Registra un evento de envío y devuelve el Interaction creado.

        Lo llama `NetworkModel.step()` por cada `(src, tgt)` en
        `active_messages` al final de cada paso. El `message_id` se asigna
        siempre automáticamente; no se acepta como parámetro porque debe
        ser único e irrepetible.

        Args:
            timestep: Paso de simulación en el que ocurre el envío.
            source: Node id del emisor.
            target: Node id del receptor.
            trace_id: Id de traza preexistente para asociar este envío
                (caso "memoria del agente": responde/reenvía/reacciona a
                algo previo). Si es None, se reserva un trace_id nuevo
                (decisión espontánea).
            previous_message_ids: id de los mensajes anteriores con la misma
                traza relevantes para haber decidido la interacción

        Returns:
            El `Interaction` recién creado y ya añadido a `self.traces`.
        """
        # Sin trace_id, el envío inicia una traza nueva.
        # Cuando los agentes tengan memoria, deberán pasar el trace_id que recibieron.
        if trace_id is None:
            trace_id = self.new_trace_id()

        interaction = Interaction(
            trace_id=trace_id,
            previous_message_ids=previous_message_ids or [],
            message_id=self._next_message_id,
            timestep=timestep,
            source_node=source,
            target_node=target,
            layer=layer,
            emotion=emotion,
            emotional_load=emotional_load,
            modalities=modalities,
            veracity=veracity,
            salience=salience,
            parent_message_id=parent_message_id,
        )
        self.interactions.append(interaction)
        self._next_message_id += 1

        return interaction

    def __len__(self) -> int:
        """Número de interacciones acumuladas.

        Returns:
            Cantidad total de eventos registrados en `self.interactions`.
        """
        return len(self.interactions)

    def to_csv(self, path: str | Path) -> Path:
        """Exporta todos las interacciones a un fichero CSV.

        Args:
            path: Ruta de destino. Las carpetas padre se crean si no existen.

        Returns:
            La ruta efectivamente escrita, como `Path`.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # `newline=""` es la convención recomendada por la doc de csv:
        # evita líneas en blanco extra en Windows.
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "trace_id",
                    "message_id",
                    "timestep",
                    "source_node",
                    "target_node",
                    "previous_message_ids",
                    "layer",
                    "emotion",
                    "emotional_load",
                    "modalities",
                    "veracity",
                    "salience",
                    "parent_message_id",
                ],
            )
            writer.writeheader()
            for tr in self.interactions:
                writer.writerow(asdict(tr))
        return path

    def to_json(self, path: str | Path) -> Path:
        """Exporta las interacciones a un fichero JSON.

        El JSON producido es una lista de objetos, útil para herramientas
        web o para post-procesado con `pandas.read_json()`.

        Args:
            path: Ruta de destino. Las carpetas padre se crean si no existen.

        Returns:
            La ruta efectivamente escrita, como `Path`.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            # `indent=2` -> humano-legible. Si el fichero crece mucho,
            # se puede quitar para ahorrar bytes.
            json.dump([asdict(tr) for tr in self.interactions], f, indent=2)
        return path
