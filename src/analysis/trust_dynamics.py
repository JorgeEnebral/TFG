"""Evolución de trust si se hace adaptativa (placeholder)."""
from __future__ import annotations


def trust_summary(
    trust_matrix: dict[tuple[int, int], float],
) -> dict[str, float]:
    """Calcula estadísticas básicas de la matriz de confianza.

    Args:
        trust_matrix: Mapa ``{(origen, destino): trust}`` con valores en [0, 1].

    Returns:
        Diccionario con ``"mean"``, ``"min"`` y ``"max"``, o vacío si la
        matriz está vacía.
    """
    values = list(trust_matrix.values())
    if not values:
        return {}
    return {
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
    }
