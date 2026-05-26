"""
Visualizaciones específicas de simulación.

  - ``PostSimAnimator`` : genera un GIF a partir de ficheros guardados
                          (grafo JSON + mensajes CSV/JSON). No requiere
                          re-ejecutar la simulación.
  - ``MessageHeatmap``  : heatmap de mensajes por par (origen, destino).
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from src.simulation.datacollector import DataCollector


class _DarkStyle:
    BG = "#0f1419"
    EDGE = "#2a3142"
    EDGE_ACTIVE = "#ff6b9d"
    NODE_FIRE = "#ffd166"
    NODE_RECV = "#06d6a0"
    NODE_IDLE = "#4a90e2"
    TEXT = "white"
    SUBTEXT = "#a0a8b8"


class PostSimAnimator:
    """Genera un GIF de replay a partir de ficheros guardados por la simulación.

    No ejecuta la simulación; lee el grafo y los mensajes grabados y los
    reproduce frame a frame.

    Attributes:
        graph: Grafo cargado del fichero.
        messages_by_step: Dict ``{timestep: [(source, target), ...]}``.
        total_steps: Número total de pasos registrados.
    """

    def __init__(
        self,
        graph_path: Path | str,
        messages_path: Path | str,
    ) -> None:
        """Carga el grafo y los mensajes desde fichero.

        Args:
            graph_path: Ruta al JSON en formato node-link (guardado por ``Simulation``).
            messages_path: Ruta al CSV o JSON de mensajes (guardado por ``DataCollector``).
        """
        graph_path = Path(graph_path)
        messages_path = Path(messages_path)

        with open(graph_path, encoding="utf-8") as f:
            data = json.load(f)
        self.graph: nx.Graph = nx.node_link_graph(data)

        messages_by_step: dict[int, list[tuple[int, int]]] = defaultdict(list)
        if messages_path.suffix == ".csv":
            with open(messages_path, encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    messages_by_step[int(row["timestep"])].append(
                        (int(row["source_node"]), int(row["target_node"]))
                    )
        else:
            with open(messages_path, encoding="utf-8") as f:
                for rec in json.load(f):
                    messages_by_step[int(rec["timestep"])].append(
                        (int(rec["source_node"]), int(rec["target_node"]))
                    )

        self.messages_by_step: dict[int, list[tuple[int, int]]] = dict(messages_by_step)
        self.total_steps: int = (
            max(self.messages_by_step.keys()) + 1 if self.messages_by_step else 0
        )

    def save_gif(
        self,
        path: Path | str,
        interval_ms: int = 500,
        layout_seed: int | None = None,
        figsize: tuple[float, float] = (10, 8),
    ) -> Path:
        """Genera y guarda el GIF de replay.

        Args:
            path: Ruta de destino del GIF.
            interval_ms: Milisegundos entre frames.
            layout_seed: Semilla del spring layout.
            figsize: Tamaño de la figura.

        Returns:
            Ruta del GIF escrito.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        g = self.graph
        pos = nx.spring_layout(g, seed=layout_seed, k=1.5)

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor(_DarkStyle.BG)
        ax.set_facecolor(_DarkStyle.BG)

        def _draw(frame: int) -> tuple[Axes]:
            ax.clear()
            ax.set_facecolor(_DarkStyle.BG)

            nx.draw_networkx_edges(
                g, pos, ax=ax, edge_color=_DarkStyle.EDGE, width=1.0, alpha=0.5
            )

            active = self.messages_by_step.get(frame, [])
            if active:
                dg = nx.DiGraph()
                dg.add_nodes_from(g.nodes())
                dg.add_edges_from(active)
                nx.draw_networkx_edges(
                    dg, pos, ax=ax,
                    edgelist=list(dg.edges()),
                    edge_color=_DarkStyle.EDGE_ACTIVE,
                    width=3.0, alpha=0.95,
                    arrows=True, arrowsize=22, arrowstyle="-|>",
                    connectionstyle="arc3,rad=0.12",
                    node_size=700,
                )

            firing = {s for s, _ in active}
            receiving = {t for _, t in active}
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
                g, pos, ax=ax,
                node_color=node_colors, node_size=node_sizes,
                edgecolors="white", linewidths=0.5, alpha=0.95,
            )
            ax.set_title(
                f"Paso {frame}/{self.total_steps}    Mensajes: {len(active)}",
                color=_DarkStyle.TEXT, fontsize=13, pad=14,
            )
            ax.text(
                0.5, -0.04,
                "● amarillo: dispara    ● verde: recibe    ● azul: reposo",
                transform=ax.transAxes, ha="center", va="top",
                color=_DarkStyle.SUBTEXT, fontsize=10,
            )
            ax.axis("off")
            return (ax,)

        anim = FuncAnimation(
            fig, _draw,
            frames=self.total_steps,
            interval=interval_ms,
            repeat=False,
            blit=False,
        )
        fps = max(1, 1000 // interval_ms)
        anim.save(str(path), writer=PillowWriter(fps=fps))
        plt.close(fig)
        return path


class MessageHeatmap:
    """Heatmap de número de mensajes por par (origen, destino).

    Attributes:
        data_collector: DataCollector con las trazas.
        num_nodes: Tamaño del lado del heatmap.
    """

    def __init__(self, data_collector: DataCollector, num_nodes: int) -> None:
        """Args:
            data_collector: DataCollector con las trazas a visualizar.
            num_nodes: Número de nodos del grafo (lado de la matriz).
        """
        self.data_collector = data_collector
        self.num_nodes = num_nodes

    def render(self, path: Path | str | None = None) -> Figure:
        """Genera el heatmap. Guarda a fichero si ``path`` dado, muestra si no.

        Args:
            path: Ruta de destino. Si es None, llama a ``plt.show()``.

        Returns:
            La figura generada.
        """
        counter: Counter[tuple[int, int]] = Counter(
            (tr.source_node, tr.target_node) for tr in self.data_collector.interactions
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
            plt.close(fig)
        else:
            plt.show()
        return fig
