"""
Hipergrafo.

Un hipergrafo generaliza el concepto de grafo: en lugar de aristas que unen
EXACTAMENTE dos nodos, una *hiperarista* puede unir un conjunto arbitrario
(>= 2) de nodos. Modela bien las "interacciones de grupo" (chats grupales,
publicaciones que ven N seguidores, mesas de discusión...) que en redes
sociales son tan o más importantes que las relaciones uno-a-uno.

Como Mesa y NetworkX trabajan con grafos simples, exponemos también la
**clique-expansion**: cada hiperarista se transforma en una clique (grafo
completo) entre sus miembros. Eso permite que el resto de la simulación
(agentes, visualizador) consuma el hipergrafo como si fuera un grafo normal.
La hiperestructura original se conserva en `self.hyperedges` para análisis
o agentes que necesiten razonar sobre grupos enteros.
"""

from __future__ import annotations

# Usamos el `random.Random` propio (instanciado con seed) en vez del módulo
# global, para que la generación sea reproducible y aislada.
import random

# `combinations(iterable, 2)` devuelve todos los pares no ordenados.
# Lo usamos para generar las aristas de la clique de cada hiperarista.
from itertools import combinations

import networkx as nx

from src.graphs.base import BaseGraph


class HyperGraph(BaseGraph):
    """
    Hipergrafo simple, no dirigido.

    Atributos:
      - `num_nodes` (int): número total de nodos.
      - `num_hyperedges` (int): cuántas hiperaristas generar.
      - `hyperedge_size_range` (tuple[int, int]): rango (lo, hi) inclusive
        del tamaño de cada hiperarista. Se elige uniformemente en ese rango.
      - `seed` (int | None): semilla del generador.
      - `hyperedges` (list[frozenset[int]]): rellenado por `build()`.
        Cada hiperarista es un `frozenset` (inmutable + hashable -> deduplicable).
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

        # Lista de hiperaristas. Se rellena en `build()`.
        # Tipado como `list[frozenset[int]]`: cada hiperarista es un set de nodos.
        self.hyperedges: list[frozenset[int]] = []

    def build(self) -> nx.Graph:
        # RNG local para no mezclar con el `random` global del proceso.
        # Sembrado con `self.seed` -> reproducibilidad.
        rng = random.Random(self.seed)
        nodes = list(range(self.num_nodes))

        # Desempaquetamos el rango. Permitimos `hi > num_nodes` capándolo
        # más abajo, para que el caller no tenga que validar tamaños.
        lo, hi = self.hyperedge_size_range

        # Reseteamos por si `build()` se llama varias veces (no debería,
        # gracias a la caché lazy del padre, pero por robustez).
        self.hyperedges = []
        for _ in range(self.num_hyperedges):
            # Tamaño aleatorio dentro del rango pedido, capado al nº de nodos.
            size = rng.randint(lo, min(hi, self.num_nodes))

            # `rng.sample` elige `k` elementos sin reemplazo -> nodos únicos.
            # `frozenset` lo hace inmutable y hashable (por si en el futuro
            # queremos detectar duplicados con un `set` de hiperaristas).
            members = frozenset(rng.sample(nodes, k=size))
            self.hyperedges.append(members)

        # Proyección clique: por cada hiperarista creamos un grafo completo
        # entre sus miembros. Eso aplana el hipergrafo a un `nx.Graph` simple.
        # Pérdida de información: dos hiperaristas {A,B,C} y {A,B,D} se
        # superponen y no se distinguen en el grafo proyectado. Por eso
        # guardamos también `self.hyperedges` originales.
        g = nx.Graph()
        g.add_nodes_from(nodes)  # incluimos nodos aislados aunque no entren en ninguna hiperarista
        for he in self.hyperedges:
            for u, v in combinations(he, 2):
                g.add_edge(u, v)
        return g

    def neighbors_via_hyperedges(self, node: int) -> set[int]:
        """
        Vecinos de `node` a través de hiperaristas.

        Si `node` pertenece a una hiperarista {A, B, C}, sus vecinos
        "hipergráficos" son {A, B, C} \\ {node}. Es equivalente a los
        vecinos en la proyección clique, pero calculado directamente
        sobre la estructura de hiperaristas (más informativo si en el
        futuro queremos pesos por co-pertenencia, etc.).

        Devuelve un `set[int]` (sin duplicados, sin incluir a `node`).
        """
        result: set[int] = set()
        for he in self.hyperedges:
            if node in he:
                result.update(he)
        # Eliminamos al propio nodo: un nodo no es vecino de sí mismo.
        result.discard(node)
        return result

    def hyperedges_of(self, node: int) -> list[frozenset[int]]:
        """
        Devuelve todas las hiperaristas a las que pertenece `node`.

        Útil para agentes que razonen "qué grupos formo" en lugar de
        "con quién me conecto". Por ejemplo, un troll podría amplificar
        el mensaje a TODA la hiperarista (post grupal) en vez de a un
        vecino aleatorio.
        """
        return [he for he in self.hyperedges if node in he]
