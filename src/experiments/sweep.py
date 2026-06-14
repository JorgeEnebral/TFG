"""
Runner OFAT multi-topología para el escenario resistente — sweep v2.

Mide cómo la resistencia cognitiva de la población depende de cinco palancas
de la narrativa, sobre dos topologías de red (scale_free y small_world), con
10 réplicas Monte Carlo por celda.

Diseño: OFAT (one-factor-at-a-time). Se fija un baseline y se mueve una sola
palanca cada vez. Produce curvas marginales con bandas de varianza a coste bajo
(~280 runs ≈ 30 min).

Salida::

    data/results/sweep_v2/
      sweep_summary.csv
      {topology}/{factor}/{factor}={valor}/seed={mc}/sim/
          graph.json
          simulation_agent_states.csv
          simulation_adoptions.csv
          simulation.csv

Uso::

    python -m src.experiments.sweep
"""

from __future__ import annotations

import contextlib
import csv
import io
import math
import os
import statistics
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path

from tqdm import tqdm

from src.agents import ResistantAgent
from src.config import (
    AgentConfig,
    GraphConfig,
    NarrativeConfig,
    ScaleFreeConfig,
    SimulationConfig,
    WattsConfig,
)
from src.simulation.simulation import DATA_DIR, Simulation, build_graph

# --- Parámetros del barrido --------------------------------------------------
NUM_NODES: int = 10_000
N_REPLICAS: int = 50
BASE_SEED: int = 1_000
DAYS: int = 3
STEPS_PER_DAY: int = 15
NVT: float = 0.30  # narrative_veracity_threshold (clasifica mensajes de narrativa)

# Baseline: valor central de cada palanca
BASE_NARRATIVE: NarrativeConfig = NarrativeConfig(
    k_seeds=50,  # 0.5 %
    seed_strategy="hubs",
    seed_fanout=0.4,
    veracity=0.1,
    emotional_load=0.6,
    gamma=0.5,
    susceptible_fraction=0.5,
    theta_susceptible_mu=0.30,
    theta_resistant_mu=0.70,
    theta_sigma=0.10,
    forward_probability=0.1,
)

# Topologías a comparar
TOPOLOGIES: dict[str, GraphConfig] = {
    "scale_free": ScaleFreeConfig(num_nodes=NUM_NODES, layer="digital"),
    "small_world": WattsConfig(num_nodes=NUM_NODES, k=10, rewire_prob=0.1, layer="analog"),
}

# Factores OFAT: (nombre_campo_NarrativeConfig, niveles)
# k_seeds se especifica como fracción de N; el resto en sus unidades nativas.
FACTORS: list[tuple[str, list[object]]] = [
    ("gamma",                [0.25, 0.5, 0.75]),
    ("seed_strategy",        ["hubs", "random"]),
    ("seed_fanout",          [0.2, 0.4, 0.6]),
    ("k_seeds",              [0.001, 0.005, 0.01]),  # fracciones → se convierten a int
    ("forward_probability",  [0.05, 0.1, 0.15]),
    ("susceptible_fraction", [0.25, 0.5, 0.75]),
    ("emotional_load",       [0.4, 0.6, 0.8]),
]

OUT_ROOT: Path = DATA_DIR / "results" / "sweep"
# -----------------------------------------------------------------------------

Metric = dict[str, float | int | str | None]

SUMMARY_FIELDS: list[str] = [
    "topology", "factor", "valor", "k_abs", "seed",
    "N", "seeds", "conversiones",
    "tasa_ataque", "resiliencia", "entropia", "t50",
    "reach", "narrative_msgs", "mean_Ri", "peak_new", "t_peak",
]


def _build_narrative(factor: str, level: object) -> tuple[NarrativeConfig, int | None]:
    """Construye la narrativa OFAT variando *factor* al nivel *level*.

    Args:
        factor: Nombre del campo de ``NarrativeConfig`` a variar.
        level: Valor del factor. Para ``k_seeds``, es una fracción de N.

    Returns:
        Tupla (narrativa, k_abs): k_abs es el nº absoluto de semillas cuando
        ``factor == "k_seeds"``; ``None`` para el resto de factores.
    """
    if factor == "k_seeds":
        frac = float(level)  # type: ignore[arg-type]
        k = max(1, round(frac * NUM_NODES))
        return replace(BASE_NARRATIVE, k_seeds=k), k
    return replace(BASE_NARRATIVE, **{factor: level}), None  # type: ignore[arg-type]


def _metrics(sim: Simulation) -> Metric:
    """Calcula las métricas extendidas de un run a partir del modelo y el collector.

    Args:
        sim: Simulación ya ejecutada.

    Returns:
        Diccionario con todas las métricas definidas en ``SUMMARY_FIELDS``.
    """
    agents = [a for a in sim.model.agent_by_node.values() if isinstance(a, ResistantAgent)]
    n = len(agents)
    n_seed = sum(1 for a in agents if a.is_seed)
    believers = sum(1 for a in agents if a.adopted and not a.is_seed)
    denom = n - n_seed

    attack = believers / denom if denom else float("nan")
    if math.isnan(attack) or attack in (0.0, 1.0):
        entropy = 0.0
    else:
        entropy = -(attack * math.log2(attack) + (1 - attack) * math.log2(1 - attack))

    conv_times = sorted(
        a.adopted_at
        for a in agents
        if a.adopted and not a.is_seed and a.adopted_at is not None
    )
    t50: int | None = conv_times[math.ceil(0.5 * len(conv_times)) - 1] if conv_times else None

    # Mensajes de narrativa: veracity <= NVT
    narrative_ints = [i for i in sim.collector.interactions if i.veracity <= NVT]
    reach = len({i.target_node for i in narrative_ints})
    narrative_msgs = len(narrative_ints)

    # R_i: θ medio de no-semillas expuestas (capacidad de resistencia del alcanzado)
    exposed_ns = [a for a in agents if not a.is_seed and a.exposures > 0]
    mean_ri: float = statistics.mean(a.theta for a in exposed_ns) if exposed_ns else float("nan")

    # Pico de conversiones
    step_counts: Counter[int] = Counter(ad.timestep for ad in sim.collector.adoptions)
    t_peak: int | None
    peak_new: int
    if step_counts:
        t_peak = max(step_counts, key=step_counts.__getitem__)
        peak_new = step_counts[t_peak]
    else:
        t_peak = None
        peak_new = 0

    return {
        "N": n,
        "seeds": n_seed,
        "conversiones": believers,
        "tasa_ataque": round(attack, 4),
        "resiliencia": round(1 - attack, 4) if denom else float("nan"),
        "entropia": round(entropy, 4),
        "t50": t50,
        "reach": reach,
        "narrative_msgs": narrative_msgs,
        "mean_Ri": round(mean_ri, 4) if not math.isnan(mean_ri) else float("nan"),
        "peak_new": peak_new,
        "t_peak": t_peak,
    }


def run_one(
    topo_cfg: GraphConfig,
    narrative: NarrativeConfig,
    seed: int,
    out_dir: Path,
) -> Metric:
    """Ejecuta un único run, guarda los 4 ficheros y devuelve las métricas.

    Args:
        topo_cfg: Configuración de la topología (ScaleFreeConfig o WattsConfig).
        narrative: Configuración de la narrativa para este run.
        seed: Semilla MC (regenera grafo, umbrales θ y dinámica).
        out_dir: Directorio raíz del run (se crea ``sim/`` debajo).

    Returns:
        Diccionario de métricas calculadas tras la simulación.
    """
    graph = build_graph(topo_cfg, seed=seed)
    agent_cfg = AgentConfig(type="resistant", fire_probability=0.0, narrative=narrative)
    sim_cfg = SimulationConfig(days=DAYS, steps_per_day=STEPS_PER_DAY, seed=seed)

    sim = Simulation(graph=graph, agent=agent_cfg, sim=sim_cfg, out_dir=out_dir)
    sim.inject_narrative(narrative)

    for _ in range(sim.sim_time):
        sim.model.step()

    # Guardar los 4 ficheros por run
    sim.save_graph_structure()
    sim.collector.adoptions_to_csv(sim.sim_dir / "simulation_adoptions.csv")
    with contextlib.redirect_stdout(io.StringIO()):
        sim.export_agent_states(basename="simulation")
    sim.collector.to_csv(sim.sim_dir / "simulation.csv")

    return _metrics(sim)


def _aggregate(rows: list[dict[str, object]]) -> None:
    """Imprime media ± sd de tasa de ataque por (topología, factor, nivel).

    Args:
        rows: Lista de filas del summary.
    """
    cells: dict[tuple[object, object, object], list[float]] = {}
    for r in rows:
        ar = r["tasa_ataque"]
        if isinstance(ar, float) and not math.isnan(ar):
            cells.setdefault((r["topology"], r["factor"], r["valor"]), []).append(ar)
    print("\n=== Resumen (tasa de ataque media ± sd por celda) ===")
    for (topo, factor, valor), vals in cells.items():
        mean = statistics.mean(vals)
        sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
        print(f"  {topo} | {factor}={valor}: {mean:.3f} ± {sd:.3f}  (n={len(vals)})")


_Task = tuple[str, GraphConfig, str, object, int | None, int, NarrativeConfig, Path]


def _run_task(task: _Task) -> dict[str, object]:
    """Wrapper serializable para ProcessPoolExecutor.

    Args:
        task: Tupla con todos los parámetros de un run individual.

    Returns:
        Fila completa lista para escribir en sweep_summary.csv.
    """
    topo_name, topo_cfg, factor, level, k_abs, seed, narrative, out_dir = task
    metrics = run_one(topo_cfg, narrative, seed, out_dir)
    return {
        "topology": topo_name,
        "factor": factor,
        "valor": level,
        "k_abs": k_abs if k_abs is not None else "",
        "seed": seed,
        **metrics,
    }


def main() -> None:
    """Construye las tareas OFAT, corre el barrido en paralelo y escribe sweep_summary.csv."""
    tasks: list[_Task] = []

    for topo_name, topo_cfg in TOPOLOGIES.items():
        for factor, levels in FACTORS:
            for level in levels:
                narrative, k_abs = _build_narrative(factor, level)
                for r in range(N_REPLICAS):
                    seed = BASE_SEED + r
                    out_dir = (
                        OUT_ROOT / topo_name / factor
                        / f"{factor}={level}"
                        / f"seed={seed}"
                    )
                    tasks.append((topo_name, topo_cfg, factor, level, k_abs, seed, narrative, out_dir))

    workers = 5
    rows: list[dict[str, object]] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run_task, t): t for t in tasks}
        for fut in tqdm(as_completed(futures), total=len(tasks), desc="Sweep", unit="run"):
            rows.append(fut.result())

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    summary = OUT_ROOT / "sweep_summary.csv"
    with open(summary, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"\n[OK] {len(rows)} runs -> {summary}")
    _aggregate(rows)


if __name__ == "__main__":
    main()
