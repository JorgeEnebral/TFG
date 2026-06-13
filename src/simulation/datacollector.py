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
    layer: str = "analog"
    emotion: str = "neutral"
    emotional_load: float = 0.0
    modalities: str = "text"   # valores separados por "|"
    veracity: float = 0.5
    salience: float = 0.5
    parent_message_id: int | None = None


@dataclass
class Adoption:
    """Un evento de adopción = un agente cruza su umbral de resistencia.

    Solo se registra la primera vez que un agente adopta la narrativa (no
    las semillas, que arrancan adoptadas por inyección). Es la fuente de
    verdad para la curva de adopción y las métricas de resistencia.

    Attributes:
        node: Nodo que adopta la narrativa.
        timestep: Paso de simulación en el que cruza el umbral.
        conviction: Convicción acumulada en el momento de adoptar.
        exposures: Nº de exposiciones a la narrativa hasta adoptar (dosis).
    """

    node: int
    timestep: int
    conviction: float
    exposures: int


@dataclass
class DataCollector:
    """Acumula registros y los exporta.

    Attributes:
        interactions: Lista cronológica de interacciones.
        _next_trace_id: Contador autoincremental para `trace_id`. Se reserva
            uno nuevo por cada mensaje espontáneo (sin antecedente).
    """

    interactions: list[Interaction] = field(default_factory=list)
    adoptions: list[Adoption] = field(default_factory=list)
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
        """Registra un Message, usando su message_id y trace_id directamente."""
        from src.messages import Message  # import local para evitar circular

        assert isinstance(msg, Message)
        modalities_str = "|".join(sorted(m.value for m in msg.modalities)) or "text"
        interaction = Interaction(
            trace_id=msg.trace_id,
            message_id=msg.message_id,
            timestep=msg.timestep,
            source_node=msg.source,
            target_node=msg.target,
            layer=msg.layer.value,
            emotion=msg.emotion.value,
            emotional_load=msg.emotional_load,
            modalities=modalities_str,
            veracity=msg.veracity,
            salience=msg.salience,
            parent_message_id=msg.parent_message_id,
        )
        self.interactions.append(interaction)
        return interaction

    def record_adoption(
        self,
        node: int,
        timestep: int,
        conviction: float,
        exposures: int,
    ) -> Adoption:
        """Registra la adopción de la narrativa por un agente."""
        adoption = Adoption(
            node=node,
            timestep=timestep,
            conviction=conviction,
            exposures=exposures,
        )
        self.adoptions.append(adoption)
        return adoption

    def __len__(self) -> int:
        """Número de interacciones acumuladas.

        Returns:
            Cantidad total de eventos registrados en `self.interactions`.
        """
        return len(self.interactions)

    def to_csv(self, path: str | Path) -> Path:
        """Exporta todas las interacciones a un fichero CSV.

        Args:
            path: Ruta de destino. Las carpetas padre se crean si no existen.

        Returns:
            La ruta efectivamente escrita, como `Path`.
            
        Example:
        trace_id,message_id,timestep,source_node,target_node,layer,
            emotion,emotional_load,modalities,veracity,salience,parent_message_id
        100,2001,1,1,2,analog,neutral,0.0,text,1.0,0.4,
        100,2002,2,2,1,digital,anger,0.85,text|image,0.0,0.9,2001
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "trace_id",
                    "message_id",
                    "timestep",
                    "source_node",
                    "target_node",
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

    def adoptions_to_csv(self, path: str | Path) -> Path:
        """Exporta los eventos de adopción a un fichero CSV.

        Args:
            path: Ruta de destino. Las carpetas padre se crean si no existen.

        Returns:
            La ruta efectivamente escrita, como `Path`.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["node", "timestep", "conviction", "exposures"],
            )
            writer.writeheader()
            for ad in self.adoptions:
                writer.writerow(asdict(ad))
        return path

    def to_json(self, path: str | Path) -> Path:
        """Exporta las interacciones a un fichero JSON.

        Args:
            path: Ruta de destino. Las carpetas padre se crean si no existen.

        Returns:
            La ruta efectivamente escrita, como `Path`.
            
        Example:
        [
            {
                "trace_id": 100,
                "message_id": 2001,
                "timestep": 1,
                "source_node": 1,
                "target_node": 2,
                "layer": "analog",
                "emotion": "neutral",
                "emotional_load": 0.0,
                "modalities": "text",
                "veracity": 1.0,
                "salience": 0.4,
                "parent_message_id": null
            },
            {
                "trace_id": 100,
                "message_id": 2002,
                "timestep": 2,
                "source_node": 2,
                "target_node": 1,
                "layer": "digital",
                "emotion": "anger",
                "emotional_load": 0.85,
                "modalities": "text|image",
                "veracity": 0.0,
                "salience": 0.9,
                "parent_message_id": 2001
            }
            ]
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(tr) for tr in self.interactions], f, indent=2)
        return path
