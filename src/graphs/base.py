"""
Interfaz base para los grafos de la simulación.

Toda topología single-layer hereda de `BaseGraph` e implementa `_build_topology()`.
El método `build()` es el template method: llama a `_build_topology()` y después
a `_annotate()`, que convierte el resultado a `MultiDiGraph` con atributos
`layer` y `trust` en cada arista.

`MultiLayerGraph` es la única excepción: sobrescribe `build()` directamente
porque gestiona dos topologías y la prioridad digital > analog.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod

import networkx as nx

from src.messages import Layer


class BaseGraph(ABC):
    """Envoltorio común para todos los tipos de grafos.

    Patrón de diseño: **lazy construction** + **template method**.
    El grafo NO se construye en el `__init__`, sino la primera vez que
    alguien accede a `.graph`. Las subclases implementan `_build_topology()`
    con la topología desnuda; `build()` se encarga de anotar aristas.

    Attributes:
        seed: Semilla para los generadores aleatorios.
        layer: Capa que se asignará a todas las aristas del grafo.
        _graph: Caché interna del grafo construido.
    """

    def __init__(self, seed: int | None = None, layer: Layer = Layer.ANALOG) -> None:
        """Inicializa el grafo (sin construirlo todavía).

        Args:
            seed: Semilla para los generadores aleatorios de las subclases.
            layer: Capa (`ANALOG` o `DIGITAL`) asignada a cada arista.
        """
        self.seed = seed
        self.layer = layer
        self._graph: nx.MultiDiGraph | None = None

    @property
    def graph(self) -> nx.MultiDiGraph:
        """Acceso público al grafo subyacente, con construcción lazy.

        Returns:
            `nx.MultiDiGraph` con atributos `layer` y `trust` en aristas.
        """
        if self._graph is None:
            self._graph = self.build()
        return self._graph

    @abstractmethod
    def _build_topology(self) -> nx.Graph:
        """Construye y devuelve la topología desnuda (sin anotar aristas).

        Cada subclase single-layer implementa solo este método.

        Returns:
            Grafo de NetworkX (Graph, DiGraph, …) con la topología deseada.
        """

    def build(self) -> nx.MultiDiGraph:
        """Template method: construye la topología y la anota.

        `MultiLayerGraph` sobrescribe este método directamente.

        Returns:
            `nx.MultiDiGraph` con `layer` y `trust` en cada arista.
        """
        raw = self._build_topology()
        return self._annotate(raw)

    def _annotate(self, g: nx.Graph) -> nx.MultiDiGraph:
        """Convierte `g` a `MultiDiGraph` añadiendo `layer` y `trust` a cada arista.

        Para grafos no dirigidos añade las dos direcciones u→v y v→u con el
        mismo valor de trust (mismo patrón que la capa analógica de multilayer).

        Args:
            g: Grafo de topología desnuda.

        Returns:
            `nx.MultiDiGraph` completamente anotado.
        """
        from src.graphs.trust import TRUST_FN  # evita ciclo en import del módulo

        rng = random.Random(self.seed)
        trust_fn = TRUST_FN[self.layer]

        mg: nx.MultiDiGraph = nx.MultiDiGraph()
        mg.add_nodes_from(g.nodes())
        # Preserva la direccionalidad original para que draw_graph no pinte flechas
        # en grafos que conceptualmente son no dirigidos (e.g. Erdős-Rényi ANALOG).
        mg.graph["directed"] = g.is_directed()

        seen: set[frozenset[int]] = set()
        if g.is_directed():
            for u, v in g.edges():
                trust = trust_fn(u, v, g, rng)
                mg.add_edge(u, v, layer=self.layer, trust=trust)
        else:
            for u, v in g.edges():
                pair: frozenset[int] = frozenset((u, v))
                if pair in seen:
                    continue
                seen.add(pair)
                trust = trust_fn(u, v, g, rng)
                mg.add_edge(u, v, layer=self.layer, trust=trust)
                mg.add_edge(v, u, layer=self.layer, trust=trust)

        return mg

    @staticmethod
    def ensure_connected(g: nx.Graph) -> nx.Graph:
        """Une componentes conexas añadiendo aristas mínimas.

        Args:
            g: Grafo de NetworkX. Se modifica in-place.

        Returns:
            El mismo grafo `g`, garantizado conexo.
        """
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
            g.add_edge(v, u)

        return g

    def __len__(self) -> int:
        """Número de nodos del grafo.

        Returns:
            Número de nodos (`graph.number_of_nodes()`).
        """
        n_nodes: int = self.graph.number_of_nodes()
        return n_nodes
