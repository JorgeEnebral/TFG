"""Grafos aleatorios clásicos."""

from __future__ import annotations

import networkx as nx

from src.graphs.base import BaseGraph


class ErdosRenyiGraph(BaseGraph):
    """Grafo Erdős–Rényi G(n, p)."""

    def __init__(
        self,
        num_nodes: int,
        edge_prob: float,
        seed: int | None = None,
        connected: bool = True,
    ) -> None:
        super().__init__(seed=seed)
        self.num_nodes = num_nodes
        self.edge_prob = edge_prob
        self.connected = connected

    def build(self) -> nx.Graph:
        g = nx.erdos_renyi_graph(n=self.num_nodes, p=self.edge_prob, seed=self.seed)
        if self.connected:
            g = self.ensure_connected(g)
        return g


class BarabasiAlbertGraph(BaseGraph):
    """Grafo Barabási–Albert (preferential attachment)."""

    def __init__(
        self,
        num_nodes: int,
        m: int,
        seed: int | None = None,
    ) -> None:
        super().__init__(seed=seed)
        self.num_nodes = num_nodes
        self.m = m

    def build(self) -> nx.Graph:
        return nx.barabasi_albert_graph(n=self.num_nodes, m=self.m, seed=self.seed)


class WattsStrogatzGraph(BaseGraph):
    """Grafo Watts–Strogatz small-world."""

    def __init__(
        self,
        num_nodes: int,
        k: int,
        rewire_prob: float,
        seed: int | None = None,
    ) -> None:
        super().__init__(seed=seed)
        self.num_nodes = num_nodes
        self.k = k
        self.rewire_prob = rewire_prob

    def build(self) -> nx.Graph:
        return nx.watts_strogatz_graph(
            n=self.num_nodes, k=self.k, p=self.rewire_prob, seed=self.seed
        )
