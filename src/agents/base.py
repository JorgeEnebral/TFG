"""
Clase base para todos los agentes de la simulación.

Todo agente concreto debe heredar de `BaseAgent`. Así garantizamos:
  1. Que todos los agentes están registrados en el modelo Mesa.
  2. Que todos tienen un atributo `node_id` que los conecta con el grafo.
  3. Que todos exponen un método `step()` aunque sea distinto en cada subclase.
"""

# Todas las anotaciones de tipo se evalúan como strings en tiempo de ejecución.
# Esto permite usar el nombre `NetworkModel` en la firma sin tener
# que importarlo realmente al cargar el módulo (evita un import circular)
from __future__ import annotations

# `TYPE_CHECKING` es una constante que vale True solo cuando un mypy
# está analizando el código, y False en ejecución normal.
# Se usa para importar `NetworkModel` exclusivamente para anotaciones
from typing import TYPE_CHECKING

import mesa

if TYPE_CHECKING:
    # Solo se ejecuta en análisis estático -> no hay import real en runtime.
    from src.model import NetworkModel


class BaseAgent(mesa.Agent):  # type: ignore
    """Agente abstracto.

    No implementa comportamiento: solo guarda el `node_id` y delega
    `step()` en las subclases.

    Attributes:
        node_id: Id del nodo del grafo donde "vive" este agente.
        model: Heredado de `mesa.Agent`. Referencia al modelo padre.
        unique_id: Heredado de `mesa.Agent`. Id autoincremental único.
    """

    def __init__(self, model: NetworkModel, node_id: int) -> None:
        """Inicializa el agente y lo registra en el modelo.

        Args:
            model: NetworkModel donde se registra el agente vía
                `mesa.Agent.__init__`.
            node_id: Id del nodo del grafo en el que vive este agente.
        """
        # `super().__init__(model)` dispara `mesa.Agent.__init__`, que:
        #   1) Asigna `self.model = model`.
        #   2) Asigna un `unique_id` autoincremental.
        #   3) Registra al agente en `model.agents` (AgentSet de Mesa).
        # Sin esta llamada el agente NO se ejecutaría en `model.agents.shuffle_do("step")`.
        super().__init__(model)

        # Guarda la posición del agente en el grafo
        self.node_id = node_id

    def step(self) -> None:  # pragma: no cover - método abstracto
        """Lógica que se ejecuta una vez por agente y por paso de simulación.

        Método abstracto: debe ser implementado por cada subclase concreta.

        Raises:
            NotImplementedError: Siempre, si se llama directamente sobre
                `BaseAgent` sin que una subclase lo haya sobreescrito.
        """
        # Lanzar `NotImplementedError` deja claro que `BaseAgent` no se debe instanciar directamente
        # `# pragma: no cover` le dice al medidor de cobertura que ignore esta línea
        raise NotImplementedError(
            "Las subclases de BaseAgent deben implementar `step()`."
        )
