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
    """Una interacción = un evento de envío individual.

    Attributes:
        trace_id: Id de la traza lógica a la que pertenece este envío.
            Varios envíos pueden compartirlo si forman parte de una cadena
            causal (memoria de agente).
        message_id: Id único del envío. Monotónico desde 0; nunca se repite.
        timestep: Paso de simulación (0, 1, 2, ...).
        source_node: Nodo emisor del grafo.
        target_node: Nodo receptor del grafo.
        previous_message_ids: Ids de mensajes anteriores de la misma traza
            que motivaron esta interacción.
    """

    trace_id: int
    message_id: int
    timestep: int
    source_node: int
    target_node: int
    previous_message_ids: list[int] = field(default_factory=list)


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

    def record(
        self,
        timestep: int,
        source: int,
        target: int,
        trace_id: int | None = None,
        previous_message_ids: list[int] | None = None,
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

    def filter_by_timestep(self, t: int) -> list[Interaction]:
        """Devuelve todos las interacciones de un paso de simulación dado.

        Args:
            t: Paso de simulación a filtrar.

        Returns:
            Lista de `Interaction` cuyo `timestep == t`.
        """
        return [tr for tr in self.interactions if tr.timestep == t]

    def filter_by_trace(self, trace_id: int) -> dict[str, object]:
        """Devuelve los envíos de una traza lógica ordenados por timestep.

        Útil cuando los agentes tengan memoria: permite ver toda la
        secuencia de decisiones encadenadas a partir de un mismo origen.

        Args:
            trace_id: Id de la traza lógica a recuperar.

        Returns:
            Diccionario de la traza agrupado por timesteps, y cada interacción
            con su message_id, sus previous_message_ids, source_node, target_node
        """
        interactions = sorted(
            (tr for tr in self.interactions if tr.trace_id == trace_id),
            key=lambda tr: (tr.timestep, tr.source_node),
        )

        by_timestep: dict[str, list[dict[str, object]]] = {}
        for tr in interactions:
            bucket = str(tr.timestep)
            if bucket not in by_timestep:
                by_timestep[bucket] = []
            by_timestep[bucket].append(
                {
                    "message_id": tr.message_id,
                    "previous_message_ids": tr.previous_message_ids,
                    "source_node": tr.source_node,
                    "target_node": tr.target_node,
                }
            )

        return {"trace_id": trace_id, "by_timestep": by_timestep}

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

    def summary(self) -> dict[str, int]:
        """Resumen rápido de las interacciones acumuladas.

        Returns:
            Diccionario con tres claves:
              - `total_messages`: total de envíos registrados.
              - `total_traces`: número de trazas lógicas distintas.
              - `timesteps`: número de pasos cubiertos (max timestep + 1).
            Si no hay interacciones, todos los valores son 0.
        """
        if not self.interactions:
            return {"total_messages": 0, "total_traces": 0, "timesteps": 0}
        return {
            "total_messages": len(self.interactions),
            # `set()` deduplica los trace_id para contar trazas únicas.
            "total_traces": len({tr.trace_id for tr in self.interactions}),
            # +1 porque los timesteps son 0-indexed.
            "timesteps": max(tr.timestep for tr in self.interactions) + 1,
        }
