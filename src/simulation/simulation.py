"""
Punto de entrada de la simulación.

Uso:
    python -m src.simulation.simulation          # lee src/config.py

Estructura de salida:
    data/results/{tipo_grafo}-{tipo_agente}/
        sim/
            graph.json          (estructura del grafo, formato node-link)
            {basename}.csv/.json (trazas de mensajes)
        graph/
            graph.png           (visualización del grafo)
            histograms.png      (distribución de grado y centralidades)
            metrics.json        (métricas escalares)
            heatmap.png         (mensajes por par origen-destino)
        {basename}.gif          (replay post-simulación, si render_gif=True)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import networkx as nx
import src.config as cfg
from src.agents import BayesianAgent, EmotionalBrain, StochasticAgent
from src.agents.brain import BrainHyperparams
from src.config import (
    BrainConfig,
    ErdosConfig,
    GraphConfig,
    MultiLayerConfig,
    ScaleFreeConfig,
    SNAPConfig,
    WattsConfig,
)
from src.graphs import (
    BaseGraph,
    ErdosRenyiGraph,
    MultiLayerGraph,
    ScaleFreeGraph,
    SNAPGraph,
    WattsStrogatzGraph,
)
from src.simulation.datacollector import DataCollector
from src.simulation.model import NetworkModel

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class Simulation:
    """Configura y ejecuta una simulación completa."""

    def __init__(
        self,
        graph: BaseGraph,
        agent_type: Literal["stochastic", "bayesian"] = "stochastic",
        fire_probability: float = 0.20,
        sim_time: int = 40,
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
            seed: Semilla del RNG compartido.
            out_dir: Directorio raíz de salida (se crean subdirectorios ``sim/`` y ``graph/``).
        """
        self.graph = graph
        self.fire_probability = fire_probability
        self.sim_time = sim_time
        self.seed = seed
        self.out_dir = Path(out_dir)
        self.sim_dir = self.out_dir / "sim"
        self.graph_dir = self.out_dir / "graph"
        self.sim_dir.mkdir(parents=True, exist_ok=True)

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

    def run(self) -> None:
        """Ejecuta la simulación (siempre headless)."""
        for _ in range(self.sim_time):
            self.model.step()

    def save_graph_structure(self) -> Path:
        """Guarda la estructura del grafo en formato node-link JSON.

        Returns:
            Ruta del fichero escrito (``sim/graph.json``).
        """
        path = self.sim_dir / "graph.json"
        data = nx.node_link_data(self.model.graph)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def export_data(
        self,
        export_format: Literal["csv", "json"],
        basename: str = "simulation",
    ) -> Path:
        """Exporta las trazas al formato indicado.

        Args:
            export_format: ``"csv"`` o ``"json"``.
            basename: Prefijo del nombre de fichero.

        Returns:
            Ruta del fichero escrito.
        """
        if export_format == "csv":
            path = self.collector.to_csv(self.sim_dir / f"{basename}.csv")
        else:
            path = self.collector.to_json(self.sim_dir / f"{basename}.json")
        print(f"[OK] Trazas ({export_format.upper()}) -> {path}")
        return path

    def render_graph_analysis(self, basename: str = "simulation") -> Path:
        """Genera análisis estático del grafo: imágenes + metrics.json + heatmap.

        Args:
            basename: Prefijo para el heatmap.

        Returns:
            Directorio donde se guardaron los ficheros.
        """
        from src.visualization.plots import analyse_graph  # lazy: evita import circular
        from src.visualization.visualizer import MessageHeatmap  # lazy: ídem

        self.graph_dir.mkdir(parents=True, exist_ok=True)
        analyse_graph(self.model.graph, basename, out_dir=self.graph_dir, seed=self.seed)
        heatmap_path = self.graph_dir / f"{basename}_heatmap.png"
        MessageHeatmap(self.collector, num_nodes=len(self.graph)).render(heatmap_path)
        print(f"[OK] Análisis grafo -> {self.graph_dir}")
        return self.graph_dir

    def render_gif(
        self,
        messages_path: Path,
        interval_ms: int = 500,
        basename: str = "simulation",
    ) -> Path:
        """Genera GIF de replay a partir de los ficheros guardados.

        Args:
            messages_path: Ruta al fichero de mensajes (CSV o JSON).
            interval_ms: Milisegundos entre frames.
            basename: Prefijo del nombre del GIF.

        Returns:
            Ruta del GIF escrito.
        """
        from src.visualization.visualizer import PostSimAnimator  # lazy: evita import circular

        graph_path = self.sim_dir / "graph.json"
        gif_path = self.out_dir / f"{basename}.gif"
        animator = PostSimAnimator(graph_path=graph_path, messages_path=messages_path)
        saved = animator.save_gif(gif_path, interval_ms=interval_ms, layout_seed=self.seed)
        print(f"[OK] GIF guardado en: {saved}")
        return saved


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
            digital = SNAPGraph(
                dataset_name=g.digital.dataset_name,
                cache_dir=g.digital.cache_dir,
                directed=True,
                seed=seed,
            )
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
        seed=seed,
        out_dir=out_dir,
        brain_config=cfg.AGENT.brain,
    )

    sim.run()
    print(f"[OK] Total mensajes disparados: {len(sim.collector)}")

    messages_path: Path | None = None
    if cfg.OUTPUT.save_graph:
        sim.save_graph_structure()
    if cfg.OUTPUT.export_format != "none":
        messages_path = sim.export_data(
            export_format=cfg.OUTPUT.export_format,
            basename=cfg.OUTPUT.basename,
        )
    if cfg.OUTPUT.render_plots:
        sim.render_graph_analysis(basename=cfg.OUTPUT.basename)
    if cfg.OUTPUT.render_gif and messages_path is not None:
        sim.render_gif(
            messages_path=messages_path,
            interval_ms=cfg.SIMULATION.interval_ms,
            basename=cfg.OUTPUT.basename,
        )


if __name__ == "__main__":
    main()
