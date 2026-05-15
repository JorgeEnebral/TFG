"""
Grafos aleatorios clásicos.

Tres familias muy estudiadas en la literatura de redes complejas:

  - Erdős-Rényi G(n, p):
      cada par de nodos está conectado con probabilidad `p`, independiente.

  - Barabási-Albert (preferential attachment):
      crecimiento incremental: cada nodo nuevo se conecta a `m` existentes
      con probabilidad proporcional al grado de cada candidato. Produce
      distribución de grado libre de escala (power-law) y "hubs". Es el
      modelo canónico para redes sociales/citación a gran escala.

  - Watts-Strogatz (small-world):
      parte de un anillo regular k-vecinos y recablea cada arista con
      probabilidad `p`. Combina alto clustering local con caminos cortos
      globales -> "seis grados de separación".
"""

from __future__ import annotations

import networkx as nx

from src.graphs.base import BaseGraph


class ErdosRenyiGraph(BaseGraph):
    """Grafo Erdős-Rényi G(n, p).

    Attributes:
        num_nodes: Número de nodos n.
        edge_prob: Probabilidad p en [0, 1] de cada arista.
        connected: Si True, postprocesa el grafo con `ensure_connected()`
            para que no haya componentes aisladas.
        seed: Heredado de `BaseGraph`; semilla del generador de NetworkX.
    """

    def __init__(
        self,
        num_nodes: int,
        edge_prob: float,
        seed: int | None = None,
        connected: bool = True,
    ) -> None:
        """Inicializa la configuración del grafo Erdős-Rényi.

        Args:
            num_nodes: Número de nodos n.
            edge_prob: Probabilidad p de cada arista.
            seed: Semilla del generador.
            connected: Si True, fuerza conexión añadiendo aristas mínimas.
        """
        # Llama al padre para guardar `seed` e inicializar la caché `_graph`.
        super().__init__(seed=seed)

        self.num_nodes = num_nodes
        self.edge_prob = edge_prob
        self.connected = connected

    def build(self) -> nx.Graph:
        """Construye el grafo Erdős-Rényi.

        Returns:
            Grafo `nx.Graph` no dirigido con `num_nodes` nodos. Si
            `self.connected` es True, está garantizado conexo.
        """
        # Generador estándar de NetworkX. Devuelve un `nx.Graph` no dirigido.
        g = nx.erdos_renyi_graph(n=self.num_nodes, p=self.edge_prob, seed=self.seed)

        if self.connected:
            g = self.ensure_connected(g)
        return g


class BarabasiAlbertGraph(BaseGraph):
    """Grafo Barabási-Albert (preferential attachment).

    Attributes:
        num_nodes: Número total de nodos finales.
        m: Cuántas aristas añade cada nodo nuevo al entrar. El grado
            mínimo final es `m`; los hubs aparecen por acumulación.
        seed: Semilla del generador.
    """

    def __init__(
        self,
        num_nodes: int,
        m: int,
        seed: int | None = None,
    ) -> None:
        """Inicializa la configuración del grafo Barabási-Albert.

        Args:
            num_nodes: Número total de nodos finales.
            m: Aristas que añade cada nodo nuevo al entrar.
            seed: Semilla del generador.
        """
        super().__init__(seed=seed)
        self.num_nodes = num_nodes
        self.m = m

    def build(self) -> nx.Graph:
        """Construye el grafo Barabási-Albert.

        Returns:
            Grafo `nx.Graph` siempre conexo por construcción.
        """
        # `barabasi_albert_graph` es siempre conexo por construcción
        # cada nodo nuevo se conecta a `m` existentes
        return nx.barabasi_albert_graph(n=self.num_nodes, m=self.m, seed=self.seed)


class WattsStrogatzGraph(BaseGraph):
    """Grafo Watts-Strogatz small-world.

    Attributes:
        num_nodes: Número de nodos en el anillo inicial.
        k: Cada nodo está conectado a sus `k` vecinos más próximos en el
            anillo (debe ser par para que el anillo sea simétrico).
        rewire_prob: Probabilidad en [0, 1] de recablear cada arista.
            `p = 0` -> red regular pura (mucho clustering, caminos largos).
            `p = 1` -> casi aleatoria (poco clustering, caminos cortos).
            `p ~ 0.1` -> régimen "small-world".
        seed: Semilla del generador.
    """

    def __init__(
        self,
        num_nodes: int,
        k: int,
        rewire_prob: float,
        seed: int | None = None,
    ) -> None:
        """Inicializa la configuración del grafo Watts-Strogatz.

        Args:
            num_nodes: Número de nodos en el anillo inicial.
            k: Vecinos más próximos en el anillo (par).
            rewire_prob: Probabilidad de recablear cada arista.
            seed: Semilla del generador.
        """
        super().__init__(seed=seed)
        self.num_nodes = num_nodes
        self.k = k
        self.rewire_prob = rewire_prob

    def build(self) -> nx.Graph:
        """Construye el grafo Watts-Strogatz.

        Returns:
            Grafo `nx.Graph` small-world. Suele ser conexo por construcción
            salvo combinaciones extremas de `rewire_prob` y `k` bajos.
        """
        # `p` aquí es la prob de recableo, no de arista.
        # NetworkX puede producir grafos no conexos si `p` es alta y `k` baja,
        # pero por construcción suele ser conexo.
        return nx.watts_strogatz_graph(
            n=self.num_nodes, k=self.k, p=self.rewire_prob, seed=self.seed
        )
