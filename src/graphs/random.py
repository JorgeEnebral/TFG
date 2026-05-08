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
    """
    Grafo Erdős-Rényi G(n, p).

    Atributos:
      - `num_nodes` (int): número de nodos n.
      - `edge_prob` (float en [0, 1]): probabilidad p de cada arista.
      - `seed` (int | None): heredado de BaseGraph; sembrado de NetworkX.
      - `connected` (bool): si True, postprocesa el grafo con
            `ensure_connected()` para que no haya componentes aisladas.
    """

    def __init__(
        self,
        num_nodes: int,
        edge_prob: float,
        seed: int | None = None,
        connected: bool = True,
    ) -> None:
        # Llamamos al padre para guardar `seed` e inicializar la caché `_graph`.
        super().__init__(seed=seed)

        self.num_nodes = num_nodes
        self.edge_prob = edge_prob
        self.connected = connected

    def build(self) -> nx.Graph:
        # Generador estándar de NetworkX. Devuelve un `nx.Graph` no dirigido.
        g = nx.erdos_renyi_graph(n=self.num_nodes, p=self.edge_prob, seed=self.seed)
        
        if self.connected:
            g = self.ensure_connected(g)
        return g


class BarabasiAlbertGraph(BaseGraph):
    """
    Grafo Barabási-Albert (preferential attachment).

    Atributos:
      - `num_nodes` (int): n total de nodos finales.
      - `m` (int): cuántas aristas añade cada nodo nuevo al entrar.
        El grado mínimo final es `m`; los hubs aparecen por acumulación.
      - `seed` (int | None): semilla del generador.
    """

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
        # `barabasi_albert_graph` es siempre conexo por construcción
        # cada nodo nuevo se conecta a `m` existentes
        return nx.barabasi_albert_graph(n=self.num_nodes, m=self.m, seed=self.seed)


class WattsStrogatzGraph(BaseGraph):
    """
    Grafo Watts-Strogatz small-world.

    Atributos:
      - `num_nodes` (int): n nodos en el anillo inicial.
      - `k` (int): cada nodo está conectado a sus `k` vecinos más próximos
        en el anillo (debe ser par para que el anillo sea simétrico).
      - `rewire_prob` (float en [0, 1]): probabilidad de recablear cada arista.
        * `p = 0` -> red regular pura (mucho clustering, caminos largos).
        * `p = 1` -> casi aleatoria (poco clustering, caminos cortos).
        * `p ~ 0.1` -> régimen "small-world".
      - `seed` (int | None): semilla.
    """

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
        # `p` aquí es la prob de recableo, no de arista. 
        # NetworkX puede producir grafos no conexos si `p` es alta y `k` baja, 
        # pero por construcción suele ser conexo.
        return nx.watts_strogatz_graph(
            n=self.num_nodes, k=self.k, p=self.rewire_prob, seed=self.seed
        )
