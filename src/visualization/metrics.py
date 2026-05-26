"""
Métricas de análisis de grafos.

Funciones puras de computación (sin I/O ni plots).
Se usan desde ``plots.py`` (simulación) y desde ``grafos.ipynb`` (exploración).
"""

from __future__ import annotations

import math
import random as _rng_mod
import warnings
from typing import Any

import networkx as nx


# ---------------------------------------------------------------------------
# Tipo de retorno
# ---------------------------------------------------------------------------

# Any justificado: el dict mezcla int, float, None y dicts de centralidad
# (_bc, _ec, _pr) que no son JSON-serializables directamente.
ComputedMetrics = dict[str, Any]


def metrics_to_json_safe(metrics: ComputedMetrics) -> ComputedMetrics:
    """Elimina las claves internas (prefijo ``_``) para serializar a JSON."""
    return {k: v for k, v in metrics.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _lcc_info(G: nx.Graph) -> tuple[int, int, float, int | None]:
    """Devuelve (n_componentes, tamaño_lcc, fraccion_lcc, n_scc_o_None)."""
    n = G.number_of_nodes()
    if n == 0:
        return 0, 0, 0.0, None
    if G.is_directed():
        wcc = list(nx.weakly_connected_components(G))
        n_scc = nx.number_strongly_connected_components(G)
        lcc = max(len(c) for c in wcc)
        return len(wcc), lcc, lcc / n, n_scc
    comps = list(nx.connected_components(G))
    lcc = max(len(c) for c in comps)
    return len(comps), lcc, lcc / n, None


def _approx_diameter(G: nx.Graph, samples: int = 200, seed: int = 42) -> int | float:
    """Diámetro exacto para n≤500, aproximado por BFS para grafos mayores."""
    if G.number_of_nodes() == 0:
        return float("nan")
    rng = _rng_mod.Random(seed)
    comps = list(
        nx.weakly_connected_components(G) if G.is_directed()
        else nx.connected_components(G)
    )
    lcc = max(comps, key=len)
    if len(lcc) <= 1:
        return 0
    G_lcc = G.subgraph(lcc)
    if len(lcc) <= 500:
        try:
            return int(nx.diameter(G_lcc))
        except Exception:
            pass
    sample = rng.sample(list(G_lcc.nodes()), min(samples, len(lcc)))
    max_d = 0
    for node in sample:
        d = max(nx.single_source_shortest_path_length(G_lcc, node).values(), default=0)
        if d > max_d:
            max_d = d
    return max_d


def _avg_shortest_path(
    G: nx.Graph,
    max_exact: int = 300,
    samples: int = 150,
    seed: int = 42,
) -> float:
    """Longitud media de camino más corto sobre la LCC (exacto o por muestreo)."""
    if G.number_of_nodes() == 0:
        return float("nan")
    comps = list(
        nx.weakly_connected_components(G) if G.is_directed()
        else nx.connected_components(G)
    )
    lcc = max(comps, key=len)
    if len(lcc) <= 1:
        return 0.0
    G_lcc = G.subgraph(lcc)
    n = len(lcc)
    if n <= max_exact:
        try:
            return float(nx.average_shortest_path_length(G_lcc))
        except Exception:
            pass
    rng = _rng_mod.Random(seed)
    sample = rng.sample(list(G_lcc.nodes()), min(samples, n))
    total, count = 0.0, 0
    for node in sample:
        lengths = nx.single_source_shortest_path_length(G_lcc, node)
        total += sum(v for v in lengths.values() if v > 0)
        count += len(lengths) - 1
    return total / count if count > 0 else float("nan")


def _powerlaw_exponent(degrees: list[int], k_min: int = 1) -> float:
    """Exponente γ de P(k) ~ k^(-γ) por el estimador MLE de Clauset-Shalizi-Newman."""
    valid = [k for k in degrees if k >= k_min]
    if len(valid) < 2:
        return float("nan")
    log_sum = sum(math.log(k / (k_min - 0.5)) for k in valid)
    if log_sum == 0:
        return float("nan")
    return 1.0 + len(valid) / log_sum


def _centrality(
    G: nx.Graph,
    seed: int = 42,
) -> tuple[dict[Any, float], dict[Any, float], dict[Any, float]]:
    """Devuelve (betweenness, eigenvector, pagerank) por nodo."""
    n = G.number_of_nodes()
    k = max(50, n // 10)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bc: dict[Any, float] = nx.betweenness_centrality(
            G, k=min(k, n), seed=seed, normalized=True
        )

    if not G.is_directed():
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ec: dict[Any, float] = nx.eigenvector_centrality(G, max_iter=1000)
        except Exception:
            ec = {v: float("nan") for v in G.nodes()}
    else:
        ec = {v: float("nan") for v in G.nodes()}

    try:
        pr: dict[Any, float] = nx.pagerank(G, max_iter=1000)
    except Exception:
        pr = {v: float("nan") for v in G.nodes()}

    return bc, ec, pr


def _pearson_r(x: list[float], y: list[float]) -> float:
    """Coeficiente de correlación de Pearson sin numpy."""
    n = len(x)
    if n <= 1:
        return float("nan")
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / n
    sx = math.sqrt(sum((xi - mx) ** 2 for xi in x) / n)
    sy = math.sqrt(sum((yi - my) ** 2 for yi in y) / n)
    if sx == 0 or sy == 0:
        return float("nan")
    return cov / (sx * sy)


def _agg(vals: list[float]) -> tuple[float, float]:
    """Devuelve (máx, media) ignorando NaN."""
    ok = [v for v in vals if not math.isnan(v)]
    return (
        max(ok, default=float("nan")),
        sum(ok) / len(ok) if ok else float("nan"),
    )


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def compute_graph_metrics(G: nx.Graph, seed: int = 42) -> ComputedMetrics:
    """Calcula todas las métricas de un grafo y las devuelve como dict.

    Las claves con prefijo ``_`` (``_bc``, ``_ec``, ``_pr``) contienen los
    dicts de centralidad por nodo, usados para plots pero no serializables
    directamente a JSON. Usa ``metrics_to_json_safe()`` antes de guardar.

    Args:
        G: Grafo de NetworkX.
        seed: Semilla para algoritmos aproximados.

    Returns:
        Dict con métricas escalares + centralidades por nodo.
    """
    is_dir = G.is_directed()
    n = G.number_of_nodes()
    m = G.number_of_edges()

    n_comp, lcc_size, lcc_frac, n_scc = _lcc_info(G)
    bc, ec, pr = _centrality(G, seed=seed)
    bc_max, bc_avg = _agg(list(bc.values()))
    ec_max, ec_avg = _agg(list(ec.values()))
    pr_max, pr_avg = _agg(list(pr.values()))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            assort: float = float(nx.degree_assortativity_coefficient(G))
        except Exception:
            assort = float("nan")

    metrics: ComputedMetrics = {
        "n": n,
        "m": m,
        "density": float(nx.density(G)),
        "n_components": n_comp,
        "lcc_size": lcc_size,
        "lcc_fraction": lcc_frac,
        "transitivity": float(nx.transitivity(G)),
        "avg_shortest_path": _avg_shortest_path(G, seed=seed),
        "diameter": _approx_diameter(G, seed=seed),
        "assortativity": assort,
        "betweenness_max": bc_max,
        "betweenness_avg": bc_avg,
        "pagerank_max": pr_max,
        "pagerank_avg": pr_avg,
        # Centralidades por nodo (uso interno para plots)
        "_bc": bc,
        "_ec": ec,
        "_pr": pr,
    }

    if is_dir:
        in_d = [d for _, d in G.in_degree()]
        out_d = [d for _, d in G.out_degree()]
        metrics.update({
            "n_scc": n_scc,
            "reciprocity": float(nx.reciprocity(G)),
            "in_degree_max": max(in_d, default=0),
            "in_degree_avg": sum(in_d) / n if n else 0.0,
            "out_degree_max": max(out_d, default=0),
            "out_degree_avg": sum(out_d) / n if n else 0.0,
            "powerlaw_gamma_in": _powerlaw_exponent(in_d),
            "powerlaw_gamma_out": _powerlaw_exponent(out_d),
        })
    else:
        degs = [d for _, d in G.degree()]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                clust_avg: float = float(nx.average_clustering(G))
            except Exception:
                clust_avg = float("nan")
        metrics.update({
            "degree_max": max(degs, default=0),
            "degree_avg": sum(degs) / n if n else 0.0,
            "powerlaw_gamma": _powerlaw_exponent(degs),
            "clustering_avg": clust_avg,
            "eigenvector_max": ec_max,
            "eigenvector_avg": ec_avg,
        })

    return metrics


def compute_multilayer_metrics(
    ml_G: nx.Graph,
    G_a: nx.Graph,
    G_d: nx.DiGraph,
) -> ComputedMetrics:
    """Calcula métricas multicapa (correlación entre capas, participación).

    Args:
        ml_G: Grafo multicapa completo.
        G_a: Subgrafo de la capa analógica.
        G_d: Subgrafo de la capa digital.

    Returns:
        Dict con métricas multicapa serializables.
    """
    nodes = list(ml_G.nodes())
    deg_a = [float(G_a.degree(v)) for v in nodes]
    deg_d = [float(G_d.in_degree(v) + G_d.out_degree(v)) for v in nodes]
    total = [a + d for a, d in zip(deg_a, deg_d)]

    participation: list[float] = []
    for t, a, d in zip(total, deg_a, deg_d):
        if t > 0:
            p_a = a / t
            p_d = d / t
            participation.append(1.0 - (p_a ** 2 + p_d ** 2))

    part_avg = sum(participation) / len(participation) if participation else float("nan")
    corr = _pearson_r(deg_a, deg_d)

    active_a = sum(1 for a in deg_a if a > 0)
    active_d = sum(1 for d in deg_d if d > 0)
    active_both = sum(1 for a, d in zip(deg_a, deg_d) if a > 0 and d > 0)

    return {
        "active_analog": active_a,
        "active_digital": active_d,
        "active_both": active_both,
        "degree_correlation": corr,
        "participation_avg": part_avg,
        # Lista para plots de histograma
        "_participation": participation,
        "_deg_a": deg_a,
        "_deg_d": deg_d,
    }
