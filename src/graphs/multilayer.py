"""Grafo bicapa que combina una capa analógica y una capa digital.

La capa analógica (Watts-Strogatz) modela relaciones cara a cara con
confianza basada en distancia de Dunbar. La capa digital (Barabási-Albert)
modela relaciones online con confianza log-normal ponderada por grado.
"""

from __future__ import annotations

import random

import networkx as nx

from src.graphs.base import BaseGraph
from src.graphs.random import ScaleFreeGraph, WattsStrogatzGraph
from src.messages import Layer


class MultiLayerGraph(BaseGraph):
    """Grafo bicapa: analógica (Watts-Strogatz) + digital (ScaleFree dirigido).

    Invariante: ningún par ordenado (u, v) aparece en ambas capas.
    """

    def __init__(
        self,
        num_nodes: int = 10_000,
        ws_k: int = 220,
        ws_rewire_prob: float = 0.1,
        sf_alpha: float = 0.41,
        sf_beta: float = 0.54,
        sf_gamma: float = 0.05,
        sf_delta_in: float = 0.2,
        sf_delta_out: float = 0.0,
        seed: int | None = None,
    ) -> None:
        """Inicializa la configuración del grafo bicapa.

        Args:
            num_nodes: Número de nodos en ambas capas.
            ws_k: Vecinos en el anillo inicial de Watts-Strogatz (par).
            ws_rewire_prob: Probabilidad de recableo en la capa analógica.
            sf_alpha: Prob. de crecimiento por in-grado en la capa digital.
            sf_beta: Prob. de enlace entre nodos existentes en la capa digital.
            sf_gamma: Prob. de crecimiento por out-grado en la capa digital.
            sf_delta_in: Sesgo de selección por in-grado.
            sf_delta_out: Sesgo de selección por out-grado.
            seed: Semilla del generador.
        """
        super().__init__(seed=seed)
        self.num_nodes = num_nodes
        self.ws_k = ws_k
        self.ws_rewire_prob = ws_rewire_prob
        self.sf_alpha = sf_alpha
        self.sf_beta = sf_beta
        self.sf_gamma = sf_gamma
        self.sf_delta_in = sf_delta_in
        self.sf_delta_out = sf_delta_out

    def __len__(self) -> int:
        """Devuelve el número de nodos configurado."""
        return self.num_nodes

    def build(self) -> nx.MultiDiGraph:
        """Construye el grafo bicapa combinando las dos capas.

        Returns:
            ``nx.MultiDiGraph`` con aristas etiquetadas por ``layer`` y
            ``trust``. Ningún par ordenado (u, v) aparece en ambas capas.
        """
        rng = random.Random(self.seed)

        analog_nx = WattsStrogatzGraph(
            self.num_nodes, k=self.ws_k, rewire_prob=self.ws_rewire_prob, seed=self.seed
        ).graph
        digital_base: nx.MultiDiGraph = ScaleFreeGraph(
            self.num_nodes,
            alpha=self.sf_alpha,
            beta=self.sf_beta,
            gamma=self.sf_gamma,
            delta_in=self.sf_delta_in,
            delta_out=self.sf_delta_out,
            seed=self.seed,
        ).graph

        g: nx.MultiDiGraph = nx.MultiDiGraph()
        g.add_nodes_from(range(self.num_nodes))

        # Capa analógica (no dirigida → 2 aristas dirigidas por par)
        analog_pairs: set[frozenset[int]] = set()
        for u, v in analog_nx.edges():
            analog_pairs.add(frozenset((u, v)))
            trust = self._dunbar_trust(u, v, analog_nx, rng)
            g.add_edge(u, v, layer=Layer.ANALOG, trust=trust)
            g.add_edge(v, u, layer=Layer.ANALOG, trust=trust)

        # Capa digital (dirigida); ya orientada, solo evita pares en analógica
        for u, v in digital_base.edges():
            if frozenset((u, v)) in analog_pairs:
                continue
            # Evitar duplicados en la misma capa digital
            if any(
                d.get("layer") == Layer.DIGITAL
                for d in g.get_edge_data(u, v, default={}).values()
            ):
                continue
            trust = self._digital_trust(u, v, digital_base, rng)
            g.add_edge(u, v, layer=Layer.DIGITAL, trust=trust)

        return g

    def _dunbar_trust(
        self,
        u: int,
        v: int,
        analog: nx.Graph,
        rng: random.Random,
    ) -> float:
        """Calcula la confianza analógica basada en distancia de Dunbar.

        Cuanto mayor la distancia en el grafo analógico, menor la confianza.

        Args:
            u: Nodo origen.
            v: Nodo destino.
            analog: Grafo analógico subyacente (Watts-Strogatz).
            rng: Generador aleatorio local.

        Returns:
            Valor de confianza en [0.15, 1.0] según la distancia entre u y v.
        """
        # Distancia en el anillo original (posición relativa)
        n = analog.number_of_nodes()
        ring_dist = min(abs(u - v), n - abs(u - v))  # distancia circular

        thresholds = [5, 15, 50, 150]

        if ring_dist <= thresholds[0]:
            return rng.uniform(0.85, 1.00)   # íntimos
        if ring_dist <= thresholds[1]:
            return rng.uniform(0.65, 0.85)   # buenos amigos
        if ring_dist <= thresholds[2]:
            return rng.uniform(0.40, 0.65)   # amigos
        return rng.uniform(0.15, 0.40)       # conocidos

    def _digital_trust(
        self,
        a: int,
        b: int,
        digital: nx.DiGraph,
        rng: random.Random,
    ) -> float:
        in_b  = digital.in_degree(b)   # popularidad del destino
        out_a = digital.out_degree(a)  # selectividad del origen

        # Media: inversamente proporcional a la popularidad del destino.
        # Un hub con 1000 seguidores genera menos confianza individual
        # que un nodo con 10 seguidores.
        mu = 1.0 / (1.0 + 0.005 * in_b)

        # Sigma: el origen poco selectivo (sigue a mucha gente)
        # tiene confianza más dispersa — menos deliberada.
        sigma = 0.05 + 0.003 * out_a

        # Vecinos comunes como bonus — reciprocidad social digital
        common = len(
            set(digital.successors(a)) & set(digital.predecessors(b))
        )
        bonus = 0.04 * min(common, 5)  # cap en 5 vecinos comunes

        trust = rng.gauss(mu, sigma) + bonus
        return min(1.0, max(0.0, trust))
