"""
Paquete `graphs`
================

Contiene todas las topologías de red que pueden modelar la "sociedad"
sobre la que viven los agentes.

Familias incluidas:
  - `BaseGraph`            : interfaz común (clase abstracta).
  - Aleatorios clásicos    : Erdős-Rényi, Barabási-Albert, Watts-Strogatz.
  - Hipergrafos            : `HyperGraph` (hiperaristas + proyección clique).
  - Datasets reales (SNAP) : `SNAPGraph` + `SNAPDownloader` para cargar
                             redes sociales/de citación reales.
"""

from src.graphs.base import BaseGraph
from src.graphs.hypergraph import HyperGraph
from src.graphs.random import (
    BarabasiAlbertGraph,
    ErdosRenyiGraph,
    WattsStrogatzGraph,
)
from src.graphs.snap import SNAPDownloader, SNAPGraph

__all__ = [
    "BaseGraph",
    "ErdosRenyiGraph",
    "BarabasiAlbertGraph",
    "WattsStrogatzGraph",
    "HyperGraph",
    "SNAPDownloader",
    "SNAPGraph",
]
