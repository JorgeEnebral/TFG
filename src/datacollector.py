"""
Recolector de datos de la simulación.

Cada mensaje disparado se registra como una `Trace` con:
  - trace_id: identificador único del mensaje
  - timestep: paso de simulación en el que ocurre
  - source_node: nodo emisor
  - target_node: nodo receptor
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Trace:
    trace_id: int
    timestep: int
    source_node: int
    target_node: int


@dataclass
class DataCollector:
    """Acumula trazas y permite exportarlas a CSV/JSON."""

    traces: list[Trace] = field(default_factory=list)
    _next_id: int = 0

    def record(self, timestep: int, source: int, target: int) -> Trace:
        trace = Trace(
            trace_id=self._next_id,
            timestep=timestep,
            source_node=source,
            target_node=target,
        )
        self.traces.append(trace)
        self._next_id += 1
        return trace

    def __len__(self) -> int:
        return len(self.traces)

    def by_timestep(self, t: int) -> list[Trace]:
        return [tr for tr in self.traces if tr.timestep == t]

    def to_csv(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["trace_id", "timestep", "source_node", "target_node"]
            )
            writer.writeheader()
            for tr in self.traces:
                writer.writerow(asdict(tr))
        return path

    def to_json(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(tr) for tr in self.traces], f, indent=2)
        return path

    def summary(self) -> dict[str, int]:
        if not self.traces:
            return {"total": 0, "timesteps": 0}
        return {
            "total": len(self.traces),
            "timesteps": max(tr.timestep for tr in self.traces) + 1,
        }
