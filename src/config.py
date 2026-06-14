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

    days: int = 3
    steps_per_day: int = 15
    seed: int = 42
    interval_ms: int = 500


@dataclass
class NarrativeConfig:
    """Parámetros de la narrativa-operación inyectada (solo ``resistant``).

    Modela la adopción por umbral (Linear Threshold) y la inyección de
    semilla. Ver ``AI_plans/resistencia_cognitiva.md``.

    El umbral de resistencia θ se muestrea de una mezcla **bimodal**: dos
    subpoblaciones (susceptibles de θ bajo y resistentes de θ alto), más
    realista que una unimodal (Granovetter 1978; Watts 2002).

    Attributes:
        enabled: Si se inyecta la narrativa al inicio de la simulación.
        k_seeds: Número de nodos semilla que lanzan la narrativa en t=0.
        seed_strategy: ``"hubs"`` (mayor nº de seguidores) o ``"random"``.
        seed_fanout: Fracción de seguidores a los que cada semilla envía en
            t=0 (un subconjunto, no toda la audiencia de golpe).
        veracity: Veracidad de la narrativa (baja = desinfo). Debe ser
            <= ``narrative_veracity_threshold`` para que cuente. Es solo
            la etiqueta de la campaña; no modula la persuasión.
        narrative_veracity_threshold: Umbral de veracidad para clasificar
            un mensaje como narrativa.
        emotional_load: Carga emocional de la narrativa en [0, 1]. Es el
            único driver de persuasión que aporta el mensaje.
        gamma: Ganancia de persuasión por exposición en [0, 1].
        susceptible_fraction: Fracción de agentes en el modo susceptible.
        theta_susceptible_mu: Media de θ de los susceptibles.
        theta_resistant_mu: Media de θ de los resistentes.
        theta_sigma: Desviación típica de cada modo.
        forward_probability: Prob. de reenvío de la narrativa si adoptado.
    """

    enabled: bool = True
    k_seeds: int = 1
    seed_strategy: Literal["hubs", "random"] = "hubs"
    seed_fanout: float = 0.4
    veracity: float = 0.1
    narrative_veracity_threshold: float = 0.30
    emotional_load: float = 0.6
    gamma: float = 0.50
    susceptible_fraction: float = 0.50
    theta_susceptible_mu: float = 0.25
    theta_resistant_mu: float = 0.75
    theta_sigma: float = 0.10
    forward_probability: float = 0.1


@dataclass
class AgentConfig:
    """Configuración del tipo y comportamiento de los agentes.

    Attributes:
        type: Clase de agente a instanciar.
        fire_probability: Probabilidad de disparo por paso (stochastic y
            resistant; en resistant es el ruido neutro ambiental).
        max_targets: Número máximo de destinatarios por emisión en capa analógica.
        narrative: Parámetros de la narrativa (sólo si ``type == "resistant"``).
    """

    type: Literal["stochastic", "resistant"] = "resistant"
    fire_probability: float = 0.2
    trace_continue_probability: float = 0.50
    max_targets: int = 5
    narrative: NarrativeConfig = field(default_factory=NarrativeConfig)


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
    export_format: Literal["csv", "json", "none"] = "json"
    save_graph: bool = True
    render_plots: bool = False
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
    num_nodes: int = 30
    edge_prob: float = 0.1
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
    num_nodes: int = 5_000
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
    num_nodes: int = 5_000
    k: int = 10
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
GRAPH: GraphConfig = ScaleFreeConfig()
AGENT: AgentConfig = AgentConfig()
OUTPUT: OutputConfig = OutputConfig()