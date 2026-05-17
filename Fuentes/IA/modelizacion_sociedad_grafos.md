# Modelización de la sociedad como grafo: redes analógicas, digitales e híbridas

> **Resumen.** Este documento desarrolla, de forma rigurosa pero pedagógica, cómo modelizar una sociedad humana mediante grafos en los que los **nodos representan personas** y las **aristas representan vínculos**. Se distingue cuidadosamente entre la *red social analógica* (relaciones cara a cara, físicas, mediadas por copresencia) y la *red social digital* (relaciones mediadas por plataformas en línea), se enumeran las **restricciones estructurales y cognitivas** de cada una, y se reseñan los principales trabajos académicos que las han modelizado, con énfasis en los que **integran ambas capas simultáneamente** mediante grafos multicapa.

---

## Tabla de contenidos

1. [Marco teórico: la sociedad como grafo](#1-marco-teórico-la-sociedad-como-grafo)
2. [Fundamentos formales y notación](#2-fundamentos-formales-y-notación)
3. [La red social analógica](#3-la-red-social-analógica)
4. [La red social digital](#4-la-red-social-digital)
5. [Comparativa estructural](#5-comparativa-estructural)
6. [Modelos híbridos: redes multicapa y multiplex](#6-modelos-híbridos-redes-multicapa-y-multiplex)
7. [Trabajos académicos de referencia](#7-trabajos-académicos-de-referencia)
8. [Aplicaciones prácticas](#8-aplicaciones-prácticas)
9. [Limitaciones, sesgos y ética](#9-limitaciones-sesgos-y-ética)
10. [Referencias bibliográficas](#10-referencias-bibliográficas)

---

## 1. Marco teórico: la sociedad como grafo

La idea de representar una sociedad como un grafo se remonta a la **sociometría** de Jacob L. Moreno (1934), que ya dibujaba *sociogramas* con personas como puntos y relaciones como líneas. La consolidación matemática llegó con el **Análisis de Redes Sociales** (SNA, *Social Network Analysis*) de la escuela de Harrison White, Mark Granovetter y Linton Freeman entre las décadas de 1960 y 1980, y se transformó radicalmente con la *ciencia de redes* de finales de los noventa (Watts & Strogatz, 1998; Barabási & Albert, 1999), que descubrió que muchas redes sociales reales presentan propiedades estadísticas universales.

La premisa básica es sencilla: cualquier conjunto de relaciones entre individuos puede representarse mediante un grafo $G = (V, E)$ donde:

- $V$ es el conjunto de **nodos** (personas, agentes, individuos).
- $E \subseteq V \times V$ es el conjunto de **aristas** (vínculos, conexiones, lazos).

A partir de aquí, la complejidad emerge según cómo definamos qué cuenta como "vínculo": un saludo cordial, una llamada al mes, una amistad íntima de décadas o un *follow* en Twitter son objetos de naturaleza muy distinta, y por eso conviene separar la **red analógica** de la **red digital**.

---

## 2. Fundamentos formales y notación

### 2.1. Tipos de grafo aplicables

| Tipo de grafo | Cuándo se usa | Ejemplo |
|---|---|---|
| **No dirigido** | Vínculos simétricos | Amistad mutua, parentesco |
| **Dirigido** | Vínculos asimétricos | *Follower* en Twitter, "yo confío en X" |
| **Ponderado** | La intensidad del lazo importa | Frecuencia de llamadas, tiempo juntos |
| **Temporal / dinámico** | Las aristas aparecen y desaparecen en el tiempo | Encuentros físicos, mensajes |
| **Multigrafo** | Coexisten varios tipos de relación entre los mismos pares | Compañeros de trabajo *y* amigos *y* familiares |
| **Multicapa / multiplex** | Cada capa es un tipo de relación distinto | Capa "amistad offline" + capa "Facebook" |
| **Hipergrafo** | Una arista conecta más de dos nodos | Pertenecer a un grupo, asistir a una fiesta |

### 2.2. Métricas estructurales clave

- **Grado** ($k_i$): número de vínculos del nodo $i$. Se interpreta como popularidad o sociabilidad.
- **Distribución de grado** $P(k)$: en redes humanas suele ser muy heterogénea.
- **Coeficiente de clustering** ($C$): probabilidad de que dos amigos míos sean amigos entre sí. Mide la "transitividad" o cierre triádico.
- **Longitud media del camino** ($\langle l \rangle$): número medio de pasos para conectar dos nodos arbitrarios.
- **Centralidad** (de grado, intermediación, cercanía, vector propio, PageRank): mide la "importancia" estructural de un nodo.
- **Comunidades / módulos**: subconjuntos densamente conectados internamente y débilmente entre sí (Girvan-Newman, Louvain, Leiden).
- **Asortatividad**: tendencia de nodos similares a conectarse entre sí (homofilia).

### 2.3. Modelos generativos relevantes

- **Erdős–Rényi** $G(n, p)$: aristas aleatorias e independientes. Útil como *baseline*, irreal para sociedades.
- **Watts–Strogatz** (1998): **mundos pequeños**, alto clustering y diámetro corto. Captura bien redes analógicas.
- **Barabási–Albert** (1999): **libre de escala**, $P(k) \sim k^{-\gamma}$, generado por *attachment preferencial*. Captura bien redes digitales.
- **Stochastic Block Model (SBM)**: comunidades latentes; útil para inferencia estadística.
- **Exponential Random Graph Models (ERGM)**: marco probabilístico clásico en SNA.

---

## 3. La red social analógica

La red analógica es el grafo de relaciones humanas mediadas por **copresencia física, comunicación oral o canales no digitales** (carta postal, encuentros, parentesco). Es la red que existió durante toda la historia humana hasta finales del siglo XX.

### 3.1. Características generales

- **Densa pero pequeña**: cada persona tiene pocos vínculos en términos absolutos, pero muy entrelazados.
- **Alto clustering**: si A y B son amigos y B y C también, hay una probabilidad alta de que A y C se conozcan (típicamente $C \approx 0.1$–$0.5$).
- **Homofilia muy marcada**: la gente se relaciona con personas similares en edad, clase, etnia, ideología, nivel educativo y proximidad geográfica (McPherson, Smith-Lovin & Cook, 2001).
- **Estructura de pequeño mundo**: pese al clustering alto, la distancia media es corta (Milgram estimó ~6 saltos).
- **Decaimiento con la distancia geográfica**: la probabilidad de un vínculo disminuye, aproximadamente, como una ley de potencia con la distancia física (Liben-Nowell et al., 2005).

### 3.2. Restricciones de la red analógica

Esta es la sección donde la red analógica se diferencia más drásticamente de la digital. Las restricciones son **biológicas, cognitivas, temporales y espaciales**:

#### 3.2.1. Restricción cognitiva: el número de Dunbar

Robin Dunbar (1992, 1993) propuso, a partir de la correlación entre tamaño del neocórtex y tamaño de los grupos sociales en primates, que el ser humano puede mantener relaciones sociales estables con un máximo de aproximadamente **150 personas** (a menudo redondeado a un rango 100–230). Esta cifra se conoce como el **número de Dunbar**.

Dunbar también propuso una **estructura jerárquica anidada** de círculos sociales, frecuentemente descrita como una "serie de Dunbar":

| Círculo | Tamaño aprox. | Naturaleza del vínculo |
|---|---|---|
| Núcleo de apoyo | ~5 | Relaciones íntimas, soporte emocional diario |
| Grupo de simpatía | ~15 | Amigos cercanos |
| Grupo de banda | ~50 | Conocidos frecuentes |
| **Grupo de Dunbar** | **~150** | **Relaciones estables y recíprocas** |
| Reconocimiento facial | ~500 | Personas que reconoces de vista |
| Reconocimiento por nombre | ~1500 | Personas cuyo nombre asocias a una cara |

> **Matiz importante.** El número de Dunbar suele caricaturizarse como "no más de 200 conexiones", pero en rigor es un *límite blando* sobre relaciones **estables, recíprocas y mantenidas activamente**. No impide reconocer caras, recordar nombres ni interactuar puntualmente con miles de personas.

#### 3.2.2. Restricción temporal

Mantener un vínculo analógico cuesta tiempo. Roberts & Dunbar (2011) mostraron que los lazos que no se refuerzan con interacción decaen significativamente en cuestión de meses. Como cada persona dispone de un presupuesto finito de horas de socialización, el tamaño de la red cercana está mecánicamente limitado.

#### 3.2.3. Restricción espacial / geográfica

En redes analógicas, la probabilidad de vínculo decae rápidamente con la distancia física. Antes del transporte y las telecomunicaciones, prácticamente todos los vínculos eran locales. Incluso hoy, una fracción mayoritaria de los amigos cercanos vive a menos de unas decenas de kilómetros.

#### 3.2.4. Restricción de visibilidad y descubrimiento

En la red analógica no existe un mecanismo de "búsqueda global": para conocer a alguien hace falta un encuentro físico, una presentación o un evento compartido. Esto impone un fuerte efecto de **focalización** (Feld, 1981): los vínculos se forman en *foci* (escuela, trabajo, barrio, club).

#### 3.2.5. Restricción de canal

La comunicación cara a cara tiene ancho de banda altísimo (lenguaje, tono, gesto, contexto) pero baja escalabilidad. Una persona no puede mantener conversación significativa simultánea con más de un puñado de interlocutores.

### 3.3. Propiedades estructurales típicas

- $\langle k \rangle$ ≈ 5–150 dependiendo de cómo se defina "vínculo".
- $C$ alto (cierre triádico fuerte; Granovetter, 1973).
- Distribución de grado **acotada**, aproximadamente *log-normal* o exponencial truncada, **no libre de escala** (Amaral et al., 2000, llamaron a estas redes *broad-scale* o *single-scale*).
- Distancia media corta gracias a los *weak ties* (lazos débiles): las amistades casuales conectan comunidades densas (Granovetter, 1973).

---

## 4. La red social digital

La red digital es el grafo de relaciones mediadas por **plataformas tecnológicas**: redes sociales (Facebook, X/Twitter, Instagram, LinkedIn, TikTok), mensajería (WhatsApp, Telegram), correo electrónico, foros, etc.

### 4.1. Características generales

- **Escala masiva**: miles de millones de nodos (Facebook supera los 3000 millones de usuarios activos mensuales en 2024–2025).
- **Distribuciones de grado libres de escala** o de cola muy pesada: unos pocos *hubs* concentran enormes audiencias.
- **Distancias medias muy cortas**: Backstrom et al. (2012) midieron 3.57 grados de separación medios entre usuarios activos de Facebook, frente a los ~6 de Milgram.
- **Persistencia y trazabilidad**: cada interacción queda registrada, lo que produce datasets gigantescos para investigación.
- **Asimetría posible**: muchas plataformas (Twitter/X, Instagram, TikTok) usan grafos dirigidos *follower/followed*.
- **Mezcla de vínculos fuertes y débiles muy heterogénea**: el "amigo de Facebook" no equivale al "amigo offline".

### 4.2. Restricciones de la red digital

A diferencia de la analógica, las restricciones son fundamentalmente **técnicas, de plataforma y de atención**, no cognitivas en el sentido clásico:

#### 4.2.1. Límites de plataforma (caps explícitos)

Cada plataforma impone su propio máximo:

- **Facebook**: hasta 5000 *amigos* (vínculo bidireccional). Sin límite de *seguidores*.
- **Instagram**: hasta 7500 cuentas seguidas; sin límite de seguidores.
- **X (Twitter)**: hasta 5000 cuentas seguidas inicialmente; más allá la plataforma aplica una ratio respecto a los *followers*. Sin límite de *followers*.
- **LinkedIn**: hasta 30 000 conexiones de primer grado.
- **WhatsApp**: hasta 1024 miembros por grupo; hasta 1024 contactos en una lista de difusión (cifras a 2024–2025).
- **TikTok**: hasta 10 000 cuentas seguidas.

> Estos topes cambian con frecuencia, pero la lección estructural es estable: **los límites son artificiales y mucho más altos que el número de Dunbar**.

#### 4.2.2. Restricciones de atención y curación algorítmica

Aunque un usuario pueda *seguir* a 5000 cuentas, el algoritmo de *feed* solo le muestra una fracción mínima. La red "vivida" por el usuario es **muy distinta del grafo nominal** de seguidores. Hay que distinguir:

- **Grafo declarado** (quién sigue a quién): el que las plataformas exponen en su API.
- **Grafo de interacción** (quién comenta, da *like*, mensajea con quién): mucho más escaso y más parecido a la red analógica.

Bernardo Huberman, Romero & Wu (2009) demostraron que, incluso teniendo cientos de "amigos" de Twitter, los usuarios solo interactúan recurrentemente con un núcleo de unas pocas personas, **muy próximo al número de Dunbar**.

#### 4.2.3. Restricciones de identidad

- **Anonimato y multicuenta**: un nodo digital no es necesariamente una persona; pueden ser bots, *sock puppets*, organizaciones, cuentas falsas o muertas.
- **Verificabilidad**: difícil garantizar la unicidad persona-nodo.

#### 4.2.4. Restricciones de mediación algorítmica

Las recomendaciones ("personas que quizá conozcas", *People You May Know*) **modifican activamente** el grafo. La estructura observada está endógenamente influida por la plataforma. Esto rompe muchos supuestos clásicos del SNA.

#### 4.2.5. Restricciones temporales relajadas

A diferencia de la red analógica, mantener un *follow* o una "amistad" en Facebook tiene coste marginal cero. Esto explica por qué los grafos digitales acumulan vínculos latentes que no reflejan relaciones reales activas.

### 4.3. Propiedades estructurales típicas

- $\langle k \rangle$ amplio: desde decenas a miles dependiendo de la plataforma.
- $C$ menor que en la analógica, aunque sigue siendo alto comparado con grafos aleatorios.
- $P(k)$ con cola pesada, frecuentemente compatible con **ley de potencias** $P(k) \sim k^{-\gamma}$ con $\gamma \in [2, 3]$, especialmente en redes dirigidas tipo Twitter/X.
- **Diámetro efectivo** muy bajo (3–5 saltos).
- **Comunidades** marcadas por intereses, idioma, geografía y, crucialmente, ideología (cámaras de eco).

---

## 5. Comparativa estructural

| Dimensión | Red analógica | Red digital |
|---|---|---|
| Tamaño típico de la vecindad inmediata | ~5–150 (Dunbar) | Hasta miles (cap de plataforma) |
| Coste marginal de añadir un vínculo | Alto (tiempo, presencia) | Casi cero (un clic) |
| Coste de mantener un vínculo | Alto (interacción periódica) | Cero |
| Distribución de grado | Acotada, log-normal | Cola pesada, frecuentemente libre de escala |
| Distancia media | ~6 saltos (Milgram) | ~3.5–4 saltos (Backstrom et al., 2012) |
| Clustering | Alto | Moderado a alto, pero menor |
| Homofilia | Muy fuerte | Fuerte (a menudo amplificada algorítmicamente) |
| Visibilidad de terceros | Limitada | Total (amigos de amigos visibles) |
| Persistencia de datos | Memoria y oralidad | Registros permanentes |
| Mediación de un tercero | Solo introducciones | Algoritmos que recomiendan, ordenan y filtran |
| Asimetría de vínculos | Posible pero rara | Frecuente (modelo *follower*) |
| Relación nodo-persona | 1:1 (idealizado) | n:m (bots, multicuenta, cuentas inactivas) |

---

## 6. Modelos híbridos: redes multicapa y multiplex

La realidad es que las personas viven simultáneamente en **ambas redes**, y los lazos se transfieren entre capas. El marco matemático adecuado es el de **redes multicapa** (*multilayer networks*) y, dentro de ellas, las **redes multiplex** (donde el conjunto de nodos es el mismo en todas las capas, pero hay distintos tipos de aristas).

### 6.1. Formalismo

Una red multicapa se define como $\mathcal{M} = (V_M, E_M, V, \mathbf{L})$ donde $V$ es el conjunto base de nodos (personas), $\mathbf{L} = \{L_1, \ldots, L_d\}$ son las capas (analógica, Facebook, WhatsApp, llamadas...), $V_M \subseteq V \times L_1 \times \cdots \times L_d$ son los nodos en cada capa, y $E_M$ contiene aristas *intra-capa* (dentro de la misma capa) y aristas *inter-capa* (que conectan al mismo individuo a través de capas diferentes, llamadas *coupling edges*).

Este formalismo, sistematizado por **Kivelä et al. (2014)** y **Boccaletti et al. (2014)**, permite preguntas como:

- ¿Qué fracción de mis lazos digitales se corresponden con lazos analógicos?
- ¿Cómo se propaga un comportamiento (un rumor, un voto, una vacuna) cuando puede saltar entre la red offline y la online?
- ¿Qué nodos tienen alta centralidad multicapa pero baja en una sola capa?
- ¿Cuándo el grafo digital "predice" un vínculo offline, y viceversa?

### 6.2. Tipologías de hibridación observadas

1. **Relaciones offline que migran online**: amistades de la infancia que terminan en Facebook.
2. **Relaciones online que migran offline**: parejas conocidas en aplicaciones de citas, amigos de comunidades online que se conocen en persona.
3. **Relaciones puramente online**: comunidades de fandom, *gaming*, foros profesionales sin contraparte física.
4. **Relaciones puramente offline**: vecindarios, familiares ancianos no digitalizados, contactos esporádicos.
5. **Capas paralelas**: dos personas mantienen vínculo simultáneo offline + WhatsApp + Instagram, cada uno con dinámica propia.

### 6.3. Hallazgos cuantitativos relevantes

- **Solapamiento parcial**: estudios como el de Dunbar et al. (2015) sobre Facebook y Twitter encontraron que, pese al gran tamaño nominal de las redes digitales, el *núcleo activo* sigue limitado por algo muy parecido al número de Dunbar.
- **Las capas no son redundantes**: De Domenico et al. (2013) mostraron que tratar una red multicapa como una red agregada ("aplastada") destruye información estructural y conduce a errores en métricas como centralidad, comunidades y dinámica de difusión.
- **La dinámica de difusión es distinta**: un contagio (informacional o epidémico) que se propaga simultáneamente por múltiples capas tiene umbrales y velocidades diferentes a los de una sola capa (Granell, Gómez & Arenas, 2013).

---

## 7. Trabajos académicos de referencia

### 7.1. Modelización clásica de la red analógica

- **Moreno, J. L. (1934).** *Who Shall Survive?* Origen de la sociometría.
- **Milgram, S. (1967).** "The small-world problem." *Psychology Today*. Famoso experimento de los seis grados de separación con cartas postales.
- **Granovetter, M. (1973).** "The strength of weak ties." *American Journal of Sociology* 78(6). Distinción entre lazos fuertes y débiles; los débiles son los que conectan comunidades.
- **Dunbar, R. (1992, 1993).** Trabajos sobre el tamaño del neocórtex y el límite cognitivo de las relaciones sociales estables (~150).
- **Watts, D. J., & Strogatz, S. H. (1998).** "Collective dynamics of 'small-world' networks." *Nature* 393. Modelo formal de mundo pequeño.
- **McPherson, M., Smith-Lovin, L., & Cook, J. M. (2001).** "Birds of a feather: Homophily in social networks." Revisión canónica sobre homofilia.
- **Christakis, N. A., & Fowler, J. H. (2007–2009).** Estudios sobre la propagación de la obesidad, el tabaquismo y la felicidad en la red de Framingham (red analógica reconstruida).

### 7.2. Modelización de la red digital

- **Barabási, A.-L., & Albert, R. (1999).** "Emergence of scaling in random networks." *Science* 286. Modelo libre de escala, base teórica para entender muchas redes online.
- **Leskovec, J., & Horvitz, E. (2008).** "Planetary-scale views on a large instant-messaging network." Análisis de 240 millones de usuarios de MSN Messenger; 6.6 grados de separación medios.
- **Mislove, A. et al. (2007).** "Measurement and analysis of online social networks." Estudio fundacional sobre Flickr, YouTube, LiveJournal, Orkut.
- **Kwak, H., Lee, C., Park, H., & Moon, S. (2010).** "What is Twitter, a social network or a news media?" Análisis del grafo completo de Twitter en 2009 (~41M nodos).
- **Ugander, J., Karrer, B., Backstrom, L., & Marlow, C. (2011).** "The anatomy of the Facebook social graph." Estructura del grafo completo de Facebook (~721M nodos).
- **Backstrom, L., Boldi, P., Rosa, M., Ugander, J., & Vigna, S. (2012).** "Four degrees of separation." Demostraron que el diámetro efectivo de Facebook es 3.74.

### 7.3. Trabajos que mezclan red analógica y red digital (núcleo de tu interés)

Estos trabajos son los más relevantes para una visión integrada:

- **Eagle, N., Pentland, A. S., & Lazer, D. (2009).** "Inferring friendship network structure by using mobile phone data." *PNAS* 106(36). El célebre **Reality Mining** del MIT: instrumentaron a 94 personas con teléfonos móviles registrando llamadas, SMS, Bluetooth y proximidad, y reconstruyeron la red analógica a partir de la actividad digital. Demostraron que los datos de móvil predicen amistades autorreportadas con alta precisión.

- **Stopczynski, A., Sekara, V., Sapieżyński, P., Cuttone, A., Madsen, M. M., Larsen, J. E., & Lehmann, S. (2014).** "Measuring large-scale social networks with high resolution." *PLoS ONE* 9(4). El **Copenhagen Networks Study**: 1000 estudiantes de la Universidad Técnica de Dinamarca instrumentados durante años, capturando simultáneamente Bluetooth (proximidad física), llamadas, SMS, Facebook y cuestionarios. Es el dataset de referencia para análisis multicapa de redes humanas reales.

- **Sapiezyński, P., Stopczynski, A., Lassen, D. D., & Lehmann, S. (2019).** "Interaction data from the Copenhagen Networks Study." *Scientific Data*. Publicación del dataset multicapa anonimizado.

- **Wellman, B., & Rainie, L. (2012).** *Networked: The New Social Operating System.* MIT Press. Marco sociológico sobre el "individualismo en red" y la coexistencia online–offline.

- **Hampton, K. N., Sessions, L. F., & Her, E. J. (2011).** "Core networks, social isolation, and new media." Cómo las redes digitales modifican los lazos centrales offline.

- **Dunbar, R. I. M., Arnaboldi, V., Conti, M., & Passarella, A. (2015).** "The structure of online social networks mirrors those in the offline world." *Social Networks* 43. Comprobaron que el tamaño del núcleo activo en Facebook y Twitter sigue las **mismas capas anidadas (~5, 15, 50, 150)** que las relaciones offline.

- **Onnela, J.-P., Saramäki, J., Hyvönen, J., Szabó, G., Lazer, D., Kaski, K., Kertész, J., & Barabási, A.-L. (2007).** "Structure and tie strengths in mobile communication networks." *PNAS* 104(18). Análisis de millones de usuarios de telefonía móvil; aunque la capa es "digital", reconstruye la red social subyacente.

- **De Domenico, M., Solé-Ribalta, A., Cozzo, E., Kivelä, M., Moreno, Y., Porter, M. A., Gómez, S., & Arenas, A. (2013).** "Mathematical formulation of multilayer networks." *Physical Review X* 3. Marco matemático canónico para tratar capas analógica y digital simultáneamente.

- **Kivelä, M., Arenas, A., Barthelemy, M., Gleeson, J. P., Moreno, Y., & Porter, M. A. (2014).** "Multilayer networks." *Journal of Complex Networks* 2(3). Revisión exhaustiva del campo, con secciones específicas sobre redes sociales mixtas.

- **Boccaletti, S., Bianconi, G., Criado, R., del Genio, C. I., Gómez-Gardeñes, J., Romance, M., Sendiña-Nadal, I., Wang, Z., & Zanin, M. (2014).** "The structure and dynamics of multilayer networks." *Physics Reports* 544(1). Otro tratado de referencia.

- **Granell, C., Gómez, S., & Arenas, A. (2013).** "Dynamical interplay between awareness and epidemic spreading in multiplex networks." *Physical Review Letters* 111. Modeliza explícitamente la **interacción entre capa de contagio físico y capa de información digital**, un caso paradigmático de hibridación analógico-digital.

- **Aiello, L. M., et al. (2012).** "Friendship prediction and homophily in social media." Cruza datos de redes online con homofilia offline.

- **Centola, D. (2010, 2018).** Experimentos sobre difusión de comportamientos comparando redes online controladas con predicciones de redes offline; obras: *How Behavior Spreads* (2018).

- **Lazer, D., Pentland, A., Adamic, L., et al. (2009).** "Computational Social Science." *Science* 323. Manifiesto que articula la disciplina y propone explícitamente el cruce de capas digitales y analógicas como su programa de investigación.

- **Subrahmanyam, K., Reich, S. M., Waechter, N., & Espinoza, G. (2008).** "Online and offline social networks: Use of social networking sites by emerging adults." *Journal of Applied Developmental Psychology*. Estudio empírico del solapamiento offline–Facebook en jóvenes.

### 7.4. Software y herramientas

- **NetworkX** (Python): manejo general de grafos.
- **igraph** (R, Python, C): rendimiento alto en redes grandes.
- **Graph-tool** (Python/C++): algoritmos de SBM y redes muy grandes.
- **Gephi**: visualización interactiva.
- **Pajek**: SNA clásico.
- **MuxViz**, **pymnet**: herramientas específicas para redes multicapa.

---

## 8. Aplicaciones prácticas

- **Epidemiología**: modelos de propagación de enfermedades (COVID-19) que combinan contactos físicos (Bluetooth, encuestas) con difusión informacional (Twitter, WhatsApp).
- **Marketing viral y difusión de innovaciones**: identificar *influencers* que conectan capa offline y online.
- **Detección de comunidades y polarización**: cámaras de eco digitales y su relación con segregación residencial offline.
- **Predicción de vínculos** (*link prediction*): inferir amistades offline desde rastros digitales y viceversa.
- **Análisis criminal y de seguridad**: redes de cooperación que combinan reuniones presenciales con comunicaciones cifradas.
- **Salud pública**: difusión de comportamientos saludables (Christakis & Fowler) combinando entrevistas y datos digitales.
- **Diseño de políticas**: comprender brechas digitales y exclusión.

---

## 9. Limitaciones, sesgos y ética

- **Privacidad**: especialmente grave en datasets multicapa, donde combinar capas re-identifica individuos. El propio Reality Mining tuvo controversias.
- **Sesgo de muestreo**: las API de plataformas digitales solo exponen una fracción del grafo; las encuestas analógicas tienen sesgos de memoria y deseabilidad social.
- **Definición operacional del vínculo**: ¿qué cuenta como arista? Una llamada al año, un *like*, una conversación íntima... La elección altera radicalmente las propiedades emergentes.
- **Endogeneidad algorítmica**: los grafos digitales no son "naturales", están moldeados por recomendadores; modelizarlos como sistemas exógenos es engañoso.
- **No estacionariedad**: las plataformas cambian, los caps cambian, los hábitos cambian; cualquier estudio tiene fecha de caducidad.
- **Ética del consentimiento**: la mayoría de los datasets digitales se construyen con consentimiento opaco; los analógicos requieren consentimiento informado explícito.
- **Riesgo de reificación**: un grafo es siempre una *abstracción* de relaciones humanas, no la realidad social. Confundir ambas niveles es un error categorial frecuente.

---

## 10. Referencias bibliográficas

1. Amaral, L. A. N., Scala, A., Barthélémy, M., & Stanley, H. E. (2000). Classes of small-world networks. *PNAS* 97(21).
2. Backstrom, L., Boldi, P., Rosa, M., Ugander, J., & Vigna, S. (2012). Four degrees of separation. *WebSci '12*.
3. Barabási, A.-L., & Albert, R. (1999). Emergence of scaling in random networks. *Science* 286.
4. Boccaletti, S. et al. (2014). The structure and dynamics of multilayer networks. *Physics Reports* 544(1).
5. Centola, D. (2018). *How Behavior Spreads*. Princeton University Press.
6. Christakis, N. A., & Fowler, J. H. (2007). The spread of obesity in a large social network over 32 years. *NEJM* 357.
7. De Domenico, M. et al. (2013). Mathematical formulation of multilayer networks. *Physical Review X* 3.
8. Dunbar, R. I. M. (1992). Neocortex size as a constraint on group size in primates. *Journal of Human Evolution* 22.
9. Dunbar, R. I. M., Arnaboldi, V., Conti, M., & Passarella, A. (2015). The structure of online social networks mirrors those in the offline world. *Social Networks* 43.
10. Eagle, N., Pentland, A. S., & Lazer, D. (2009). Inferring friendship network structure by using mobile phone data. *PNAS* 106(36).
11. Feld, S. L. (1981). The focused organization of social ties. *American Journal of Sociology* 86(5).
12. Granell, C., Gómez, S., & Arenas, A. (2013). Dynamical interplay between awareness and epidemic spreading in multiplex networks. *Physical Review Letters* 111.
13. Granovetter, M. S. (1973). The strength of weak ties. *American Journal of Sociology* 78(6).
14. Hampton, K. N., Sessions, L. F., & Her, E. J. (2011). Core networks, social isolation, and new media. *Information, Communication & Society* 14(1).
15. Huberman, B. A., Romero, D. M., & Wu, F. (2009). Social networks that matter: Twitter under the microscope. *First Monday*.
16. Kivelä, M. et al. (2014). Multilayer networks. *Journal of Complex Networks* 2(3).
17. Kwak, H., Lee, C., Park, H., & Moon, S. (2010). What is Twitter, a social network or a news media? *WWW '10*.
18. Lazer, D. et al. (2009). Computational social science. *Science* 323.
19. Leskovec, J., & Horvitz, E. (2008). Planetary-scale views on a large instant-messaging network. *WWW '08*.
20. Liben-Nowell, D., Novak, J., Kumar, R., Raghavan, P., & Tomkins, A. (2005). Geographic routing in social networks. *PNAS* 102(33).
21. McPherson, M., Smith-Lovin, L., & Cook, J. M. (2001). Birds of a feather: Homophily in social networks. *Annual Review of Sociology* 27.
22. Milgram, S. (1967). The small-world problem. *Psychology Today*.
23. Mislove, A., Marcon, M., Gummadi, K. P., Druschel, P., & Bhattacharjee, B. (2007). Measurement and analysis of online social networks. *IMC '07*.
24. Moreno, J. L. (1934). *Who Shall Survive?*
25. Onnela, J.-P. et al. (2007). Structure and tie strengths in mobile communication networks. *PNAS* 104(18).
26. Roberts, S. G. B., & Dunbar, R. I. M. (2011). Communication in social networks: Effects of kinship, network size, and emotional closeness. *Personal Relationships* 18(3).
27. Sapiezyński, P., Stopczynski, A., Lassen, D. D., & Lehmann, S. (2019). Interaction data from the Copenhagen Networks Study. *Scientific Data* 6.
28. Stopczynski, A. et al. (2014). Measuring large-scale social networks with high resolution. *PLoS ONE* 9(4).
29. Subrahmanyam, K., Reich, S. M., Waechter, N., & Espinoza, G. (2008). Online and offline social networks. *Journal of Applied Developmental Psychology* 29(6).
30. Ugander, J., Karrer, B., Backstrom, L., & Marlow, C. (2011). The anatomy of the Facebook social graph. arXiv:1111.4503.
31. Watts, D. J., & Strogatz, S. H. (1998). Collective dynamics of 'small-world' networks. *Nature* 393.
32. Wellman, B., & Rainie, L. (2012). *Networked: The New Social Operating System*. MIT Press.

---

*Documento preparado como referencia para la modelización de redes sociales humanas en su doble dimensión analógica y digital.*
