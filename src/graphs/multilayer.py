"""Grafo bicapa que combina una capa analógica y una capa digital.

La capa analógica (Watts-Strogatz) modela relaciones cara a cara con
confianza basada en distancia de Dunbar. La capa digital (ScaleFree o SNAP)
modela relaciones online con confianza log-normal ponderada por grado.

Ambas capas se construyen externamente y se inyectan como `BaseGraph`,
lo que permite usar cualquier topología en cada capa.
"""

from __future__ import annotations

import random

import networkx as nx

from src.graphs.base import BaseGraph
from src.messages import Layer


class MultiLayerGraph(BaseGraph):
    """Grafo bicapa: analógica (small-world) + digital (scale-free o SNAP).

    Invariante: ningún par de nodos {u, v} aparece en ambas capas.
    La capa digital tiene prioridad; la analógica descarta sus aristas repetidas.

    Attributes:
        digital_graph: Grafo de la capa digital (dirigido preferiblemente).
        analog_graph: Grafo de la capa analógica (no dirigido, p.ej. WS).
        seed: Semilla para los generadores de confianza.
    """

    def __init__(
        self,
        digital_graph: BaseGraph,
        analog_graph: BaseGraph,
        seed: int | None = None,
    ) -> None:
        """Inicializa el grafo bicapa.

        Args:
            digital_graph: Topología de la capa digital.
            analog_graph: Topología de la capa analógica.
            seed: Semilla del generador de confianza.
        """
        super().__init__(seed=seed)
        self.digital_graph = digital_graph
        self.analog_graph = analog_graph

    def build(self) -> nx.MultiDiGraph:
        """Construye el grafo bicapa combinando las dos capas.

        Primero incorpora la capa digital completa. Después añade las aristas
        de la capa analógica, omitiendo los pares ya presentes en la digital.

        Returns:
            ``nx.MultiDiGraph`` con aristas etiquetadas por ``layer`` y
            ``trust``. Ningún par {u, v} aparece en ambas capas.
        """
        rng = random.Random(self.seed)

        # Normalizar IDs a enteros consecutivos (necesario para SNAP)
        digital_nx: nx.Graph = nx.convert_node_labels_to_integers(
            self.digital_graph.graph
        )
        analog_nx: nx.Graph = nx.convert_node_labels_to_integers(
            self.analog_graph.graph
        )

        g: nx.MultiDiGraph = nx.MultiDiGraph()
        g.add_nodes_from(digital_nx.nodes())
        g.add_nodes_from(analog_nx.nodes())

        # --- Capa digital (tiene prioridad) ---
        digital_pairs: set[frozenset[int]] = set()
        for u, v in digital_nx.edges():
            pair: frozenset[int] = frozenset((u, v))
            if pair in digital_pairs:
                continue
            digital_pairs.add(pair)
            trust = self._digital_trust(u, v, digital_nx, rng)
            g.add_edge(u, v, layer=Layer.DIGITAL, trust=trust)

        # --- Capa analógica (omite pares ya en digital) ---
        for u, v in analog_nx.edges():
            if frozenset((u, v)) in digital_pairs:
                continue
            trust = self._dunbar_trust(u, v, analog_nx, rng)
            g.add_edge(u, v, layer=Layer.ANALOG, trust=trust)
            g.add_edge(v, u, layer=Layer.ANALOG, trust=trust)

        return g

    def _dunbar_trust(
        self,
        u: int,
        v: int,
        analog: nx.Graph,
        rng: random.Random,
    ) -> float:
        """Calcula la confianza analógica basada en distancia de Dunbar.

        Args:
            u: Nodo origen.
            v: Nodo destino.
            analog: Grafo analógico subyacente.
            rng: Generador aleatorio local.

        Returns:
            Valor de confianza en [0.15, 1.0] según la distancia circular.
        """
        n = analog.number_of_nodes()
        ring_dist = min(abs(u - v), n - abs(u - v))

        if ring_dist <= 5:
            return rng.uniform(0.85, 1.00)
        if ring_dist <= 15:
            return rng.uniform(0.65, 0.85)
        if ring_dist <= 50:
            return rng.uniform(0.40, 0.65)
        return rng.uniform(0.15, 0.40)

    def _digital_trust(
        self,
        a: int,
        b: int,
        digital: nx.Graph,
        rng: random.Random,
    ) -> float:
        """Calcula la confianza digital basada en grado de los nodos.

        Funciona tanto con grafos dirigidos (in/out-degree) como no dirigidos.

        Args:
            a: Nodo origen.
            b: Nodo destino.
            digital: Grafo digital subyacente.
            rng: Generador aleatorio local.

        Returns:
            Valor de confianza en [0.0, 1.0].
        """
        if isinstance(digital, nx.DiGraph):
            in_b = digital.in_degree(b)
            out_a = digital.out_degree(a)
            common = len(set(digital.successors(a)) & set(digital.predecessors(b)))
        else:
            in_b = digital.degree(b)
            out_a = digital.degree(a)
            common = len(set(digital.neighbors(a)) & set(digital.neighbors(b)))

        mu = 1.0 / (1.0 + 0.005 * in_b)
        sigma = 0.05 + 0.003 * out_a
        bonus = 0.04 * min(common, 5)

        trust = rng.gauss(mu, sigma) + bonus
        return min(1.0, max(0.0, trust))
