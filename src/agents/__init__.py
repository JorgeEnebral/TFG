"""
Paquete `agents`
================

Contiene todos los tipos de agentes que pueden poblar la simulación.

Cada agente vive en un nodo del grafo y, en cada paso de simulación,
ejecuta su método `step()` (definido por la subclase concreta).

- `BaseAgent`      : clase abstracta común. Aporta el `node_id` y la
                     integración con Mesa, pero no define comportamiento.
- `StochasticAgent`: agente simple. Con probabilidad `fire_probability`
                     dispara un mensaje a un vecino aleatorio.
- `BayesianAgent`  : agente con bucle OODA; delega las decisiones en un
                     cerebro inyectado (``Brain``).
- `EmotionalBrain` : implementación de ``Brain`` puramente emocional;
                     mantiene humor con decay y decide sin tópicos.
"""

from src.agents.base import BaseAgent
from src.agents.bayesian import BayesianAgent
from src.agents.brain import EmotionalBrain
from src.agents.stochastic import StochasticAgent

__all__ = ["BaseAgent", "BayesianAgent", "EmotionalBrain", "StochasticAgent"]
