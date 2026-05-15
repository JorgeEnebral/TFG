"""
Visualizaciones de la simulación.

Tres clases independientes, todas con estilo "dark":

  - `NetworkAnimator`        : anima el grafo paso a paso (GIF / ventana live).
                               Es la única que avanza la simulación
                               (llama a `model.step()` en cada frame).
  - `DegreeDistributionPlot` : histograma estático de grado del grafo.
                               No depende de la dinámica.
  - `MessageHeatmap`         : matriz origen X destino del nº de mensajes.
                               Depende del DataCollector tras la sim.

Cada visualizador es independiente: NO se obliga a usar todos. Se pueden
añadir más (series temporales, distribución de cascadas, etc.) creando
una clase nueva que herede el estilo `_DarkStyle`.
"""

from __future__ import annotations

# `Counter` es un dict especializado en contar repeticiones.
# Se usa en MessageHeatmap para sumar mensajes por par (src, tgt).
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

# `FuncAnimation` orquesta la animación llamando a una función-frame.
# `PillowWriter` exporta a GIF sin necesidad de ffmpeg.
from matplotlib.animation import FuncAnimation, PillowWriter

# Tipo de los Axes para anotaciones (mejora autocomplete en IDE).
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from src.datacollector import DataCollector
from src.model import NetworkModel


class _DarkStyle:
    """Constantes de color del tema "dark" compartido por los visualizadores.

    Es una clase sin estado (solo atributos de clase). Convención `_xxx`
    -> "uso interno del módulo". Centralizamos colores aquí para tocar
    un único sitio si queremos cambiar la paleta.

    Attributes:
        BG: Fondo (figura y axes), en hex.
        EDGE: Aristas en reposo.
        EDGE_ACTIVE: Aristas con mensaje activo (rosa fluorescente).
        NODE_FIRE: Nodo que dispara este paso (amarillo).
        NODE_RECV: Nodo que recibe (verde).
        NODE_IDLE: Nodo en reposo (azul).
        TEXT: Texto principal.
        SUBTEXT: Texto secundario, ticks, leyendas.
    """

    BG = "#0f1419"
    EDGE = "#2a3142"
    EDGE_ACTIVE = "#ff6b9d"
    NODE_FIRE = "#ffd166"
    NODE_RECV = "#06d6a0"
    NODE_IDLE = "#4a90e2"
    TEXT = "white"
    SUBTEXT = "#a0a8b8"


class NetworkAnimator:
    """Anima el grafo en tiempo real mientras avanza la simulación.

    Es el visualizador más complejo: combina `FuncAnimation` con la
    función `_draw_frame` que (1) avanza un paso del modelo y (2) repinta.

    Attributes:
        model: NetworkModel que se "tickea" en cada frame.
        sim_time: Número de frames totales (= nº de pasos de simulación).
        interval_ms: Milisegundos entre frames (afecta a la velocidad del GIF).
        layout_seed: Semilla del `spring_layout` (posiciones reproducibles).
        figsize: Tamaño de la figura (pulgadas).
        title_suffix: Texto extra para el título (p.ej. "p_fire = 0.2").
        pos: Dict `{node_id: (x, y)}` con las posiciones fijas. Se calcula
            una vez para que los nodos no salten entre frames.
        fig: Figura matplotlib donde se dibuja.
        ax: Axes matplotlib asociado a `fig`.
    """

    def __init__(
        self,
        model: NetworkModel,
        sim_time: int,
        interval_ms: int = 500,
        layout_seed: int | None = None,
        figsize: tuple[float, float] = (10, 8),
        title_suffix: str = "",
    ) -> None:
        """Inicializa el animador y precalcula el layout.

        Args:
            model: NetworkModel que se va a animar.
            sim_time: Número total de pasos (= frames) a generar.
            interval_ms: Milisegundos entre frames.
            layout_seed: Semilla del `spring_layout` para reproducibilidad.
            figsize: Tamaño de la figura en pulgadas.
            title_suffix: Texto extra que se concatena al título.
        """
        self.model = model
        self.sim_time = sim_time
        self.interval_ms = interval_ms
        self.layout_seed = layout_seed
        self.figsize = figsize
        self.title_suffix = title_suffix

        # Layout spring-force precalculado UNA vez. Si se recalculara
        # por frame los nodos saltarían y la animación sería inservible.
        # `k=1.5` regula la separación ideal entre nodos.
        self.pos = nx.spring_layout(model.graph, seed=layout_seed, k=1.5)

        # `plt.subplots()` crea figura + un único Axes.
        self.fig, self.ax = plt.subplots(figsize=figsize)
        # Aplica el fondo oscuro tanto a la figura entera como al área
        # del axes (sin ambos, se ven márgenes blancos).
        self.fig.patch.set_facecolor(_DarkStyle.BG)
        self.ax.set_facecolor(_DarkStyle.BG)

    def _draw_frame(self, _frame: int) -> tuple[Axes]:
        """Avanza la simulación un paso y repinta el frame.

        Es la función que `FuncAnimation` llama una vez por frame.

        Args:
            _frame: Número de frame que pasa matplotlib. No se usa, pero
                la firma es obligatoria.

        Returns:
            Tupla `(ax,)` para cumplir el contrato de `FuncAnimation`
            con blit (aunque aquí `blit=False`).
        """
        ax = self.ax
        ax.clear()
        ax.set_facecolor(_DarkStyle.BG)

        # AVANZAR LA SIMULACIÓN. Aquí es donde se "tickea" el modelo.
        # Llamarlo aquí (y no antes/después) sincroniza simulación con render.
        self.model.step()

        g = self.model.graph

        # Dibujar las aristas de fondo (el grafo "estático").
        # Color tenue para no competir visualmente con los mensajes activos.
        nx.draw_networkx_edges(
            g, self.pos, ax=ax, edge_color=_DarkStyle.EDGE, width=1.0, alpha=0.5
        )

        # Si hay mensajes en este paso, se dibujan como flechas brillantes.
        # Crea un DiGraph efímero con SOLO esos pares para usar el
        # soporte de flechas de NetworkX.
        if self.model.active_messages:
            dg = nx.DiGraph()
            dg.add_nodes_from(g.nodes())
            dg.add_edges_from(self.model.active_messages)
            nx.draw_networkx_edges(
                dg,
                self.pos,
                ax=ax,
                edgelist=list(dg.edges()),
                edge_color=_DarkStyle.EDGE_ACTIVE,
                width=3.0,
                alpha=0.95,
                arrows=True,
                arrowsize=22,
                arrowstyle="-|>",
                # `connectionstyle` curva ligeramente la flecha para que
                # mensajes A->B y B->A no se solapen visualmente.
                connectionstyle="arc3,rad=0.12",
                # `node_size` aquí indica desde DÓNDE empieza la flecha
                # (debe coincidir con el tamaño de nodo para que no se solape).
                node_size=700,
            )

        # Clasificación de nodos por rol en este paso:
        #   - firing: nodos que disparan al menos un mensaje.
        #   - receiving: nodos que reciben al menos un mensaje.
        # Set comprehension para deduplicar y O(1) al consultar pertenencia.
        firing = {s for s, _ in self.model.active_messages}
        receiving = {t for _, t in self.model.active_messages}

        # Listas paralelas (una entrada por nodo, en el mismo orden que `g.nodes()`).
        # NetworkX las consume así para colorear/redimensionar.
        node_colors, node_sizes = [], []
        for n in g.nodes():
            # Prioridad: si dispara Y recibe, se pinta como "fire" (es más
            # informativo verlo como activo). Por eso `firing` se evalúa primero.
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
            g,
            self.pos,
            ax=ax,
            node_color=node_colors,
            node_size=node_sizes,
            edgecolors="white",
            linewidths=0.5,
            alpha=0.95,
        )

        # HUD: título con info de progreso. `len(self.model.data_collector)`
        # acumula el total de mensajes lanzados desde el inicio.
        ax.set_title(
            f"Paso {self.model.current_step}/{self.sim_time}    "
            f"Mensajes activos: {len(self.model.active_messages)}    "
            f"Total enviados: {len(self.model.data_collector)}"
            + (f"    {self.title_suffix}" if self.title_suffix else ""),
            color=_DarkStyle.TEXT,
            fontsize=13,
            pad=14,
        )
        # Leyenda inferior. `transform=ax.transAxes` -> coords relativas (0..1).
        ax.text(
            0.5,
            -0.04,
            "● amarillo: dispara    ● verde: recibe    ● azul: reposo",
            transform=ax.transAxes,
            ha="center",
            va="top",
            color=_DarkStyle.SUBTEXT,
            fontsize=10,
        )
        ax.axis("off")  # quitar ejes/ticks (no aportan en grafos).
        return (ax,)

    def animate(self) -> FuncAnimation:
        """Crea el objeto `FuncAnimation` que orquesta la animación.

        NO la dispara por sí solo; hay que llamar a `save_gif()` o
        `show()` (o asignar el resultado a una variable viva; si se
        descarta, Python lo recolectaría y la animación se congelaría).

        Returns:
            Un `FuncAnimation` configurado con `_draw_frame` como callback.
        """
        return FuncAnimation(
            self.fig,
            self._draw_frame,
            frames=self.sim_time,
            interval=self.interval_ms,
            repeat=False,
            # blit=False: redibuja todo cada frame. Más simple y robusto
            # que blit=True (que requiere devolver SOLO los artists modificados).
            blit=False,
        )

    def save_gif(self, path: str | Path) -> Path:
        """Renderiza la animación a un GIF con `PillowWriter`.

        Args:
            path: Ruta del GIF de salida. Las carpetas padre se crean
                si no existen.

        Returns:
            La ruta efectivamente escrita, como `Path`.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        anim = self.animate()
        # FPS = frames por segundo. Calculado a partir de `interval_ms`
        # para que la velocidad del GIF coincida con la "live".
        # `max(1, ...)` evita 0 fps si el intervalo es muy alto.
        fps = max(1, 1000 // self.interval_ms)
        anim.save(str(path), writer=PillowWriter(fps=fps))
        return path

    def show(self) -> None:
        """Muestra la animación en una ventana matplotlib.

        Requiere un display gráfico disponible.
        """
        # OJO: hay que mantener viva la referencia al FuncAnimation en una
        # variable local; si se perdiera, Python la recolectaría y la
        # animación se "congelaría". `plt.show()` mantiene el event loop.
        self.animate()
        plt.tight_layout()
        plt.show()

    def close(self) -> None:
        """Libera los recursos de la figura matplotlib asociada."""
        plt.close(self.fig)


class DegreeDistributionPlot:
    """Histograma del grado de los nodos.

    Solo depende de la topología (no de la dinámica). Útil para
    caracterizar la red: detectar power-laws (BA), bell-curves (ER), etc.

    Attributes:
        graph: Grafo a analizar.
    """

    def __init__(self, graph: nx.Graph) -> None:
        """Inicializa el plot.

        Args:
            graph: Grafo de NetworkX cuyo grado se va a representar.
        """
        self.graph = graph

    def render(self, path: str | Path | None = None) -> Figure:
        """Genera el histograma de grado.

        Args:
            path: Ruta donde guardar la figura. Si es None, no se persiste.

        Returns:
            La figura `matplotlib.figure.Figure` generada.
        """
        # `g.degree()` devuelve un iterable de `(nodo, grado)`. Solo
        # interesa el grado: lista por comprensión `d for _, d`.
        degrees = [d for _, d in self.graph.degree()]

        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor(_DarkStyle.BG)
        ax.set_facecolor(_DarkStyle.BG)

        # Histograma con 20 bins. Para datasets con cola larga (BA real)
        # convendría escala log; se deja lineal por simplicidad.
        ax.hist(degrees, bins=20, color=_DarkStyle.NODE_RECV, edgecolor="white")
        ax.set_xlabel("Grado", color=_DarkStyle.TEXT)
        ax.set_ylabel("Frecuencia", color=_DarkStyle.TEXT)
        ax.set_title("Distribución de grado", color=_DarkStyle.TEXT)
        ax.tick_params(colors=_DarkStyle.SUBTEXT)
        # Pintar también los bordes del axes (spines) en color suave.
        for spine in ax.spines.values():
            spine.set_color(_DarkStyle.SUBTEXT)

        # Si se pasa ruta, se guarda. Si no, devuelve la figura para
        # que el caller decida (mostrarla, embebida en notebook, etc.).
        if path is not None:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            # `facecolor=fig.get_facecolor()` -> respeta el fondo dark al guardar.
            fig.savefig(path, facecolor=fig.get_facecolor())
        return fig


class MessageHeatmap:
    """Heatmap de número de mensajes por par (origen, destino).

    Mapa cuadrado N×N donde N = nº de nodos; cada celda (i, j) es el
    número total de mensajes de i -> j. Útil para detectar "canales
    privilegiados" o asimetrías.

    Attributes:
        data_collector: DataCollector con las trazas.
        num_nodes: Tamaño del lado del heatmap.
    """

    def __init__(self, data_collector: DataCollector, num_nodes: int) -> None:
        """Inicializa el heatmap.

        Args:
            data_collector: DataCollector con las trazas a visualizar.
            num_nodes: Número de nodos del grafo (lado de la matriz).
        """
        self.data_collector = data_collector
        self.num_nodes = num_nodes

    def render(self, path: str | Path | None = None) -> Figure:
        """Genera el heatmap de mensajes por par (origen, destino).

        Args:
            path: Ruta donde guardar la figura. Si es None, no se persiste.

        Returns:
            La figura `matplotlib.figure.Figure` generada.
        """
        # Counter cuenta repeticiones de claves automáticamente.
        # Más legible que un dict manual con `+= 1`.
        counter: Counter[tuple[int, int]] = Counter(
            (tr.source_node, tr.target_node) for tr in self.data_collector.interactions
        )

        # Matriz N×N inicializada a 0. Lista de listas en lugar de numpy
        # para no añadir dependencia (matplotlib acepta listas anidadas).
        matrix = [[0] * self.num_nodes for _ in range(self.num_nodes)]
        for (s, t), c in counter.items():
            # Salvaguarda: en grafos SNAP los node_ids no son contiguos
            # ni empiezan en 0. Si superan `num_nodes`, se ignoran
            # silenciosamente para no salirnos de la matriz.
            if s < self.num_nodes and t < self.num_nodes:
                matrix[s][t] = c

        fig, ax = plt.subplots(figsize=(8, 7))
        fig.patch.set_facecolor(_DarkStyle.BG)
        ax.set_facecolor(_DarkStyle.BG)
        # `imshow` pinta la matriz como imagen. `cmap="magma"` casa con
        # el tema dark. `aspect="auto"` la deforma para llenar el axes.
        im = ax.imshow(matrix, cmap="magma", aspect="auto")
        ax.set_xlabel("Destino", color=_DarkStyle.TEXT)
        ax.set_ylabel("Origen", color=_DarkStyle.TEXT)
        ax.set_title("Mensajes por par (origen, destino)", color=_DarkStyle.TEXT)
        ax.tick_params(colors=_DarkStyle.SUBTEXT)

        # Colorbar para que la escala de colores tenga referencia numérica.
        cbar = fig.colorbar(im, ax=ax)
        cbar.ax.tick_params(colors=_DarkStyle.SUBTEXT)

        if path is not None:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(path, facecolor=fig.get_facecolor())
        return fig
