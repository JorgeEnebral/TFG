"""
Punto de entrada de la simulación.

Uso:
    python -m src.simulation          # lee configs/config.py
"""

from __future__ import annotations

from pathlib import Path

import configs.config as cfg
from src.agents import StochasticAgent
from src.datacollector import DataCollector
from src.graphs import (
    BaseGraph,
    ErdosRenyiGraph,
    HyperGraph,
    MultiLayerGraph,
    ScaleFreeGraph,
    SNAPGraph,
    WattsStrogatzGraph,
)
from src.model import NetworkModel
from src.visualizer import DegreeDistributionPlot, MessageHeatmap, NetworkAnimator

DATA_DIR = Path(__file__).parent.parent / "data"


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
        """Inicializa la simulación creando el modelo y el recolector.

        Args:
            graph: Topología de red ya construida (o lazy).
            fire_probability: Probabilidad de disparo por agente y paso.
            sim_time: Número total de pasos a simular.
            interval_ms: Milisegundos entre frames en la animación.
            seed: Semilla del RNG compartido.
            out_dir: Directorio de salida para datos y figuras.
        """
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
        """Ejecuta la simulación con animación matplotlib.

        Args:
            gif_path: Si se proporciona, guarda la animación como GIF.
            show: Si True, abre una ventana matplotlib en tiempo real.

        Returns:
            El ``NetworkAnimator`` usado, por si el caller quiere reutilizarlo.
        """
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
        """Ejecuta la simulación sin visualización."""
        for _ in range(self.sim_time):
            self.model.step()

    def export_data(self, basename: str = "simulation") -> dict[str, Path]:
        """Exporta las trazas recogidas a CSV y JSON.

        Args:
            basename: Prefijo del nombre de archivo sin extensión.

        Returns:
            Diccionario ``{"csv": Path, "json": Path}`` con las rutas escritas.
        """
        csv_path = self.collector.to_csv(self.out_dir / f"{basename}.csv")
        json_path = self.collector.to_json(self.out_dir / f"{basename}.json")
        print(f"[OK] Trazas CSV  -> {csv_path}")
        print(f"[OK] Trazas JSON -> {json_path}")
        return {"csv": csv_path, "json": json_path}

    def render_static_plots(self, basename: str = "simulation") -> dict[str, Path]:
        """Genera los plots estáticos de distribución de grado y heatmap.

        Args:
            basename: Prefijo del nombre de archivo sin extensión.

        Returns:
            Diccionario ``{"degree": Path, "heatmap": Path}`` con las rutas.
        """
        deg_path = self.out_dir / f"{basename}_degree.png"
        heat_path = self.out_dir / f"{basename}_heatmap.png"
        DegreeDistributionPlot(self.graph.graph).render(deg_path)
        MessageHeatmap(self.collector, num_nodes=len(self.graph)).render(heat_path)
        print(f"[OK] Distribución grado -> {deg_path}")
        print(f"[OK] Heatmap mensajes   -> {heat_path}")
        return {"degree": deg_path, "heatmap": heat_path}


def build_graph(g: dict[str, object], seed: int) -> BaseGraph:
    """Construye el ``BaseGraph`` correcto a partir del dict de configuración.

    Args:
        g: Diccionario con al menos la clave ``"type"`` y los parámetros
            específicos de esa topología.
        seed: Semilla del generador aleatorio.

    Returns:
        Instancia del ``BaseGraph`` correspondiente al tipo indicado.

    Raises:
        ValueError: Si ``g["type"]`` no corresponde a ninguna topología conocida.
    """
    kind = g["type"]
    if kind == "erdos":
        return ErdosRenyiGraph(num_nodes=g["num_nodes"], edge_prob=g["edge_prob"], seed=seed)
    if kind == "scale_free":
        return ScaleFreeGraph(
            num_nodes=g["num_nodes"],
            alpha=g["sf_alpha"],
            beta=g["sf_beta"],
            gamma=g["sf_gamma"],
            delta_in=g["sf_delta_in"],
            delta_out=g["sf_delta_out"],
            seed=seed,
        )
    if kind == "watts":
        return WattsStrogatzGraph(num_nodes=g["num_nodes"], k=g["ws_k"], rewire_prob=g["ws_rewire_prob"], seed=seed)
    if kind == "snap":
        return SNAPGraph(dataset_name=g["snap_dataset"], seed=seed)
    if kind == "multilayer":
        return MultiLayerGraph(
            num_nodes=g["num_nodes"],
            ws_k=g["ws_k"],
            ws_rewire_prob=g["ws_rewire_prob"],
            sf_alpha=g["sf_alpha"],
            sf_beta=g["sf_beta"],
            sf_gamma=g["sf_gamma"],
            sf_delta_in=g["sf_delta_in"],
            sf_delta_out=g["sf_delta_out"],
            seed=seed,
        )
    raise ValueError(f"Tipo de grafo desconocido: {kind!r}")


def main() -> None:
    """Punto de entrada principal: lee config, construye y ejecuta la simulación."""
    seed = cfg.SIMULATION["seed"]
    sim_time = cfg.SIMULATION["days"] * cfg.SIMULATION["steps_per_day"]

    graph = build_graph(cfg.GRAPH, seed=seed)

    folder = (
        f"snap-{cfg.GRAPH['snap_dataset']}"
        if cfg.GRAPH["type"] == "snap"
        else f"{cfg.GRAPH['type']}-{cfg.GRAPH['num_nodes']}"
    )
    out_dir = DATA_DIR / "results" / folder

    sim = Simulation(
        graph=graph,
        fire_probability=cfg.SIMULATION["fire_probability"],
        sim_time=sim_time,
        interval_ms=cfg.SIMULATION["interval_ms"],
        seed=seed,
        out_dir=out_dir,
    )

    headless = not cfg.OUTPUT["render_gif"] and not cfg.OUTPUT["show"]
    if headless:
        sim.run_headless()
    else:
        gif_path = out_dir / f"{cfg.OUTPUT['basename']}.gif" if cfg.OUTPUT["render_gif"] else None
        sim.run_with_animation(gif_path=gif_path, show=cfg.OUTPUT["show"])

    if cfg.OUTPUT["export_csv"] or cfg.OUTPUT["export_json"]:
        sim.export_data(basename=cfg.OUTPUT["basename"])
    if cfg.OUTPUT["render_plots"]:
        sim.render_static_plots(basename=cfg.OUTPUT["basename"])
    print(f"[OK] Total mensajes disparados: {len(sim.collector)}")


if __name__ == "__main__":
    main()
