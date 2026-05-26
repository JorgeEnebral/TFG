"""
Grafo bicapa que combina una capa analógica y una capa digital.

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
from src.graphs.trust import digital_trust, dunbar_trust
from src.messages import Layer


class MultiLayerGraph(BaseGraph):
    """Grafo bicapa: analógica (small-world) + digital (scale-free o SNAP).

    Invariante: ningún par de nodos {u, v} aparece en ambas capas.
    La capa digital tiene prioridad; la analógica descarta sus aristas repetidas.

    Sobrescribe `build()` directamente (no usa el template method de `BaseGraph`)
    porque gestiona dos topologías y la prioridad digital > analog.

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

    def _build_topology(self) -> nx.Graph:
        """No usado: `MultiLayerGraph` sobrescribe `build()` directamente."""
        raise NotImplementedError  # pragma: no cover

    def build(self) -> nx.MultiDiGraph:
        """Construye el grafo bicapa combinando las dos capas.

        Primero incorpora la capa digital completa. Después añade las aristas
        de la capa analógica, omitiendo los pares ya presentes en la digital.

        Returns:
            ``nx.MultiDiGraph`` con aristas etiquetadas por ``layer`` y
            ``trust``. Ningún par {u, v} aparece en ambas capas.
        """
        rng = random.Random(self.seed)

        digital_nx: nx.Graph = nx.convert_node_labels_to_integers(
            self.digital_graph.graph
        )
        analog_nx: nx.Graph = nx.convert_node_labels_to_integers(
            self.analog_graph.graph
        )

        g: nx.MultiDiGraph = nx.MultiDiGraph()
        g.add_nodes_from(digital_nx.nodes())
        g.add_nodes_from(analog_nx.nodes())
        g.graph["directed"] = True

        # --- Capa digital (tiene prioridad) ---
        digital_pairs: set[frozenset[int]] = set()
        for u, v in digital_nx.edges():
            pair: frozenset[int] = frozenset((u, v))
            if pair in digital_pairs:
                continue
            digital_pairs.add(pair)
            trust = digital_trust(u, v, digital_nx, rng)
            g.add_edge(u, v, layer=Layer.DIGITAL, trust=trust)

        # --- Capa analógica (omite pares ya en digital) ---
        # El grafo analógico es ahora un MultiDiGraph con u→v Y v→u por cada
        # arista original, así que necesitamos deduplicar igual que en digital.
        analog_seen: set[frozenset[int]] = set()
        for u, v in analog_nx.edges():
            pair: frozenset[int] = frozenset((u, v))
            if pair in digital_pairs or pair in analog_seen:
                continue
            analog_seen.add(pair)
            trust = dunbar_trust(u, v, analog_nx, rng)
            g.add_edge(u, v, layer=Layer.ANALOG, trust=trust)
            g.add_edge(v, u, layer=Layer.ANALOG, trust=trust)

        return g
