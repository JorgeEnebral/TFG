"""Scoring de Superioridad Cognitiva (CSS).

Derivado del paper Fuentes/Papers/2603.05222v1.pdf.
CSS(i, j) = Σ_{a ∈ acciones(j)} Δdecision_j(a) · w_role(j) · trust(i→j)
            solo sobre acciones cuyo caused_by contiene mensajes de i.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

ROLE_WEIGHT: dict[str, float] = {
    "defender": 2.0,
    "influencer": 1.5,
    "civilian": 1.0,
    "adversary": 1.0,
}


@dataclass
class DecisionEvent:
    """Cambio de creencia en un agente causado por mensajes recibidos.

    Attributes:
        timestep: Paso de simulación en el que ocurre el cambio.
        agent_id: Agente cuya creencia cambia.
        topic: Tópico sobre el que cambia la creencia.
        prev_value: Valor de creencia antes del cambio.
        new_value: Valor de creencia después del cambio.
        caused_by: IDs de los mensajes que motivaron el cambio.
    """

    timestep: int
    agent_id: int
    topic: str
    prev_value: float
    new_value: float
    caused_by: list[int]


def compute_css(
    decision_events: list[DecisionEvent],
    agent_roles: dict[int, str],
    trust_matrix: dict[tuple[int, int], float],
    sender_messages: dict[int, list[int]],  # agent_id -> list[message_id]
) -> dict[int, float]:
    """Calcula CSS agregado por agente emisor.

    Args:
        decision_events: Lista de cambios de decisión registrados.
        agent_roles: Mapa agent_id -> role.
        trust_matrix: Mapa (sender, receiver) -> trust ∈ [0,1].
        sender_messages: Mapa agent_id -> [message_ids emitidos].

    Returns:
        Mapa agent_id -> CSS total.
    """
    # Índice inverso: message_id -> sender
    msg_to_sender: dict[int, int] = {}
    for sender, msgs in sender_messages.items():
        for mid in msgs:
            msg_to_sender[mid] = sender

    css: dict[int, float] = defaultdict(float)

    for event in decision_events:
        j = event.agent_id
        delta = abs(event.new_value - event.prev_value)
        w_role = ROLE_WEIGHT.get(agent_roles.get(j, "civilian"), 1.0)

        senders_involved: set[int] = set()
        for mid in event.caused_by:
            if mid in msg_to_sender:
                senders_involved.add(msg_to_sender[mid])

        for i in senders_involved:
            trust = trust_matrix.get((i, j), 0.5)
            css[i] += delta * w_role * trust

    return dict(css)


def css_attacker(
    css_pairs: dict[tuple[int, int], float],
    agent_roles: dict[int, str],
) -> dict[int, float]:
    """Calcula el CSS ofensivo de cada agente emisor sobre defensores.

    Args:
        css_pairs: Mapa ``{(emisor, receptor): css}`` par a par.
        agent_roles: Mapa ``agent_id -> role``.

    Returns:
        Mapa ``agent_id -> CSS_attacker`` sumado sobre receptores defensores.
    """
    result: dict[int, float] = defaultdict(float)
    for (i, j), val in css_pairs.items():
        if agent_roles.get(j) == "defender":
            result[i] += val
    return dict(result)


def css_defender_resilience(
    decision_events: list[DecisionEvent],
    agent_roles: dict[int, str],
    sender_messages: dict[int, list[int]],
    adversary_ids: set[int],
) -> dict[int, float]:
    """Calcula la resiliencia cognitiva de cada agente defensor.

    La resiliencia es ``1 - (cambios causados por adversarios / total cambios)``.

    Args:
        decision_events: Lista de cambios de decisión registrados.
        agent_roles: Mapa ``agent_id -> role``.
        sender_messages: Mapa ``agent_id -> [message_ids emitidos]``.
        adversary_ids: Conjunto de IDs de agentes adversarios.

    Returns:
        Mapa ``agent_id -> resiliencia`` para cada defensor con al menos
        un cambio registrado.
    """
    total: dict[int, int] = defaultdict(int)
    adv_caused: dict[int, int] = defaultdict(int)

    msg_to_sender: dict[int, int] = {}
    for sender, msgs in sender_messages.items():
        for mid in msgs:
            msg_to_sender[mid] = sender

    for event in decision_events:
        j = event.agent_id
        if agent_roles.get(j) != "defender":
            continue
        total[j] += 1
        if any(msg_to_sender.get(mid) in adversary_ids for mid in event.caused_by):
            adv_caused[j] += 1

    return {
        j: 1.0 - adv_caused[j] / total[j]
        for j in total
        if total[j] > 0
    }
