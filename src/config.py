"""
Configuración centralizada de la simulación.

Edita este fichero para cambiar topología, parámetros de simulación y
opciones de salida sin tocar el código fuente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union


@dataclass
class SimulationConfig:
    """Parámetros temporales y de semilla de la simulación.

    Attributes:
        days: Número de días a simular.
        steps_per_day: Pasos de mesa por día.
        seed: Semilla del RNG global.
        interval_ms: Milisegundos entre frames en la animación.
    """

    days: int = 60
    steps_per_day: int = 24
    seed: int = 42
    interval_ms: int = 500


@dataclass
class BrainConfig:
    """Hiperparámetros del ``EmotionalBrain`` (ver agente_inteligente.md).

    Todos los defaults provienen de literatura empírica. Edita aquí para
    barrer experimentos. ``None`` en cualquier campo significa "usa el
    default del propio ``BrainHyperparams``".

    Attributes:
        p_create_analog: HY-1. Prob. horaria de emitir mensaje analógico.
        p_create_digital_base: HY-2. Prob. base digital antes del escalado.
        k_follower: HY-2. Denominador del término log(1+followers).
        theta_send: HY-7. Umbral vectorial de emisión.
        forward_base: HY-8. Probabilidad base de reenvío.
        forward_boost_anger: HY-8. Bonus a p_forward por dim anger.
        forward_boost_surprise: HY-8. Bonus a p_forward por dim surprise.
        attention_capacity: HY-10. Mensajes/step antes de atenuar atención.
        self_confidence_floor: HY-11. Piso de la escala (0.5 ⇒ rango 0.5×–1.5×).
        genetics_mu: HY-5. Media de la TruncNormal de genética.
        genetics_sigma: HY-5. Desviación típica.
    """

    p_create_analog: float = 0.05
    p_create_digital_base: float = 0.02
    k_follower: float = 5.0
    theta_send: float = 0.35
    forward_base: float = 0.08
    forward_boost_anger: float = 0.20
    forward_boost_surprise: float = 0.10
    attention_capacity: int = 7
    self_confidence_floor: float = 0.5
    genetics_mu: float = 0.5
    genetics_sigma: float = 0.15


@dataclass
class AgentConfig:
    """Configuración del tipo y comportamiento de los agentes.

    Attributes:
        type: Clase de agente a instanciar.
        fire_probability: Probabilidad de disparo por paso (solo stochastic).
        brain: Hiperparámetros del cerebro (sólo si ``type == "bayesian"``).
    """

    type: Literal["stochastic", "bayesian"] = "stochastic"
    fire_probability: float = 0.20
    brain: BrainConfig = field(default_factory=BrainConfig)


@dataclass
class OutputConfig:
    """Opciones de exportación y visualización.

    Attributes:
        basename: Prefijo de los ficheros de salida.
        export_format: Formato de exportación de trazas: ``"csv"``, ``"json"`` o ``"none"``.
        save_graph: Guardar la estructura del grafo (nodos + aristas) en JSON.
        render_plots: Generar análisis estático del grafo (imágenes + metrics.json).
        render_gif: Generar GIF de replay post-simulación.
    """

    basename: str = "simulation"
    export_format: Literal["csv", "json", "none"] = "csv"
    save_graph: bool = True
    render_plots: bool = True
    render_gif: bool = False


# ---------------------------------------------------------------------------
# Configuraciones de grafo — una clase por topología
# ---------------------------------------------------------------------------

@dataclass
class ErdosConfig:
    """Grafo Erdős Rényi G(n, p).

    Attributes:
        num_nodes: Número de nodos.
        edge_prob: Probabilidad de cada arista.
        directed: Si True genera DiGraph.
        layer: Capa asignada a todas las aristas.
    """

    type: Literal["erdos"] = field(default="erdos", init=False)
    num_nodes: int = 10_000
    edge_prob: float = 0.25
    directed: bool = False
    layer: Literal["analog", "digital"] = "analog"


@dataclass
class ScaleFreeConfig:
    """Grafo libre de escala.

    Attributes:
        num_nodes: Número de nodos.
        alpha: Prob. de añadir arista desde nodo nuevo.
        beta: Prob. de añadir arista entre nodos existentes.
        gamma: Prob. de añadir arista hacia nodo nuevo.
        delta_in: Sesgo de preferencia de entrada.
        delta_out: Sesgo de preferencia de salida.
        layer: Capa asignada a todas las aristas (default digital, acorde a su naturaleza dirigida).
    """

    type: Literal["scale_free"] = field(default="scale_free", init=False)
    num_nodes: int = 10_000
    alpha: float = 0.41
    beta: float = 0.54
    gamma: float = 0.05
    delta_in: float = 0.2
    delta_out: float = 0.0
    layer: Literal["analog", "digital"] = "digital"


@dataclass
class WattsConfig:
    """Grafo pequeño mundo de Watts Strogatz.

    Attributes:
        num_nodes: Número de nodos.
        k: Cada nodo conectado a sus k vecinos más cercanos.
        rewire_prob: Probabilidad de reconectar cada arista.
        directed: Si True aplica orientación proporcional al grado.
        layer: Capa asignada a todas las aristas.
    """

    type: Literal["watts"] = field(default="watts", init=False)
    num_nodes: int = 10_000
    k: int = 6
    rewire_prob: float = 0.1
    directed: bool = False
    layer: Literal["analog", "digital"] = "analog"


@dataclass
class SNAPConfig:
    """Dataset real del repositorio SNAP de Stanford.

    Attributes:
        dataset_name: Clave del catálogo SNAP (p.ej. "ego-Facebook").
        cache_dir: Carpeta local donde se cachea el dataset.
        directed: Si True fuerza grafo dirigido (convirtiendo si es necesario).
        layer: Capa asignada a todas las aristas.
    """

    type: Literal["snap"] = field(default="snap", init=False)
    dataset_name: str = "ego-Facebook"
    cache_dir: str = "./data/snap"
    directed: bool = False
    layer: Literal["analog", "digital"] = "digital"


@dataclass
class MultiLayerConfig:
    """Grafo bicapa con capa analógica (WS) y capa digital (ScaleFree o SNAP).

    La capa digital tiene prioridad: sus aristas no se duplican en la analógica.
    La capa analógica (WS) siempre se crea con el mismo nº de nodos que la digital.
    Si `digital` es `SNAPConfig`, la dirección se fuerza a True automáticamente.

    Uso con ScaleFree (por defecto):
        GRAPH = MultiLayerConfig()

    Uso con SNAP como capa digital:
        GRAPH = MultiLayerConfig(
            analog=WattsConfig(k=6, rewire_prob=0.1),         # num_nodes ignorado: lo fija SNAP
            digital=SNAPConfig(dataset_name="ego-Twitter"),   # dirigido se fuerza a True
        )

    Attributes:
        analog: Configuración de la capa analógica (Watts-Strogatz).
        digital: Configuración de la capa digital (ScaleFree o SNAP).
    """

    type: Literal["multilayer"] = field(default="multilayer", init=False)
    analog: WattsConfig = field(default_factory=WattsConfig)
    digital: Union[ScaleFreeConfig, SNAPConfig] = field(default_factory=ScaleFreeConfig)


GraphConfig = Union[ErdosConfig, ScaleFreeConfig, WattsConfig, SNAPConfig, MultiLayerConfig]

# ---------------------------------------------------------------------------
# Instancias — edita aquí para cambiar la configuración activa
# ---------------------------------------------------------------------------

SIMULATION: SimulationConfig = SimulationConfig()
GRAPH: GraphConfig = ErdosConfig()
AGENT: AgentConfig = AgentConfig()
OUTPUT: OutputConfig = OutputConfig()
