"""Interfaz base para los grafos de la simulación."""

from __future__ import annotations

from abc import ABC, abstractmethod

import networkx as nx


class BaseGraph(ABC):
    """
    Envoltorio común para todos los tipos de grafos. Cada subclase construye
    un `networkx.Graph` (o `DiGraph`) en `build()` y lo expone en `.graph`.
    """

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed
        self._graph: nx.Graph | None = None

    @property
    def graph(self) -> nx.Graph:
        if self._graph is None:
            self._graph = self.build()
        return self._graph

    @abstractmethod
    def build(self) -> nx.Graph:
        """Construye y devuelve el grafo subyacente."""

    @staticmethod
    def ensure_connected(g: nx.Graph) -> nx.Graph:
        """Une componentes conexas añadiendo aristas mínimas."""
        if isinstance(g, nx.DiGraph):
            base = g.to_undirected()
        else:
            base = g
        if nx.is_connected(base):
            return g
        components = list(nx.connected_components(base))
        for i in range(len(components) - 1):
            u = next(iter(components[i]))
            v = next(iter(components[i + 1]))
            g.add_edge(u, v)
        return g

    def __len__(self) -> int:
        return self.graph.number_of_nodes()
