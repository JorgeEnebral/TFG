"""
Punto de entrada de la simulación.

Orquesta todas las piezas:
  - Construcción del grafo (clases en `src.graphs`).
  - Modelo Mesa con factoría de agentes (`src.model.NetworkModel`).
  - DataCollector (`src.datacollector`).
  - Visualizadores (animación, distribuciones, heatmap).

Aquí vive también la **CLI**: argparse + `build_graph()` + `main()`.
La clase `Simulation` es reutilizable desde notebooks o tests sin
necesidad de pasar por la CLI.
"""

from __future__ import annotations

import argparse
from pathlib import Path

# Importamos los componentes de la simulación. Cada uno vive en su propio
# módulo y solo este fichero los conoce a todos a la vez (es el "ensamblador").
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

# Ruta absoluta a `src/data/`, calculada a partir de la ubicación de este fichero.
# `__file__` -> ruta del módulo actual; `.parent` -> carpeta `src/`.
# Usar Path absoluta evita problemas de "current working directory" cuando
# se ejecuta desde sitios distintos (`uv run`, IDE, notebook, etc.).
DATA_DIR = Path(__file__).parent / "data"


class Simulation:
    """
    Configura y ejecuta una simulación completa.

    Es la fachada de alto nivel. Quien la use NO necesita saber cómo
    interactúan modelo, agentes y collector: solo construye una
    `Simulation` con los parámetros y llama a uno de sus métodos.

    Atributos:
      - `graph`            : instancia de `BaseGraph` (cualquier topología).
      - `fire_probability` : prob. por agente y paso de disparar mensaje.
      - `sim_time`         : nº total de pasos a simular.
      - `interval_ms`      : ms entre frames de la animación.
      - `seed`             : semilla compartida para reproducibilidad.
      - `out_dir`          : carpeta donde escribir outputs.
      - `collector`        : DataCollector creado y mantenido por la sim.
      - `model`            : NetworkModel ya inicializado con agentes.
    """

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
        # Aseguramos que el directorio de salida exista (idempotente).
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

        # Creamos el DataCollector ANTES del modelo y se lo inyectamos.
        # Así mantenemos una referencia desde fuera (`sim.collector`)
        # y a la vez el modelo lo rellena (es la misma instancia).
        self.collector = DataCollector()

        # El modelo recibe:
        #   - el `nx.Graph` (no el envoltorio BaseGraph). `graph.graph`
        #     dispara la construcción lazy si era la primera vez.
        #   - una factoría de agentes via `lambda`. Aquí decidimos que
        #     todos los agentes son StochasticAgent con la misma probabilidad.
        #     Para poblaciones heterogéneas bastaría con un lambda más
        #     elaborado (p.ej. mezclar tipos según `node_id`).
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
        """
        Ejecuta la simulación renderizándola como animación.

        El `NetworkAnimator.draw_frame` es quien llama a `model.step()`
        en cada frame, así que el avance de la simulación está acoplado
        al pintado. Si quieres rapidez sin gráficos, usa `run_headless`.
        """
        animator = NetworkAnimator(
            model=self.model,
            sim_time=self.sim_time,
            interval_ms=self.interval_ms,
            layout_seed=self.seed,
            title_suffix=f"p_fire = {self.fire_probability}",
        )
        # Guardar GIF y/o mostrar ventana son operaciones independientes.
        # `gif_path is not None` -> escribimos a disco.
        if gif_path is not None:
            saved = animator.save_gif(gif_path)
            print(f"[OK] GIF guardado en: {saved}")
        # `show=True` -> ventana matplotlib interactiva (requiere display).
        if show:
            animator.show()
        else:
            # Cerramos la figura para liberar memoria si no la mostramos.
            animator.close()
        return animator

    def run_headless(self) -> None:
        """
        Ejecuta la simulación sin graficar. Mucho más rápido.

        Útil para barridos de parámetros, generación masiva de trazas
        o cuando el resultado interesa solo en CSV/JSON.
        """
        for _ in range(self.sim_time):
            self.model.step()

    def export_data(self, basename: str = "simulation") -> dict[str, Path]:
        """Exporta las trazas a CSV y JSON en `out_dir`."""
        csv_path = self.collector.to_csv(self.out_dir / f"{basename}.csv")
        json_path = self.collector.to_json(self.out_dir / f"{basename}.json")
        print(f"[OK] Trazas CSV  -> {csv_path}")
        print(f"[OK] Trazas JSON -> {json_path}")
        return {"csv": csv_path, "json": json_path}

    def render_static_plots(self, basename: str = "simulation") -> dict[str, Path]:
        """Genera plots estáticos resumiendo el grafo y la dinámica."""
        deg_path = self.out_dir / f"{basename}_degree.png"
        heat_path = self.out_dir / f"{basename}_heatmap.png"
        # `DegreeDistributionPlot` solo depende del grafo (estructura).
        DegreeDistributionPlot(self.graph.graph).render(deg_path)
        # `MessageHeatmap` depende de la dinámica (collector) + tamaño del grafo.
        MessageHeatmap(self.collector, num_nodes=len(self.graph)).render(heat_path)
        print(f"[OK] Distribución grado -> {deg_path}")
        print(f"[OK] Heatmap mensajes   -> {heat_path}")
        return {"degree": deg_path, "heatmap": heat_path}


# ============================================================
# Selector de grafos por nombre (CLI)
# ============================================================
def build_graph(args: argparse.Namespace) -> BaseGraph:
    """
    Mapea `args.graph` (string) -> instancia concreta de `BaseGraph`.

    Es un dispatcher simple: cinco ramas, una por topología soportada
    en la CLI. Conforme añadamos más tipos de grafo (LFR, SBM, etc.),
    aquí se mete una nueva rama.
    """
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
        # `cache_dir` apunta a `src/data/snap/` para que los datasets
        # SNAP descargados convivan con el resto de outputs.
        return SNAPGraph(
            dataset_name=args.snap_dataset, cache_dir=DATA_DIR / "snap", seed=args.seed
        )
    raise ValueError(f"Tipo de grafo desconocido: {kind}")


def parse_args() -> argparse.Namespace:
    """Define la CLI completa. Cada argumento mapea a un parámetro."""
    p = argparse.ArgumentParser(description="Simulación de red de agentes (TFG).")

    # --- Selección de topología ---
    # `choices` filtra valores inválidos antes de llegar a `build_graph`.
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

    # --- Parámetros de simulación ---
    p.add_argument("--fire-prob", type=float, default=0.20)
    p.add_argument("--time", type=int, default=40)
    p.add_argument("--interval", type=int, default=500)
    p.add_argument("--seed", type=int, default=42)

    # --- Flags de salida (action="store_true" -> presencia = True) ---
    p.add_argument("--no-gif", action="store_true")
    p.add_argument("--show", action="store_true")
    p.add_argument("--out", type=str, default="simulation")
    p.add_argument("--no-export", action="store_true")
    p.add_argument("--no-plots", action="store_true")
    return p.parse_args()


def main() -> None:
    """Pipeline completo de la CLI: parse -> build -> run -> export -> plots."""
    args = parse_args()
    graph = build_graph(args)
    sim = Simulation(
        graph=graph,
        fire_probability=args.fire_prob,
        sim_time=args.time,
        interval_ms=args.interval,
        seed=args.seed,
    )

    # Decisión de cómo correr:
    #   - sin GIF y sin ventana -> headless (rápido, sin matplotlib).
    #   - en otro caso -> con animación (más lento, pero genera GIF/ventana).
    # Si ambos flags están desactivados ahorramos pintar todo.
    if args.no_gif and not args.show:
        sim.run_headless()
    else:
        gif_path = None if args.no_gif else DATA_DIR / f"{args.out}.gif"
        sim.run_with_animation(gif_path=gif_path, show=args.show)

    # Exportar trazas y plots son opcionales (flags --no-export / --no-plots).
    if not args.no_export:
        sim.export_data(basename=args.out)
    if not args.no_plots:
        sim.render_static_plots(basename=args.out)
    print(f"[OK] Total mensajes disparados: {len(sim.collector)}")


# Bloque guard: solo se ejecuta si llamamos al fichero directamente
# (no si lo importamos como módulo). `python -m src.simulation` lo dispara.
if __name__ == "__main__":
    main()
