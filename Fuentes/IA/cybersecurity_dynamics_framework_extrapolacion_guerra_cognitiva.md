# El Framework de Cybersecurity Dynamics de Shouhuai Xu: Modelización Matemática y su Extrapolación a Guerra Cognitiva

## Contexto: ¿Por Qué Esta Línea de Investigación Es Estratégica para tu TFG?

Shouhuai Xu, uno de los coautores del paper "Cognitive Warfare: Definition, Framework, and Case Study" (2026) que estás traduciendo, es el arquitecto de un programa de investigación de más de una década denominado **Cybersecurity Dynamics**. Fundó el *Laboratory for Cybersecurity Dynamics* en UCCS (antes en UTSA) y ha recibido financiación sustancial del Ejército de EE.UU. precisamente para desarrollar esta línea.

La tesis central de su investigación reciente, explícita en el paper de guerra cognitiva que tienes en las manos, es que **el marco matemático que se ha construido para entender ataques y defensas cibernéticas puede trasladarse con las adaptaciones adecuadas al dominio cognitivo**. Esto tiene implicaciones enormes: en lugar de tratar la guerra cognitiva como un campo puramente descriptivo o cualitativo, podría convertirse en una disciplina cuantitativa con modelos predictivos, umbrales críticos, y análisis de estabilidad rigurosos. Esta es una oportunidad académica excepcional para un TFG.

---

## 1. El Marco Conceptual de Cybersecurity Dynamics

### 1.1 La Ecuación Fundamental

Xu propone que la ciberseguridad puede entenderse como la evolución temporal de un **estado global de seguridad** que depende de cuatro familias de factores. La ecuación madre de todo el framework es:

$$\text{security\_state}(t) = f(C(t), L(t), D(t), A(t))$$

donde:
- $C(t)$ representa el **estado de configuración** de la red (topología, servicios corriendo, permisos)
- $L(t)$ representa los **landscapes de vulnerabilidad** (parches aplicados, CVEs conocidas, exposición)
- $D(t)$ representa las **defensas desplegadas** (firewalls, IDS, monitorización, respuesta)
- $A(t)$ representa los **ataques activos** (campañas en curso, TTPs adversarias)

Lo que busca Xu es encontrar la familia de funciones $\{f\}$ que permita:
1. Medir de forma rigurosa el estado de seguridad como cantidad agregada
2. Comparar dos configuraciones de red ($C_1$ vs $C_2$) cuantitativamente
3. Predecir cómo evoluciona la seguridad en el tiempo dado un ataque
4. Optimizar la postura defensiva ($D$ óptimo dado $A$)

Esta formulación es deliberadamente abstracta porque el objetivo es construir una **teoría general**, no un modelo para una situación específica. Es análoga a cómo la termodinámica define "temperatura" o "entropía" como cantidades macroscópicas que surgen del comportamiento microscópico.

### 1.2 Los Tres Ejes del Programa de Investigación

Xu organiza Cybersecurity Dynamics en tres ejes complementarios:

**Eje X — Modelización first-principle (desde principios primarios).** Partir de la mecánica microscópica de las interacciones ataque-defensa (un nodo ataca a otro, un defensor parchea, etc.) y derivar propiedades macroscópicas emergentes. Aquí es donde entran los modelos de ecuaciones diferenciales que veremos abajo.

**Eje Y — Analítica de datos de ciberseguridad.** Extraer patrones y métricas de datos reales (logs, telemetría de honeypots, datos de malware).

**Eje Z — Métricas de ciberseguridad.** Desarrollar cantidades medibles con propiedades axiomáticas que permitan comparar sistemas de forma rigurosa.

El eje X es el que más interesa para extrapolación a guerra cognitiva, porque es el que produce las ecuaciones y teoremas de estabilidad.

### 1.3 La Inspiración Epidemiológica

El programa de Xu se inspira en una analogía profunda con la epidemiología matemática. La idea, que se remonta a los trabajos pioneros de Kephart y White en los años 90 pero que Xu formaliza sistemáticamente, es que la propagación de malware en una red se parece mucho a la propagación de una enfermedad infecciosa en una población. Por ello, los modelos clásicos SIS, SIR y sus variantes se adaptan al ciberespacio con modificaciones específicas.

La analogía no es superficial: McKendrick publicó las aplicaciones de matemáticas a problemas médicos en 1926, y exactamente el mismo formalismo de ecuaciones diferenciales es el que se usa hoy para modelar ataques cibernéticos. Lo que cambia son las interpretaciones de los compartimentos y las tasas.

---

## 2. Los Modelos Matemáticos Centrales

### 2.1 El Modelo SIS Básico Aplicado a Ciberseguridad

El modelo más elemental es el **Susceptible-Infectado-Susceptible (SIS)**. En el contexto ciber, cada nodo (ordenador, servidor, dispositivo) está en uno de dos estados:
- **Susceptible (S)**: no comprometido pero vulnerable
- **Infectado (I)**: comprometido por el atacante

La dinámica se describe por dos ecuaciones diferenciales ordinarias acopladas:

$$\frac{dS}{dt} = -\beta S I + \gamma I$$

$$\frac{dI}{dt} = \beta S I - \gamma I$$

con la restricción $S(t) + I(t) = N$ (población total constante), donde:
- $\beta$ es la **tasa de infección** (probabilidad por unidad de tiempo de que un nodo infectado comprometa a uno susceptible con el que está en contacto)
- $\gamma$ es la **tasa de recuperación** (probabilidad por unidad de tiempo de que un nodo infectado sea limpiado/parchado y vuelva al estado susceptible)

El modelo SIS captura malware sin inmunidad permanente: un ordenador limpio puede volver a infectarse. Ideal para modelar, por ejemplo, worms auto-propagantes.

**Umbral epidémico crítico.** La propiedad más importante de este modelo es que predice un **umbral de epidemia**: si $R_0 = \beta N / \gamma > 1$, la infección crece y se establece; si $R_0 < 1$, muere. Este número básico de reproducción $R_0$ es la cantidad estratégica más importante: determina si un patógeno (o un malware) puede sostener una epidemia.

### 2.2 El Modelo SIR y Variantes

El **Susceptible-Infectado-Recuperado (SIR)** añade un compartimento de inmunidad permanente:

$$\frac{dS}{dt} = -\beta S I$$

$$\frac{dI}{dt} = \beta S I - \gamma I$$

$$\frac{dR}{dt} = \gamma I$$

Útil cuando un parche una vez aplicado hace al nodo inmune a esa variante concreta de malware.

Sus extensiones incluyen:
- **SEIR**: añade un estado "Expuesto" (E) para capturar el periodo de latencia entre que un nodo es comprometido y empieza a propagar
- **SIRS**: permite que la inmunidad decaiga con el tiempo (nuevas variantes del malware evaden el parche)
- **MSEIR**: añade un estado "Maternal" para inmunidad heredada (útil en epidemiología humana, menos en ciber)

### 2.3 La Limitación Fundamental de los Modelos Clásicos: Homogeneidad

Los modelos SIS/SIR clásicos asumen que **cada nodo está equiprobable en contacto con cualquier otro nodo** (la llamada asunción de *mean-field*, o mezcla homogénea). Esta asunción es groseramente falsa en redes reales, donde la estructura importa enormemente: los hubs (nodos con muchas conexiones) se infectan primero y propagan desproporcionadamente.

El trabajo seminal de Chakrabarti et al. (2008, *ACM TISSEC*) demostró que en redes arbitrarias, el umbral epidémico no depende solo de las tasas sino de **el autovalor dominante de la matriz de adyacencia** de la red:

$$\text{Umbral crítico: } \frac{\gamma}{\beta} < \lambda_{\max}(A)$$

donde $\lambda_{\max}(A)$ es el autovalor más grande de la matriz de adyacencia $A$. Esto significa que en una red estructurada, la topología se convierte en un parámetro de seguridad de primer orden.

### 2.4 Las Familias de Dinámicas Desarrolladas por Xu

Aquí viene la contribución específica de Xu. Ha desarrollado y caracterizado matemáticamente varias familias de dinámicas ataque-defensa:

**1. Preventive and Reactive Cyber Defense Dynamics (PRCDD).** Modela la interacción entre defensas preventivas (filtros, listas negras) y defensas reactivas (detección y limpieza de malware) contra ataques push (propagación activa) y pull (drive-by download). Los artículos clave son Zheng, Lu & Xu (2018, *IEEE Trans.*) y Han, Lu & Xu (2020, *arXiv:2001.07958*), donde demuestran que esta dinámica es **globalmente convergente** bajo parámetros constantes y **globalmente atractiva** bajo parámetros ergódicos dependientes del tiempo.

**2. Active Cyber Defense Dynamics (ACDD).** Xu, Lu & Li (2015, *Internet Mathematics* 11(1)) introducen el modelo canónico. "Defensa activa" significa que el defensor no solo se defiende pasivamente sino que contraataca — por ejemplo, desplegando "white worms" que buscan y eliminan malware malicioso en la red. El modelo es un proceso de Markov nativo que, al ser intratable en su forma bruta por la explosión combinatoria del espacio de estados, se aproxima por **mean-field approximation** a un sistema dinámico:

$$\frac{db_v(t)}{dt} = (1 - b_v(t)) \cdot f_{rb}(\theta_{v,rb}(t)) - b_v(t) \cdot f_{br}(\theta_{v,br}(t))$$

donde $b_v(t)$ es la probabilidad de que el nodo $v$ esté en estado "malo" (comprometido) en el tiempo $t$. Los términos $\theta_{v,rb}$ y $\theta_{v,br}$ codifican la influencia de los vecinos de $v$ (el estado local de la red). Las funciones $f_{rb}$ y $f_{br}$ son las tasas de transición "rojo→azul" (limpieza) y "azul→rojo" (compromiso). El paper estudia especialmente funciones tipo sigmoide (Type II), donde hay un umbral $\tau$ por debajo del cual $f_{rb}(x) < x$ (convexo) y por encima del cual $f_{rb}(x) > x$ (cóncavo), capturando efectos de masa crítica.

**3. Adaptive Cyber Defense Dynamics.** Los defensores (o atacantes) cambian su comportamiento en función del estado observado del sistema. Se modelan con ecuaciones donde los parámetros $\beta$, $\gamma$ son a su vez funciones de $I(t)$ o $S(t)$.

**4. Proactive Cyber Defense Dynamics.** El defensor actúa antes de ser atacado, tipo Moving Target Defense (MTD), donde la configuración de la red cambia proactivamente para complicar los ataques.

**5. Multivirus Dynamics.** Xu, Lu & Zhan (2012, *IEEE Trans. DSC*) modelan la competencia entre múltiples tipos de malware simultáneamente, con ecuaciones acopladas para cada cepa.

### 2.5 La Técnica Matemática Central: Mean-Field Approximation

El obstáculo central es la **barrera de escalabilidad**: un modelo nativo completo de un sistema con $n$ nodos y 2 estados por nodo tiene $2^n$ estados globales. Para $n = 100$ eso son más estados que átomos en el universo observable. Intratable.

La solución que Xu adopta sistemáticamente es la **aproximación de campo medio**. En vez de rastrear el estado exacto de cada nodo, se rastrea la **probabilidad** de que cada nodo esté en cada estado, asumiendo ciertas independencias entre nodos. Esto reduce la dimensionalidad de $2^n$ a $n$ (lineal en el tamaño de la red), lo cual es tratable.

El coste conceptual es que se pierde información sobre correlaciones exactas entre nodos, pero típicamente se gana una buena aproximación si la red no es extrema. Los papers posteriores de Xu se dedican en parte a demostrar cuándo esta aproximación es válida y cuándo falla (corrección de orden superior con *pair approximation* o *moment closure*).

### 2.6 Las Preguntas Matemáticas Que Se Hace Xu

Una vez tienes el sistema dinámico, las preguntas naturales son:

1. **Puntos de equilibrio**: ¿Qué estados son estacionarios? Típicamente el equilibrio trivial $I^* = 0$ (sin infección) y un equilibrio endémico $I^* > 0$ (infección persistente).
2. **Estabilidad local y global**: ¿Los equilibrios son estables? Si perturbo ligeramente, ¿vuelve el sistema al equilibrio o diverge? Se analiza con linealización y matriz jacobiana (estabilidad local) o funciones de Lyapunov (estabilidad global).
3. **Umbrales críticos**: ¿Existe un valor de parámetros $R_0^* = 1$ que separe el régimen "infección muere" del "infección persiste"? En redes estructuradas, el umbral involucra autovalores de la matriz de adyacencia.
4. **Bifurcaciones**: ¿Cambian cualitativamente las dinámicas cuando cruzamos un umbral? Bifurcaciones transcríticas, pitchfork, Hopf.
5. **Convergencia temporal**: ¿Con qué velocidad se alcanza el equilibrio? ¿Hay oscilaciones (ciclos límite)?
6. **Optimización de control**: Dado un presupuesto defensivo, ¿cuál es la estrategia óptima? Aquí entra la ecuación de **Hamilton-Jacobi-Bellman (HJB)** para control óptimo.

Los resultados típicos son teoremas del tipo: "Si $\beta/\gamma < \lambda_{\max}(A)^{-1}$ entonces la epidemia muere exponencialmente rápido; si $\beta/\gamma > \lambda_{\max}(A)^{-1}$ entonces converge al equilibrio endémico con tasa de convergencia proporcional a $|\beta\lambda_{\max} - \gamma|$".

---

## 3. El Puente a la Guerra Cognitiva

Aquí es donde se vuelve interesante para tu TFG. La literatura **ya ha establecido** esta analogía, pero todavía hay enormes oportunidades de investigación. La clave está en entender qué se traduce directamente y qué requiere adaptación.

### 3.1 La Analogía Central: Creencias Como Patógenos

La idea fundamental es que **la propagación de narrativas y creencias en una red social obedece a dinámicas matemáticas análogas a la propagación de malware en una red informática**. Esto no es una metáfora vaga: Ducasse & Tréton (2024, *arXiv:2412.10000*) lo formalizan explícitamente en su modelo de reacción-difusión para propagación de opiniones, partiendo del modelo clásico SIR de Kermack-McKendrick y modificándolo para "contagio social".

La traducción de los compartimentos es:

| Dominio Cibernético | Dominio Cognitivo |
|---|---|
| Susceptible (S) | Ignorante / no expuesto a la narrativa |
| Infectado (I) | Portador activo / difusor de la narrativa |
| Recuperado (R) | Inmunizado / no interesado / fact-checked |
| Malware | Narrativa, rumor, desinformación |
| Tasa de infección $\beta$ | Credibilidad × exposición × afinidad |
| Tasa de recuperación $\gamma$ | Efectividad del fact-checking + decaimiento de interés |

Los investigadores Zhao et al., Zhang et al., y otros (resumidos en el paper de *Scientific Reports* 2024 sobre spreading dynamics) han aplicado explícitamente SIR al flujo de información en redes sociales, definiendo los compartimentos como:
- **Ignorante (I en su notación): usuarios no expuestos
- **Spreader (S): usuarios activamente propagando
- **Recovered (R): usuarios que dejan de propagar

Y han derivado umbrales de propagación formalmente análogos a los umbrales epidémicos en redes ciber.

### 3.2 Lo Que Se Traduce Directamente

**1. La estructura matemática de las ecuaciones.** Las ODEs son idénticas salvo interpretación. Si en ciber tienes $dI/dt = \beta SI - \gamma I$, en cognitivo tienes exactamente lo mismo con $\beta$ = tasa de adopción de la narrativa y $\gamma$ = tasa de abandono.

**2. La dependencia topológica.** El resultado de Chakrabarti sobre que el umbral epidémico depende del autovalor dominante de la matriz de adyacencia se aplica igual: una narrativa se propaga por encima del umbral si y solo si $\beta/\gamma \cdot \lambda_{\max}(A) > 1$. Esto implica que **la estructura de la red social** (presencia de hubs, clustering, componente gigante) determina si una campaña de desinformación puede sostenerse o muere.

**3. La aproximación de mean-field.** La misma técnica que usa Xu para pasar de procesos de Markov intratables a sistemas dinámicos tratables se aplica en dinámica de opiniones. Cada agente tiene una probabilidad $p_i(t)$ de creer la narrativa, y las ecuaciones acopladas se derivan análogamente.

**4. Los análisis de estabilidad y umbrales.** Preguntas del tipo "¿bajo qué condiciones la narrativa falsa converge a cero?" tienen la misma estructura matemática que "¿bajo qué condiciones el malware se erradica?".

**5. El control óptimo.** El trabajo reciente de Liu et al. (2026, *arXiv:2509.23116*) sobre "Cyber Risk Management and Mitigation via Controlled Stochastic SIS Dynamics" plantea el problema como control óptimo con HJB, introduciendo:
- Un control **proactivo** (reduce tasa de infección) — análogo a "prebunking" en guerra cognitiva
- Un control **reactivo** (acelera recuperación) — análogo a fact-checking post-exposición

El *trade-off* entre gasto en prevención y gasto en mitigación que ellos formalizan matemáticamente es exactamente el dilema estratégico de la resiliencia cognitiva.

### 3.3 Lo Que Hay Que Adaptar

Aquí es donde el TFG puede aportar originalidad. La guerra cognitiva **no es idéntica** a ciberseguridad, y ciertas adaptaciones son necesarias:

**1. El estado no es binario.** En ciber, un nodo está comprometido o no (o en SEIR, en una de 4 estados discretos). En cognición, una persona tiene una creencia que es una **variable continua** (grado de acuerdo en $[-1, 1]$, por ejemplo). Esto lleva naturalmente a modelos como:
- **DeGroot (1974)**: $x_i(t+1) = \sum_j w_{ij} x_j(t)$, donde la opinión es un promedio ponderado de las opiniones de los vecinos
- **Hegselmann-Krause (2002)**: solo se influencia por vecinos cuya opinión difiere menos que un umbral $\epsilon$ (bounded confidence)
- **Deffuant-Weisbuch (2000)**: interacciones por pares con ajuste parcial

**2. La "recuperación" no es limpia.** Un ordenador parcheado queda idéntico al estado pre-infección. Una persona expuesta a desinformación retiene efectos incluso tras fact-check (ilusión de verdad, exposición repetida). Esto requiere modelos con **memoria** o con **heterogeneidad de susceptibilidad**.

**3. Existen creencias que compiten.** En ciber puedes tener multivirus, pero generalmente un nodo está infectado por un malware u otro. En cognición, una persona puede sostener creencias parcialmente contradictorias, y la "victoria narrativa" es cuestión de grado. Esto lleva a modelos **multidimensionales** de opinión (cada dimensión es un eje ideológico).

**4. Los atacantes pueden adaptar narrativas.** El malware es estático (salvo polimorfismo); una campaña de desinformación pivota (ver el estudio de caso del paper de Rushing-Hersch-Xu: Red pasa de "ocurrió" a "lo están encubriendo"). Esto introduce **coevolución atacante-defensor** que va más allá del modelo ACDD estándar.

**5. Efectos crónicos vs agudos.** La innovación clave del paper de Rushing-Hersch-Xu que tienes en las manos es precisamente distinguir efectos agudos (horizonte corto, minutos-días) de efectos crónicos (semanas-años). Esto no tiene un paralelo claro en ciberseguridad, donde los tiempos de ataque-defensa son más homogéneos. Formalmente, los efectos crónicos **re-parametrizan** las dinámicas agudas al desplazar $\beta$ y $\gamma$ en el tiempo:

$$\beta_{\text{acute}}(t) = \beta_0 + g(\text{chronic\_erosion}(t))$$

Esta reparametrización temporal es un extensión matemática natural de los modelos de Xu, y sería publicable como contribución original si la desarrollas.

### 3.4 Un Modelo Cognitivo-Warfare Dinamical Concreto

Para aterrizar todo esto, te propongo un modelo concreto que podrías implementar y analizar en tu TFG, combinando elementos ACDD de Xu con dinámica de opiniones:

**Variables de estado.** Para cada nodo $v$ en una red social $G = (V, E)$:
- $x_v(t) \in [-1, 1]$: posición ideológica del agente
- $b_v(t) \in [0, 1]$: grado de creencia en la narrativa adversaria (análogo al $b_v$ del ACDD de Xu)
- $c_v(t) \in [0, 1]$: nivel de confianza institucional

**Dinámica.** La evolución de cada variable se rige por:

$$\frac{db_v}{dt} = (1 - b_v) \cdot f_{\text{adopt}}\left(\sum_{u \in N(v)} w_{uv} \cdot b_u\right) - b_v \cdot f_{\text{reject}}(c_v, \text{fact\_check}(t))$$

donde:
- $f_{\text{adopt}}$ es una función sigmoide que modela la adopción basada en presión social (promedio ponderado de creencias de vecinos)
- $w_{uv}$ es el peso de confianza interpersonal entre $u$ y $v$ (arista de la red)
- $f_{\text{reject}}$ modela la resistencia a la narrativa, creciente con la confianza institucional $c_v$ y la presencia de fact-checks

La confianza institucional $c_v$ evoluciona cronicamente bajo presión adversaria:

$$\frac{dc_v}{dt} = -\alpha \cdot \text{adversary\_erosion}(t) + \beta \cdot \text{institutional\_signal}(t) - \delta \cdot (c_v - c_{\text{baseline}})$$

**Atacantes y defensores.** Red modelada como nodos que inyectan narrativas (incrementan $b_v$ inicial en nodos sembrados) y ejecutan erosión crónica (primer término de la ecuación de $c_v$). Blue modelados como nodos que ejecutan fact-checks (aumentan $f_{\text{reject}}$) y contra-narrativas (boost de $c_v$ en nodos dentro de su alcance).

**Preguntas analíticas.** Con este modelo puedes preguntar:
1. ¿Cuál es el umbral crítico $\beta^*/\gamma^*$ por debajo del cual la narrativa adversaria muere?
2. ¿Cómo depende ese umbral de la estructura de la red (autovalor dominante, densidad, clustering)?
3. Para un presupuesto defensivo fijo, ¿es óptimo gastar más en fact-checking (reactivo) o en educación pre-exposición (preventivo)?
4. ¿Cómo afecta la erosión crónica de $c_v$ al umbral agudo? (Tu paper predice que la baja $c$ amplifica ataques agudos.)
5. ¿Existen bifurcaciones en función de la densidad de conexiones? ¿Cámaras de eco como atractores estables?

Este modelo es publicable a nivel de TFG o incluso de congreso si lo implementas con cuidado numérico y análisis de sensibilidad.

### 3.5 Desarrollos Matemáticos Recientes Relevantes

Para citar en tu TFG y dar solidez bibliográfica a la extrapolación:

**1. Modelos SIR acoplados con opinion dynamics.** Peak Infection Time for a Networked SIR Epidemic with Opinion Dynamics (arXiv:2109.14135) desarrolla precisamente el acoplamiento entre dinámica epidémica y dinámica de opiniones, derivando un "número reproductivo efectivo" que depende del estado de opinión. Esto es directamente aplicable al modelado de guerra cognitiva.

**2. GAN-SEIR para opinión pública.** Wang et al. (2025, *Social Network Analysis and Mining*) combinan Generative Adversarial Networks con SEIR para modelar evolución de opinión pública, mostrando que el acoplamiento entre capas (inter-layer coupling) impacta significativamente la eficiencia de transmisión informacional.

**3. Cyber Risk Stochastic Control.** Liu et al. (2026, *arXiv:2509.23116*) formalizan el trade-off proactivo vs. reactivo como problema de control óptimo estocástico con ecuación HJB. Directamente extrapolable a estrategias de defensa cognitiva.

**4. Scientific Machine Learning para propagación.** El paper de UDEs (Universal Differential Equations, 2025) muestra cómo combinar ODEs clásicas con redes neuronales para descubrir dinámicas no-lineales ocultas. Útil si tienes datos reales de propagación de narrativas y quieres ajustar parámetros.

---

## 4. Por Qué Esto Es Una Oportunidad Para Tu TFG

Hay tres razones por las que esta línea es excepcional para un TFG:

**1. Rigor matemático disponible.** Todo el aparato de Xu, desarrollado durante 15 años, está publicado, probado con teoremas, y disponible. Tú no tienes que inventar las ecuaciones desde cero; las adaptas con justificación.

**2. Implementación en Python viable.** Las ODEs del framework son tratables con SciPy (`scipy.integrate.solve_ivp`), el sustrato de red con NetworkX, y la simulación con Mesa. Todo es compatible con la pila que te recomendé en la conversación anterior.

**3. Hueco académico real.** El paper de Rushing-Hersch-Xu de 2026 explícitamente abre la puerta a extrapolar Cybersecurity Dynamics a guerra cognitiva. Están invitando a que otros investigadores trabajen en esta dirección. Un TFG riguroso en esta línea tiene potencial de ser publicable en una conferencia como ECCWS (European Conference on Cyber Warfare and Security), donde Bonnie Rushing ya publica.

---

## 5. Bibliografía Esencial para tu TFG

### El canon de Shouhuai Xu (citas directas del paper que tienes)
- Xu, S. (2014). "Cybersecurity dynamics". *Proceedings of the 2014 Symposium and Bootcamp on the Science of Security (HotSoS 2014)*. ACM. DOI: 10.1145/2600176.2600190
- Xu, S. (2019). "Cybersecurity Dynamics: A Foundation for the Science of Cybersecurity". En *Proactive and Dynamic Network Defense*, Vol. 74. Springer, pp. 1-31.
- Xu, S. (2020). "The Cybersecurity Dynamics Way of Thinking and Landscape". *Proceedings of the 7th ACM Workshop on Moving Target Defense (MTD@CCS 2020)*. ACM, pp. 69-80. DOI: 10.1145/3411496.3421225

### Los modelos matemáticos concretos
- Xu, S., Lu, W., & Li, H. (2015). "A Stochastic Model of Active Cyber Defense Dynamics". *Internet Mathematics*, 11(1), 23-61. — **El paper central de ACDD.**
- Xu, S., Lu, W., & Zhan, Z. (2012). "A stochastic model of multivirus dynamics". *IEEE Transactions on Dependable and Secure Computing*, 9(1), 30-45.
- Zheng, R., Lu, W., & Xu, S. (2018). "Preventive and Reactive Cyber Defense Dynamics Is Globally Stable". — Incluye la prueba de convergencia.
- Han, Y., Lu, W., & Xu, S. (2020). "Preventive and Reactive Cyber Defense Dynamics with Ergodic Time-dependent Parameters Is Globally Attractive". *arXiv:2001.07958*.
- Lin, Z., Lu, W., & Xu, S. (2019). "Unified Preventive and Reactive Cyber Defense Dynamics Is Still Globally Convergent". *IEEE/ACM Transactions on Networking*, 27(3), 1098-1111.
- Lu, W., Xu, S., & Yi, X. (2013). "Optimizing Active Cyber Defense Dynamics". *GameSec 2013*, pp. 206-225.

### Fundamentos epidemiológicos (se citan por todos)
- Kermack, W. O., & McKendrick, A. G. (1927). "A contribution to the mathematical theory of epidemics". *Proceedings of the Royal Society A*, 115(772), 700-721. — El paper fundacional.
- Hethcote, H. W. (2000). "The Mathematics of Infectious Diseases". *SIAM Review*, 42(4), 599-653. — Revisión canónica.
- Chakrabarti, D., Wang, Y., Wang, C., Leskovec, J., & Faloutsos, C. (2008). "Epidemic thresholds in real networks". *ACM Transactions on Information and System Security*, 10(4), 1-26. — El resultado sobre autovalor dominante.

### Puentes a dinámica de opiniones (lo que adaptarías tú)
- DeGroot, M. H. (1974). "Reaching a consensus". *Journal of the American Statistical Association*, 69(345), 118-121.
- Hegselmann, R., & Krause, U. (2002). "Opinion dynamics and bounded confidence models". *Journal of Artificial Societies and Social Simulation*, 5(3).
- Deffuant, G., Neau, D., Amblard, F., & Weisbuch, G. (2000). "Mixing beliefs among interacting agents". *Advances in Complex Systems*, 3, 87-98.
- Ducasse, R., & Tréton, S. (2024). "Emergence of complexity in opinion propagation: A reaction-diffusion model". *arXiv:2412.10000*. — Conecta SIR con propagación de opiniones.
- Liu, Y., et al. (2026). "Cyber Risk Management and Mitigation via Controlled Stochastic SIS Dynamics: An Optimal Control Approach". *arXiv:2509.23116*. — Control óptimo con HJB para el trade-off prevención/mitigación.

### Para opinión en redes
- Nature Scientific Reports (2024). "Modeling and simulation on the spreading dynamics of public opinion information in temporal group networks". DOI: 10.1038/s41598-024-79543-4.

---

## Resumen Ejecutivo

Shouhuai Xu ha construido durante 15 años un marco matemático riguroso para modelar ciberseguridad como sistema dinámico ataque-defensa, basado en ecuaciones diferenciales inspiradas en epidemiología, con análisis formal de estabilidad, umbrales críticos y convergencia. El framework se resume en $\text{security\_state}(t) = f(C, L, D, A)$ y se concretiza en familias de modelos (PRCDD, ACDD, adaptativos, proactivos, multivirus) todos analizables matemáticamente vía mean-field approximation.

Este marco **se puede extrapolar a guerra cognitiva** porque la propagación de narrativas en redes sociales obedece ecuaciones matemáticamente análogas a la propagación de malware. La literatura ya establece el puente: los modelos SIR/SIS aplicados a opinión pública dan umbrales epidémicos de información; el autovalor dominante de la matriz de adyacencia de la red social determina si una narrativa puede sostenerse; las estrategias óptimas entre prevención y mitigación se derivan vía HJB igual que en ciberseguridad.

Para tu TFG, la oportunidad es combinar el aparato matemático de Xu (ACDD, análisis de estabilidad) con dinámica de opiniones continua (DeGroot, Hegselmann-Krause) y el marco OODA Multi-Horizonte del paper de Rushing-Hersch-Xu (distinción efectos agudos vs crónicos), produciendo un **modelo cuantitativo de guerra cognitiva** implementable en Python con NetworkX + Mesa + SciPy. Es ambicioso pero factible, está explícitamente invitado por los autores del paper que estás traduciendo, y tiene potencial publicable.
