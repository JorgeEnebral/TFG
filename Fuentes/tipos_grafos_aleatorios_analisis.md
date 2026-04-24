# Tipos de Grafos Aleatorios: Análisis Exhaustivo de Modelos Generativos

## Contexto

Cuando quieres simular una red social (por ejemplo, para modelar propagación de narrativas en guerra cognitiva), necesitas generar un grafo sintético que se parezca a la realidad. ¿Cómo? Existen varias familias de modelos generativos, cada uno con supuestos, virtudes y limitaciones distintas. Este documento analiza los principales y responde a la pregunta clave: **¿es posible crear grafos aleatorios a partir de probabilidades de conexión que representen la realidad?**

---

## 1. Los Grandes Modelos Generativos de Grafos Aleatorios

### 1.1 Erdős–Rényi (ER) — El modelo más simple

**Cómo funciona.** Defines $n$ nodos y una probabilidad $p$. Para cada par posible de nodos, lanzas una moneda sesgada y conectas con probabilidad $p$. Dos variantes: $G(n, p)$ (probabilidad fija) y $G(n, M)$ (número fijo de aristas $M$).

**Propiedades matemáticas.**
- Distribución de grado: **binomial**, aproximadamente Poisson para $n$ grande con media $\langle k \rangle = (n-1)p$
- Diámetro: logarítmico en $n$
- Coeficiente de clustering: $p$ (muy bajo si $p$ es pequeño)
- Transición de fase famosa: en $p = 1/n$ aparece súbitamente un **componente gigante** que conecta una fracción mayoritaria de los nodos

**Qué representa bien.** Nada realista en sociología. Sirve como *baseline* nulo: "si la red fuera aleatoria, ¿qué pasaría?". Es la hipótesis nula contra la que comparas redes reales.

**Qué representa MAL.** Casi todo lo social. Las redes humanas no tienen distribución Poisson de contactos (hay hubs), no tienen bajo clustering (los amigos de tus amigos suelen ser tus amigos), y no son homogéneas.

**En NetworkX:** `nx.erdos_renyi_graph(n, p)` o `nx.gnp_random_graph(n, p)`.

**Cita canónica:** Erdős, P., & Rényi, A. (1960). "On the evolution of random graphs". *Publicationes Mathematicae Debrecen*, 6, 290-297.

### 1.2 Small-World (Watts–Strogatz) — Mundos pequeños

**Cómo funciona.** Partes de una red regular en anillo donde cada nodo se conecta a sus $k$ vecinos más cercanos. Luego, con probabilidad $p$, cada arista se "recablea" aleatoriamente a otro nodo. El parámetro $p$ interpola entre orden total ($p=0$, red regular) y desorden total ($p=1$, red aleatoria).

**Propiedades matemáticas.**
- Coeficiente de clustering alto (heredado de la estructura regular)
- Diámetro corto (por los atajos aleatorios)
- Distribución de grado relativamente homogénea (no hay superhubs)

**Qué representa bien.** El fenómeno de los "seis grados de separación" de Milgram. Redes donde hay estructura local fuerte (grupos de amigos, pueblos) pero con atajos ocasionales que conectan el mundo (un conocido que vive en otro país).

**Qué representa MAL.** No captura la presencia de superhubs. Todos los nodos tienen aproximadamente el mismo número de conexiones, lo cual es falso en redes sociales reales donde hay unos pocos influencers con millones de seguidores y muchos usuarios con decenas.

**En NetworkX:** `nx.watts_strogatz_graph(n, k, p)` o la variante `nx.newman_watts_strogatz_graph()` que añade aristas en vez de recablearlas.

**Cita canónica:** Watts, D. J., & Strogatz, S. H. (1998). "Collective dynamics of 'small-world' networks". *Nature*, 393(6684), 440-442.

### 1.3 Scale-Free (Barabási–Albert)

**Cómo funciona.** Partes de un núcleo pequeño de nodos conectados. Vas añadiendo nodos uno a uno; cada nodo nuevo se conecta a $m$ nodos existentes, pero **con probabilidad proporcional a su grado actual**. Los ricos se hacen más ricos (*preferential attachment*).

**Propiedades matemáticas.**
- Distribución de grado: **ley de potencias** $P(k) \sim k^{-\gamma}$ con $\gamma \approx 3$ en el modelo original
- Presencia de **hubs**: unos pocos nodos con grado extraordinariamente alto
- Diámetro ultra-corto (más que logarítmico)
- Robustez a fallos aleatorios pero fragilidad a ataques dirigidos a hubs

**Qué representa bien.** La Web, Twitter/X, redes de citas académicas, redes de aerolíneas, y muchas redes sociales donde hay influencers dominantes. Es el modelo que más cita la literatura de guerra cognitiva precisamente porque las redes de propagación de información tienen esta estructura.

**Qué representa MAL.** No captura clustering (los amigos de tus amigos). El modelo puro BA tiene clustering bajo, lo cual no refleja bien comunidades reales. Tampoco captura homofilia (tendencia a conectarte con gente parecida a ti).

**En NetworkX:** `nx.barabasi_albert_graph(n, m)`. Variantes: `nx.powerlaw_cluster_graph(n, m, p)` añade clustering.

**Cita canónica:** Barabási, A.-L., & Albert, R. (1999). "Emergence of scaling in random networks". *Science*, 286(5439), 509-512. — Uno de los papers más citados de la historia de la ciencia de redes.

### 1.4 ERGM (Exponential Random Graph Models)

**Cómo funciona.** Es un enfoque fundamentalmente distinto: en vez de un algoritmo constructivo, es un modelo estadístico. Defines una distribución de probabilidad sobre todos los grafos posibles de $n$ nodos, con la forma:

$$P(G) = \frac{1}{Z} \exp\left(\sum_i \theta_i \cdot s_i(G)\right)$$

donde $s_i(G)$ son estadísticos del grafo (número de aristas, número de triángulos, número de estrellas, homofilia por atributo, etc.) y $\theta_i$ son coeficientes que calibras a partir de datos reales. $Z$ es una constante de normalización.

**Qué representa bien.** Casi cualquier cosa que puedas expresar como estadístico de grafo. Puedes decir "quiero un grafo con esta densidad, este nivel de transitividad, esta homofilia por ideología, y estas probabilidades de conexión dentro/entre comunidades". Es el modelo más usado en sociología cuantitativa.

**Qué representa MAL.** Problemas de degeneración (ciertas combinaciones de parámetros producen grafos patológicos: o vacíos o completos). Computacionalmente caro para redes grandes. Requiere datos reales para calibrar.

**En Python:** la librería estándar está en R (`statnet`, `ergm`), pero hay `PyERGM` y más recientemente `ergm.python` vía `rpy2`.

**Cita canónica:** Robins, G., Pattison, P., Kalish, Y., & Lusher, D. (2007). "An introduction to exponential random graph (p\*) models for social networks". *Social Networks*, 29(2), 173-191.

---

## 2. Otros Modelos Importantes

### 2.1 Stochastic Block Models (SBM) — Comunidades explícitas

**Cómo funciona.** Divides los $n$ nodos en $K$ bloques (comunidades). Defines una matriz $P$ de $K \times K$ donde $P_{ij}$ es la probabilidad de que un nodo del bloque $i$ esté conectado con uno del bloque $j$. Típicamente la diagonal es alta (mucha conexión dentro del bloque) y fuera de diagonal baja (menos entre bloques).

**Propiedades.** Captura explícitamente la estructura de comunidades, que es ubicua en redes sociales reales (tribus ideológicas, grupos profesionales, comunidades geográficas).

**Variantes.**
- **Degree-Corrected SBM**: corrige por heterogeneidad de grado dentro de cada bloque
- **Mixed Membership SBM**: cada nodo puede pertenecer parcialmente a varios bloques
- **Nested SBM** de Peixoto: infiere jerarquías de bloques automáticamente

**Por qué importa para guerra cognitiva.** Permite modelar cámaras de eco e ideológicas como bloques con alta conexión interna y baja externa. Puedes calibrar $P_{\text{dentro-tribu}} = 0.3$ y $P_{\text{entre-tribus}} = 0.01$ para simular polarización.

**En Python:** `graph-tool` tiene la implementación más sofisticada (inferencia bayesiana de SBM). NetworkX tiene `nx.stochastic_block_model()`.

**Cita:** Holland, P. W., Laskey, K. B., & Leinhardt, S. (1983). "Stochastic blockmodels: First steps". *Social Networks*, 5(2), 109-137.

### 2.2 Configuration Model — Preservar grados exactos

**Cómo funciona.** Le das una secuencia específica de grados $(k_1, k_2, ..., k_n)$ y el algoritmo construye un grafo aleatorio que cumple exactamente esa secuencia. Cada nodo tiene "semi-aristas" iguales a su grado deseado, y se emparejan aleatoriamente.

**Qué representa bien.** Cuando tienes datos reales y quieres un grafo sintético con exactamente la misma distribución de grado pero aleatorio en todo lo demás. Es el *baseline* perfecto contra el que comparar efectos estructurales más allá de la distribución de grado.

**En NetworkX:** `nx.configuration_model(degree_sequence)`.

**Cita:** Molloy, M., & Reed, B. (1995). "A critical point for random graphs with a given degree sequence". *Random Structures & Algorithms*, 6(2-3), 161-180.

### 2.3 LFR Benchmark (Lancichinetti–Fortunato–Radicchi) — El más realista

**Cómo funciona.** Genera redes con distribución de grado en ley de potencias Y distribución de tamaños de comunidades en ley de potencias Y clustering ajustable. Es decir, combina las virtudes de scale-free con las de SBM.

**Por qué es importante.** Es el benchmark estándar para evaluar algoritmos de detección de comunidades, precisamente porque se parece más a redes reales que cualquiera de los modelos anteriores.

**En Python:** `nx.LFR_benchmark_graph()` desde NetworkX 2.4.

**Cita:** Lancichinetti, A., Fortunato, S., & Radicchi, F. (2008). "Benchmark graphs for testing community detection algorithms". *Physical Review E*, 78(4), 046110.

### 2.4 Modelos Temporales y Evolutivos

**Forest Fire Model (Leskovec).** Cada nodo nuevo elige un nodo "semilla" aleatorio y luego, como un fuego, se propaga por sus vecinos con cierta probabilidad, conectándose a todos los nodos "quemados". Captura crecimiento en bursts típico de redes reales.

**Kronecker Graphs (Leskovec et al.).** Generación recursiva vía producto de Kronecker de una matriz de iniciación pequeña. Captura auto-similaridad (fractalidad) de redes reales. Usado por Facebook para generar benchmarks sintéticos de su grafo social.

**Duplication-Divergence.** Cada nodo nuevo "duplica" a un nodo existente (copia sus conexiones) y luego diverge (pierde/gana algunas aleatoriamente). Captura bien redes biológicas (proteínas) y algunas sociales.

### 2.5 Modelos Espaciales y Geométricos

**Random Geometric Graphs.** Colocas $n$ puntos aleatorios en un espacio métrico (un cuadrado, una esfera) y conectas pares cuya distancia es menor que un radio $r$. Captura restricciones físicas/geográficas.

**Hyperbolic Graphs.** Los nodos viven en un espacio hiperbólico 2D; la conexión depende de la distancia hiperbólica. Notable porque reproduce simultáneamente scale-free, clustering alto Y navegabilidad eficiente. Modelo más realista de Internet según Papadopoulos et al.

**En NetworkX:** `nx.random_geometric_graph()`.

**Cita del hiperbólico:** Papadopoulos, F., Kitsak, M., Serrano, M. Á., Boguñá, M., & Krioukov, D. (2012). "Popularity versus similarity in growing networks". *Nature*, 489(7417), 537-540.

### 2.6 Redes Multicapa y Temporales

**Redes temporales** (temporal networks), donde las aristas aparecen y desaparecen en el tiempo. Para guerra cognitiva son cruciales porque la estructura de contacto en Twitter/X cambia segundo a segundo.

**Librerías:** `teneto`, `tnetwork` en Python.

---

## 3. Comparativa: ¿Cuál Se Parece Más a la Realidad Social?

| Propiedad real de redes sociales | ER | Small-World | Scale-Free (BA) | SBM | LFR | ERGM |
|---|---|---|---|---|---|---|
| Distribución de grado en ley de potencias | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ (si lo pides) |
| Clustering alto (triángulos) | ✗ | ✓ | ✗ | parcial | ✓ | ✓ (si lo pides) |
| Diámetro corto (six degrees) | ✓ | ✓ | ✓ | ✓ | ✓ | depende |
| Estructura de comunidades | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ (si lo pides) |
| Homofilia por atributos | ✗ | ✗ | ✗ | parcial | ✗ | ✓ |
| Calibrable desde datos reales | ✗ | ✗ | ✗ | parcial | ✗ | ✓ |

**El veredicto:** ninguno de los modelos clásicos (ER, WS, BA) captura la realidad social completa. Para guerra cognitiva mi recomendación concreta es:

- **Si quieres simplicidad y un modelo defendible:** `powerlaw_cluster_graph` de NetworkX (BA con clustering añadido)
- **Si quieres capturar cámaras de eco ideológicas:** SBM con bloques correspondientes a tribus ideológicas
- **Si quieres el modelo más realista:** LFR benchmark
- **Si tienes datos reales a los que ajustar:** ERGM (pero es R o `rpy2`)

---

## 4. Respondiendo Directamente a la Pregunta

### "¿Es posible crear grafos aleatorios a partir de probabilidad de conexiones que puedan representar la realidad?"

**Sí, pero con matices importantes.** Los modelos basados en probabilidad pueden reproducir las **propiedades estadísticas agregadas** de redes reales (distribución de grado, clustering, diámetro, modularidad) con bastante fidelidad si eliges el modelo adecuado. Esto es suficiente para propósitos de simulación y análisis teórico, porque los resultados de las dinámicas que corres sobre el grafo (propagación de información, formación de cámaras de eco, umbrales epidémicos) dependen principalmente de esas propiedades agregadas, no de la identidad exacta de los nodos.

**Pero hay tres caveats importantes:**

1. **Ningún modelo sintético captura todas las propiedades reales simultáneamente.** Cada modelo hace un trade-off. ER es tratable matemáticamente pero irreal; ERGM es realista pero computacionalmente pesado y con problemas de degeneración.

2. **La realidad social tiene propiedades que los modelos generativos capturan mal:** mecanismos de formación de lazos específicos (cómo conoces a alguien), correlaciones complejas entre atributos (ideología, edad, nivel educativo), y dinámica temporal fina (cuándo se activan los lazos).

3. **Para un TFG, el enfoque estándar defendible es:** generar una red sintética con un modelo justificado (por ejemplo, BA con clustering, o SBM si quieres polarización), documentar explícitamente sus propiedades vs. propiedades de redes reales conocidas (hay datasets públicos como el Stanford SNAP), y hacer **análisis de robustez** mostrando que tus conclusiones se mantienen bajo diferentes modelos generativos. Esto es lo que piden los revisores en congresos serios.

---

## 5. Práctica: Código Python Para Cada Modelo

```python
import networkx as nx

# Erdős-Rényi
G_er = nx.erdos_renyi_graph(n=1000, p=0.01, seed=42)

# Small-world (Watts-Strogatz)
G_ws = nx.watts_strogatz_graph(n=1000, k=10, p=0.1, seed=42)

# Scale-free (Barabási-Albert)
G_ba = nx.barabasi_albert_graph(n=1000, m=5, seed=42)

# Scale-free CON clustering (más realista)
G_pc = nx.powerlaw_cluster_graph(n=1000, m=5, p=0.3, seed=42)

# Stochastic Block Model (2 comunidades ideológicas)
sizes = [500, 500]
probs = [[0.1, 0.005],   # dentro de comunidad 1, entre comunidades
         [0.005, 0.1]]   # entre, dentro de comunidad 2
G_sbm = nx.stochastic_block_model(sizes, probs, seed=42)

# LFR Benchmark (el más realista)
G_lfr = nx.LFR_benchmark_graph(
    n=1000, 
    tau1=3,        # exponente ley potencias grados
    tau2=1.5,      # exponente ley potencias tamaños comunidad
    mu=0.1,        # fracción de aristas inter-comunidad
    average_degree=10, 
    min_community=50, 
    seed=42
)

# Configuration Model (preservando grados exactos de otra red)
degrees = [d for n, d in G_ba.degree()]
G_config = nx.configuration_model(degrees, seed=42)
```

---

## 6. Bibliografía Esencial

**Fundamentales (citar en TFG):**
- Erdős, P., & Rényi, A. (1960). "On the evolution of random graphs". *Publicationes Mathematicae Debrecen*, 6, 290-297.
- Watts, D. J., & Strogatz, S. H. (1998). "Collective dynamics of 'small-world' networks". *Nature*, 393(6684), 440-442.
- Barabási, A.-L., & Albert, R. (1999). "Emergence of scaling in random networks". *Science*, 286(5439), 509-512.
- Holland, P. W., Laskey, K. B., & Leinhardt, S. (1983). "Stochastic blockmodels: First steps". *Social Networks*, 5(2), 109-137.
- Lancichinetti, A., Fortunato, S., & Radicchi, F. (2008). "Benchmark graphs for testing community detection algorithms". *Physical Review E*, 78(4), 046110.
- Robins, G., Pattison, P., Kalish, Y., & Lusher, D. (2007). "An introduction to exponential random graph (p*) models for social networks". *Social Networks*, 29(2), 173-191.

**Libros de referencia:**
- Newman, M. E. J. (2018). *Networks* (2nd ed.). Oxford University Press. — El manual canónico.
- Barabási, A.-L. (2016). *Network Science*. Cambridge University Press. — Disponible gratis online, muy pedagógico.
- Estrada, E. (2011). *The Structure of Complex Networks: Theory and Applications*. Oxford University Press.

---

## Resumen en Una Línea

Para un TFG de guerra cognitiva, usa **`powerlaw_cluster_graph`** como baseline (scale-free con clustering, simple y realista) o **`stochastic_block_model`** si quieres modelar explícitamente tribus ideológicas polarizadas. Justifica la elección citando Barabási-Albert 1999 (para el scale-free) y Holland et al. 1983 (para SBM), y haz análisis de robustez con al menos un segundo modelo como check.
