"""
Hipergrafo: cada hiperarista conecta un conjunto arbitrario de nodos.

Se expone también una proyección a `networkx.Graph` (clique-expansion),
de modo que cualquier código que espere un grafo simple pueda consumirlo.
"""

from __future__ import annotations

import random
from itertools import combinations

import networkx as nx

from src.graphs.base import BaseGraph


class HyperGraph(BaseGraph):
    """
    Hipergrafo simple. Una hiperarista es un `frozenset` de nodos.
    `build()` devuelve la proyección clique (cada hiperarista -> clique).
    """

    def __init__(
        self,
        num_nodes: int,
        num_hyperedges: int,
        hyperedge_size_range: tuple[int, int] = (2, 4),
        seed: int | None = None,
    ) -> None:
        super().__init__(seed=seed)
        self.num_nodes = num_nodes
        self.num_hyperedges = num_hyperedges
        self.hyperedge_size_range = hyperedge_size_range
        self.hyperedges: list[frozenset[int]] = []

    def build(self) -> nx.Graph:
        rng = random.Random(self.seed)
        nodes = list(range(self.num_nodes))
        lo, hi = self.hyperedge_size_range

        self.hyperedges = []
        for _ in range(self.num_hyperedges):
            size = rng.randint(lo, min(hi, self.num_nodes))
            members = frozenset(rng.sample(nodes, k=size))
            self.hyperedges.append(members)

        g = nx.Graph()
        g.add_nodes_from(nodes)
        for he in self.hyperedges:
            for u, v in combinations(he, 2):
                g.add_edge(u, v)
        return g

    def neighbors_via_hyperedges(self, node: int) -> set[int]:
        """Vecinos a través de hiperaristas (incluye toda la hiperarista)."""
        result: set[int] = set()
        for he in self.hyperedges:
            if node in he:
                result.update(he)
        result.discard(node)
        return result

    def hyperedges_of(self, node: int) -> list[frozenset[int]]:
        return [he for he in self.hyperedges if node in he]
