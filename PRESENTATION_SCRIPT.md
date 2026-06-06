# SentinelAI — Judge Presentation Pack

> Based only on what we actually built. Honest about what is real vs. simulated.

---

# PART 1 — The Essential Parts (what to highlight)

Our system has **three layers**: it **SEES**, it **THINKS**, and it **ACTS**.

### Layer 1 — SEE (perception)
1. **Multi-source data ingestion** — CCTV AI, police records, citizen reports, IoT
   sensors. Crime types are normalised, coordinates validated, duplicates removed.
2. **CCTV AI detection** — YOLO real-time object detection that auto-selects the
   best model for the hardware. Detects **person, bags, vehicles, knife/weapon**.
   Runs on a webcam *or* a real TP-Link Tapo CCTV (RTSP) with auto-reconnect.
3. **Tracking** — ByteTrack gives every person a persistent ID across frames.
4. **Behaviour analysis** — from tracking we infer **running, chasing, loitering,
   fighting, crowd anomaly**. Each becomes an event with a confidence score.
5. **Face recognition** — DeepFace matches faces against a wanted-persons list.

### Layer 2 — THINK (the brain — our core innovation)
6. **Historical intelligence**
   - **HDBSCAN** clusters past crimes into spatial **hotspots** (and ignores noise) → `P_spatial`
   - **SARIMA** forecasts crime by **time** (night/day/weekend patterns) → `P_time`
   - Baseline: `P_base = 0.5·P_spatial + 0.5·P_time`
7. **Probabilistic Risk Fusion Engine** — turns many uncertain signals into one
   number:
   - `P_event = AI_confidence × Event_Reliability_Weight`  (weapon 0.9, running 0.3…)
   - `P_combined = 1 − Π(1 − P_event_i)`  (chance at least one is a real threat)
   - `W_context = W_time × W_crowd × W_recency × W_zone`
   - `P_realtime = P_combined × W_context`
   - **Final:** `R_zone = 0.4·P_base + 0.6·P_realtime` → a live 0–100% risk per zone
8. **Per-event-type redundancy decay** — every crime category fades at its **own
   rate**: a "running" event expires in ~60 s, a "weapon" stays weighted ~300 s,
   a "wanted face" ~600 s. Stale signals don't inflate risk; serious ones linger.

### Layer 3 — ACT (response)
9. **Alert system** — LOW / MEDIUM / HIGH / CRITICAL, auto-fires at HIGH+ with a
   cooldown so it never spams; special **WANTED PERSON** alerts.
10. **Uber H3 patrol dispatch** — the city is split into **hexagons** (~0.74 km²
    each). Every incident is indexed to a hexagon, each patrol owns a coverage
    zone, and a high-risk event is matched to the **nearest patrol with distance
    + ETA**. Dispatch can fire automatically on an alert.
11. **Continuous learning feedback loop** — officers mark each alert true/false;
    the system reinforces or penalises that zone and retrains over time.

### The control surface
12. **Command-center dashboard** — a live **hexagon risk map** of the whole city,
    a **live incident feed**, the **patrol dispatch panel**, CCTV monitor, alerts,
    analytics, and officer feedback.

### Tech stack (one slide)
`YOLO · ByteTrack · DeepFace · OpenCV` (vision) · `HDBSCAN · SARIMA · Uber H3 ·
custom fusion math` (intelligence) · `Flask + SQLite` (backend) · `Streamlit +
Plotly` (dashboard) · `TP-Link Tapo RTSP` (camera).

### The one-sentence pipeline
```
Data + CCTV → AI detection + behaviour → Risk Fusion (history + real-time)
   → Alert → Uber H3 nearest-patrol dispatch → Officer feedback → learns
```

---

# PART 2 — The Spoken Script (~6–8 minutes)

*Speaker cues in [brackets]. Demo cues in **[SHOW: …]**.*

---

## 1. The hook (30 sec)
"Good [morning/afternoon], judges. Imagine a snatch-theft happening on a busy
street in Kuala Lumpur. By the time someone calls the police, gives the address,
and a patrol is found and sent — the suspect is long gone. The problem isn't a
lack of cameras. It's that nobody is *watching all of them at once*, and nobody
can instantly decide *where the danger is* and *who to send*.

That is the gap our project closes. We call it **SentinelAI**."

## 2. The big idea (30 sec)
"SentinelAI is an **AI crime-prevention and response platform**. In one sentence:
it **watches** CCTV with AI, **calculates** how dangerous each area is in real
time, and **recommends the nearest patrol** to respond — automatically.

It works in three layers: it **SEES**, it **THINKS**, and it **ACTS**."
**[SHOW: the dashboard — the live hexagon map of KL.]**

## 3. Layer 1 — SEE (1 min)
"First, perception. Our system takes a live camera feed — this can be a webcam,
or a real TP-Link CCTV camera over the network.

A YOLO model detects objects every frame — people, bags, vehicles, and weapons
like a knife. A tracker called ByteTrack gives each person a unique ID, so we can
follow movement. From that movement we recognise **behaviours** — someone
**running**, one person **chasing** another, **loitering**, **fighting**, or a
sudden **crowd surge**. We also run face recognition to flag a **wanted person**.

Each of these becomes an *event* with a confidence score. But — and this is the
key — one event alone doesn't mean a crime. So we don't stop at detection."

## 4. Layer 2 — THINK (2 min — the star of the show)
"This is our core innovation: the **Risk Fusion Engine**. It answers one question —
*'How dangerous is this area, right now, on a scale of 0 to 100?'*

It combines two kinds of intelligence.

**One — history.** Using three years of crime data, **HDBSCAN** clusters the city
into crime **hotspots**, and **SARIMA** learns the *time* patterns — crime is
higher at night, on weekends, near certain areas. Together they give a baseline
risk for any place and time.

**Two — what's happening live.** Every AI event is weighted by how reliable it is —
a detected **weapon** is weighted 0.9, a person **running** only 0.3, because
running isn't always a crime. We then combine all active events with a
probability formula — *the chance that at least one of them is a genuine threat* —
and multiply by context: time of day, crowd density, how recent, and whether it's
a known hotspot.

Finally we fuse history and real-time into a single score:
**40% history, 60% live.**

And one detail we're proud of: **each type of event fades at its own speed.** A
'running' alert becomes irrelevant in about a minute, but a 'weapon' stays
significant for five. So the risk score reflects what's *actually still
dangerous*, not what happened and ended."
**[SHOW: pick a zone → the risk score and the P_base / P_realtime breakdown.]**

## 5. Layer 3 — ACT (1.5 min — the second star)
"A risk score is useless without a response. This is where we use **Uber's H3
hexagonal grid**.

Most systems split a city into squares. But with squares, your diagonal
neighbour is further than your side neighbour — distances are inconsistent. H3
uses **hexagons**, where all six neighbours are **equidistant**. We split KL into
hundreds of hexagons, each about **0.74 square kilometres**."
**[SHOW: the hexagon map filling the city — green safe, amber medium, red high.]**

"Every patrol unit owns a **coverage zone** of hexagons. So when a high-risk event
fires, the system converts the location to a hexagon, finds the **nearest
available patrol**, and returns the **distance and the estimated response time** —
instantly."
**[SHOW: Patrol Dispatch tab → select a high-risk zone → 'Recommend Patrol' →
the ACTIVE INCIDENT card with nearest patrol, distance, ETA.]**

"And it can happen **automatically**: a CRITICAL alert can dispatch the nearest
unit without a human clicking anything."

## 6. It gets smarter (45 sec)
"The system also **learns**. After each response, an officer marks whether it was
a real crime or a false alarm. A real crime **strengthens** that area's risk
signals; a false alarm **reduces** them. Over time, the predictions get more
accurate — it adapts to the city it's deployed in."

## 7. Honesty + scalability (45 sec)
"We want to be transparent about what is real and what is simulated, because we
think that's more credible than pretending.

The AI detection, the risk maths, the HDBSCAN and SARIMA models, the Uber H3
indexing, the dispatch logic, the database, the dashboard — **all of that is real
and running**. What we **simulate** is the patrol units' GPS positions and some of
the live demo data, because we don't have access to a real police fleet.

But the architecture is built so that going live means **only changing the data
source** — plug in real patrol GPS, real CCTV feeds, real police records — and the
same engine runs. It's designed to scale from one camera to a whole city."

## 8. The close (30 sec)
"To summarise — SentinelAI turns passive cameras into an **active prevention
network**. It sees crime forming, calculates the danger, and sends the nearest
help, while learning the whole time.

It's not just *'a camera that detects a person.'* It's a complete **crime
prevention and response platform** — and we built it as students, in three months.
Thank you. We'd love to take your questions."

---

# PART 3 — Likely judge questions + answers

- **"Is the patrol data real?"** → No — patrol GPS is simulated for the prototype.
  Everything else (detection, risk engine, H3, dispatch logic) is real. Going live
  means swapping the data source, not rewriting the system.
- **"Why hexagons, not a normal map/grid?"** → Equal areas and 6 equidistant
  neighbours → fair, consistent nearest-patrol and coverage maths. It's the same
  system Uber uses for dispatch.
- **"How is this different from normal CCTV / motion detection?"** → Motion
  detection only says 'something moved.' We classify *what* and *who*, score *how
  dangerous*, fuse it with history, and *act* on it with a patrol recommendation.
- **"What about false alarms / privacy?"** → The decay + reliability weighting
  reduce false alarms, and the officer feedback loop keeps improving it. A real
  deployment would add privacy/data-governance controls.
- **"What's your accuracy?"** → For a prototype we focus on the *workflow and
  architecture* being correct end-to-end; accuracy improves with real data and the
  feedback loop. (Be honest — don't quote a fake number.)

---

# PART 4 — Suggested live-demo order (2–3 min)
1. **[Risk Map tab]** — "The whole city, split into Uber H3 hexagons, scored live."
2. **[Point at red hexes]** — "Only 2–4 high-risk zones at a time — these are where
   danger is concentrated right now."
3. **[Live incident feed]** — "Real-time events as they're detected — theft,
   running, burglary."
4. **[Patrol Dispatch tab → Recommend Patrol]** — "An incident fires → nearest
   patrol, distance, ETA — instantly."
5. **[CCTV Monitor tab, if camera ready]** — show live YOLO boxes; hold up a
   knife/bag → weapon/object detected → risk spikes.
6. **[System Info tab]** — show the architecture diagram and the risk formula.
