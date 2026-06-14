# Plan de finalización de la memoria (TFG)

Documento de trabajo. Recoge, explicado y desglosado, **todo lo que falta por
implementar** en la memoria antes de darla por cerrada. No ejecuta nada por sí
mismo: es la hoja de ruta para las siguientes sesiones de edición.

Rutas relevantes:

- Documento maestro: `Burocracia/Memoria/memoria.tex`
- Secciones incluidas: `Burocracia/Memoria/secciones/*.tex`
- Imágenes: `Burocracia/Memoria/images/`
- Bibliografía: `Burocracia/Memoria/ref_tfg.bib`
- Notebook de resultados: `src/notebooks/analisis_sweep-resistente.ipynb`
- Notebook de métricas de red: `src/notebooks/grafos_metricas.ipynb`

---

## 0. Partes CONGELADAS (no tocar)

Las siguientes partes están **finalizadas**. No se debe quitar, añadir ni
modificar nada en ellas durante la implementación de este plan:

1. **Formato de la memoria** — preámbulo, paquetes, geometría, cabeceras/pies,
   portada (`\ComillasTitlePage`, `Anexo_I.tex`), numeración romana/arábiga.
   Todo el bloque anterior a `\begin{document}` y la maquinaria de página.
2. **Resúmenes ejecutivos ES/EN** — secciones *Introducción/Introduction*,
   *Objetivos/Objectives* y *Descripción del simulador/Description of the
   Simulator* (`memoria.tex` líneas ~221–341).
   > ⚠️ **Excepción**: las subsecciones *Resultados/Results* y
   > *Conclusiones/Conclusions* de ambos resúmenes **sí** se reescriben
   > (ver Tarea 3). Confirmar con el usuario que esta es la lectura correcta,
   > porque el enunciado marca el resumen ejecutivo como "finalizado" pero
   > a la vez pide rehacer sus apartados de resultados y conclusiones.
3. **Estado del arte** (`sec:related`, `memoria.tex` líneas ~431–481):
   guerra cognitiva, modelado de redes complejas, psicología individual y
   colectiva, vacío identificado.
4. **Marco teórico** (`sec:marco`): los tres ficheros
   `secciones/met_marco_guerra_cognitiva.tex`, `met_marco_grafos.tex`,
   `met_marco_agentes.tex`.

Cualquier cambio fuera de las Tareas 1–5 sobre estos bloques es un error.

---

## Tarea 1 — Tabla de hiperparámetros (Tabla 6): partir en fijos + barridos

**Qué es la "Tabla 6 de simulación".** Contando las tablas en orden de
aparición en el cuerpo, la nº 6 es `tab:hiperparametros`
(`secciones/met_simulacion.tex`, líneas 53–87), titulada *"Hiperparámetros del
experimento de referencia"*. La nº 7 es `tab:experimentos` (diseño OFAT).

**Problema actual.** `tab:hiperparametros` mezcla en una sola tabla los
parámetros que permanecen **fijos** durante todo el barrido con los que
**se barren** ($\gamma$, $p_s$, $\lambda$, $f$, $k$, $\rho$, estrategia de
semilla aparecen además en `tab:experimentos`). Eso duplica información y no
deja claro el diseño.

**Objetivo.**

1. **Mantener la información en el cuerpo de la memoria, en el punto donde se
   menciona** (sección `met_simulacion.tex`, párrafo "Hiperparámetros de
   referencia"). **No** moverla al anexo.
2. **Dividir en dos tablas**:
   - **Tabla A — Hiperparámetros FIJOS**: los que no varían en ningún
     experimento. A partir de la tabla actual: $N$ / réplicas MC, días/pasos
     ($T=45$), $\mu_s/\mu_r/\sigma$ (0,30 / 0,70 / 0,10), umbral de veracidad
     $v_{\text{thr}}=0{,}30$, parámetros de la topología libre de escala
     ($\alpha,\beta,\gamma_{\mathrm{BA}},\delta_{\mathrm{in}}$) y de mundo
     pequeño ($k$, $p_{\mathrm{rewire}}$). Mantener columnas
     *Valor / Justificación / Fuente*.
   - **Tabla B — Hiperparámetros BARRIDOS**: $\gamma$, estrategia de semilla,
     $\rho$, $k$ (nº semillas), $f$, $p_s$, $\lambda$, con su **valor baseline**
     y los **niveles** del barrido. En la práctica es una refundición de la
     información de `tab:experimentos`; decidir si se fusiona con
     `tab:experimentos` o se deja como tabla de valores + se conserva
     `tab:experimentos` para los niveles/métricas. **Recomendado**: una sola
     tabla de barridos (valor baseline + niveles) y eliminar la redundancia.
3. **Texto explicativo nuevo** (1–2 párrafos antes/entre las tablas) que
   justifique **por qué** cada grupo es fijo o barrido:
   - *Fijos*: parámetros de calibración estructural y de población que definen
     el escenario de referencia y que, de variarse, cambiarían el sistema
     simulado en lugar de la campaña (tamaño $N$, horizonte temporal,
     distribución bimodal de umbrales, parámetros generativos de cada
     topología). Se fijan para aislar el efecto de la narrativa.
   - *Barridos*: las **palancas de la campaña** controlables por el atacante
     ($\gamma$, $f$, estrategia y nº de semillas, $\rho$) y dos moduladores de
     composición/contenido ($p_s$, $\lambda$). Son las variables cuya
     sensibilidad sobre la resiliencia es el objeto del estudio (OFAT).

**Archivos a tocar**: solo `secciones/met_simulacion.tex`. Actualizar las
referencias `\ref{tab:hiperparametros}` / `\ref{tab:experimentos}` si cambian
las etiquetas.

**Verificación**: compila sin `??`; la Tabla A no contiene ningún parámetro
barrido y la Tabla B no contiene ningún parámetro fijo; el texto justifica
ambos grupos.

---

## Tarea 2 — Resultados: regenerar TODAS las imágenes desde el notebook

**Objetivo.** Quitar las imágenes de resultados actualmente insertadas y
volver a generarlas desde `src/notebooks/analisis_sweep-resistente.ipynb`,
para que reflejen los datos finales del barrido.

**Estado del notebook.** Las celdas de figuras **no tienen `savefig`** (generan
las figuras en memoria). Hay que añadir el guardado a disco.

**Figuras referenciadas en `memoria.tex` (sección `sec:results`)** y su celda
de origen en el notebook:

| Figura (label)        | Archivo                              | Celda nb | Contenido                              |
|-----------------------|--------------------------------------|----------|----------------------------------------|
| `fig:marginal`        | `sweep_marginal_resiliencia.png`     | 5        | Curvas marginales OFAT (2×4)           |
| `fig:temporalgamma`   | `sweep_temporal_gamma.png`           | 11       | Adopción temporal por $\gamma$         |
| `fig:hubsrandom`      | `sweep_hubs_vs_random.png`           | 9        | Hubs vs random por topología           |
| `fig:temporalps`      | `sweep_temporal_susceptible.png`     | 13       | Adopción temporal por $p_s$            |
| `fig:t50tpeak`        | `sweep_t50_tpeak.png`                | 15       | $t_{50}$ y $t_{\mathrm{peak}}$         |
| `fig:heatmap`         | `sweep_heatmap.png`                  | 17       | Heatmap factor × nivel (2×2)           |
| `fig:envolvente`      | `sweep_envolvente.png`               | 19       | Envolvente global + distribución $t_{50}$ |

(La celda 7 genera un boxplot —`sweep_boxplot_tasa.png`— que **no** se usa
actualmente en la memoria; decidir si se incorpora o se ignora.)

**Pasos.**

1. En cada celda de figura del notebook, añadir al final
   `fig.savefig(IMG_DIR / "<nombre>.png", dpi=200, bbox_inches="tight")`,
   con `IMG_DIR = Path("../../Burocracia/Memoria/images")` (definir una vez en
   la celda 1). Usar **exactamente los mismos nombres de archivo** de la tabla
   anterior para no tocar los `\includegraphics` de la memoria.
2. Ejecutar el notebook de principio a fin (kernel limpio) con los datos
   finales en `data/results/.../sim/` para regenerar los PNG.
3. Verificar que los 7 PNG en `images/` se han actualizado (timestamp / git
   diff) y que se ven correctamente.
4. En la memoria, **no** hace falta cambiar las rutas si se respetan los
   nombres; solo revisar que los pies de figura siguen describiendo lo que
   muestra cada imagen regenerada (cifras citadas en el texto deben coincidir
   con las nuevas figuras — ver Tarea 3, que reusa esos números).

> ⚠️ Pedir confirmación antes de **ejecutar** el notebook (preferencia del
> usuario: no correr tests/ejecuciones sin pedirlo). El plan deja listo el
> *qué*; la ejecución se autoriza aparte.

**Verificación**: cada `\ref{fig:*}` resuelve; las 7 imágenes provienen de la
última ejecución del notebook; no quedan PNG huérfanos referenciados.

---

## Tarea 3 — Resúmenes ejecutivos ES/EN: Resultados y Conclusiones

**Objetivo.** Reescribir **solo** las subsecciones *Resultados* y
*Conclusiones* de los dos resúmenes ejecutivos, con dos requisitos:

1. **Basarse en los resultados totales** ya consolidados en el Capítulo de
   Resultados (`sec:results`) y en las Conclusiones (`sec:conclusion`,
   C1–C6). Es decir, sintetizar los hallazgos finales del barrido OFAT:
   dominancia de la topología ($R=0{,}87$ mundo pequeño vs $R=0{,}59$ libre de
   escala en baseline), $\gamma$ y $f$ como palancas de cascada, asimetría de
   la siembra en hubs (brecha 31 pp en libre de escala, 4 pp en mundo
   pequeño), $p_s$/$\lambda$ como moduladores graduales, $\rho$ irrelevante,
   velocidad $t_{50}$ (~17 pasos libre de escala vs ~31 mundo pequeño), y las
   métricas que operacionalizan la superioridad cognitiva de la OTAN.
2. **El resumen en español y el inglés deben ser traducción literal el uno del
   otro.** Redactar primero una versión y traducir la otra frase a frase, sin
   divergencias de contenido ni de cifras.

**Archivos / ubicación.**

- ES: `memoria.tex`, `\sectionnotoc{Resultados}` (~líneas 263–269) y
  `\sectionnotoc{Conclusiones}` (~líneas 271–275).
- EN: `memoria.tex`, `\sectionnotoc{Results}` (~líneas 329–335) y
  `\sectionnotoc{Conclusions}` (~líneas 337–341).

**Coherencia numérica.** Las cifras del resumen deben coincidir con las del
cuerpo **tras** la Tarea 2 (figuras regeneradas). Hacer esta tarea **después**
de Resultados, o re-verificar las cifras al cierre.

**Verificación**: ES y EN dicen exactamente lo mismo (mismas cifras, mismo
orden de ideas); las cifras coinciden con `sec:results` y `sec:conclusion`.

---

## Tarea 4 — Ampliar Introducción y Motivación + Estructura del trabajo

**Diagnóstico.** La Introducción (`memoria.tex` ~líneas 386–396) es muy
escueta y prácticamente solo habla de guerra cognitiva. La *Estructura del
trabajo* (~líneas 414–424) enumera los capítulos sin desarrollar qué contiene
cada uno.

**Objetivo (hacer al FINAL, con la memoria ya cerrada).**

1. **Introducción / Motivación más extensas y con más aristas**, sin limitarse
   a la guerra cognitiva. Incorporar (apoyándose en citas ya presentes en
   `ref_tfg.bib` y el estado del arte):
   - La dimensión de **redes complejas** (aldea global de McLuhan, distancia
     media < 4 saltos de Backstrom, libre de escala vs mundo pequeño) como
     sustrato del fenómeno.
   - La dimensión de **dinámicas de contagio / psicología de la decisión**
     (umbrales de Granovetter, contagio complejo de Centola–Macy, cascadas de
     Watts) que justifica el modelo de agente.
   - La dimensión **empírica de la desinformación** (Vosoughi: lo falso viaja
     más lejos/rápido; cámaras de eco de Del Vicario).
   - El **porqué de un enfoque de simulación multiagente** y de un banco de
     pruebas abierto/reproducible (encadena con el vacío metodológico ya
     enunciado).
   Mantener el hilo hacia la pregunta de investigación; no duplicar el estado
   del arte, sino motivar.
2. **Estructura del trabajo**: desarrollar 2–4 frases por capítulo explicando
   qué contiene cada uno (Estado del arte → tres ejes; Metodología → marco
   teórico [mensaje+OODA, grafos, agentes], implementación [grafos/agentes],
   simulación [arquitectura, pipeline, diseño OFAT]; Resultados → 7 factores ×
   2 topologías, figuras y ranking; Conclusiones → C1–C6 y trabajo futuro;
   Anexos → tablas de métricas y resultados extendidos del barrido).

**Restricción.** No tocar *Objetivos* (O1–O3) salvo coherencia mínima. No
contradecir el estado del arte (congelado).

**Verificación**: la introducción cubre los tres/cuatro ejes (no solo guerra
cognitiva); cada capítulo del apartado "Estructura del trabajo" tiene una
descripción de contenido, no solo el título.

---

## Tarea 5 — Arreglos finales: índice de bibliografía + trabajo futuro

### 5a. Bibliografía en el índice

**Diagnóstico.** La bibliografía se imprime con
`\section{Bibliografía}\label{sec:bibliography}` seguido de
`\printbibliography[heading=none]`, todo dentro de `\begin{refsection}[ref_tfg.bib]`
(`memoria.tex` ~líneas 679–683). Hay que revisar cómo aparece en el índice
(`\tableofcontents`): comprobar si entra numerada y enlazada a la página
correcta, o si falta / apunta mal.

**Acción.** Compilar con la cadena **pdflatex → biber → pdflatex × 2**
(los *Citation undefined* del diagnóstico actual son por no haber corrido
biber, no un error de contenido). Tras compilar:
- Si la entrada de bibliografía no aparece o aparece descolocada en el TOC,
  fijarla con `\phantomsection\addcontentsline{toc}{section}{Bibliografía}`
  antes del `\section`/`\printbibliography`, o usar el `heading` propio de
  biblatex de forma consistente con el resto de secciones numeradas.
- Verificar que el hipervínculo del TOC salta a la página correcta.

**Verificación**: la bibliografía figura en el índice con su número/página
correctos y el enlace funciona; no hay `Citation undefined` tras biber.

### 5b. Trabajo futuro: cambio de framework por rendimiento

**Acción.** Añadir un punto nuevo a la lista de *Trabajo Futuro*
(`memoria.tex`, `itemize` ~líneas 662–672):

> **Migración de framework de simulación.** Sustituir/complementar Mesa por
> un framework de mayor rendimiento (p. ej. motor vectorizado/compilado o
> ejecución en C/Rust/GPU) para acelerar las ejecuciones del barrido y
> permitir poblaciones mayores o más réplicas Monte Carlo en el mismo
> tiempo de cómputo.

Redactar en el estilo de los demás ítems (negrita + explicación). Mantener
los puntos existentes.

**Verificación**: el nuevo ítem aparece en la lista, coherente en estilo.

---

## Orden de ejecución recomendado

1. **Tarea 1** (tablas de hiperparámetros) — autocontenida, en `met_simulacion.tex`.
2. **Tarea 2** (regenerar imágenes) — requiere autorización para ejecutar el notebook.
3. **Tarea 3** (resúmenes Resultados/Conclusiones) — después de fijar cifras de la Tarea 2.
4. **Tarea 5b** (trabajo futuro) — rápida.
5. **Tarea 4** (introducción/estructura) — al final, con la memoria ya cerrada.
6. **Tarea 5a** (bibliografía/índice) — último paso, en la compilación final.

## Checklist de cierre

- [ ] Tabla 6 partida en fijos + barridos, en el cuerpo, con justificación.
- [ ] 7 figuras de resultados regeneradas desde el notebook (mismos nombres).
- [ ] Resúmenes ES/EN: Resultados y Conclusiones reescritos y traducción literal mutua.
- [ ] Introducción/Motivación ampliada (más allá de guerra cognitiva).
- [ ] Estructura del trabajo: contenido desarrollado por capítulo.
- [ ] Trabajo futuro incluye migración de framework por rendimiento.
- [ ] Bibliografía correcta en el índice; compila con biber sin citas indefinidas.
- [ ] Partes congeladas intactas (formato, estado del arte, marco teórico,
      y resto del resumen ejecutivo).
