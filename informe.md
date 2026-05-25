# Informe — Métricas y librerías de grafos

Análisis del notebook `src/notebooks/grafos.ipynb` y revisión de alternativas a NetworkX para el simulador multicapa.

---

## 1. Métricas actuales en `grafos.ipynb`

La función `graph_stats` calcula sobre cada grafo (o subgrafo por capa):

| Métrica | Dirigido | No dirigido |
|---|---|---|
| Nodos / aristas | ✓ | ✓ |
| In/Out-grado (max, medio) | ✓ | — |
| Grado (max, medio) | — | ✓ |
| Clustering medio | — | ✓ |
| Diámetro aproximado (BFS desde *k* nodos) | ✓ | ✓ |
| Asortatividad de grado | ✓ | ✓ |
| Betweenness centrality (max, medio) | ✓ | ✓ |
| Eigenvector centrality (max, medio) | ✓ | ✓ |

Más histogramas de grado, betweenness y eigenvector en `plot_histograms`.

---

## 2. Métricas que faltan (relevantes para el TFG)

### 2.1 Estructurales básicas

- **Densidad** (`nx.density`). Una línea, contexto inmediato sobre qué tan denso es el grafo. Imprescindible para comparar topologías.
- **Número y tamaño de componentes conexas** (`nx.connected_components` / `nx.weakly_connected_components`). Ahora mismo solo se usa internamente en `_approx_diameter` y se descarta. Saber si el grafo está fragmentado es crítico antes de hablar de propagación.
- **Transitividad / clustering global** (`nx.transitivity`). Complementa el clustering local promedio: detecta si los triángulos están concentrados en hubs.
- **Longitud media de camino más corto** sobre la LCC (con muestreo si *n* > 1000). Junto al clustering, define la firma “small-world”.

### 2.2 Específicas para grafos dirigidos (capa digital)

- **PageRank** (`nx.pagerank`). Más robusto y estándar que eigenvector centrality en dirigidos; eigenvector frecuentemente no converge en redes con sumideros (de hecho el código ya captura la excepción).
- **Reciprocidad** (`nx.reciprocity`). Fracción de aristas con su recíproca; muy relevante para distinguir “follow” asimétrico (Twitter-style) de “friendship” simétrico (Facebook-style).
- **Strongly connected components** además de weakly. La diferencia entre ambas cuenta una historia sobre si la información puede circular o solo difundirse en árbol.

### 2.3 Específicas para detectar el modelo subyacente

- **Ajuste de ley de potencias** (paquete `powerlaw`). El notebook genera redes Scale-Free pero no verifica empíricamente el exponente α ni el corte. Una columna “α (powerlaw fit)” validaría que el generador hace lo que dice.
- **σ y ω small-worldness** (`nx.sigma`, `nx.omega`). Caro de calcular, pero al menos para *n* = 300 es viable y justifica llamar “small-world” a la capa analógica.
- **K-core / degeneración** (`nx.core_number`). Útil para localizar el núcleo denso de la red — relevante en propagación de cascadas.

### 2.4 Multilayer-específicas (NO existen en NetworkX)

Aquí está la mayor laguna del notebook: las métricas se calculan por capa de forma independiente, pero el grafo es **bicapa** y eso debería medirse:

- **Edge overlap** entre capas: ¿cuántas aristas analógicas tienen su contraparte digital? El invariante actual del modelo lo prohíbe, pero medir el solape *potencial* (vecinos comunes entre capas) informa.
- **Participation coefficient multiplex**: para cada nodo, qué fracción de sus aristas viven en cada capa. Identifica nodos “bilingües” vs especialistas.
- **Correlación entre grados** de un mismo nodo en ambas capas: ¿los hubs digitales son también hubs analógicos?
- **Average activity / node degree multiplex**.

Estas no se pueden calcular cómodamente en NetworkX porque su modelo de datos es monocapa; ver §4 sobre `pymnet`.

---

## 3. Métricas que sobran o son cuestionables

- **Eigenvector centrality** en grafos dirigidos rara vez aporta información útil más allá de PageRank, y aquí el `try/except` que devuelve `nan` confirma que falla con frecuencia. En no dirigidos sí tiene sentido. Propuesta: sustituir por PageRank en dirigidos y mantener eigenvector solo en no dirigidos.
- **Betweenness con `k=500` sobre grafos de *n* = 500**: equivale a calcularlo exacto. Si la intención era aproximar, fijar `k = min(100, n // 5)`. Si era exacto, decirlo en el nombre.
- **Diámetro aproximado con `samples=200`** en grafos pequeños: igual que arriba, “aproximado” es engañoso cuando se muestrean casi todos los nodos. Para *n* ≤ 500 conviene llamar a `nx.diameter` directo sobre la LCC.
- Los **histogramas de eigenvector** muchas veces salen vacíos cuando el cálculo falla (todo `nan`); habría que ocultar el subplot en ese caso en lugar de mostrar un eje en blanco.

---

## 4. Librerías de grafos — comparativa para este TFG

### 4.1 NetworkX (actual)

- **Para qué**: prototipado, didáctica, integración con el resto del ecosistema Python.
- **Pros**: API limpia, todo en Python puro, integración total con Mesa.
- **Contras**: lento en grafos > 10⁴ nodos; sin soporte nativo multilayer; algoritmos costosos (betweenness exacto, eigenvector) escalan mal.

### 4.2 igraph (`python-igraph`)

- **Para qué**: análisis estructural rápido en redes medianas-grandes (10⁵-10⁶ nodos). Detección de comunidades (Louvain, Leiden, Infomap), métricas de centralidad eficientes.
- **Pros**: backend en C, **10×-100× más rápido** que NetworkX en muchos algoritmos. Tiene Leiden de fábrica.
- **Contras**: IDs de nodo siempre enteros consecutivos, lo que obliga a mapeos manuales; API menos pythónica.
- **Conversión desde NetworkX**: trivial. `ig.Graph.from_networkx(G)` desde igraph ≥ 0.10. Atributos de aristas/nodos se preservan.
- **Recomendación**: úsalo para repetir las métricas pesadas (betweenness exacta, comunidades) sobre el dataset SNAP de 4039 nodos. En grafos pequeños no compensa el cambio.

### 4.3 graph-tool

- **Para qué**: análisis estadístico avanzado (Stochastic Block Models, inferencia bayesiana de comunidades), visualización de alta calidad, redes muy grandes.
- **Pros**: el más rápido del ecosistema Python (C++ + Boost + OpenMP). Sus implementaciones de SBM son de referencia académica.
- **Contras**: instalación dolorosa (no hay wheels en pip; recomienda conda-forge o compilar). API muy distinta a NetworkX.
- **Conversión**: no hay puente directo; se reconstruye desde lista de aristas. Hay funciones contribuidas (`graph_tool_utils`) pero no oficiales.
- **Recomendación**: solo si el TFG explora detección de comunidades con SBM. Para lo demás es over-kill.

### 4.4 pymnet

- **Para qué**: **redes multicapa y multiplex**, exactamente el caso del TFG. Implementa el formalismo de Kivelä et al. (2014), referencia teórica del campo.
- **Pros**: tipos de datos nativos para multilayer (`MultilayerNetwork`, `MultiplexNetwork`). Implementa métricas que NetworkX no tiene: *multiplex degree*, *participation coefficient*, *interlayer mutual information*, *aggregated network*, etc.
- **Contras**: mantenimiento esporádico, comunidad pequeña, documentación limitada. Sin generadores tan ricos como NetworkX.
- **Conversión desde NetworkX**: manual. Se itera sobre `G.edges(data=True)` y se hace `mnet[u, v, layer_u, layer_v] = 1`. Para este proyecto el coste de conversión es bajo porque `MultiLayerGraph.build()` ya separa las capas por etiqueta.
- **Recomendación**: **alta**. Es la librería natural para validar y enriquecer las métricas multicapa que ahora faltan (§2.4). Mantén NetworkX para construir las capas individualmente y exporta a pymnet para las métricas multiplex.

### 4.5 multinetx

- **Para qué**: alternativa a pymnet, construida *encima* de NetworkX usando matrices de adyacencia supra-bloque.
- **Pros**: compatibilidad inmediata con NetworkX (la red multicapa es esencialmente un `nx.Graph` con bloques).
- **Contras**: menos métricas multilayer dedicadas que pymnet; proyecto poco activo desde 2018; obliga a pensar en términos de supra-adjacency.
- **Conversión**: prácticamente trivial al estar basado en NetworkX.
- **Recomendación**: si pymnet da problemas de instalación o documentación, es el plan B.

### 4.6 NetworKit

- **Para qué**: análisis de redes grandes con paralelización (OpenMP). Pensado para 10⁶-10⁸ aristas.
- **Pros**: muy rápido, buena cobertura de algoritmos clásicos, paralelizado.
- **Contras**: API propia. Sin soporte multilayer nativo.
- **Conversión desde NetworkX**: directa, con utilidades dedicadas: `networkit.nxadapter.nx2nk(G)` y `nk2nx`.
- **Recomendación**: útil si el TFG escala a redes SNAP grandes (LiveJournal, Twitter). Para *n* ≤ 5000 no compensa.

### 4.7 SNAP.py

- **Para qué**: análisis de redes grandes del repositorio SNAP (Stanford). Backend en C++.
- **Pros**: muy rápido en operaciones masivas; integración natural con los datasets que ya descarga `SNAPGraph`.
- **Contras**: API en estilo C, poco pythónica; el proyecto ya descarga estos datasets y los carga en NetworkX sin problema.
- **Conversión**: manual vía lista de aristas.
- **Recomendación**: baja. El cuello de botella del proyecto no es procesar redes SNAP grandes sino simular la propagación con Mesa.

### 4.8 CDlib

- **Para qué**: **detección de comunidades**, compendio que envuelve >70 algoritmos (Louvain, Leiden, label propagation, etc.) con una API uniforme.
- **Pros**: si en algún momento se necesita medir modularidad o detectar comunidades, ahorra horas de búsqueda; acepta grafos de NetworkX directamente.
- **Conversión**: ninguna, acepta `nx.Graph` y `nx.DiGraph`.
- **Recomendación**: añadir como dependencia opcional si se quiere comparar cómo se propagan los mensajes dentro vs entre comunidades.

---

## 5. Resumen de cambios sugeridos

**Prioridad alta (NetworkX, 10 minutos):**
1. Añadir `nx.density`, número y tamaño de componentes, transitividad y longitud media de camino.
2. Sustituir eigenvector por PageRank en grafos dirigidos.
3. Añadir `nx.reciprocity` para la capa digital.

**Prioridad media (NetworkX + `powerlaw`):**
4. Verificar empíricamente el exponente α de Scale-Free.
5. Calcular σ small-worldness en la capa WS (solo si *n* ≤ 500).

**Prioridad alta (cambio de librería para métricas multicapa):**
6. Integrar `pymnet` para calcular *participation coefficient*, *overlap* y correlación de grados entre capas — son las métricas que justifican que el grafo sea **bicapa** y no dos grafos sueltos.

**Limpieza:**
7. Ajustar `k` de betweenness a algo realmente aproximado o renombrar a “exacto”.
8. Ocultar el subplot de eigenvector cuando devuelve todo `nan`.
