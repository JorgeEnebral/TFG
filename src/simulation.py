"""
Punto de entrada de la simulación. Orquesta:
  - Construcción del grafo (clase de `src.graphs`)
  - Modelo Mesa con factoría de agentes
  - DataCollector
  - Visualizadores (animación, distribuciones)
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.agents import StochasticAgent
from src.datacollector import DataCollector
from src.graphs import (
    BarabasiAlbertGraph,
    BaseGraph,
    ErdosRenyiGraph,
    HyperGraph,
    SNAPGraph,
    WattsStrogatzGraph,
)
from src.model import NetworkModel
from src.visualizer import DegreeDistributionPlot, MessageHeatmap, NetworkAnimator

DATA_DIR = Path(__file__).parent / "data"


class Simulation:
    """Configura y ejecuta una simulación completa."""

    def __init__(
        self,
        graph: BaseGraph,
        fire_probability: float = 0.20,
        sim_time: int = 40,
        interval_ms: int = 500,
        seed: int = 42,
        out_dir: str | Path = DATA_DIR,
    ) -> None:
        self.graph = graph
        self.fire_probability = fire_probability
        self.sim_time = sim_time
        self.interval_ms = interval_ms
        self.seed = seed
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.collector = DataCollector()
        self.model = NetworkModel(
            graph=self.graph.graph,
            agent_factory=lambda model, node_id: StochasticAgent(
                model=model,
                node_id=node_id,
                fire_probability=self.fire_probability,
            ),
            data_collector=self.collector,
            seed=self.seed,
        )

    def run_with_animation(
        self,
        gif_path: str | Path | None = None,
        show: bool = False,
    ) -> NetworkAnimator:
        animator = NetworkAnimator(
            model=self.model,
            sim_time=self.sim_time,
            interval_ms=self.interval_ms,
            layout_seed=self.seed,
            title_suffix=f"p_fire = {self.fire_probability}",
        )
        if gif_path is not None:
            saved = animator.save_gif(gif_path)
            print(f"[OK] GIF guardado en: {saved}")
        if show:
            animator.show()
        else:
            animator.close()
        return animator

    def run_headless(self) -> None:
        for _ in range(self.sim_time):
            self.model.step()

    def export_data(self, basename: str = "simulation") -> dict[str, Path]:
        csv_path = self.collector.to_csv(self.out_dir / f"{basename}.csv")
        json_path = self.collector.to_json(self.out_dir / f"{basename}.json")
        print(f"[OK] Trazas CSV  -> {csv_path}")
        print(f"[OK] Trazas JSON -> {json_path}")
        return {"csv": csv_path, "json": json_path}

    def render_static_plots(self, basename: str = "simulation") -> dict[str, Path]:
        deg_path = self.out_dir / f"{basename}_degree.png"
        heat_path = self.out_dir / f"{basename}_heatmap.png"
        DegreeDistributionPlot(self.graph.graph).render(deg_path)
        MessageHeatmap(self.collector, num_nodes=len(self.graph)).render(heat_path)
        print(f"[OK] Distribución grado -> {deg_path}")
        print(f"[OK] Heatmap mensajes   -> {heat_path}")
        return {"degree": deg_path, "heatmap": heat_path}


# ============================================================
# Selector de grafos por nombre (CLI)
# ============================================================
def build_graph(args: argparse.Namespace) -> BaseGraph:
    kind = args.graph
    if kind == "erdos":
        return ErdosRenyiGraph(
            num_nodes=args.nodes, edge_prob=args.edge_prob, seed=args.seed
        )
    if kind == "barabasi":
        return BarabasiAlbertGraph(num_nodes=args.nodes, m=args.m, seed=args.seed)
    if kind == "watts":
        return WattsStrogatzGraph(
            num_nodes=args.nodes, k=args.k, rewire_prob=args.rewire_prob, seed=args.seed
        )
    if kind == "hyper":
        return HyperGraph(
            num_nodes=args.nodes,
            num_hyperedges=args.hyperedges,
            hyperedge_size_range=(args.he_min, args.he_max),
            seed=args.seed,
        )
    if kind == "snap":
        return SNAPGraph(
            dataset_name=args.snap_dataset, cache_dir=DATA_DIR / "snap", seed=args.seed
        )
    raise ValueError(f"Tipo de grafo desconocido: {kind}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Simulación de red de agentes (TFG).")
    p.add_argument(
        "--graph",
        choices=["erdos", "barabasi", "watts", "hyper", "snap"],
        default="erdos",
    )
    p.add_argument("--nodes", type=int, default=12)
    p.add_argument("--edge-prob", type=float, default=0.25)
    p.add_argument("--m", type=int, default=2, help="Barabási–Albert: aristas/nodo")
    p.add_argument("--k", type=int, default=4, help="Watts–Strogatz: vecinos")
    p.add_argument(
        "--rewire-prob", type=float, default=0.1, help="Watts–Strogatz: prob. recableo"
    )
    p.add_argument("--hyperedges", type=int, default=10)
    p.add_argument("--he-min", type=int, default=2)
    p.add_argument("--he-max", type=int, default=4)
    p.add_argument("--snap-dataset", type=str, default="ca-GrQc")

    p.add_argument("--fire-prob", type=float, default=0.20)
    p.add_argument("--time", type=int, default=40)
    p.add_argument("--interval", type=int, default=500)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-gif", action="store_true")
    p.add_argument("--show", action="store_true")
    p.add_argument("--out", type=str, default="simulation")
    p.add_argument("--no-export", action="store_true")
    p.add_argument("--no-plots", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    graph = build_graph(args)
    sim = Simulation(
        graph=graph,
        fire_probability=args.fire_prob,
        sim_time=args.time,
        interval_ms=args.interval,
        seed=args.seed,
    )
    if args.no_gif and not args.show:
        sim.run_headless()
    else:
        gif_path = None if args.no_gif else DATA_DIR / f"{args.out}.gif"
        sim.run_with_animation(gif_path=gif_path, show=args.show)

    if not args.no_export:
        sim.export_data(basename=args.out)
    if not args.no_plots:
        sim.render_static_plots(basename=args.out)
    print(f"[OK] Total mensajes disparados: {len(sim.collector)}")


if __name__ == "__main__":
    main()
