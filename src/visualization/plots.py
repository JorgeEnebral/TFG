"""
Visualizaciones de análisis de grafos.

Sirve tanto para exploración interactiva (``grafos.ipynb``) como para
generación automática en simulación.

Comportamiento dual:
  - ``out_dir=None``  → modo notebook: ``plt.show()`` por cada figura.
  - ``out_dir=Path``  → modo simulación: guarda PNGs + ``metrics.json``,
                        cierra figuras (sin ventanas).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.figure import Figure

from src.messages import Layer
from src.visualization.metrics import (
    ComputedMetrics,
    compute_graph_metrics,
    compute_multilayer_metrics,
    metrics_to_json_safe,
)

# ---------------------------------------------------------------------------
# Paleta compartida (alineada con _DarkStyle de visualizer.py)
# ---------------------------------------------------------------------------
_BG = "#0f1419"
_NODE = "#4fc3f7"
_EDGE = "#546e7a"
_ANALOG = "#ff7043"
_DIGITAL = "#29b6f6"
_BC_COLOR = "#ab47bc"
_PR_COLOR = "#66bb6a"
_EC_COLOR = "#66bb6a"


def _apply_dark(ax: Any) -> None:
    ax.set_facecolor(_BG)
    for sp in ax.spines.values():
        sp.set_edgecolor(_EDGE)
    ax.tick_params(colors="white", labelsize=8)


def _finish(fig: Figure, path: Path | None) -> Figure:
    """Guarda a fichero o muestra interactivamente según ``path``."""
    plt.tight_layout()
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, facecolor=fig.get_facecolor())
        plt.close(fig)
    else:
        plt.show()
    return fig


# ---------------------------------------------------------------------------
# Funciones de plotting
# ---------------------------------------------------------------------------

def draw_graph(
    G: nx.Graph,
    title: str,
    path: Path | None = None,
    seed: int = 42,
) -> Figure:
    """Dibuja el grafo con spring layout sobre fondo oscuro.

    Args:
        G: Grafo a visualizar.
        title: Título de la figura.
        path: Si se proporciona, guarda la figura y cierra. Si no, ``plt.show()``.
        seed: Semilla del layout.

    Returns:
        La figura generada.
    """
    n = G.number_of_nodes()
    k = 2 / n ** 0.5 if n > 500 else 0.5
    its = 15 if n > 1000 else 50
    pos = nx.spring_layout(G, seed=seed, k=k, iterations=its)
    ns = max(2, min(80, 6000 // max(n, 1)))

    fig, ax = plt.subplots(figsize=(8, 8), facecolor=_BG)
    ax.set_facecolor(_BG)
    nx.draw_networkx(
        G, pos=pos, ax=ax,
        node_size=ns, width=0.3, alpha=0.8,
        node_color=_NODE, edge_color=_EDGE,
        with_labels=False,
        arrows=G.is_directed(),
    )
    ax.set_title(title, color="white", fontsize=12, pad=10)
    ax.axis("off")
    return _finish(fig, path)


def plot_centrality_histograms(
    G: nx.Graph,
    name: str,
    metrics: ComputedMetrics,
    path: Path | None = None,
) -> Figure:
    """3 subplots: distribución de grado, betweenness, PageRank/eigenvector.

    Args:
        G: Grafo analizado.
        name: Nombre para el título.
        metrics: Dict devuelto por ``compute_graph_metrics``.
        path: Si se proporciona, guarda y cierra.

    Returns:
        La figura generada.
    """
    is_dir = G.is_directed()
    bc_vals = list(metrics["_bc"].values())
    ec_ok = [v for v in metrics["_ec"].values() if not math.isnan(v)]
    pr_ok = [v for v in metrics["_pr"].values() if not math.isnan(v)]

    fig, axes = plt.subplots(1, 3, figsize=(18, 5), facecolor=_BG)
    fig.suptitle(name, color="white", fontsize=12)

    # Distribución de grado
    ax = axes[0]
    _apply_dark(ax)
    if is_dir:
        in_d = [d for _, d in G.in_degree()]
        out_d = [d for _, d in G.out_degree()]
        ax.hist(in_d, bins=40, color=_DIGITAL, alpha=0.75, label="in-grado")
        ax.hist(out_d, bins=40, color=_ANALOG, alpha=0.75, label="out-grado")
        ax.legend(facecolor="#1a2332", labelcolor="white", fontsize=8)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title("Distribución de grado (log-log)", color="white", fontsize=10)
    else:
        ax.hist([d for _, d in G.degree()], bins=40, color=_NODE, alpha=0.85)
        ax.set_title("Distribución de grado", color="white", fontsize=10)
    ax.set_xlabel("grado", color="white", fontsize=9)
    ax.set_ylabel("nodos", color="white", fontsize=9)

    # Betweenness
    ax = axes[1]
    _apply_dark(ax)
    ax.hist(bc_vals, bins=40, color=_BC_COLOR, alpha=0.85)
    ax.set_title("Betweenness centrality", color="white", fontsize=10)
    ax.set_xlabel("betweenness", color="white", fontsize=9)
    ax.set_ylabel("nodos", color="white", fontsize=9)

    # PageRank (dirigido) / Eigenvector (no dirigido)
    ax = axes[2]
    _apply_dark(ax)
    if is_dir:
        if pr_ok:
            ax.hist(pr_ok, bins=40, color=_PR_COLOR, alpha=0.85)
        ax.set_title("PageRank", color="white", fontsize=10)
        ax.set_xlabel("pagerank", color="white", fontsize=9)
    else:
        if ec_ok:
            ax.hist(ec_ok, bins=40, color=_EC_COLOR, alpha=0.85)
        else:
            ax.text(0.5, 0.5, "No disponible", ha="center", va="center",
                    color="white", transform=ax.transAxes, fontsize=10)
        ax.set_title("Eigenvector centrality", color="white", fontsize=10)
        ax.set_xlabel("eigenvector", color="white", fontsize=9)
    ax.set_ylabel("nodos", color="white", fontsize=9)

    return _finish(fig, path)


def _multilayer_plots(
    metrics_ml: ComputedMetrics,
    name: str,
    path: Path | None = None,
) -> Figure:
    """Scatter de correlación entre capas + histograma de participación."""
    deg_a: list[float] = metrics_ml["_deg_a"]
    deg_d: list[float] = metrics_ml["_deg_d"]
    part: list[float] = metrics_ml["_participation"]
    corr: float = metrics_ml["degree_correlation"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), facecolor=_BG)
    fig.suptitle(f"{name} — Análisis multicapa", color="white", fontsize=12)

    ax = axes[0]
    _apply_dark(ax)
    ax.scatter(deg_a, deg_d, alpha=0.5, s=15, color=_NODE)
    ax.set_xlabel("Grado analógico (WS)", color="white", fontsize=9)
    ax.set_ylabel("Grado digital (in+out)", color="white", fontsize=9)
    ax.set_title(f"Correlación entre capas  r = {corr:.3f}", color="white", fontsize=10)

    ax = axes[1]
    _apply_dark(ax)
    if part:
        ax.hist(part, bins=30, color=_BC_COLOR, alpha=0.85)
        part_avg = sum(part) / len(part)
        ax.axvline(part_avg, color="white", linestyle="--",
                   linewidth=0.9, label=f"media = {part_avg:.3f}")
        ax.legend(facecolor="#1a2332", labelcolor="white", fontsize=8)
    ax.set_xlabel("Coeficiente de participación", color="white", fontsize=9)
    ax.set_ylabel("nodos", color="white", fontsize=9)
    ax.set_title("Distribución de participación multicapa", color="white", fontsize=10)

    return _finish(fig, path)


def _draw_multilayer_views(
    ml_G: nx.Graph,
    analog_edges: list[tuple[Any, Any]],
    digital_edges: list[tuple[Any, Any]],
    name: str,
    pos: dict[Any, Any],
    ns: int,
    out_dir: Path | None,
) -> None:
    """Dibuja capa analógica, digital y combinada."""
    def _layer(edges: list[tuple[Any, Any]], title: str, color: str, arrows: bool) -> None:
        fig, ax = plt.subplots(figsize=(8, 8), facecolor=_BG)
        ax.set_facecolor(_BG)
        nx.draw_networkx_nodes(ml_G, pos, ax=ax, node_size=ns, node_color=_NODE, alpha=0.9)
        nx.draw_networkx_edges(ml_G, pos, edgelist=edges, ax=ax,
                               width=0.5, edge_color=color, alpha=0.7, arrows=arrows)
        ax.set_title(title, color="white", fontsize=12)
        ax.axis("off")
        suffix = "analog" if color == _ANALOG else "digital"
        _finish(fig, out_dir / f"layer_{suffix}.png" if out_dir else None)

    _layer(analog_edges, f"{name} — Capa analógica", _ANALOG, arrows=False)
    _layer(digital_edges, f"{name} — Capa digital", _DIGITAL, arrows=True)

    # Vista combinada
    fig, ax = plt.subplots(figsize=(8, 8), facecolor=_BG)
    ax.set_facecolor(_BG)
    nx.draw_networkx_nodes(ml_G, pos, ax=ax, node_size=ns, node_color=_NODE, alpha=0.9)
    nx.draw_networkx_edges(ml_G, pos, edgelist=analog_edges, ax=ax,
                           width=0.5, edge_color=_ANALOG, alpha=0.6, arrows=False)
    nx.draw_networkx_edges(ml_G, pos, edgelist=digital_edges, ax=ax,
                           width=0.5, edge_color=_DIGITAL, alpha=0.6, arrows=True)
    handles = [
        mpatches.Patch(color=_ANALOG, label="Analógica (WS)"),
        mpatches.Patch(color=_DIGITAL, label="Digital"),
    ]
    ax.legend(handles=handles, loc="upper right", facecolor="#1a2332",
              labelcolor="white", fontsize=9)
    ax.set_title(f"{name} — Bicapa combinada", color="white", fontsize=12)
    ax.axis("off")
    _finish(fig, out_dir / "layer_combined.png" if out_dir else None)


def _save_metrics_json(metrics: ComputedMetrics, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = metrics_to_json_safe(metrics)

    def _jsonify(v: Any) -> Any:
        if isinstance(v, float) and math.isnan(v):
            return None
        return v

    with open(path, "w", encoding="utf-8") as f:
        json.dump({k: _jsonify(v) for k, v in safe.items()}, f, indent=2)


# ---------------------------------------------------------------------------
# Entrypoints públicos (usados por notebook y simulación)
# ---------------------------------------------------------------------------

def analyse_graph(
    G: nx.Graph,
    name: str,
    out_dir: Path | None = None,
    seed: int = 42,
    plot: bool = True
) -> ComputedMetrics:
    """Análisis completo de un grafo: métricas + visualizaciones.

    En modo notebook (``out_dir=None``) muestra las figuras interactivamente.
    En modo simulación (``out_dir`` dado) las guarda como PNG + ``metrics.json``.

    Args:
        G: Grafo a analizar.
        name: Nombre descriptivo (se usa en títulos y nombres de fichero).
        out_dir: Directorio de salida. Si es None, modo interactivo.
        seed: Semilla para layout y algoritmos aproximados.

    Returns:
        Dict de métricas (incluyendo centralidades internas ``_bc``, ``_ec``, ``_pr``).
    """
    metrics = compute_graph_metrics(G, seed=seed)

    graph_path = out_dir / "graph.png" if out_dir else None
    hist_path = out_dir / "histograms.png" if out_dir else None

    if plot:
        draw_graph(G, name, path=graph_path, seed=seed)
        plot_centrality_histograms(G, name, metrics, path=hist_path)

    if out_dir is not None:
        _save_metrics_json(metrics, out_dir / "metrics.json")

    return metrics_to_json_safe(metrics)


def analyse_multilayer(
    ml_G: nx.Graph,
    name: str,
    out_dir: Path | None = None,
    seed: int = 42,
) -> dict[str, ComputedMetrics]:
    """Análisis completo de un grafo multicapa.

    Args:
        ml_G: Grafo multicapa (MultiDiGraph con atributo ``layer`` en aristas).
        name: Nombre descriptivo.
        out_dir: Directorio de salida. Si es None, modo interactivo.
        seed: Semilla para layout y algoritmos.

    Returns:
        Dict ``{"analog": metrics_a, "digital": metrics_d, "multilayer": metrics_ml}``.
    """
    analog_edges = [
        (u, v) for u, v, d in ml_G.edges(data=True) if d.get("layer") == Layer.ANALOG
    ]
    digital_edges = [
        (u, v) for u, v, d in ml_G.edges(data=True) if d.get("layer") == Layer.DIGITAL
    ]

    G_a: nx.Graph = nx.Graph()
    G_a.add_nodes_from(ml_G.nodes())
    G_a.add_edges_from(analog_edges)

    G_d: nx.DiGraph = nx.DiGraph()
    G_d.add_nodes_from(ml_G.nodes())
    G_d.add_edges_from(digital_edges)

    out_a = out_dir / "analog" if out_dir else None
    out_d = out_dir / "digital" if out_dir else None
    out_ml = out_dir if out_dir else None

    metrics_a = analyse_graph(G_a, f"{name} — Analógica", out_dir=out_a, seed=seed, plot=False)
    metrics_d = analyse_graph(G_d, f"{name} — Digital", out_dir=out_d, seed=seed, plot=False)

    metrics_ml = compute_multilayer_metrics(ml_G, G_a, G_d)

    ml_plot_path = out_ml / "multilayer_plots.png" if out_ml else None
    _multilayer_plots(metrics_ml, name, path=ml_plot_path)

    n = ml_G.number_of_nodes()
    k = 2 / n ** 0.5 if n > 500 else 0.6
    its = 15 if n > 1000 else 50
    pos = nx.spring_layout(ml_G, seed=seed, k=k, iterations=its)
    ns = max(2, min(60, 5000 // max(n, 1)))
    _draw_multilayer_views(ml_G, analog_edges, digital_edges, name, pos, ns, out_dir)

    if out_dir is not None:
        _save_metrics_json(metrics_ml, out_dir / "multilayer_metrics.json")

    return {"analog": metrics_a, "digital": metrics_d, "multilayer": metrics_to_json_safe(metrics_ml)}
