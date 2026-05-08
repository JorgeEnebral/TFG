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
class Trace:
    """
    Un registro = un evento de envío individual.

    Atributos:
      - `trace_id`    : id de la traza lógica a la que pertenece este envío.
                        Varios envíos pueden compartirlo si forman parte
                        de una cadena causal (memoria de agente).
      - `message_id`  : id único del envío. Monotónico desde 0; nunca se repite.
      - `timestep`    : paso de simulación (0, 1, 2, ...).
      - `source_node` : nodo emisor del grafo.
      - `target_node` : nodo receptor del grafo.
    """

    trace_id: int
    message_id: int
    timestep: int
    source_node: int
    target_node: int


@dataclass
class DataCollector:
    """
    Acumula registros y los exporta.

    Atributos:
      - `traces` (list[Trace]): lista cronológica de registros. Se rellena
        vía `record()`. `field(default_factory=list)` evita el bug
        de "default mutable": si pusiéramos `traces: list = []`,
        TODAS las instancias compartirían la misma lista.
      - `_next_message_id` (int): contador autoincremental para `message_id`.
        Garantiza unicidad global.
      - `_next_trace_id` (int): contador autoincremental para `trace_id`.
        Se usa cuando alguien llama a `record()` sin pasar trace_id (la
        decisión es "espontánea") o cuando un agente pide explícitamente
        empezar una nueva traza con `new_trace_id()`.
    """

    traces: list[Trace] = field(default_factory=list)
    _next_message_id: int = 0
    _next_trace_id: int = 0

    def new_trace_id(self) -> int:
        """
        Reserva y devuelve un trace_id nuevo.

        Lo usa quien INICIA una traza lógica (el agente que toma una
        decisión sin antecedentes). Un agente que reacciona a un mensaje
        previo NO debe llamar a este método: debe heredar el trace_id
        del mensaje al que responde.
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
    ) -> Trace:
        """
        Registra un evento de envío y devuelve el Trace creado.

        Parámetros:
          - `timestep`, `source`, `target`: datos del envío.
          - `trace_id`: si None, se reserva un trace_id nuevo (decisión
            espontánea). Si se pasa, este envío se asocia a una traza
            preexistente (caso "memoria del agente": responde/reenvía/
            reacciona a algo previo).

        El `message_id` se asigna SIEMPRE automáticamente; no se acepta
        como parámetro porque debe ser único e irrepetible.

        Lo llama `NetworkModel.step()` por cada `(src, tgt)` en
        `active_messages` al final de cada paso.
        """
        # Política por defecto: si no nos dan trace_id, asumimos que
        # este envío inicia una traza nueva. Cuando los agentes tengan
        # memoria, deberán pasar el trace_id que recibieron.
        if trace_id is None:
            trace_id = self.new_trace_id()

        trace = Trace(
            trace_id=trace_id,
            message_id=self._next_message_id,
            timestep=timestep,
            source_node=source,
            target_node=target,
        )
        self.traces.append(trace)
        # Incrementar DESPUÉS de crear, no antes: queremos que el
        # primer message_id sea 0, no 1.
        self._next_message_id += 1
        return trace

    def __len__(self) -> int:
        # `len(collector)` -> nº de registros guardados.
        # OJO: por culpa de este __len__, `bool(collector)` es False cuando
        # está vacío. Eso nos mordió antes en NetworkModel: `dc or DataCollector()`
        # creaba uno nuevo en vez de usar el pasado. Solucionado con
        # `if dc is not None else ...` explícito en el modelo.
        return len(self.traces)

    def by_timestep(self, t: int) -> list[Trace]:
        # Filtro perezoso por paso de simulación.
        return [tr for tr in self.traces if tr.timestep == t]

    def by_trace(self, trace_id: int) -> list[Trace]:
        """
        Devuelve todos los envíos que pertenecen a una traza lógica,
        ordenados por timestep para reconstruir la cadena causal.

        Útil cuando los agentes tengan memoria: permite ver toda la
        secuencia de decisiones encadenadas a partir de un mismo origen.
        """
        return sorted(
            (tr for tr in self.traces if tr.trace_id == trace_id),
            key=lambda tr: tr.timestep,
        )

    def to_csv(self, path: str | Path) -> Path:
        """Exporta todos los registros a CSV. Devuelve la ruta escrita."""
        path = Path(path)
        # Crea carpetas padre si no existen (idempotente). Útil porque
        # los outputs viven en src/data/ que puede haberse limpiado.
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
                ],
            )
            writer.writeheader()
            for tr in self.traces:
                # `asdict(tr)` convierte el dataclass a un dict {campo: valor}.
                # `DictWriter` escribe respetando el orden de `fieldnames`.
                writer.writerow(asdict(tr))
        return path

    def to_json(self, path: str | Path) -> Path:
        """Exporta a JSON (lista de objetos). Útil para herramientas web."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            # `indent=2` -> humano-legible. Si el fichero crece mucho,
            # se puede quitar para ahorrar bytes.
            json.dump([asdict(tr) for tr in self.traces], f, indent=2)
        return path

    def summary(self) -> dict[str, int]:
        """Resumen rápido (total mensajes, trazas únicas, timesteps)."""
        # Manejo del caso vacío explícitamente: si llamamos a `max()` sobre
        # un iterable vacío Python lanza ValueError.
        if not self.traces:
            return {"total_messages": 0, "total_traces": 0, "timesteps": 0}
        return {
            "total_messages": len(self.traces),
            # `set()` deduplica los trace_id para contar trazas únicas.
            "total_traces": len({tr.trace_id for tr in self.traces}),
            # +1 porque los timesteps son 0-indexed.
            "timesteps": max(tr.timestep for tr in self.traces) + 1,
        }
