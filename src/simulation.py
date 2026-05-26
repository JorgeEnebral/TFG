"""
Punto de entrada de la simulación.

Uso:
    python -m src.simulation          # lee configs/config.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import config as cfg
from config import (
    BrainConfig,
    ErdosConfig,
    GraphConfig,
    MultiLayerConfig,
    ScaleFreeConfig,
    SNAPConfig,
    WattsConfig,
)
from src.agents import BayesianAgent, EmotionalBrain, StochasticAgent
from src.agents.brain import BrainHyperparams
from src.datacollector import DataCollector
from src.graphs import (
    BaseGraph,
    ErdosRenyiGraph,
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
        agent_type: Literal["stochastic", "bayesian"] = "stochastic",
        fire_probability: float = 0.20,
        sim_time: int = 40,
        interval_ms: int = 500,
        seed: int = 42,
        out_dir: str | Path = DATA_DIR,
        brain_config: BrainConfig | None = None,
    ) -> None:
        """Inicializa la simulación creando el modelo y el recolector.

        Args:
            graph: Topología de red ya construida (o lazy).
            agent_type: Tipo de agente a instanciar ("stochastic" o "bayesian").
            fire_probability: Probabilidad de disparo por paso (solo stochastic).
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

        if agent_type == "bayesian":
            bc = brain_config if brain_config is not None else BrainConfig()
            hp = BrainHyperparams(
                p_create_analog=bc.p_create_analog,
                p_create_digital_base=bc.p_create_digital_base,
                k_follower=bc.k_follower,
                theta_send=bc.theta_send,
                forward_base=bc.forward_base,
                forward_boost_anger=bc.forward_boost_anger,
                forward_boost_surprise=bc.forward_boost_surprise,
                attention_capacity=bc.attention_capacity,
                self_confidence_floor=bc.self_confidence_floor,
                genetics_mu=bc.genetics_mu,
                genetics_sigma=bc.genetics_sigma,
            )

            def agent_factory(model: NetworkModel, node_id: int) -> BayesianAgent:
                # Semilla derivada por nodo ⇒ genética reproducible y heterogénea.
                brain_seed = (self.seed * 1_000_003) ^ node_id
                brain = EmotionalBrain(hp=hp, seed=brain_seed)
                return BayesianAgent(model=model, node_id=node_id, brain=brain)
        else:
            def agent_factory(model: NetworkModel, node_id: int) -> StochasticAgent:  # type: ignore[misc]
                return StochasticAgent(model=model, node_id=node_id, fire_probability=self.fire_probability)

        self.collector = DataCollector()
        self.model = NetworkModel(
            graph=self.graph.graph,
            agent_factory=agent_factory,
            collector=self.collector,
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


def build_graph(g: GraphConfig, seed: int) -> BaseGraph:
    """Construye el ``BaseGraph`` correcto a partir de la configuración tipada.

    Args:
        g: Instancia de configuración de grafo.
        seed: Semilla del generador aleatorio.

    Returns:
        Instancia del ``BaseGraph`` correspondiente al tipo indicado.

    Raises:
        ValueError: Si el tipo de configuración no es reconocido.
    """
    if isinstance(g, ErdosConfig):
        return ErdosRenyiGraph(num_nodes=g.num_nodes, edge_prob=g.edge_prob, seed=seed)
    if isinstance(g, ScaleFreeConfig):
        return ScaleFreeGraph(
            num_nodes=g.num_nodes,
            alpha=g.alpha,
            beta=g.beta,
            gamma=g.gamma,
            delta_in=g.delta_in,
            delta_out=g.delta_out,
            seed=seed,
        )
    if isinstance(g, WattsConfig):
        return WattsStrogatzGraph(num_nodes=g.num_nodes, k=g.k, rewire_prob=g.rewire_prob, seed=seed)
    if isinstance(g, SNAPConfig):
        return SNAPGraph(dataset_name=g.dataset_name, cache_dir=g.cache_dir, directed=g.directed, seed=seed)
    if isinstance(g, MultiLayerConfig):
        digital: BaseGraph
        if isinstance(g.digital, SNAPConfig):
            # Capa digital siempre dirigida en multilayer
            digital = SNAPGraph(
                dataset_name=g.digital.dataset_name,
                cache_dir=g.digital.cache_dir,
                directed=True,
                seed=seed,
            )
            # Forzar build ahora para conocer el nº de nodos real del dataset
            n = len(digital)
        else:
            digital = ScaleFreeGraph(
                num_nodes=g.digital.num_nodes,
                alpha=g.digital.alpha,
                beta=g.digital.beta,
                gamma=g.digital.gamma,
                delta_in=g.digital.delta_in,
                delta_out=g.digital.delta_out,
                seed=seed,
            )
            n = g.digital.num_nodes
        analog = WattsStrogatzGraph(
            num_nodes=n,
            k=g.analog.k,
            rewire_prob=g.analog.rewire_prob,
            seed=seed,
        )
        return MultiLayerGraph(digital_graph=digital, analog_graph=analog, seed=seed)
    raise ValueError(f"Tipo de grafo desconocido: {g!r}")


def main() -> None:
    """Punto de entrada principal: lee config, construye y ejecuta la simulación."""
    seed = cfg.SIMULATION.seed
    sim_time = cfg.SIMULATION.days * cfg.SIMULATION.steps_per_day

    graph = build_graph(cfg.GRAPH, seed=seed)

    folder = f"{cfg.GRAPH.type}-{cfg.AGENT.type}"
    if isinstance(cfg.GRAPH, SNAPConfig):
        folder += f"-{cfg.GRAPH.dataset_name}"

    out_dir = DATA_DIR / "results" / folder

    sim = Simulation(
        graph=graph,
        agent_type=cfg.AGENT.type,
        fire_probability=cfg.AGENT.fire_probability,
        sim_time=sim_time,
        interval_ms=cfg.SIMULATION.interval_ms,
        seed=seed,
        out_dir=out_dir,
        brain_config=cfg.AGENT.brain,
    )

    headless = not cfg.OUTPUT.render_gif and not cfg.OUTPUT.show
    if headless:
        sim.run_headless()
    else:
        gif_path = out_dir / f"{cfg.OUTPUT.basename}.gif" if cfg.OUTPUT.render_gif else None
        sim.run_with_animation(gif_path=gif_path, show=cfg.OUTPUT.show)

    if cfg.OUTPUT.export_csv or cfg.OUTPUT.export_json:
        sim.export_data(basename=cfg.OUTPUT.basename)
    if cfg.OUTPUT.render_plots:
        sim.render_static_plots(basename=cfg.OUTPUT.basename)
    print(f"[OK] Total mensajes disparados: {len(sim.collector)}")


if __name__ == "__main__":
    main()
