"""
Interfaz base para los grafos de la simulación.

Toda topología hereda de `BaseGraph` y reimplementa `build()`.
El resto del código de la simulación NUNCA depende del tipo concreto
de grafo. Se desacopla "qué red modela la sociedad" de "cómo simulamos sobre ella".
"""

# Anotaciones diferidas (PEP 563): permite usar `int | None` y otras sintaxis
# modernas como strings sin que falle en versiones antiguas, y evita ciclos.
from __future__ import annotations

# `ABC` (Abstract Base Class) y `abstractmethod` permiten declarar la clase como abstracta
from abc import ABC, abstractmethod

import networkx as nx


class BaseGraph(ABC):
    """Envoltorio común para todos los tipos de grafos.

    Patrón de diseño: **lazy construction**. El grafo NO se construye en
    el `__init__`, sino la primera vez que alguien accede a `.graph`.
    Ventajas:
      - Crear instancias es barato (útil para batches de configuraciones).
      - Permite a las subclases retrasar trabajos costosos hasta que se usen.

    Attributes:
        seed: Semilla para los generadores aleatorios. Puede ser `None`.
        _graph: Caché interna del grafo construido. `None` hasta la primera
            llamada a `.graph`.
    """

    def __init__(self, seed: int | None = None) -> None:
        """Inicializa el grafo (sin construirlo todavía).

        Args:
            seed: Semilla para los generadores aleatorios de las subclases.
        """
        # `seed` se guarda y la usan las subclases en su `build()`.
        self.seed = seed

        # Caché perezosa. Empieza en `None` y se materializa solo si alguien accede a `.graph`.
        self._graph: nx.Graph | None = None

    @property
    def graph(self) -> nx.Graph:
        """Acceso público al grafo subyacente, con construcción lazy.

        Es un `@property`, así que se usa como atributo (`g.graph`) pero
        ejecuta este método. La primera invocación construye el grafo
        llamando a `self.build()`; las siguientes devuelven la caché.

        Returns:
            El `networkx.Graph` (o `DiGraph` para grafos dirigidos)
            subyacente. Misma instancia en sucesivas llamadas.
        """
        if self._graph is None:
            self._graph = self.build()
        return self._graph

    @abstractmethod
    def build(self) -> nx.Graph:
        """Construye y devuelve el grafo subyacente.

        Cada subclase debe sobreescribir este método. El decorador
        `@abstractmethod` hace que sea obligatorio: si una subclase
        no lo define, Python no permite instanciarla.

        Returns:
            El grafo concreto construido por la subclase.
        """
        # Sin cuerpo: las subclases lo proveen. El docstring documenta el contrato.

    @staticmethod
    def ensure_connected(g: nx.Graph) -> nx.Graph:
        """Une componentes conexas añadiendo aristas mínimas.

        Muchos generadores aleatorios producen grafos no conexos. Eso es
        válido matemáticamente pero estéticamente feo en visualización y
        rompe ciertos análisis (caminos más cortos, centralidad, etc.).
        Esta utilidad cose las componentes con una arista por par.

        Args:
            g: Grafo de NetworkX (puede ser `Graph` o `DiGraph`). Se modifica
                in-place añadiendo aristas si es necesario.

        Returns:
            El mismo grafo `g`, ya garantizado como conexo.
        """
        # Si es un grafo dirigido, conexión se mide sobre la versión no dirigida.
        # `nx.is_connected` solo funciona sobre `nx.Graph`, no sobre `nx.DiGraph`.
        if isinstance(g, nx.DiGraph):
            base = g.to_undirected()
        else:
            base = g

        # Si ya es conexo, no hay nada que hacer
        if nx.is_connected(base):
            return g

        # `connected_components` devuelve un iterador de sets de nodos.
        components = list(nx.connected_components(base))

        # Recorre componentes consecutivas y añade UNA arista entre
        # un nodo de la actual y un nodo de la siguiente.
        for i in range(len(components) - 1):
            u = next(iter(components[i]))
            v = next(iter(components[i + 1]))
            g.add_edge(u, v)

        return g

    def __len__(self) -> int:
        """Número de nodos del grafo.

        Como `.graph` es lazy, esto también dispara la construcción si
        todavía no se había accedido al grafo.

        Returns:
            Número de nodos (`graph.number_of_nodes()`).
        """
        # Permite escribir `len(my_graph)` y obtener el nº de nodos.
        # Como `.graph` es lazy, esto también dispara la construcción si hace falta.
        n_nodes: int = self.graph.number_of_nodes()
        return n_nodes
