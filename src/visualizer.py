"""
Visualizaciones de la simulación.

Cada clase es un visualizador independiente:
  - NetworkAnimator: anima el grafo paso a paso (GIF / live).
  - DegreeDistributionPlot: histograma de grado.
  - MessageHeatmap: heatmap de mensajes por par (origen, destino).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.axes import Axes

from src.datacollector import DataCollector
from src.model import NetworkModel


class _DarkStyle:
    """Estilo gráfico común a todos los visualizadores."""

    BG = "#0f1419"
    EDGE = "#2a3142"
    EDGE_ACTIVE = "#ff6b9d"
    NODE_FIRE = "#ffd166"
    NODE_RECV = "#06d6a0"
    NODE_IDLE = "#4a90e2"
    TEXT = "white"
    SUBTEXT = "#a0a8b8"


class NetworkAnimator:
    """Anima el grafo en tiempo real mientras avanza la simulación."""

    def __init__(
        self,
        model: NetworkModel,
        sim_time: int,
        interval_ms: int = 500,
        layout_seed: int | None = None,
        figsize: tuple[float, float] = (10, 8),
        title_suffix: str = "",
    ) -> None:
        self.model = model
        self.sim_time = sim_time
        self.interval_ms = interval_ms
        self.layout_seed = layout_seed
        self.figsize = figsize
        self.title_suffix = title_suffix

        self.pos = nx.spring_layout(model.graph, seed=layout_seed, k=1.5)
        self.fig, self.ax = plt.subplots(figsize=figsize)
        self.fig.patch.set_facecolor(_DarkStyle.BG)
        self.ax.set_facecolor(_DarkStyle.BG)

    def _draw_frame(self, _frame: int) -> tuple[Axes]:
        ax = self.ax
        ax.clear()
        ax.set_facecolor(_DarkStyle.BG)
        self.model.step()

        g = self.model.graph
        nx.draw_networkx_edges(
            g, self.pos, ax=ax, edge_color=_DarkStyle.EDGE, width=1.0, alpha=0.5
        )

        if self.model.active_messages:
            dg = nx.DiGraph()
            dg.add_nodes_from(g.nodes())
            dg.add_edges_from(self.model.active_messages)
            nx.draw_networkx_edges(
                dg,
                self.pos,
                ax=ax,
                edgelist=list(dg.edges()),
                edge_color=_DarkStyle.EDGE_ACTIVE,
                width=3.0,
                alpha=0.95,
                arrows=True,
                arrowsize=22,
                arrowstyle="-|>",
                connectionstyle="arc3,rad=0.12",
                node_size=700,
            )

        firing = {s for s, _ in self.model.active_messages}
        receiving = {t for _, t in self.model.active_messages}

        node_colors, node_sizes = [], []
        for n in g.nodes():
            if n in firing:
                node_colors.append(_DarkStyle.NODE_FIRE)
                node_sizes.append(100)
            elif n in receiving:
                node_colors.append(_DarkStyle.NODE_RECV)
                node_sizes.append(75)
            else:
                node_colors.append(_DarkStyle.NODE_IDLE)
                node_sizes.append(50)

        nx.draw_networkx_nodes(
            g,
            self.pos,
            ax=ax,
            node_color=node_colors,
            node_size=node_sizes,
            edgecolors="white",
            linewidths=0.5,
            alpha=0.95,
        )

        ax.set_title(
            f"Paso {self.model.current_step}/{self.sim_time}    "
            f"Mensajes activos: {len(self.model.active_messages)}    "
            f"Total enviados: {len(self.model.data_collector)}"
            + (f"    {self.title_suffix}" if self.title_suffix else ""),
            color=_DarkStyle.TEXT,
            fontsize=13,
            pad=14,
        )
        ax.text(
            0.5,
            -0.04,
            "● amarillo: dispara    ● verde: recibe    ● azul: reposo",
            transform=ax.transAxes,
            ha="center",
            va="top",
            color=_DarkStyle.SUBTEXT,
            fontsize=10,
        )
        ax.axis("off")
        return (ax,)

    def animate(self) -> FuncAnimation:
        return FuncAnimation(
            self.fig,
            self._draw_frame,
            frames=self.sim_time,
            interval=self.interval_ms,
            repeat=False,
            blit=False,
        )

    def save_gif(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        anim = self.animate()
        fps = max(1, 1000 // self.interval_ms)
        anim.save(str(path), writer=PillowWriter(fps=fps))
        return path

    def show(self) -> None:
        self.animate()
        plt.tight_layout()
        plt.show()

    def close(self) -> None:
        plt.close(self.fig)


class DegreeDistributionPlot:
    """Histograma del grado de los nodos."""

    def __init__(self, graph: nx.Graph) -> None:
        self.graph = graph

    def render(self, path: str | Path | None = None):
        degrees = [d for _, d in self.graph.degree()]
        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor(_DarkStyle.BG)
        ax.set_facecolor(_DarkStyle.BG)
        ax.hist(degrees, bins=20, color=_DarkStyle.NODE_RECV, edgecolor="white")
        ax.set_xlabel("Grado", color=_DarkStyle.TEXT)
        ax.set_ylabel("Frecuencia", color=_DarkStyle.TEXT)
        ax.set_title("Distribución de grado", color=_DarkStyle.TEXT)
        ax.tick_params(colors=_DarkStyle.SUBTEXT)
        for spine in ax.spines.values():
            spine.set_color(_DarkStyle.SUBTEXT)
        if path is not None:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(path, facecolor=fig.get_facecolor())
        return fig


class MessageHeatmap:
    """Heatmap de número de mensajes por par (origen, destino)."""

    def __init__(self, data_collector: DataCollector, num_nodes: int) -> None:
        self.data_collector = data_collector
        self.num_nodes = num_nodes

    def render(self, path: str | Path | None = None):
        counter: Counter[tuple[int, int]] = Counter(
            (tr.source_node, tr.target_node) for tr in self.data_collector.traces
        )
        matrix = [[0] * self.num_nodes for _ in range(self.num_nodes)]
        for (s, t), c in counter.items():
            if s < self.num_nodes and t < self.num_nodes:
                matrix[s][t] = c

        fig, ax = plt.subplots(figsize=(8, 7))
        fig.patch.set_facecolor(_DarkStyle.BG)
        ax.set_facecolor(_DarkStyle.BG)
        im = ax.imshow(matrix, cmap="magma", aspect="auto")
        ax.set_xlabel("Destino", color=_DarkStyle.TEXT)
        ax.set_ylabel("Origen", color=_DarkStyle.TEXT)
        ax.set_title("Mensajes por par (origen, destino)", color=_DarkStyle.TEXT)
        ax.tick_params(colors=_DarkStyle.SUBTEXT)
        cbar = fig.colorbar(im, ax=ax)
        cbar.ax.tick_params(colors=_DarkStyle.SUBTEXT)
        if path is not None:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(path, facecolor=fig.get_facecolor())
        return fig
