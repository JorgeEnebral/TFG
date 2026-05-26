"""
Grafos aleatorios clásicos.

Tres familias muy estudiadas en la literatura de redes complejas:

  - Erdős-Rényi G(n, p):
      cada par de nodos está conectado con probabilidad `p`, independiente.

  - Scale-Free (libre de escala):
      Topología de red caracterizada por una distribución de grado que sigue
      una ley de potencia P(k) ~ k^gamma. La mayoría de los nodos posee muy pocos
      enlaces, mientras que una minoría ("hubs") concentra la conectividad global.
      Carece de una escala o "nodo típico", siendo el modelo estructural que define la
      arquitectura del Internet físico, la Web y sistemas metabólicos.

  - Watts-Strogatz (small-world):
      parte de un anillo regular k-vecinos y recablea cada arista con
      probabilidad `p`. Combina alto clustering local con caminos cortos
      globales -> "seis grados de separación".
"""

from __future__ import annotations

import networkx as nx

from src.graphs.base import BaseGraph
from src.messages import Layer


class ErdosRenyiGraph(BaseGraph):
    """Grafo Erdős-Rényi G(n, p).

    Attributes:
        num_nodes: Número de nodos n.
        edge_prob: Probabilidad p en [0, 1] de cada arista.
        connected: Si True, postprocesa el grafo con `ensure_connected()`.
        layer: Capa asignada a todas las aristas.
        seed: Heredado de `BaseGraph`; semilla del generador de NetworkX.
    """

    def __init__(
        self,
        num_nodes: int,
        edge_prob: float,
        seed: int | None = None,
        connected: bool = True,
        layer: Layer = Layer.ANALOG,
    ) -> None:
        """Inicializa la configuración del grafo Erdős-Rényi.

        Args:
            num_nodes: Número de nodos n.
            edge_prob: Probabilidad p de cada arista.
            seed: Semilla del generador.
            connected: Si True, fuerza conexión añadiendo aristas mínimas.
            layer: Capa asignada a todas las aristas.
        """
        super().__init__(seed=seed, layer=layer)
        self.num_nodes = num_nodes
        self.edge_prob = edge_prob
        self.connected = connected

    def _build_topology(self) -> nx.Graph:
        """Construye la topología Erdős-Rényi desnuda.

        Returns:
            Grafo `nx.Graph` no dirigido con `num_nodes` nodos.
        """
        g = nx.erdos_renyi_graph(n=self.num_nodes, p=self.edge_prob, seed=self.seed)
        if self.connected:
            g = self.ensure_connected(g)
        return g


class ScaleFreeGraph(BaseGraph):
    """Grafo de libre de escala dirigido (Dorogovtsev-Mendes-Samukhin).

    Usa ``nx.scale_free_graph``, que crece añadiendo nodos y aristas en
    tres pasos mutuamente excluyentes controlados por ``alpha``, ``beta``
    y ``gamma`` (deben sumar 1.0). Produce un ``MultiDiGraph`` dirigido.

    Attributes:
        num_nodes: Número de nodos finales.
        alpha: Prob. de añadir un nodo nuevo conectado a uno existente
            elegido por distribución de in-grado.
        beta: Prob. de añadir una arista entre dos nodos existentes.
        gamma: Prob. de añadir un nodo nuevo conectado a uno existente
            elegido por distribución de out-grado.
        delta_in: Sesgo para la selección por in-grado.
        delta_out: Sesgo para la selección por out-grado.
        layer: Capa asignada a todas las aristas (default DIGITAL, acorde a su naturaleza dirigida).
        seed: Semilla del generador.
    """

    def __init__(
        self,
        num_nodes: int,
        alpha: float = 0.41,
        beta: float = 0.54,
        gamma: float = 0.05,
        delta_in: float = 0.2,
        delta_out: float = 0.0,
        seed: int | None = None,
        layer: Layer = Layer.DIGITAL,
    ) -> None:
        """Inicializa la configuración del grafo de libre de escala.

        Args:
            num_nodes: Número de nodos finales.
            alpha: Probabilidad de crecimiento por in-grado.
            beta: Probabilidad de enlace entre nodos existentes.
            gamma: Probabilidad de crecimiento por out-grado.
            delta_in: Sesgo de selección por in-grado.
            delta_out: Sesgo de selección por out-grado.
            seed: Semilla del generador.
            layer: Capa asignada a todas las aristas.
        """
        super().__init__(seed=seed, layer=layer)
        self.num_nodes = num_nodes
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta_in = delta_in
        self.delta_out = delta_out

    def _build_topology(self) -> nx.DiGraph:
        """Construye la topología libre de escala desnuda.

        Returns:
            ``nx.DiGraph`` dirigido con distribución de grado power-law.
        """
        mg = nx.scale_free_graph(
            n=self.num_nodes,
            alpha=self.alpha,
            beta=self.beta,
            gamma=self.gamma,
            delta_in=self.delta_in,
            delta_out=self.delta_out,
            seed=self.seed,
        )
        return nx.DiGraph(mg)


class WattsStrogatzGraph(BaseGraph):
    """Grafo Watts-Strogatz small-world.

    Attributes:
        num_nodes: Número de nodos en el anillo inicial.
        k: Cada nodo está conectado a sus `k` vecinos más próximos en el
            anillo (debe ser par para que el anillo sea simétrico).
        rewire_prob: Probabilidad en [0, 1] de recablear cada arista.
        layer: Capa asignada a todas las aristas.
        seed: Semilla del generador.
    """

    def __init__(
        self,
        num_nodes: int,
        k: int,
        rewire_prob: float,
        seed: int | None = None,
        layer: Layer = Layer.ANALOG,
    ) -> None:
        """Inicializa la configuración del grafo Watts-Strogatz.

        Args:
            num_nodes: Número de nodos en el anillo inicial.
            k: Vecinos más próximos en el anillo (par).
            rewire_prob: Probabilidad de recablear cada arista.
            seed: Semilla del generador.
            layer: Capa asignada a todas las aristas.
        """
        super().__init__(seed=seed, layer=layer)
        self.num_nodes = num_nodes
        self.k = k
        self.rewire_prob = rewire_prob

    def _build_topology(self) -> nx.Graph:
        """Construye la topología Watts-Strogatz desnuda.

        Returns:
            Grafo `nx.Graph` small-world.
        """
        return nx.watts_strogatz_graph(
            n=self.num_nodes, k=self.k, p=self.rewire_prob, seed=self.seed
        )
