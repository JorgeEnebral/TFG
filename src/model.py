"""Modelo Mesa que envuelve un grafo y agentes."""

from __future__ import annotations

from typing import Callable

import mesa
import networkx as nx

from src.agents.base import BaseAgent
from src.datacollector import DataCollector


class NetworkModel(mesa.Model):  # type: ignore
    """
    Modelo Mesa parametrizable. Recibe:
      - graph: el `nx.Graph` ya construido
      - agent_factory: callable (model, node_id) -> BaseAgent
      - data_collector: instancia de DataCollector
    """

    def __init__(
        self,
        graph: nx.Graph,
        agent_factory: Callable[["NetworkModel", int], BaseAgent],
        data_collector: DataCollector | None = None,
        seed: int = 42,
    ) -> None:
        super().__init__(rng=seed)
        self.graph = graph
        self.data_collector = (
            data_collector if data_collector is not None else DataCollector()
        )
        self.active_messages: list[tuple[int, int]] = []
        self.current_step = 0

        self.agent_by_node: dict[int, BaseAgent] = {}
        for node_id in graph.nodes():
            agent = agent_factory(self, node_id)
            self.agent_by_node[node_id] = agent

    def emit_message(self, source: int, target: int) -> None:
        """API que usan los agentes para registrar un mensaje en este paso."""
        self.active_messages.append((source, target))

    def step(self) -> None:
        self.active_messages = []
        self.agents.shuffle_do("step")
        for src, tgt in self.active_messages:
            self.data_collector.record(self.current_step, src, tgt)
        self.current_step += 1
