"""
Simulación de red de agentes con disparo probabilístico de mensajes.

Componentes:
  - NetworkX  -> define el grafo (nodos = agentes, aristas = relaciones)
  - Mesa      -> modela los agentes y el step de la simulación
  - Matplotlib FuncAnimation -> visualiza en tiempo real

Cada agente, en cada paso de la simulación, dispara un mensaje a un vecino
aleatorio con probabilidad `fire_probability`.
"""

from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import mesa
import networkx as nx
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.axes import Axes


# ============================================================
# AGENTE
# ============================================================
class MessageAgent(mesa.Agent):  # type: ignore
    """Cerebro mínimo: con probabilidad p, dispara un mensaje a un vecino."""

    def __init__(
        self, model: NetworkModel, node_id: int, fire_probability: float
    ) -> None:
        super().__init__(model)
        self.node_id = node_id  # id del nodo en el grafo
        self.fire_probability = fire_probability

    def step(self) -> None:
        if self.random.random() < self.fire_probability:
            neighbors = list(self.model.G.neighbors(self.node_id))
            if neighbors:
                target = self.random.choice(neighbors)
                # Registrar el "disparo" en el modelo
                self.model.active_messages.append((self.node_id, target))


# ============================================================
# MODELO
# ============================================================
class NetworkModel(mesa.Model):  # type: ignore
    """Modelo Mesa que envuelve un grafo de NetworkX."""

    def __init__(self, g: nx.Graph, fire_probability: float = 0.15, seed: int = 42):
        super().__init__(rng=seed)
        self.g = g
        self.active_messages: list[tuple[int, int]] = []  # mensajes del paso actual
        self.message_history: list[tuple[int, int, int]] = []  # (paso, src, tgt)
        self.current_step = 0

        # Un agente por cada nodo del grafo
        self.agent_by_node: dict[int, MessageAgent] = {}
        for node_id in g.nodes():
            agent = MessageAgent(
                self, node_id=node_id, fire_probability=fire_probability
            )
            self.agent_by_node[node_id] = agent

    def step(self) -> None:
        self.active_messages = []
        # Mesa 3.x: ejecutar el método 'step' de todos los agentes en orden aleatorio
        self.agents.shuffle_do("step")
        # Guardar en historial
        for src, tgt in self.active_messages:
            self.message_history.append((self.current_step, src, tgt))
        self.current_step += 1


# ============================================================
# VISUALIZADOR
# ============================================================
def run_simulation(
    num_nodes: int = 12,
    edge_prob: float = 0.25,
    fire_probability: float = 0.20,
    sim_time: int = 40,
    interval_ms: int = 500,
    seed: int = 42,
    save_gif: bool = True,
    gif_path: str = "simulation.gif",
    show: bool = False,
) -> tuple[FuncAnimation, NetworkModel]:
    """Crea el grafo, el modelo, y anima la simulación paso a paso."""
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals

    # 1) Grafo aleatorio (Erdős–Rényi). Cambiable a cualquier generador.
    g = nx.erdos_renyi_graph(n=num_nodes, p=edge_prob, seed=seed)

    # Asegurar que el grafo sea conexo (cosmético, ayuda a verlo)
    if not nx.is_connected(g):
        components = list(nx.connected_components(g))
        for i in range(len(components) - 1):
            u = next(iter(components[i]))
            v = next(iter(components[i + 1]))
            g.add_edge(u, v)

    # 2) Modelo Mesa
    model = NetworkModel(g, fire_probability=fire_probability, seed=seed)

    # 3) Layout fijo para que los nodos no salten
    pos = nx.spring_layout(g, seed=seed, k=1.5)

    # 4) Figura con estilo "dark"
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor("#0f1419")
    ax.set_facecolor("#0f1419")

    def draw_frame(_frame: int) -> tuple[Axes]:
        ax.clear()
        ax.set_facecolor("#0f1419")

        # Avanzar la simulación un paso
        model.step()

        # Aristas en reposo (grises)
        nx.draw_networkx_edges(
            g,
            pos,
            ax=ax,
            edge_color="#2a3142",
            width=1.0,
            alpha=0.5,
        )

        # Aristas con mensaje activo (resaltadas con flecha)
        if model.active_messages:
            # NetworkX dibuja flechas si pasamos un DiGraph o usamos arrows=True
            dg = nx.DiGraph()
            dg.add_nodes_from(g.nodes())
            dg.add_edges_from(model.active_messages)
            nx.draw_networkx_edges(
                dg,
                pos,
                ax=ax,
                edgelist=list(dg.edges()),
                edge_color="#ff6b9d",
                width=3.0,
                alpha=0.95,
                arrows=True,
                arrowsize=22,
                arrowstyle="-|>",
                connectionstyle="arc3,rad=0.12",
                node_size=700,
            )

        # Color de nodos según rol en este paso
        firing = {s for s, _ in model.active_messages}
        receiving = {t for _, t in model.active_messages}

        node_colors, node_sizes = [], []
        for n in g.nodes():
            if n in firing:
                node_colors.append("#ffd166")  # amarillo: dispara
                node_sizes.append(100)
            elif n in receiving:
                node_colors.append("#06d6a0")  # verde: recibe
                node_sizes.append(75)
            else:
                node_colors.append("#4a90e2")  # azul: reposo
                node_sizes.append(50)

        nx.draw_networkx_nodes(
            g,
            pos,
            ax=ax,
            node_color=node_colors,
            node_size=node_sizes,
            edgecolors="white",
            linewidths=0.5,
            alpha=0.95,
        )

        # PONER ID DEL NODO
        # nx.draw_networkx_labels(
        #     G, pos, ax=ax,
        #     font_size=10, font_color="white", font_weight="bold",
        # )

        # HUD
        ax.set_title(
            f"Paso {model.current_step}/{sim_time}    "
            f"Mensajes activos: {len(model.active_messages)}    "
            f"Total enviados: {len(model.message_history)}",
            color="white",
            fontsize=13,
            pad=14,
        )

        # Pequeña leyenda
        legend_text = (
            "● amarillo: dispara    "
            "● verde: recibe    "
            "● azul: reposo    "
            f"p_fire = {fire_probability}"
        )
        ax.text(
            0.5,
            -0.04,
            legend_text,
            transform=ax.transAxes,
            ha="center",
            va="top",
            color="#a0a8b8",
            fontsize=10,
        )
        ax.axis("off")
        return (ax,)

    anim = FuncAnimation(
        fig,
        draw_frame,
        frames=sim_time,
        interval=interval_ms,
        repeat=False,
        blit=False,
    )

    if save_gif:
        fps = max(1, 1000 // interval_ms)
        anim.save(gif_path, writer=PillowWriter(fps=fps))
        print(f"[OK] GIF guardado en: {gif_path}")

    if show:
        plt.tight_layout()
        plt.show()
    else:
        plt.close(fig)

    return anim, model


# ============================================================
# CLI
# ============================================================
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Simulación de red de agentes Mesa.")
    p.add_argument("--nodes", type=int, default=12, help="Número de nodos/agentes")
    p.add_argument(
        "--edge-prob",
        type=float,
        default=0.25,
        help="Probabilidad de arista (Erdős–Rényi)",
    )
    p.add_argument(
        "--fire-prob", type=float, default=0.20, help="Probabilidad de disparo por paso"
    )
    p.add_argument(
        "--time", type=int, default=40, help="Duración (pasos) de la simulación"
    )
    p.add_argument(
        "--interval", type=int, default=500, help="Intervalo entre frames en ms"
    )
    p.add_argument("--seed", type=int, default=42, help="Semilla")
    p.add_argument("--no-gif", action="store_true", help="No guardar GIF")
    p.add_argument(
        "--show", action="store_true", help="Mostrar ventana en vivo (en local)"
    )
    p.add_argument(
        "--out", type=str, default="simulation.gif", help="Ruta del GIF de salida"
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    _, sim_model = run_simulation(
        num_nodes=args.nodes,
        edge_prob=args.edge_prob,
        fire_probability=args.fire_prob,
        sim_time=args.time,
        interval_ms=args.interval,
        seed=args.seed,
        save_gif=not args.no_gif,
        gif_path=args.out,
        show=args.show,
    )
    print(f"[OK] Total mensajes disparados: {len(sim_model.message_history)}")
