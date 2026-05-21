"""Configuración centralizada de la simulación.

Edita este fichero para cambiar topología, parámetros de simulación y
opciones de salida sin tocar el código fuente.
"""

GRAPH = {
    "type": "erdos",        # erdos | scale_free | watts | snap | multilayer | hyper
    "num_nodes": 100,
    "edge_prob": 0.25,      # erdos
    "ws_k": 6,              # watts / multilayer
    "ws_rewire_prob": 0.1,  # watts / multilayer
    # scale_free / multilayer  — alpha + beta + gamma debe sumar 1.0
    "sf_alpha": 0.41,
    "sf_beta": 0.54,
    "sf_gamma": 0.05,
    "sf_delta_in": 0.2,
    "sf_delta_out": 0.0,
    "snap_dataset": "ego-Facebook",
}

SIMULATION = {
    "days": 60,
    "steps_per_day": 10,
    "fire_probability": 0.20,
    "seed": 42,
    "interval_ms": 500,
}

OUTPUT = {
    "basename": "simulation",
    "export_csv": True,
    "export_json": True,
    "render_plots": True,
    "render_gif": False,
    "show": False,
}
