# Plan: Agente inteligente — refactor de `BayesianAgent` y `EmotionalBrain`

## Context

`src/agents/brain.py::EmotionalBrain` modela hoy al agente como un vector de humor por emoción con decay diario y un único umbral `theta_send`. Esto deja fuera buena parte de la fenomenología que el TFG quiere capturar:

- **Sin probabilidad explícita de emitir** — el cerebro siempre envía si supera un umbral, sin distinguir entre emitir o reenviar, ni ajustar la propensión por número de seguidores (digital) vs. confianza fija (analógico).
- **Sin tipo de mensaje** — modalidades existen en `Message` pero el cerebro las ignora; en realidad audio (analógico, "hablar") y combinaciones texto+audio+vídeo (digital) tienen distinta carga emocional efectiva.
- **Sin diferenciación gen/embedding** — el "humor" es un único `dict[Emotion, float]` sin separar predisposición estable (genética) de estado dinámico (memoria/embedding).
- **Decisión por emoción dominante** — `max(self.mood, ...)` reduce el mensaje a una sola emoción; la realidad es vectorial.
- **Sin ritmo circadiano** — la sugestionabilidad es constante; literatura muestra variación diaria sistemática.
- **Selección de destinatarios determinista** — itera todos los vecinos, sin aleatoriedad ni diferenciación por capa Dunbar / red digital.

El refactor introduce un agente más rico psicológicamente, manteniendo la firma `Brain` y el nombre `EmotionalBrain` (acordado). Cada hiperparámetro queda anclado a literatura empírica.

`steps_per_day` se fija a **24** ⇒ **1 step = 1 hora simulada**. Esto requiere actualizar `SimulationConfig.steps_per_day` (hoy 10) en `src/config.py`.

---

## Modelo conceptual

### Dos vectores de 11 dimensiones

Las 11 dimensiones son las **8 emociones de Plutchik** (joy, fear, anger, sadness, disgust, surprise, trust, anticipation — `Emotion.NEUTRAL` queda como etiqueta neutra, no entra en el vector) más **3 dimensiones cognitivas** (atención, credulidad, autoconfianza). Las dos primeras se aplican al actualizar memoria; la tercera modula la propensión a emitir.

| # | Dim | Tipo | Rol |
|---|-----|------|-----|
| 1-8 | joy, fear, anger, sadness, disgust, surprise, trust, anticipation | Emoción (Plutchik) | Carga afectiva del mensaje y de la memoria. |
| 9 | attention | Cognitiva | Multiplica el impacto del mensaje sobre memoria (filtro perceptual). |
| 10 | credulity | Cognitiva | Sustituye al uso plano de `veracity`: cuánto cree el agente lo que llega. |
| 11 | self_confidence | Cognitiva | Multiplica la probabilidad de generar mensajes nuevos (no reenvíos). |

- **`genetics: np.ndarray[11]`** — fijo por agente, ~N(μ_dim, σ_dim) acotado a `[0, 1]`. Es **amplificador**: multiplica cómo cada mensaje impacta cada dimensión del embedding.
- **`embedding: np.ndarray[11]`** — estado dinámico del agente. Es la "memoria emocional vectorial". Se actualiza por mensajes recibidos (modulado por genética × atención × credulidad × sugestionabilidad circadiana) y decae cada step (1h) por dimensión.

### Pipeline de un step (1 hora simulada)

```
observe(msg):
    1. m_emotion_vec  = vector emocional del mensaje (one-hot * emotional_load, o multi-emoción si el mensaje lo permite)
    2. modality_gain  = f(modalities)            # ver tabla más abajo
    3. impact_vec     = m_emotion_vec * modality_gain
                       * genetics                # amplificador por dim
                       * embedding[attention]    # filtro atencional
                       * (sender_trust * embedding[credulity])  # credibilidad efectiva
                       * sugestionabilidad_circadiana(hour)
    4. embedding     += impact_vec  (clamp [0,1])
    5. memoria reciente.append(msg)              # cola FIFO acotada para parent_id y forward

decay(step):
    embedding *= decay_per_step  # vector, por dimensión

decide(neighbors_trust, timestep):
    base_p = p_create_analog                    # constante en analógica
    if layer == DIGITAL:
        base_p = p_create_digital_base * (1 + log(1 + n_followers) / K_follower)
    p_create  *= embedding[self_confidence]
    p_create  *= sugestionabilidad_circadiana(hour)
    if random() < p_create: build_new_message(embedding)   # decisión sobre vector, no emoción única
    elif random() < p_forward_given_received: build_forward(last_strong_msg)
    targets = sample_targets(neighbors_trust, layer)       # ver muestreo más abajo
```

---

## Hiperparámetros con cita

Cada HY indica el rango propuesto y la referencia que lo justifica. **No se citan blogs de marketing**; se priorizan papers revisados.

### HY-1 — `p_create_analog` (prob. emitir mensaje analógico por hora)

- **Valor inicial**: `0.05` (≈ 1–2 emisiones por jornada de 16 h despierto).
- **Cita**: Dunbar, R.I.M. (1998). *Grooming, Gossip and the Evolution of Language* — humanos dedican ~20 % del tiempo de vigilia a interacción conversacional, con ~1–3 episodios de "chisme" por persona/día en la red íntima.

### HY-2 — `p_create_digital_base` y `K_follower` (prob. base digital + escala log-seguidores)

- **Valor inicial**: `p_create_digital_base = 0.02`, `K_follower = 5`.
- **Forma**: `p_create_digital = p_create_digital_base * (1 + ln(1 + followers) / K_follower)`. La forma log captura la distribución power-law observada en frecuencia de tweets.
- **Cita**: Bakshy, Hofman, Mason & Watts (2011). *Everyone's an Influencer: Quantifying Influence on Twitter*, WSDM — número de seguidores y tasa de publicación siguen power-law; usuarios con más seguidores publican más, con escalamiento sub-lineal.

### HY-3 — `modality_gain` (peso emocional efectivo por combinación de modalidades)

- **Tabla inicial**:

  | modalities | gain |
  |---|---|
  | `{TEXT}` | 1.00 |
  | `{IMAGE}` | 1.10 |
  | `{AUDIO}` (sola — caso analógico) | 1.25 |
  | `{VIDEO}` | 1.40 |
  | `{TEXT, IMAGE}` | 1.25 |
  | `{TEXT, AUDIO}` | 1.45 |
  | `{TEXT, VIDEO}` | 1.60 |
  | `{TEXT, VIDEO, AUDIO}` | 1.75 |

  Implementado como `gain = min(1.75, 1.0 + Σ_m bonus[m])` con `bonus={TEXT:0, IMAGE:0.1, AUDIO:0.25, VIDEO:0.4}` y un techo. En la capa **analógica** las modalidades se fuerzan a `{AUDIO}` (hablar cara a cara).

- **Cita**: Poria, Cambria, Bajpai & Hussain (2017). *A review of affective computing: From unimodal analysis to multimodal fusion*, Information Fusion 37 — modelos multimodales (audio+texto+visual) superan a unimodales en ~9–13 % en tareas de afecto, justificando que la combinación de modalidades amplifica el impacto emocional efectivo.

### HY-4 — `decay_per_hour[dim]` (decay por dimensión, por step de 1 h)

- **Valor inicial** (half-life por dimensión, en horas):

  | dim | half-life (h) | decay_per_hour = 2^(-1/h) |
  |---|---|---|
  | joy | 4 | 0.841 |
  | fear, anger | 6 | 0.891 |
  | sadness | 12 | 0.944 |
  | disgust, surprise | 2 | 0.707 |
  | trust | 24 | 0.971 |
  | anticipation | 8 | 0.917 |
  | attention | 1 | 0.500 |
  | credulity | 48 | 0.986 |
  | self_confidence | 24 | 0.971 |

- **Cita**: Verduyn, Delaveau, Rotgé, Fossati & Van Mechelen (2015). *Determinants of Emotion Duration and Underlying Psychological and Neural Mechanisms*, Emotion Review 7(4):330–335 — duración media de emociones varía sistemáticamente: tristeza > miedo/ira > alegría > sorpresa/asco. La parametrización por half-life refleja ese orden.
- **Cita complementaria**: Ebbinghaus, H. (1885), reformulado por Murre & Dros (2015), *Replication and Analysis of Ebbinghaus' Forgetting Curve*, PLOS ONE — decay exponencial `R = e^(-t/S)` como forma funcional general; usamos base 2 con half-life porque es más interpretable.

### HY-5 — `genetics_prior` (distribución base de la genética por dimensión)

- **Valor inicial**: `genetics[dim] ~ TruncatedNormal(μ=0.5, σ=0.15)` en `[0.05, 1.0]`. Se proyecta desde 5 rasgos OCEAN latentes para mantener correlaciones realistas (p.ej. neuroticismo → +fear, +anger, +sadness; extraversión → +joy, +trust, +self_confidence; apertura → +attention, +surprise).
- **Cita**: Costa & McCrae (1992). *Revised NEO Personality Inventory (NEO-PI-R)*; meta-análisis de Steel, Schmidt & Shultz (2008) *Refining the Relationship Between Personality and Subjective Well-Being*, Psychological Bulletin 134(1):138–161 — correlaciones estables entre Big Five y emociones; neuroticismo (r ≈ .54 con afecto negativo), extraversión (r ≈ .44 con afecto positivo).

### HY-6 — `circadian_susceptibility(hour)` (multiplicador horario de impacto y emisión)

- **Forma**: vector `S[dim]` con curvas cosenoidales desfasadas por dimensión:

  ```
  S[dim](h) = base[dim] + amp[dim] * cos(2π * (h - peak[dim]) / 24)
  ```

  | dim | peak (h) | amp | base |
  |---|---|---|---|
  | attention, credulity | 10 | 0.30 | 1.0 |
  | joy, trust | 8 | 0.25 | 1.0 |
  | fear, anger, sadness | 22 | 0.30 | 1.0 |
  | self_confidence | 16 | 0.20 | 1.0 |

- **Cita**: Golder & Macy (2011). *Diurnal and Seasonal Mood Vary with Work, Sleep, and Daylength Across Diverse Cultures*, Science 333(6051):1878–1881 — 509M tweets, 2.4M usuarios, 84 países: afecto positivo pico ~9 h, afecto negativo pico nocturno; ritmo robusto cross-cultural.
- **Cita complementaria**: Martin & Marrington (2005). *Morningness–eveningness orientation, optimal time-of-day and attitude change*, Personality and Individual Differences 39(2):367–377 — procesamiento central (vía persuasión) sigue ritmo circadiano de arousal.

### HY-7 — `theta_send_vector` (umbral vectorial de emisión)

- **Valor inicial**: `0.35` aplicado al **score** `||embedding · genetics||₂ / √11` (norma normalizada). Sustituye `theta_send` plano sobre una sola emoción.
- **Cita**: Brady, Crockett & Van Bavel (2020). *The MAD Model of Moral Contagion*, Perspectives on Psychological Science 15(4):978–1010 — la propensión a compartir crece de forma no-lineal con la activación moral-emocional total, no con una única emoción dominante.

### HY-8 — `forward_probability_base` y `forward_boost_anger`

- **Valor inicial**: `p_forward = 0.08 + 0.20 * embedding[anger] + 0.10 * embedding[surprise]`.
- **Cita**: Brady, Wills, Jost, Tucker & Van Bavel (2017). *Emotion shapes the diffusion of moralized content in social networks*, PNAS 114(28):7313–7318 — cada palabra moral-emocional adicional en un tweet incrementa retweets en ~20 %; anger y outrage son los predictores dominantes.

### HY-9 — `target_randomness_by_layer` (ε-exploración en muestreo de destinatarios)

- **Forma**: para cada potencial destinatario, `p_pick ∝ trust^α + ε`. Distintos `α` y `ε` según capa y profundidad Dunbar:

  | grupo | α (trust exponent) | ε (ruido) | basis |
  |---|---|---|---|
  | Analógico íntimo (Dunbar 5) | 2.0 | 0.05 | semanal, alta confianza |
  | Analógico cercano (Dunbar 15) | 1.5 | 0.10 | mensual |
  | Analógico afín (Dunbar 50) | 1.0 | 0.20 | trimestral |
  | Analógico extendido (Dunbar 150) | 0.5 | 0.30 | anual |
  | Digital | 0.7 | 0.35 | broadcast asimétrico |

  La pertenencia a cada capa Dunbar se infiere del `trust` actual en la arista analógica (mapeo monotónico).

- **Cita**: Dunbar (1998) ya citada + Saramäki, Leicht, López, Roberts, Reed-Tsochas & Dunbar (2014). *Persistence of social signatures in human communication*, PNAS 111(3):942–947 — estructura de capas 5/15/50/150 estable longitudinalmente; frecuencia de contacto cae por escalones.
- **Cita complementaria**: MacCarron, Kaski & Dunbar (2016). *Calling Dunbar's numbers*, Social Networks 47:151–155 — confirmación de las capas en datos de telefonía masiva.

### HY-10 — `attention_capacity` (máx mensajes procesados por step)

- **Valor inicial**: `7` mensajes/hora; resto se descarta o procesa con `attention_decay = 0.7^k` para el k-ésimo mensaje.
- **Cita**: Miller, G.A. (1956). *The Magical Number Seven, Plus or Minus Two*, Psychological Review 63(2):81–97 — capacidad de procesamiento atencional ~7±2.

### HY-11 — `self_confidence_to_create_scale`

- **Valor inicial**: `p_create *= (0.5 + embedding[self_confidence])` (rango efectivo 0.5×–1.5×).
- **Cita**: Bandura, A. (1997). *Self-Efficacy: The Exercise of Control*, W.H. Freeman — auto-eficacia modula la iniciación de comportamientos (aquí: emitir un mensaje propio vs. permanecer pasivo).

---

## Cambios en el código

### Archivos a modificar (alcance contenido)

1. **`src/agents/brain.py`** — refactor de `EmotionalBrain` manteniendo el nombre y la firma `Brain`. Cambios:
   - Reemplazar `self.mood: dict[Emotion, float]` por `self.embedding: np.ndarray[11]` y `self.genetics: np.ndarray[11]`.
   - `__init__` añade parámetros: `genetics`, `decay_per_hour`, `modality_gain`, `circadian`, `p_create_analog`, `p_create_digital_base`, `k_follower`, `theta_send`, `attention_capacity`, `forward_base`, `target_randomness`. Todos con default citado.
   - Nuevo helper privado `_message_to_vector(msg)` que construye el vector emocional desde `msg.emotion` + `emotional_load`. Cuando `Message` sea multi-emoción (futuro), aquí se generaliza.
   - Nuevo helper `_modality_gain(modalities)`.
   - Nuevo helper `_circadian_factor(timestep, dim)` con `hour = timestep % 24`.
   - `observe()` aplica el pipeline completo de impacto vectorial y mantiene una cola `_recent_msgs` (deque) para forwards.
   - `decide()`:
     - Aplica `decay_per_hour` por dimensión.
     - Calcula `p_create` con genética × self_confidence × circadiana × log(followers).
     - Decide vectorialmente (no por emoción dominante): si emite, llama a `_compose_message_from_embedding()` que escoge la emoción de salida muestreando sobre el embedding (softmax), y `emotional_load = ||emocional_8d||`.
     - Decide reenvíos sobre `_recent_msgs` con `p_forward`.
     - Muestreo de destinatarios con `_sample_targets(neighbors_trust, layer)` según HY-9.
   - Eliminar `action.__dict__.update(...)` (acordado quitar): se sustituye por campos del dataclass `Action` (añadir `emotion`, `emotional_load`, `salience`, `parent_id`, `modalities` como `Action` extendido).

2. **`src/agents/brain.py::Action`** — añadir campos opcionales `emotion`, `emotional_load`, `salience`, `parent_id`, `modalities` para no depender de `__dict__.update`.

3. **`src/agents/bayesian.py::BayesianAgent.step`** — leer los campos tipados de `Action` en vez de `getattr(action, "_emotion", None)`. También pasa a `brain.observe()` el `timestep` (necesario para circadiano) y a `brain.decide()` el conteo de seguidores (`len(predecessors)` en la capa digital) además de `neighbors_trust`.

4. **`src/agents/brain.py::Brain`** (ABC) — extender la firma de `observe` para aceptar `timestep`, y la de `decide` para aceptar `followers_by_layer: dict[Layer, int]`. Coordinado con `BayesianAgent`.

5. **`src/config.py`**:
   - `SimulationConfig.steps_per_day = 24`.
   - Nuevo `BrainConfig` con todos los HY (defaults citados arriba). Se inyecta en `AgentConfig` cuando `type == "bayesian"`.

6. **`src/model.py`** — añadir método helper `followers(node_id, layer)` para que el agente lo consulte sin recalcular sobre `MultiDiGraph` (analógica = no aplica → devuelve `0`).

7. **`src/messages.py::Message`** — sin cambios estructurales obligatorios; opcionalmente añadir validador para garantizar que la capa analógica fuerza `modalities = {AUDIO}` (puede hacerse en `NetworkModel.make_message`).

8. **`src/agents/stochastic.py`** — sin cambios, sigue siendo el baseline simple.

### Archivos NO tocados

`src/graphs/*`, `src/datacollector.py`, `src/simulation.py`, notebooks. El refactor es local a la capa de agentes.

---

## Verificación

1. **Tests unitarios nuevos** (`tests/test_brain.py` — crear):
   - `test_decay_halves_after_halflife()` — tras `h` steps el componente cae a ~0.5.
   - `test_modality_gain_monotonic()` — `{TEXT,VIDEO,AUDIO}` > `{TEXT,VIDEO}` > `{TEXT}`.
   - `test_circadian_peaks()` — `attention` máxima ~h=10, `anger` máxima ~h=22.
   - `test_p_create_digital_grows_log_with_followers()` — slope ≈ `1/K_follower` en escala log.
   - `test_target_sampling_respects_layer_randomness()` — Monte Carlo: capa Dunbar-150 tiene mayor entropía de elección que Dunbar-5.

2. **Ejecución E2E**: `python -m src.simulation` con `MultiLayerConfig` (10k nodos, 60 días = 1440 steps). Verificar en el CSV de trazas:
   - Distribución horaria de emisiones tiene picos cerca de 10h (positivo) y 22h (negativo).
   - Mensajes con `modalities={TEXT,VIDEO,AUDIO}` y `emotional_load` alto generan más reenvíos en t+1, t+2 que solo `{TEXT}`.
   - Agentes con `len(predecessors)` digital alto emiten más.

3. **Notebook de validación** (`src/notebooks/agente_inteligente.ipynb` — opcional, sólo si tras la implementación queremos visualizar): heatmap embedding × tiempo de un agente representativo, curva de decay observada vs. teórica por dimensión.

4. **`mypy --strict src/agents/`** debe pasar sin nuevos `Any`.

---

## Resumen de HY y citas (índice)

| HY | Parámetro | Cita principal |
|---|---|---|
| HY-1 | `p_create_analog` | Dunbar (1998) |
| HY-2 | `p_create_digital_base`, `K_follower` | Bakshy et al. (2011) WSDM |
| HY-3 | `modality_gain` | Poria et al. (2017) Information Fusion |
| HY-4 | `decay_per_hour[dim]` | Verduyn et al. (2015); Murre & Dros (2015) |
| HY-5 | `genetics_prior` | Costa & McCrae (1992); Steel et al. (2008) |
| HY-6 | `circadian_susceptibility` | Golder & Macy (2011) Science; Martin & Marrington (2005) |
| HY-7 | `theta_send_vector` | Brady, Crockett & Van Bavel (2020) MAD model |
| HY-8 | `forward_probability` | Brady et al. (2017) PNAS |
| HY-9 | `target_randomness_by_layer` | Saramäki et al. (2014); MacCarron et al. (2016) |
| HY-10 | `attention_capacity` | Miller (1956) |
| HY-11 | `self_confidence_scale` | Bandura (1997) |
