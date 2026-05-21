"""Series temporales de emoción por capa y rol."""
from __future__ import annotations

from collections import defaultdict


def emotion_series(
    interactions: list[dict[str, object]],
    group_by: str = "layer",
) -> dict[str, dict[int, int]]:
    """Construye series temporales de conteo de mensajes agrupados por campo.

    Args:
        interactions: Filas de interacción (``asdict(Interaction)``).
        group_by: Campo por el que agrupar: ``"layer"``, ``"emotion"``
            o ``"intent"``.

    Returns:
        Diccionario ``{valor_grupo: {timestep: conteo}}``.
    """
    result: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for row in interactions:
        key = row.get(group_by, "unknown")
        t = row["timestep"]
        result[key][t] += 1
    return {k: dict(v) for k, v in result.items()}
