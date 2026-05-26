"""
Funciones de confianza para aristas de grafo.

Punto único de definición: `MultiLayerGraph` y `BaseGraph._annotate`
consumen estas funciones vía el despachador `TRUST_FN`.
"""

from __future__ import annotations

import random
from collections.abc import Callable

import networkx as nx

from src.messages import Layer


def dunbar_trust(u: int, v: int, graph: nx.Graph, rng: random.Random) -> float:
    """Confianza analógica basada en distancia circular (modelo de Dunbar).

    Args:
        u: Nodo origen.
        v: Nodo destino.
        graph: Grafo subyacente (se usa solo para obtener `number_of_nodes`).
        rng: Generador aleatorio local.

    Returns:
        Valor de confianza en [0.15, 1.0] según la distancia circular.
    """
    n = graph.number_of_nodes()
    ring_dist = min(abs(u - v), n - abs(u - v))
    if ring_dist <= 5:
        return rng.uniform(0.85, 1.00)
    if ring_dist <= 15:
        return rng.uniform(0.65, 0.85)
    if ring_dist <= 50:
        return rng.uniform(0.40, 0.65)
    return rng.uniform(0.15, 0.40)


def digital_trust(a: int, b: int, graph: nx.Graph, rng: random.Random) -> float:
    """Confianza digital basada en grado de los nodos.

    Funciona tanto con grafos dirigidos (in/out-degree) como no dirigidos.

    Args:
        a: Nodo origen.
        b: Nodo destino.
        graph: Grafo subyacente.
        rng: Generador aleatorio local.

    Returns:
        Valor de confianza en [0.0, 1.0].
    """
    if isinstance(graph, nx.DiGraph):
        in_b = graph.in_degree(b)
        out_a = graph.out_degree(a)
        common = len(set(graph.successors(a)) & set(graph.predecessors(b)))
    else:
        in_b = graph.degree(b)
        out_a = graph.degree(a)
        common = len(set(graph.neighbors(a)) & set(graph.neighbors(b)))

    mu = 1.0 / (1.0 + 0.005 * in_b)
    sigma = 0.05 + 0.003 * out_a
    bonus = 0.04 * min(common, 5)
    trust = rng.gauss(mu, sigma) + bonus
    return min(1.0, max(0.0, trust))


TRUST_FN: dict[Layer, Callable[[int, int, nx.Graph, random.Random], float]] = {
    Layer.ANALOG: dunbar_trust,
    Layer.DIGITAL: digital_trust,
}
