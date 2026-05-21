"""Análisis de cascadas de propagación.

Una cascada es el subárbol causal originado por un mensaje semilla,
trazado via parent_message_id en los registros del DataCollector.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx


@dataclass
class CascadeStats:
    """Métricas de una cascada de propagación.

    Attributes:
        trace_id: Identificador de la traza analizada.
        depth: Profundidad máxima del árbol causal.
        width_max: Anchura máxima (nodos en el nivel más ancho).
        virality: Número de nodos únicos alcanzados.
        extinction_step: Timestep en el que se extingue la cascada.
    """

    trace_id: int
    depth: int
    width_max: int
    virality: int
    extinction_step: int


# Tipo alias para filas de interacción exportadas como dicts (de asdict()).
# Se usa dict[str, object] para evitar Any: los valores son int, str o float.
_InteractionRow = dict[str, object]


def build_cascade_tree(interactions: list[_InteractionRow]) -> nx.DiGraph:
    """Construye el árbol causal de una cascada.

    Args:
        interactions: Lista de filas de interacción (``asdict(Interaction)``).
            Cada fila debe tener ``message_id``, ``parent_message_id``,
            ``timestep`` y ``target_node``.

    Returns:
        ``nx.DiGraph`` donde cada nodo es un ``message_id`` y cada arista
        ``parent → hijo`` representa la cadena causal.
    """
    g: nx.DiGraph = nx.DiGraph()
    for row in interactions:
        mid = row["message_id"]
        pid = row.get("parent_message_id")
        g.add_node(mid, timestep=row["timestep"], target=row["target_node"])
        if pid is not None:
            g.add_edge(pid, mid)
    return g


def cascade_stats(trace_id: int, interactions: list[_InteractionRow]) -> CascadeStats:
    """Calcula las métricas de una cascada.

    Args:
        trace_id: Identificador de la traza.
        interactions: Filas de interacción pertenecientes a esa traza.

    Returns:
        ``CascadeStats`` con profundidad, anchura, viralidad y timestep
        de extinción.
    """
    tree = build_cascade_tree(interactions)
    if not tree.nodes:
        return CascadeStats(trace_id, 0, 0, 0, 0)

    depths = nx.single_source_shortest_path_length(tree, min(tree.nodes))
    max_depth = max(depths.values()) if depths else 0

    by_depth: dict[int, int] = {}
    for d in depths.values():
        by_depth[d] = by_depth.get(d, 0) + 1
    max_width = max(by_depth.values()) if by_depth else 0

    virality = len({row["target_node"] for row in interactions})
    extinction = max((row["timestep"] for row in interactions), default=0)

    return CascadeStats(trace_id, max_depth, max_width, virality, extinction)
