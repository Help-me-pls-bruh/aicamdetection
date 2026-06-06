# SentinelAI — Judge Presentation Pack (Detailed Edition)

> Team **Technosapiens** · *"Smart-city = Safe-city"*
> Tagline: **"The Waze for Crime — a real-time AI system that prevents crime
> before it happens, not after."**
>
> This pack is built from **what we actually implemented**. Where something is a
> design target or simulated for the prototype, we say so plainly — judges trust
> honesty more than hype.

---

# PART 1 — Essential Parts (the full technical breakdown)

Our system has **three layers — it SEES, it THINKS, and it ACTS** — wrapped in a
**self-learning loop**. Internally these are **five AI/data models, Model A–E**,
unified by one probabilistic fusion engine.

---

## 0. The problem we are solving (why this matters)
- KL's most common crimes are **property crimes** — theft, snatch theft, burglary;
  in 2019 alone there were **2,000+ snatch-theft/robbery reports**.
- Crime **concentrates in space** — Bukit Bintang, Chow Kit, KLCC, Chinatown,
  KL Sentral, Setapak, Wangsa Maju — and **in time** — evenings, nights,
  weekends, festive periods (**~77.6% of break-ins happen at night**).
- Today's policing is **reactive**: CCTV is mostly a *recording* tool reviewed
  *after* the fact; patrols are spread evenly so high-crime zones stay
  understaffed; and there is a **delay between report and arrival** that lets
  suspects escape.
- The deeper failure is **fragmentation** — CCTV, police records, and transit
  data sit in **separate silos** with no shared, real-time picture.

**Our thesis:** the city doesn't need more cameras — it needs **intelligence that
fuses what already exists, scores danger in real time, and dispatches the nearest
help automatically.**

---

## Layer 1 — SEE (perception)

**1. Multi-source data ingestion**
- Designed to fuse **four streams**: police records (PDRM/DOSM), AI-CCTV event
  metadata, citizen app reports, and map/geo-context (OpenStreetMap).
- Every input is forced into **one canonical schema** —
  `[zone_id, latitude, longitude, timestamp, event_type, confidence_score, source]`.
  This "data contract" is what makes multi-source fusion possible.
- On ingest we **validate** coordinates, **normalise** crime-type names, and
  **de-duplicate** (same type, near-same place, within a 5-minute window).
- *Built now:* CCTV-AI + citizen-report + seeded historical ingestion into SQLite.
  *Prototype note:* live PDRM/transit feeds are the production data source.

**2. CCTV AI detection — "Model C, Stage 1"**
- **YOLO** real-time object detection; the model **auto-selects by hardware**
  (lighter model on CPU, heavier on GPU) so it always runs in real time.
- Detects **person, backpack, handbag, suitcase, vehicles, chair, and knife**.
- Runs on a **webcam OR a real TP-Link Tapo CCTV** over RTSP, with **automatic
  reconnect** if the network drops.
- *Privacy-by-design intent:* in deployment the camera is an **edge node** that
  transmits only **JSON event metadata, never raw video** (~95% bandwidth saving,
  PDPA-friendly).

**3. Tracking**
- **ByteTrack** assigns every detected person a **persistent ID** across frames,
  so we can measure **speed, direction, and the spatial relationship between
  people** — the raw material for behaviour analysis.

**4. Behaviour analysis — "Model C, Stage 2" (5-class anomaly taxonomy)**
From the tracks we classify the exact five behaviours in our design:
  1. **Running / directional urgency**
  2. **Physical altercation (fighting / grappling)**
  3. **Crowd surge / dispersal anomaly**
  4. **Extended loitering** in a sensitive zone
  5. **Pursuer–target relationship (chasing)**
Each becomes an **event** with an AI confidence score.

**5. Face recognition (wanted-criminal match)**
- **DeepFace** compares detected faces against a **wanted-persons** watch-list and
  raises an immediate **WANTED PERSON** flag. (Kept strictly to a watch-list, not
  mass facial recognition.)

---

## Layer 2 — THINK (the brain — our core innovation)

**6. Historical intelligence — Model A + Model B → `P_base`**

*Model A — HDBSCAN (spatial hotspots → `P_spatial`)*
- Clusters years of geo-tagged crimes into **irregular, real-shaped hotspots**.
- **Why HDBSCAN, not K-means?** Urban crime is **non-uniform and noisy**.
  K-means forces round, equal blobs and is fooled by outliers; HDBSCAN handles
  **varying density and shape** and **filters isolated noise**, so a single random
  incident never paints a whole area red.

*Model B — SARIMA (temporal forecast → `P_time`)*
- Learns the **cyclical rhythm** of crime: Friday/Saturday-night peaks, weekday
  vehicle-theft mornings, festive spikes.
- Components: **AR** (yesterday informs today) + **I** (removes long-term drift) +
  **MA** (smooths noise) + **Seasonal** (weekly/annual cycles) → a short-horizon
  "how likely is crime here, this hour" estimate.

*Combine:* **`P_base = 0.5 · P_spatial + 0.5 · P_time`**

**7. Probabilistic Risk Fusion Engine — Model D (THE core innovation)**

Turns many **weak, uncertain signals** into one trustworthy number per zone:
- **Per-event probability:** `P_event = AI_confidence × Event_Reliability_Weight`
  (weapon ≈ 0.9, chasing ≈ 0.7, running ≈ 0.3 — because running alone isn't a crime)
- **Combine events (noisy-OR):** `P_combined = 1 − Π(1 − P_event_i)`
  — the probability that **at least one** active signal is a genuine threat.
- **Context multiplier:** `W_context = W_time × W_crowd × W_recency × W_zone`
  (night, dense crowd, just-happened, known hotspot all push risk up).
- **Real-time risk:** `P_realtime = P_combined × W_context`
- **Final fused score:** **`R_zone = 0.4 · P_base + 0.6 · P_realtime`**
  → a single live **0–100%** risk per zone.

**Worked example (this is exactly what our code computes):**
| Signal | conf × weight | P_event |
|---|---|---|
| Running | 0.6 × 0.3 | 0.18 |
| Being chased | 0.8 × 0.7 | 0.56 |
| Abandoned bag | 0.7 × 0.6 | 0.42 |

`P_combined = 1 − (1−0.18)(1−0.56)(1−0.42) = 1 − (0.82·0.44·0.58) = `**`0.79`** → **79% CRITICAL**.
> Running **alone** = 18% (ignored). Running **+** chasing **+** bag = **79%** (act now).
> **That is the leap: probabilistic fusion, not single-event rules — it slashes false alarms.**

**8. Per-event-type redundancy decay (our upgrade *beyond* the proposal)**
- The proposal had **one** 15-minute decay for everything. **We made decay
  per-category:** a `running` event expires in **~60 s**, `weapon` stays weighted
  **~300 s**, `wanted-face` **~600 s** — each recalculated on its own interval.
- Formula: each signal is faded by `e^(−λ_category · t)` before fusion, and the
  zone score itself decays continuously.
- **Why it's innovative:** it kills **"permanent red zones"** and **alert
  fatigue** — risk reflects what's *still* happening, weighting a knife far longer
  than a jogger. This is the single biggest engineering improvement we made on
  top of the original design.

---

## Layer 3 — ACT (response)

**9. Alert system (4 tiers)**
| R_zone | Level | Action |
|---|---|---|
| 0.00–0.30 | **LOW (green)** | normal patrol |
| 0.30–0.55 | **MEDIUM (yellow)** | elevated awareness |
| 0.55–0.75 | **HIGH (orange)** | priority dispatch + public alert |
| 0.75–1.00 | **CRITICAL (red)** | immediate response + escalation |
- Auto-fires at HIGH+ with a **cooldown** so it never spams; **WANTED PERSON**
  raises an instant critical flag.

**10. Uber H3 spatial intelligence + patrol dispatch (optimising response)**
- The city is tiled into **H3 hexagons (~0.74 km² each)**. **Why hexagons over
  squares?** Every hexagon has **6 equidistant neighbours**; squares don't
  (diagonals are farther) — so "nearest patrol" and coverage maths are
  **geometrically fair**. It's the same indexing Uber uses for dispatch.
- Each incident is indexed to a hexagon; each patrol **owns a coverage zone**
  (a k-ring of hexagons). A high-risk event is matched to the **nearest available
  patrol**, returning **distance + ETA** instantly — and a CRITICAL alert can
  **auto-dispatch** with no human click.
- *Built now:* full H3 grid, coverage zones, nearest-patrol + ETA, auto-dispatch.
  *Prototype note:* patrol GPS positions are **simulated** — going live means
  swapping in real vehicle GPS, nothing else changes.

---

## The self-learning wrapper

**11. Continuous learning feedback loop — Model E**
- After each response, an officer logs **TRUE_CRIME** or **FALSE_ALARM** with one tap.
- **True positive →** reinforce that HDBSCAN cluster + SARIMA seasonality.
- **False positive →** penalise that event-type/sensor in the fusion weights.
- Accumulated feedback **retrains** the models — so the system **appreciates**
  over time instead of depreciating like static CCTV.

---

## The control surface
**12. Police command-center dashboard (built in Streamlit):**
- **Live hexagon risk map** of the whole city (drill into any zone to see the
  decomposed `P_base / P_realtime` and the contributing events)
- **Live incident feed** · **patrol-dispatch panel (nearest unit + ETA)** ·
  **CCTV monitor** · **alerts + one-tap officer feedback** · **crime analytics**.

## Tech stack (one line)
`YOLO · ByteTrack · DeepFace · OpenCV` (vision) · `HDBSCAN · SARIMA · Uber H3 +
custom probabilistic fusion` (intelligence) · `Flask + SQLite` (backend) ·
`Streamlit + Plotly` (dashboard) · `TP-Link Tapo RTSP` (camera).

## Honest scope — what is real vs. simulated vs. roadmap
- **Real & running:** HDBSCAN, SARIMA, YOLO + ByteTrack + 5-class behaviour,
  the probabilistic fusion engine, **per-event decay**, Uber H3 patrol dispatch,
  the feedback loop, the database, the API, and the full dashboard.
- **Simulated for the demo:** patrol GPS positions and some live event data.
- **Design roadmap (not in prototype):** the public mobile app, edge-AI hardware
  (Jetson/Coral), the production data pipeline (Kafka/PostGIS/InfluxDB), and
  pose/gait psychology models. The architecture is built so these slot in by
  **changing the data source, not the engine.**

## The one-sentence pipeline
```
4 data streams → AI detection + 5-class behaviour → Risk Fusion (history × live)
   → tiered alert → Uber H3 nearest-patrol dispatch → officer feedback → it learns
```

---

# PART 2 — The Spoken Script (~7–9 minutes, detailed)

*Speaker cues in [brackets]. Demo cues in **[SHOW: …]**.*

## 1. The hook (40 sec)
"Good [morning/afternoon], judges. Picture a snatch-theft on Jalan Alor on a
Saturday night. Someone calls the police, tries to describe the location, an
officer is found and sent — and by the time they arrive, minutes later, the
suspect is gone. In 2019 alone, Kuala Lumpur logged **over two thousand**
snatch-theft and robbery reports, most of them at night, most clustered in just a
handful of districts.

Here's the uncomfortable truth: the city is **full of cameras**, but they're
**recorders, not preventers**. Police logs, CCTV, and transit data sit in
**separate silos**. Nobody is watching all of it at once, and nobody can instantly
decide *where* the danger is and *who* to send. That delay is where crime wins.

We are Technosapiens, and we built **SentinelAI** to close that gap."

## 2. The big idea (40 sec)
"Our tagline is *'the Waze for crime — a system that prevents crime before it
happens, not after.'*

SentinelAI fuses three intelligence streams — **historical patterns, real-time
CCTV, and behaviour** — into **one probabilistic risk score per city zone**, and
then it **acts** on that score by dispatching the nearest patrol.

It works in three layers: it **SEES**, it **THINKS**, and it **ACTS** — and it
**learns** the whole time. Under the hood that's **five AI models, A through E**.
Let me walk you through them."
**[SHOW: dashboard — the live hexagon risk map of KL.]**

## 3. Layer 1 — SEE  (Model C) (1.5 min)
"First, perception — **Model C**, our real-time computer vision, in two stages.

**Stage one:** a YOLO model detects people, bags, vehicles and weapons in every
frame, and a tracker called **ByteTrack** gives each person a **unique ID** so we
can measure their speed, direction, and how they relate to others. This runs on a
plain webcam *or* a real CCTV camera over the network — with auto-reconnect.

**Stage two** is the clever part — **behaviour**. From those tracks we classify
exactly five anomalies: **running, fighting, a crowd surge, loitering, and one
person chasing another.** We also match faces against a **wanted-person watch-list**.

But here's our design principle: **one event is never a verdict.** A person
running might be late for a train. So detection is only the input. The decision
happens in the brain."

## 4. Layer 2 — THINK  (Models A, B, D) (2.5–3 min — the centrepiece)
"The brain answers one question: *how dangerous is this zone, right now, from 0 to
100?* It fuses two kinds of intelligence.

**History — Models A and B.** Using years of crime data, **HDBSCAN** finds the
real crime **hotspots**. We chose HDBSCAN over the more common K-means
deliberately: crime isn't tidy circles — it's irregular and noisy, and HDBSCAN
**filters out random one-off incidents** instead of letting them smear a whole
area red. Then **SARIMA** learns the **time rhythm** — Friday nights, festive
spikes, the quiet weekday mornings. Together they give a **historical baseline**.

**Real-time — Model D, our core innovation: probabilistic fusion.** Watch what
this does. Every live event is weighted by how reliable it is — a detected
**weapon** counts 0.9, **running** only 0.3. Then, instead of firing on any single
event, we combine them as a probability — *the chance that at least one of these
signals is a real threat.*

Let me make it concrete."
**[SHOW: zone detail / the formula on the System Info tab.]**
"Running **alone** scores **eighteen percent** — we ignore it. But running, **plus**
being chased, **plus** an abandoned bag — the same formula now gives **seventy-nine
percent**: CRITICAL. Three weak signals become one strong, trustworthy alarm.
**That is the difference between a system that cries wolf and one police can
trust** — probabilistic fusion, not rigid rules.

We then multiply by **context** — time of day, crowd density, recency, whether
it's a known hotspot — and fuse everything: **forty percent history, sixty percent
live.**

And one detail we're genuinely proud of, because it's our improvement on the
original design: **every type of event decays at its own speed.** A 'running'
alert fades in about a minute; a detected **weapon** stays weighted for five;
a wanted face for ten. So the risk score always reflects what is **still**
dangerous — it never freezes a neighbourhood as 'permanently red,' and it never
nags officers with stale alerts. That solves the alert-fatigue problem that broke
earlier predictive-policing tools."

## 5. Layer 3 — ACT  (Uber H3 dispatch) (1.5 min — second centrepiece)
"A score is useless without a response — and this is where we use **Uber's H3
hexagonal grid.**

Most systems split a city into squares. But with squares, your diagonal neighbour
is farther than your side neighbour — distances are inconsistent, so 'nearest
patrol' is subtly wrong. **Hexagons fix that: six equidistant neighbours, equal
areas.** We tile KL into hundreds of hexagons, each about **0.74 square
kilometres** — the exact indexing Uber uses to dispatch drivers."
**[SHOW: the hexagon map filling KL — mostly green, a few amber, 2–4 red.]**
"Every patrol owns a **coverage zone** of hexagons. So when a zone goes
high-risk, the system converts the location to a hexagon, finds the **nearest
available patrol**, and returns the **distance and estimated arrival time** —
instantly."
**[SHOW: Patrol Dispatch tab → pick a red zone → 'Recommend Patrol' → ACTIVE
INCIDENT card: nearest unit, distance, ETA.]**
"And for a CRITICAL alert, this fires **automatically** — no human in the loop,
no dispatcher delay."

## 6. It gets smarter — Model E (45 sec)
"Finally, the system **learns**. After each response the officer taps **true crime**
or **false alarm**. A confirmed crime **strengthens** that hotspot and time
pattern; a false alarm **penalises** that signal. Over time the predictions sharpen
— unlike static CCTV that loses value, SentinelAI **appreciates** with every day of
data."

## 7. Honesty + scalability (50 sec)
"We want to be precise about what's real, because that's more credible than
pretending. The **AI detection, the HDBSCAN and SARIMA models, the probabilistic
fusion maths, the per-event decay, the Uber H3 dispatch, the database, the API,
and this dashboard — all of it is real and running** in our prototype.

What we **simulate** is the patrol units' GPS and some live demo data, because we
don't have a police fleet. And what's on our **roadmap** — the public Waze-style
app, edge-AI camera chips, and the big-city data pipeline — is deliberately
modular: going live means **changing the data source, not rebuilding the engine.**
It's designed to scale from one camera to a whole city, and to any ASEAN city
after that."

## 8. The close (35 sec)
"So — SentinelAI turns passive cameras into an **active prevention network.** It
**sees** crime forming, **calculates** the danger with explainable probability,
**acts** by sending the nearest help, and **learns** from every outcome.

It is not 'a camera that detects a person.' It is a complete, self-improving
**crime-prevention and response platform** — and we built the working core of it,
as students, in three months. Smart city, safe city. Thank you — we'd love your
questions."

---

# PART 3 — Likely judge questions + sharp answers

- **"Is the patrol data real?"** → No — patrol GPS is simulated for the prototype;
  everything else (detection, HDBSCAN, SARIMA, fusion, decay, H3, dispatch) is
  real. Going live = swap the data source, not rewrite the system.
- **"Why HDBSCAN over K-means?"** → Crime is irregular and noisy. K-means forces
  round, equal clusters and is distorted by outliers; HDBSCAN handles arbitrary
  shapes/densities and **filters noise**, so one random incident can't create a
  fake hotspot.
- **"Why hexagons, not squares?"** → Equal areas + 6 equidistant neighbours →
  fair, consistent nearest-patrol and coverage maths. Same system Uber uses.
- **"How is this different from normal CCTV?"** → CCTV records; we **classify**
  what/who, **score** how dangerous by fusing weak signals probabilistically, and
  **act** with a patrol recommendation — in real time, not on next-day review.
- **"How do you avoid false alarms?"** → Two ways: probabilistic fusion (single
  events stay low) and **per-event decay** (alerts auto-resolve), plus the officer
  feedback loop that penalises bad signals.
- **"What about privacy?"** → By design the camera is an edge node sending only
  **metadata, never raw video**; face-matching is a narrow watch-list, not mass
  recognition.
- **"What's your accuracy?"** → As a prototype we prove the **end-to-end workflow
  and the maths** are correct; accuracy improves with real data via the feedback
  loop. (We don't quote a fake number.)
- **"Why should we believe the impact?"** → Our targets are scaled conservatively
  from real deployments (PredPol, ShotSpotter) — see Part 5 — and framed as
  targets, not claims.

---

# PART 4 — Suggested live-demo order (2–3 min)
1. **[Risk Map tab]** — "The whole city, tiled into Uber H3 hexagons, scored live."
2. **[Point at red hexes]** — "Only 2–4 high-risk zones at once — danger
   concentrated where it actually is, right now."
3. **[Live incident feed]** — "Events as they're detected — theft, running, burglary."
4. **[Patrol Dispatch tab → Recommend Patrol]** — "Incident → nearest patrol,
   distance, ETA — instantly. CRITICAL alerts dispatch automatically."
5. **[CCTV Monitor, if camera ready]** — live YOLO boxes; hold up a knife/bag →
   weapon/object detected → risk spikes → alert.
6. **[System Info tab]** — show the architecture + the fusion formula and the
   18% → 79% worked example.

---

# PART 5 — Impact targets (framed honestly, scaled from real deployments)
> Quote these as **targets**, benchmarked from PredPol (LA), ShotSpotter (Chicago),
> and safety-app studies — not as proven results.

- **↓ 15–20%** crime in targeted categories (theft, assault)
- **↓ 40%** patrol response time via pre-positioning on risk alerts
- **< 30 s** anomaly-detected → officer-notified (vs minutes today)
- **≥ 85%** alert precision target at the 90-day feedback mark
- **3×** coverage vs CCTV-only, via citizen crowdsourcing
- **~95%** bandwidth saved (metadata, not raw video)
- Aligns with **MyDIGITAL Blueprint** & **KL City Plan 2040** (street-crime KPI),
  and **PDPA** (privacy-by-design).
