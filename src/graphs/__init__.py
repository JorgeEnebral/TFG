"""Tipos de grafos que pueden modelar la sociedad."""

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
