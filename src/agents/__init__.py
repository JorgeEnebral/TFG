"""
Paquete `agents`
================

Contiene todos los tipos de agentes que pueden poblar la simulación.

Cada agente vive en un nodo del grafo y, en cada paso de simulación,
ejecuta su método `step()` (definido por la subclase concreta).

- `BaseAgent`    : clase abstracta común. Aporta el `node_id` y la
                   integración con Mesa, pero no define comportamiento.
- `StochasticAgent` : agente más simple. Con probabilidad `fire_probability`
                   dispara un mensaje a un vecino aleatorio.
"""

# Reexportamos las clases en el __init__ para poder hacer:
#   from src.agents import StochasticAgent y no from src.agents.message import StochasticAgent
from src.agents.base import BaseAgent
from src.agents.stochastic import StochasticAgent

# `__all__` controla qué se exporta cuando se hace `from src.agents import *`.
__all__ = ["BaseAgent", "StochasticAgent"]
