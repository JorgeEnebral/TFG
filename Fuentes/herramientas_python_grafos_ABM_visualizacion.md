# Análisis Exhaustivo: Herramientas Python para Grafos, Modelos Basados en Agentes (ABM) y Visualización de Redes

## Contexto y Enfoque

Este análisis está orientado a tu TFG sobre guerra cognitiva, donde necesitas modelar:
- **Redes sociales complejas** (grafos de relaciones)
- **Agentes con procesos cognitivos** (sesgos, creencias, toma de decisiones)
- **Múltiples tipos de relaciones simultáneas** (confianza, flujos de información, afinidad ideológica)
- **Visualización dinámica** de cómo se propagan narrativas y creencias

Empiezo respondiendo tus preguntas conceptuales (son las más importantes y definen qué herramientas elegir), y luego profundizo en cada familia de librerías.

---

## 1. Respuestas Directas a tus Preguntas Conceptuales

### 1.1 ¿Se puede meter un "cerebro" a un agente que procese información de una manera determinada?

**Sí, absolutamente.** Esto es precisamente lo que define un agente cognitivo (cognitive agent) frente a un agente reactivo simple. Hay tres niveles crecientes de sofisticación:

**Nivel 1 — Agente con reglas cognitivas explícitas (clásico).** Cada agente tiene atributos (creencias, nivel de confianza, sesgos) y una función `step()` que procesa la información del entorno según reglas. Por ejemplo, un agente puede tener:
- Un sesgo de confirmación (peso mayor a información que confirma creencia previa)
- Un umbral de credibilidad (ignora mensajes por debajo)
- Una memoria con decaimiento temporal
- Un nivel de susceptibilidad a presión social (conformidad)

Esto se implementa directamente en Mesa o AgentPy como atributos del agente y una lógica dentro del método `step()`. Es el enfoque dominante en ABM social clásica (Schelling, Axelrod, Epstein).

**Nivel 2 — Arquitecturas cognitivas formales.** Modelos BDI (Belief-Desire-Intention), ACT-R, SOAR, CLARION, donde el "cerebro" tiene módulos explícitos: memoria de trabajo, memoria a largo plazo, sistema de atención, sistema de decisión. Existen implementaciones Python como `PyACT-R`, `pyClarion`, y frameworks BDI como `SPADE-BDI`. Útil si quieres modelar la arquitectura cognitiva con fidelidad psicológica.

**Nivel 3 — Agentes con LLM como "cerebro" (estado del arte 2025-2026).** La línea más caliente de investigación actual. Cada agente tiene acceso a un LLM (GPT-4, Claude, LLaMA) que le permite:
- Interpretar mensajes textuales con contexto
- Tener "personalidad" (rasgos del Big Five, ideología, etc.) vía prompt
- Razonamiento en cadena (Chain-of-Thought)
- Memoria episódica (qué mensajes vio, cómo reaccionó)
- Memoria semántica (conocimientos generales via RAG)

El paper de referencia es **Mesa 3** (ter Hoeven et al., 2025, JOSS), que documenta el framework, y **MESA-LLM** es una línea activa de desarrollo (Google Summer of Code 2025). El framework más avanzado para este paradigma es **Shachi** (Kuroki et al., 2025), que estandariza la arquitectura de agentes LLM para ABM reproducible.

Para guerra cognitiva, el Nivel 1 suele ser suficiente y más reproducible; el Nivel 3 es potentísimo pero introduce no-determinismo y costes computacionales altos.

### 1.2 ¿Cada nodo del grafo puede ser un agente, y las aristas pueden ser relaciones de confianza?

**Sí, y es el patrón arquitectónico estándar en ABM de redes sociales.** Tanto Mesa como AgentPy tienen soporte nativo para esto mediante una clase `NetworkGrid` (Mesa) o `Network` (AgentPy) que acepta un grafo NetworkX como sustrato.

Arquitectónicamente funciona así:
- Creas un grafo NetworkX (puede ser scale-free, small-world, Erdős-Rényi, o uno que cargues desde datos reales)
- Cada nodo es una "celda" que puede contener uno o varios agentes
- Los agentes pueden consultar sus vecinos vía `model.grid.get_neighbors(agent_pos)`
- Las aristas pueden tener atributos: `G.add_edge(A, B, trust=0.8, ideology_distance=0.2, weight=1.0)`

Esto permite exactamente lo que buscas para guerra cognitiva: nodos = personas/instituciones/medios; aristas = lazos de confianza, seguimiento, influencia. Cuando una narrativa se propaga, cada agente decide si la acepta y retransmite según su propio "cerebro" y la confianza que tiene en quien se la pasó.

### 1.3 ¿Puede haber dos (o más) dimensiones de relaciones distintas simultáneamente entre los mismos dos agentes?

**Sí, y hay tres arquitecturas diferentes para modelarlo, cada una con trade-offs:**

**Opción A — MultiGraph de NetworkX.** Permite múltiples aristas paralelas entre los mismos dos nodos, cada una con sus atributos. Es la opción más simple:
```python
G = nx.MultiGraph()
G.add_edge("Alice", "Bob", relation="trust", weight=0.8)
G.add_edge("Alice", "Bob", relation="ideology", weight=0.3)
G.add_edge("Alice", "Bob", relation="frequency", weight=0.9)
```
Ventaja: trivial de implementar. Desventaja: los algoritmos de NetworkX tratan todas las aristas por igual, así que tienes que filtrar manualmente por `relation` en cada análisis.

**Opción B — Un grafo por tipo de relación, coordinados sobre el mismo conjunto de nodos.** Creas `G_confianza`, `G_ideología`, `G_contacto`, todos con los mismos nodos pero diferentes aristas. Ventaja: cada capa es un grafo limpio donde puedes aplicar algoritmos estándar (PageRank en la capa de confianza, detección de comunidades en la capa ideológica). Desventaja: no captura interacciones entre capas explícitamente.

**Opción C — Red multicapa (multilayer network), que es la formalización matemática rigurosa.** Aquí entra la teoría de Mikko Kivelä et al. (2014, "Multilayer networks", *Journal of Complex Networks*), que es el artículo canónico. En Python tienes dos librerías:
- **pymnet** — la más completa, implementa el formalismo tensorial de Kivelä directamente. Soporta "aspectos" múltiples (puedes tener simultáneamente capas por tipo de relación Y capas temporales).
- **multinetx** — más simple, construida sobre NetworkX. Buena si ya conoces NetworkX.

En una red multicapa formal, un "nodo-capa" es el par (nodo, capa), y las aristas pueden ser intra-capa (mismo tipo de relación) o inter-capa (diferentes tipos). Esto permite preguntas como: "¿una ruptura de confianza entre A y B afecta su interacción ideológica?" mediante acoplamientos entre capas.

**Para guerra cognitiva, mi recomendación es la Opción C con pymnet**, porque es exactamente el formalismo que la literatura académica utiliza para modelar ecosistemas informacionales con múltiples vectores simultáneos (confianza institucional, flujos noticiosos, afinidad tribal).

---

## 2. Librerías de Grafos en Python

### 2.1 NetworkX

**Qué es.** La librería pura-Python estándar de facto. Creada en Los Alamos National Laboratory (2008), mantenida por una comunidad amplia. Versión actual 3.x.

**Ventajas.**
- API intuitiva, Pythónica y extraordinariamente bien documentada
- Catálogo gigantesco de algoritmos: centralidades, detección de comunidades (Louvain, Girvan-Newman, Label Propagation), flujos, caminos mínimos, generadores de grafos aleatorios (Erdős-Rényi, Barabási-Albert, Watts-Strogatz), análisis de clustering, asortatividad, K-core
- Soporta dirigidos, no dirigidos, ponderados, multigrafos (múltiples aristas entre mismos nodos)
- Atributos arbitrarios en nodos y aristas (ideal para modelar agentes con propiedades)
- Integración nativa con Mesa, AgentPy, Pandas, NumPy, SciPy
- Curva de aprendizaje suave

**Desventajas.**
- **Rendimiento pobre en grafos grandes.** Benchmarks consistentes muestran que es 10 a 250 veces más lento que graph-tool en los mismos algoritmos. Para grafos con más de ~100.000 nodos se vuelve impráctico.
- Uso de memoria alto (dict-of-dicts en Python puro)
- Sin paralelismo nativo

**Cuándo usarla.** Prototipado, grafos medianos (hasta ~50.000 nodos), educación, cualquier proyecto donde la simplicidad supera a la velocidad. Para un TFG sobre guerra cognitiva donde vas a simular poblaciones de 1.000-10.000 agentes, NetworkX sobra.

**Bibliografía clave.**
- Hagberg, A. A., Schult, D. A., & Swart, P. J. (2008). "Exploring network structure, dynamics, and function using NetworkX". *Proceedings of the 7th Python in Science Conference (SciPy)*, 11-15.
- Documentación oficial: https://networkx.org/

### 2.2 igraph (python-igraph)

**Qué es.** Biblioteca con núcleo en C y bindings para Python, R y Mathematica. Creada por Gábor Csárdi y Tamás Nepusz.

**Ventajas.**
- Entre 10 y 100 veces más rápida que NetworkX en la mayoría de algoritmos
- Uso de memoria eficiente (estructuras en C)
- Algoritmos de detección de comunidades muy completos (Infomap, Leiden, Walktrap, etc.)
- Bindings cross-language (si colaboras con alguien que usa R)
- Algoritmos de Dijkstra, PageRank, betweenness extremadamente rápidos

**Desventajas.**
- API menos Pythónica (traducción directa de C)
- Documentación a veces seca o poco ejemplificada en español
- Los nodos se indexan por enteros internos, no por nombres (hay que mapear)
- Menos integración fluida con el ecosistema scipy/pandas

**Cuándo usarla.** Cuando tu grafo supera los 50.000 nodos o cuando necesitas ejecutar el análisis muchas veces (experimentos con múltiples semillas, sensibilidad a parámetros).

**Bibliografía clave.**
- Csárdi, G., & Nepusz, T. (2006). "The igraph software package for complex network research". *InterJournal, Complex Systems*, 1695.
- Documentación: https://python.igraph.org/

### 2.3 graph-tool

**Qué es.** Biblioteca de Tiago Peixoto (Central European University). Núcleo en C++ con metaprogramación de plantillas (Boost Graph Library), OpenMP para paralelismo.

**Ventajas.**
- **La más rápida de las tres.** Con OpenMP activado bate a igraph significativamente en PageRank, betweenness y clustering global
- Escalabilidad real a millones de nodos
- **Inferencia de Stochastic Block Models (SBM)**, única entre las librerías mainstream — crucial si quieres detectar estructura latente en la red (por ejemplo, identificar cámaras de eco o comunidades ideológicas ocultas)
- Dibujo interactivo de grafos
- Filtrado de grafos potente (sub-vistas sin copiar)

**Desventajas.**
- **Instalación tortuosa.** No está en PyPI, hay que compilar o usar conda-forge. Windows especialmente problemático
- Documentación densa, con tono matemático
- API diferente al resto; más verticalidad
- No se puede instalar via `pip install` vanilla

**Cuándo usarla.** Investigación seria con grafos grandes, análisis bayesiano de estructura de comunidades, cuando necesitas SBM.

**Bibliografía clave.**
- Peixoto, T. P. (2014). "The graph-tool python library". *figshare*. DOI: 10.6084/m9.figshare.1164194
- Peixoto, T. P. (2019). "Bayesian stochastic blockmodeling". En *Advances in Network Clustering and Blockmodeling*, Wiley.
- Sitio: https://graph-tool.skewed.de/

### 2.4 NetworKit

**Qué es.** Biblioteca C++ con bindings Python, orientada específicamente a escalabilidad (Universidad de Colonia). Diseñada para análisis de redes masivas.

**Ventajas.**
- Específicamente optimizada para grafos de millones/miles de millones de aristas
- Paralelismo multicore nativo
- En algunos benchmarks (PageRank, k-core), 10x más rápida que graph-tool
- Algoritmos aproximados para cuando los exactos son intratables

**Desventajas.**
- Menos algoritmos que NetworkX o igraph
- Comunidad más pequeña
- Algunas diferencias en criterios de parada hacen que benchmarks sean matizados (usa L2 en PageRank mientras otros usan L1)

**Cuándo usarla.** Grafos de escala industrial (> 10M aristas). Para un TFG probablemente overkill.

**Bibliografía.**
- Staudt, C. L., Sazonovs, A., & Meyerhenke, H. (2016). "NetworKit: A tool suite for large-scale complex network analysis". *Network Science*, 4(4), 508-530.

### 2.5 Veredicto: ¿Cuál es el mejor para tu TFG?

**NetworkX, sin dudarlo**, por estas razones concretas:
1. Para una simulación de guerra cognitiva en un TFG, raramente necesitarás más de 5.000-10.000 agentes; el rendimiento de NetworkX es suficiente
2. Integración perfecta con Mesa (que es tu framework de ABM recomendado, ver sección siguiente)
3. La documentación ahorra semanas de trabajo
4. Si luego necesitas escalar, migrar de NetworkX a igraph es relativamente directo (la estructura del código se preserva)

Si tu grafo concreto supera los 50.000 nodos, migras a igraph. No empieces con graph-tool salvo que tengas razones muy específicas (análisis SBM).

---

## 3. Librerías Especializadas en Redes Multicapa

Esta categoría es crítica para responder a tu tercera pregunta sobre múltiples dimensiones de relación simultáneas.

### 3.1 pymnet

**Qué es.** Implementación Python del formalismo matemático de Kivelä et al. (2014) para redes multicapa. Desarrollada por Mikko Kivelä.

**Ventajas.**
- Implementa rigurosamente el formalismo tensorial (la "biblia" matemática de redes multicapa)
- Soporta múltiples aspectos simultáneamente (p.ej., tipo de relación Y tiempo)
- Escalado eficiente: genera aristas inter-capa perezosamente (lazy evaluation); puedes tener 100.000 capas sin explosión de memoria
- Soporte para reglas de acoplamiento categórico u ordinal entre capas
- Visualización 3D de capas

**Desventajas.**
- Comunidad pequeña, menos recursos didácticos
- Menos algoritmos que NetworkX
- Implementación pura Python (sin versión C++ todavía a fecha de 2026)

**Caso de uso para guerra cognitiva.** Modelar simultáneamente:
- Capa 1: red de confianza interpersonal
- Capa 2: red de afinidad ideológica
- Capa 3: red de exposición mediática (quién ve qué fuente)
- Acoplamientos inter-capa: qué tanto la confianza afecta la receptividad ideológica

**Bibliografía.**
- **Kivelä, M., Arenas, A., Barthelemy, M., Gleeson, J. P., Moreno, Y., & Porter, M. A. (2014). "Multilayer networks". *Journal of Complex Networks*, 2(3), 203-271.** — Este es EL paper fundacional, imprescindible si vas por esta ruta.
- Documentación: https://mnets.github.io/pymnet/

### 3.2 multinetx

**Qué es.** Librería más pragmática, construida directamente sobre NetworkX. Autor: Nikos Koumoulos.

**Ventajas.**
- Hereda toda la API de NetworkX (curva de aprendizaje mínima si ya lo conoces)
- Matriz de adyacencia supra clara y manipulable
- Visualización 3D de capas apiladas lista para usar
- Buena para análisis espectral (autovalores de Laplacianos supra-adjacentes)

**Desventajas.**
- Solo grafos no dirigidos en la versión actual
- Menos flexible que pymnet (un solo aspecto: capas)
- No implementa algunos algoritmos específicos multicapa (detección de comunidades multicapa, por ejemplo)

**Cuándo usarla.** Cuando quieres algo rápido de prototipar y ya dominas NetworkX.

### 3.3 MultiGraph de NetworkX (alternativa mínima)

Si no necesitas el formalismo multicapa riguroso, NetworkX tiene `MultiGraph` y `MultiDiGraph`, que permiten múltiples aristas entre los mismos nodos con diferentes atributos. Para muchos casos de guerra cognitiva, esto es suficiente: modelas cada tipo de relación como un atributo `kind` de la arista y filtras.

**Veredicto.** Para tu TFG, empieza con `MultiGraph` de NetworkX. Si te quedas corto conceptualmente (necesitas hablar de acoplamientos inter-capa, estadísticas multicapa formales, etc.), salta a **pymnet**, citando el paper de Kivelä.

---

## 4. Frameworks de Modelado Basado en Agentes (ABM)

### 4.1 Mesa 3

**Qué es.** El framework ABM dominante en el ecosistema Python. Creado en 2015, reescrito profundamente en 2024-2025 como Mesa 3. Publicado en *Journal of Open Source Software* (2025).

**Ventajas.**
- **Comunidad activísima** (Google Summer of Code 2025 y 2026)
- Integración nativa con NetworkX (clase `NetworkGrid`): cada nodo del grafo puede ser una celda que contiene agentes
- Clase `Model` con `Schedule` (gestión temporal), `Grid` (espacio), `DataCollector` (recolección de métricas)
- **SolaraViz**: visualización interactiva en navegador sin configuración complicada
- Espacios discretos (rejilla ortogonal, hexagonal, red), espacios de Voronoi, espacios continuos
- PropertyLayers: capas de variables ambientales superpuestas al espacio (útil para modelar "saturación informacional" en una región del grafo)
- `AgentSet` avanzado: selección, filtrado y operaciones masivas sobre subconjuntos de agentes
- Experimental: `DiscreteEventSimulator` (no solo ticks fijos sino eventos programados)
- Buena integración con LLMs en desarrollo (Mesa-LLM, GSoC 2025)

**Desventajas.**
- Python puro: no competitivo para millones de agentes (pero suficiente para decenas de miles)
- La migración Mesa 2 → Mesa 3 deprecó bastante API, así que cuidado con tutoriales viejos
- Visualización interactiva buena pero no al nivel de NetLogo (que tiene décadas de refinamiento)

**Bibliografía clave (ESTA CITA DEBES TENERLA EN TU TFG).**
- **ter Hoeven, E., Kwakkel, J., Hess, V., Pike, T., Wang, B., rht, & Kazil, J. (2025). "Mesa 3: Agent-based modeling with Python in 2025". *Journal of Open Source Software*, 10(107), 7668. DOI: 10.21105/joss.07668**
- Kazil, J., Masad, D., & Crooks, A. (2020). "Utilizing Python for Agent-Based Modeling: The Mesa Framework". En *Social, Cultural, and Behavioral Modeling*. Springer.

### 4.2 AgentPy

**Qué es.** Framework alternativo a Mesa, desarrollado por Joël Foramitti en su tesis doctoral (TU Berlin).

**Ventajas.**
- Integración profunda con el stack científico: NumPy, SciPy, pandas, NetworkX, Seaborn, **ema_workbench** (análisis de incertidumbre exploratoria), **SALib** (análisis de sensibilidad)
- Diseñado para experimentos multi-ejecución (como BehaviorSpace de NetLogo): muestreo de parámetros, Monte Carlo, computación paralela integrada
- Análisis de sensibilidad incorporado (Sobol, Morris)
- API ligeramente más concisa que Mesa para cosas simples
- Excelente para trabajo interactivo en Jupyter

**Desventajas.**
- Comunidad mucho más pequeña que Mesa
- Desarrollo menos activo (última actualización importante 2023)
- Menos tutoriales y ejemplos disponibles
- Visualización menos pulida

**Cuándo elegirla sobre Mesa.** Si tu TFG tiene un componente fuerte de análisis de sensibilidad y exploración sistemática de parámetros (análisis OAT, Sobol, FAST), AgentPy ahorra trabajo de pegamento. De lo contrario, Mesa es mejor apuesta por ecosistema.

**Bibliografía.**
- Foramitti, J. (2021). "AgentPy: A package for agent-based modeling in Python". *Journal of Open Source Software*, 6(62), 3065.

### 4.3 Repast4Py

**Qué es.** Port de Repast (originalmente Java/C++) a Python, desarrollado por Argonne National Laboratory. Orientado a HPC y paralelismo MPI.

**Ventajas.**
- Escalabilidad real: diseñado para supercomputadores (MPI nativo)
- Modelos de millones de agentes distribuidos
- Madurez del ecosistema Repast (usado en epidemiología militar y modelado económico serio)

**Desventajas.**
- Curva de aprendizaje pronunciada (paralelismo MPI)
- Overkill para un TFG
- Comunidad pequeña comparada con Mesa

**Cuándo usarla.** Proyectos con cómputo masivo. No recomendado para tu caso.

### 4.4 MASON (Java) y NetLogo (bonus)

No son Python, pero son referencias doctrinales obligadas:
- **NetLogo**: el estándar educativo y de investigación desde 1999. Útil para prototipar rápido y validar tu modelo antes de portarlo a Python. Tiene extensión para leer desde Python (`pyNetLogo`).
- **MASON**: framework Java de alto rendimiento, usado en simulaciones militares y económicas grandes.

### 4.5 Veredicto para tu TFG

**Mesa 3, sin dudarlo.** Razones:
1. Integración perfecta con NetworkX (lo que te permite usar grafos como sustrato de agentes)
2. Cita de Mesa 3 de 2025 es publicable y actual
3. Comunidad grande, respuestas a problemas en Stack Overflow
4. SolaraViz te da visualización interactiva gratis
5. Migración futura a Mesa-LLM si quieres agregar "cerebros" LLM

---

## 5. Librerías de Visualización

Distingo tres categorías porque sirven propósitos diferentes y las necesitas todas.

### 5.1 Visualización estática (para informes y paper)

**Matplotlib.**
- Pros: estándar universal, personalización total, calidad de publicación, funciona con NetworkX via `nx.draw()`
- Contras: API imperativa verbosa, no interactiva por defecto
- Bibliografía: Hunter, J. D. (2007). "Matplotlib: A 2D graphics environment". *Computing in Science & Engineering*, 9(3), 90-95.

**Seaborn.**
- Pros: API declarativa, gráficas estadísticas preciosas por defecto, excelente para heatmaps (útil para matrices de adyacencia)
- Contras: no orientada a grafos específicamente
- Bibliografía: Waskom, M. L. (2021). "seaborn: statistical data visualization". *Journal of Open Source Software*, 6(60), 3021.

**Veredicto estática.** Matplotlib + Seaborn para gráficas estadísticas del experimento; NetworkX `draw()` o Graphviz para grafos pequeños (<100 nodos) en informes.

### 5.2 Visualización interactiva web (para exploración y presentación)

**Pyvis.**
- Pros: extraordinariamente fácil de usar, genera HTML interactivo con física (nodos que se atraen/repelen), arrastrables, con tooltips. Conversión directa desde NetworkX
- Contras: rendimiento pobre con grafos >1.000 nodos, personalización limitada
- Uso: `net = Network(); net.from_nx(G); net.show("grafico.html")`

**Plotly.**
- Pros: calidad de publicación + interactividad, integración con Dash para dashboards reales, soporte 3D, animaciones temporales (perfecto para mostrar evolución dinámica de la red en guerra cognitiva)
- Contras: curva de aprendizaje media, scripts más largos
- Bibliografía: Plotly Technologies Inc. (2015). *Collaborative data science*. Plotly, Montréal.

**Bokeh.**
- Pros: excelente para datasets grandes (streaming, datashader integration), dashboards profesionales, soporta grafos
- Contras: API menos intuitiva que Plotly, curva de aprendizaje pronunciada

**HoloViews/hvPlot.**
- Pros: API declarativa altísima, generas una visualización interactiva en una línea, usa Bokeh/Plotly/Matplotlib como backend
- Contras: algo de magia oculta que cuesta debuggear cuando falla

**Veredicto interactiva.** 
- Para un TFG con pocos cientos de nodos: **Pyvis** (vistoso, inmediato)
- Para análisis serio con dashboard: **Plotly + Dash**
- Si tu red supera los 5.000 nodos en visualización: considera exportar a **Gephi** (aplicación de escritorio)

### 5.3 Visualización especializada de grafos grandes y multicapa

**Gephi (aplicación externa).**
- No es Python pero es OBLIGATORIO conocerla. Estándar industrial para visualización de redes medianas-grandes (hasta millones de nodos). Exporta desde NetworkX a GEXF y abres en Gephi.
- Layouts ForceAtlas2, OpenOrd, Fruchterman-Reingold optimizados
- Detección de comunidades integrada, filtrado interactivo
- Bibliografía: Bastian, M., Heymann, S., & Jacomy, M. (2009). "Gephi: an open source software for exploring and manipulating networks". *ICWSM*.

**Cytoscape.**
- Similar a Gephi pero enfocado en biología. Tiene API Python (`py4cytoscape`).

**Py3plex (multicapa).**
- Librería específica para visualización de redes multicapa. Genera layouts 2D y 3D bonitos de capas apiladas.
- Bibliografía: Škrlj, B., Kralj, J., & Lavrač, N. (2019). "Py3plex toolkit for visualization and analysis of multilayer networks". *Applied Network Science*, 4, 94.

**Datashader.**
- Para grafos VERDADERAMENTE grandes (millones de nodos). Renderiza a mapa de calor de píxeles en lugar de dibujar cada nodo. Útil solo si llegas a ese tamaño.

### 5.4 Veredicto visualización integrada

Para tu TFG necesitarás **esta combinación**:
- **Matplotlib + Seaborn**: gráficas del experimento (evolución de creencias, polarización en el tiempo)
- **NetworkX + Matplotlib**: grafos estáticos pequeños en el informe
- **Pyvis**: vista interactiva de la red para presentación/defensa
- **Plotly**: si quieres mostrar animación temporal de la propagación de narrativas
- **Gephi** (externo): si vas a incluir una visualización de la red final que impacte al tribunal

---

## 6. Arquitectura Recomendada para tu TFG de Guerra Cognitiva

Juntando todo lo anterior, esta es la pila técnica que te recomiendo, en orden de implementación:

**Semana 1-2: sustrato de red.** NetworkX para construir el grafo social (puedes usar un `MultiGraph` si necesitas múltiples tipos de relaciones, o un `Graph` simple para empezar). Generas una red scale-free con `nx.barabasi_albert_graph()` o cargas datos reales.

**Semana 2-4: agentes y cerebros.** Mesa 3 con `NetworkGrid` sobre el grafo. Cada `Agent` tiene atributos:
- `creencia` (valor en un espectro ideológico, por ejemplo [-1, 1])
- `confianza_institucional` (valor en [0, 1])
- `susceptibilidad` (qué tan fácilmente cambia de opinión)
- `sesgo_confirmacion` (peso mayor a mensajes que confirman su creencia)
- `memoria` (lista de mensajes recientes recibidos)

El método `step()` del agente implementa su "cerebro" con reglas cognitivas: recibe mensajes de vecinos, los pondera por confianza en el emisor, aplica sesgo de confirmación, actualiza su creencia según una regla tipo DeGroot modificada o bounded confidence (Hegselmann-Krause).

**Semana 4-6: propagación y operaciones.** Modelas atacantes (nodos inyectores de desinformación), defensores (fact-checkers con capacidad de contraargumentación), y dinámica temporal. El `DataCollector` de Mesa registra métricas: polarización (varianza de creencias), fragmentación (número de clusters ideológicos), confianza institucional promedio.

**Semana 6-8: experimentos y análisis.** Barrido de parámetros (con `BatchRunner` de Mesa o SALib de AgentPy si migras), múltiples semillas para robustez estadística. Análisis de sensibilidad: ¿qué importa más, densidad de red o agresividad del atacante?

**Semana 8-10: visualización y redacción.**
- Pyvis para mostrar la red en la defensa
- Plotly para animación temporal de cómo se polariza la red
- Matplotlib/Seaborn para las gráficas del TFG

---

## 7. Si quieres ir un paso más allá: agentes con "cerebro" LLM

Si quieres hacer algo vanguardista (y publicable en un congreso, si te interesa), considera el Nivel 3 de sofisticación: agentes con LLM como cerebro.

**Arquitectura:**
- Cada agente tiene un "system prompt" que define su personalidad (Big Five, ideología, profesión, nivel educativo)
- Una memoria episódica (últimos N mensajes recibidos)
- Cuando le llega un mensaje, envía al LLM: "Eres [personalidad]. Has recibido este mensaje de [vecino con confianza X]. Tu creencia previa era Y. ¿Cambias de opinión? ¿Retransmites?"
- El LLM responde con una decisión y un razonamiento

**Librerías para esto:**
- **LangChain** para orquestar el agente
- **LangGraph** para flujos de decisión más complejos
- **Mesa** para el ciclo de simulación
- **LiteLLM** para cambiar entre proveedores (OpenAI, Anthropic, local)

**Caveats importantes:**
- Coste: 10.000 agentes × 100 ticks × llamada LLM = caro. Modelos locales (Ollama con LLaMA 3) ayudan
- No-determinismo: los LLM son estocásticos, necesitas muchas ejecuciones
- Validación: es más difícil argumentar por qué el agente hizo lo que hizo

**Framework de referencia:** 
- **Shachi** (Kuroki et al., 2025): estandariza arquitectura de agentes LLM para ABM reproducible. https://arxiv.org/abs/2509.21862
- Para inspiración práctica: el repositorio `LLM-ABM-StockSim` de Mihir Chhiber en GitHub, que combina Mesa + LangChain + LLaMA.

---

## 8. Bibliografía Consolidada (para citar en tu TFG)

### Fundacional de grafos
- Hagberg, A. A., Schult, D. A., & Swart, P. J. (2008). "Exploring network structure, dynamics, and function using NetworkX". *Proceedings of the 7th Python in Science Conference*, 11-15.
- Csárdi, G., & Nepusz, T. (2006). "The igraph software package for complex network research". *InterJournal, Complex Systems*, 1695.
- Peixoto, T. P. (2014). "The graph-tool python library". DOI: 10.6084/m9.figshare.1164194

### Redes multicapa (fundamental para relaciones multidimensionales)
- **Kivelä, M., Arenas, A., Barthelemy, M., Gleeson, J. P., Moreno, Y., & Porter, M. A. (2014). "Multilayer networks". *Journal of Complex Networks*, 2(3), 203-271.** — Cita obligada.
- De Domenico, M., Solé-Ribalta, A., Cozzo, E., Kivelä, M., Moreno, Y., Porter, M. A., ... & Arenas, A. (2013). "Mathematical formulation of multilayer networks". *Physical Review X*, 3(4), 041022.
- Škrlj, B., Kralj, J., & Lavrač, N. (2019). "Py3plex toolkit for visualization and analysis of multilayer networks". *Applied Network Science*, 4, 94.

### Modelado basado en agentes
- **ter Hoeven, E., et al. (2025). "Mesa 3: Agent-based modeling with Python in 2025". *Journal of Open Source Software*, 10(107), 7668.** — Cita obligada.
- Foramitti, J. (2021). "AgentPy: A package for agent-based modeling in Python". *Journal of Open Source Software*, 6(62), 3065.
- Epstein, J. M., & Axtell, R. (1996). *Growing artificial societies: Social science from the bottom up*. Brookings Institution Press. — Fundacional conceptual de ABM social.
- Railsback, S. F., & Grimm, V. (2019). *Agent-based and individual-based modeling: A practical introduction*. Princeton University Press. — Manual pedagógico por excelencia.

### Agentes cognitivos clásicos y LLM
- Rao, A. S., & Georgeff, M. P. (1995). "BDI agents: From theory to practice". *Proceedings of the First International Conference on Multi-Agent Systems*, 312-319.
- Kuroki, et al. (2025). "Reimagining Agent-based Modeling with Large Language Model Agents via Shachi". *arXiv:2509.21862*.
- Park, J. S., et al. (2023). "Generative agents: Interactive simulacra of human behavior". *UIST 2023*. — El paper seminal de agentes LLM sociales.

### Propagación de información (teoría base para guerra cognitiva)
- Hegselmann, R., & Krause, U. (2002). "Opinion dynamics and bounded confidence models". *Journal of Artificial Societies and Social Simulation*, 5(3).
- Deffuant, G., Neau, D., Amblard, F., & Weisbuch, G. (2000). "Mixing beliefs among interacting agents". *Advances in Complex Systems*, 3, 87-98.
- Watts, D. J., & Dodds, P. S. (2007). "Influentials, networks, and public opinion formation". *Journal of Consumer Research*, 34(4), 441-458.

### Visualización
- Hunter, J. D. (2007). "Matplotlib: A 2D graphics environment". *Computing in Science & Engineering*, 9(3), 90-95.
- Bastian, M., Heymann, S., & Jacomy, M. (2009). "Gephi: an open source software for exploring and manipulating networks". *ICWSM*.

---

## Resumen Ejecutivo (TL;DR)

- **Grafos**: usa **NetworkX** (suficiente para TFG, mejor documentación)
- **Múltiples tipos de relación entre mismos nodos**: `MultiGraph` de NetworkX si es simple; **pymnet** si necesitas formalismo multicapa riguroso
- **ABM**: usa **Mesa 3** (cita ter Hoeven et al., 2025)
- **Agentes con "cerebro"**: sí, se puede; para tu TFG implementa reglas cognitivas explícitas (sesgo de confirmación, umbral de credibilidad, memoria con decaimiento). Si quieres ir al siguiente nivel, LLM via LangChain, citando Shachi
- **Nodos como agentes + aristas como confianza**: patrón estándar, `NetworkGrid` de Mesa lo soporta nativamente
- **Visualización**: Matplotlib para informe, Pyvis para presentación, Plotly para animaciones, Gephi si el grafo es grande
