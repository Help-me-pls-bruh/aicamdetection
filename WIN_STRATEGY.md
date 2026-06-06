# SentinelAI — Win Strategy & Judge Q&A Battle Plan

> Goal: maximise score on the rubric (**Problem 30% · AI & System Design 40% ·
> Prototype/Feasibility/Impact 30%**) and survive 6 minutes of Q&A without a dent.
> No one can *guarantee* a win — but this removes the ways teams usually lose.

---

## 1. THE META-GAME — how judges actually score

Judges reward, in order:
1. **A clear, real problem** they recognise (Malaysian, everyday). → nail in 45s.
2. **AI they can understand AND that's genuinely technical** (40% — your biggest
   lever). Vague "we use AI/ML" loses; a worked formula + named algorithms wins.
3. **A prototype that visibly works**, with honesty about limits.
4. **Confidence + team that clearly knows its own system** in Q&A.

Teams usually LOSE by: hand-wavy AI, overclaiming ("it's production-ready / 99%
accurate"), a demo that breaks with no backup, dodging the ethics/bias question,
or one member not knowing the system. **Avoid those five and you're top-tier.**

**Your job: make a judge able to tick every rubric line out loud.** We literally
say "the problem is…", "the AI is…", "the prototype shows…" so they can't miss it.

---

## 2. YOUR 5 "WOW" WEAPONS (rehearse these until automatic)

These are the moments that score. Deploy them deliberately.

1. **The 18% → 79% fusion reveal.** "Running alone = 18%, we ignore it. Running +
   chased + bag = 79% = CRITICAL." This proves real probabilistic engineering, not
   if-statements. **Highest-value 15 seconds you have.**
2. **HDBSCAN over K-means.** One sentence shows you chose an algorithm for a
   reason: "crime is noisy and irregular; K-means forces round blobs and is fooled
   by outliers — HDBSCAN filters noise." Signals real ML literacy.
3. **Uber H3 hexagons.** "Squares have unequal neighbour distances; hexagons have
   6 equidistant neighbours — fair nearest-patrol maths. Same as Uber." Memorable +
   visual on the map.
4. **Per-event-type decay.** "A jogger fades in a minute; a weapon stays weighted
   for five — so no permanent red zones and no alert fatigue." Shows you solved a
   *real* failure of past systems.
5. **The closed loop.** "Officer taps true/false → it retrains → it gets smarter
   every day. Static CCTV depreciates; ours appreciates." A strong closing image.

If you only land #1 and #3, you're already ahead of most teams.

---

## 3. PRESENTATION DELIVERY PLAYBOOK (the 6 minutes)

- **Open with a scene, not a definition.** The Jalan Alor snatch-theft. Make them
  *feel* the delay problem before you mention AI.
- **State the rubric words out loud** (subtly): "the problem…", "our AI…", "our
  prototype…". Judges scoring live love this.
- **Talk to the judges, not the poster/screen.** Glance, then re-engage eyes.
- **Show, don't tell, at the demo.** Let the hexagon map and the dispatch card do
  the talking; narrate in one line each.
- **Pace:** slow down on the 18%→79% moment — that's your peak. Speed up on
  housekeeping.
- **Hand off cleanly** between speakers ("…now X will show the response layer").
- **End on the line:** "Not a camera that detects a person — a self-improving
  prevention platform. Smart city, safe city." Then stop. Don't trail off.
- **Time it:** practice to 5:40 so you have buffer. Going over looks unprepared.

---

## 4. DEMO DISCIPLINE (this is where teams crash — don't)

- **Have everything already running before you walk up** — backend + dashboard
  open, camera tested, on the right tabs. Never install or load live.
- **BACKUP PLAN (do this!):** record a **30–60s screen video** of (a) the hexagon
  map refreshing, (b) a dispatch recommendation, (c) the camera detecting a
  person/knife. If wifi/camera/laptop fails on the day, you play the video and keep
  talking. *A dead demo with no backup is the #1 killer.*
- **If no camera on the day:** run `python demo_simulate.py` so the dashboard lights
  up with events + dispatches automatically.
- **Pre-stage the camera props:** the knife and bag within reach; know they detect.
- **Know the failure recovery line:** "the live feed is having a network moment —
  here's the recording of it working," said calmly, costs you almost nothing.

---

## 5. THE Q&A PLAYBOOK (6 minutes — win it on tactics)

- **Assign owners NOW:** one person owns *AI/maths* questions, one owns
  *system/feasibility*, one owns *impact/ethics*. Decide who speaks first.
- **Answer shape (20–30s):** ① direct answer in one sentence → ② one reason/proof
  → ③ stop. Don't ramble; rambling invites follow-ups you don't want.
- **"Great question" + bridge** buys you 2 seconds to think. Use sparingly.
- **Never bluff.** If you don't know: "We haven't tested that yet — here's how we'd
  find out: …". Judges respect this far more than a made-up answer.
- **Use honesty as armour:** "that part is simulated; the engine behind it is real"
  disarms gotchas instantly.
- **Bridge back to a weapon:** end tough answers by returning to a strength
  ("…and that's exactly why the per-event decay matters").
- **Don't argue with a judge.** "That's a fair point — our mitigation is…".

---

## 6. ANTICIPATED QUESTION BANK (30+, grouped, with sharp answers)

### A. Problem & relevance (Criterion 1 — 30%)
1. **"Is this really a problem in Malaysia?"** → Yes: 2,000+ snatch-thefts in KL in
   2019, ~77% of break-ins at night, crime clustered in known districts, and
   policing is reactive with siloed data. Maps to KL City Plan 2040's street-crime KPI.
2. **"Who is your actual user?"** → Primary: PDRM (dashboard + dispatch). Secondary:
   citizens (safety app, esp. women at night). Tertiary: city planners (analytics).
3. **"Why hasn't this been done already?"** → The data exists but in **silos** —
   nobody has fused CCTV + records + reports into one real-time score. That fusion
   is our contribution.

### B. AI & system design (Criterion 2 — 40% — expect the most, go deep)
4. **"Walk me through your AI pipeline."** → 5 models: A HDBSCAN (spatial), B SARIMA
   (temporal) → P_base; C YOLO+ByteTrack+behaviour → events; D fusion → R_zone; E
   feedback → retrain.
5. **"Explain the fusion formula."** → `P_event = conf × reliability`; `P_combined =
   1 − Π(1 − P_event)`; `× W_context`; `R_zone = 0.4·P_base + 0.6·P_realtime`.
   18% alone → 79% combined.
6. **"Why HDBSCAN, not K-means/DBSCAN?"** → Varying-density, arbitrary-shape clusters
   + noise filtering; K-means forces round equal blobs and is distorted by outliers.
7. **"Why SARIMA, not an LSTM/Prophet?"** → SARIMA is the right tool for strong
   *seasonal* signals (weekly/festive) with limited data and is explainable; a deep
   model would overfit our data size and be a black box. (Honest + shows judgement.)
8. **"Why hexagons (H3)?"** → Equal area + 6 equidistant neighbours → fair
   nearest-patrol/coverage maths; square grids distort distance. Uber's library.
9. **"How do AI, hardware, software and users interact?"** → Camera HW runs AI at
   the edge → sends metadata → software brain (fusion + DB) → users (police
   dashboard / citizen app) → officer feedback retrains the AI. One closed loop.
10. **"What does the per-event decay actually do?"** → Each event type fades at its
    own rate (`e^(−λ_type·t)`), so risk reflects current reality — kills permanent
    red zones and alert fatigue.
11. **"Is your behaviour detection real or rule-based?"** → It's tracking-based
    heuristics over ByteTrack (speed, direction, proximity) for 5 behaviours — honest:
    not deep pose estimation yet; that's on the roadmap.
12. **"How real-time is it?"** → Detection per frame; risk recomputed continuously;
    target <30s detection-to-dispatch.

### C. Prototype, feasibility & impact (Criterion 3 — 30%)
13. **"What's real vs. simulated?"** (THE honesty question — nail it) → **Real &
    running:** YOLO detection, HDBSCAN, SARIMA, the fusion engine + per-event decay,
    Uber H3 dispatch, the database, the dashboard, the live camera. **Simulated for
    the demo:** patrol GPS positions, and the *live map's fast scoring is driven by
    simulated event feeds* so it animates for you. **Roadmap:** mobile app, edge
    chips, production data pipeline.
14. **"Wait — the map scores look random. Is anything actually computed?"** (likely
    follow-up — be ready) → "The map is a **live visualisation** fed by simulated
    sensor data so it moves during the demo. The **scoring engine behind it is
    real** — here on the Zone Detail you can see the actual formula compute P_base,
    P_realtime and R_zone from events. In deployment the same engine runs on real
    feeds instead of simulated ones." *(This protects you completely — say it
    confidently.)*
15. **"Where's your training data? Real KL crime data?"** → We seeded realistic
    synthetic data modelled on KL hotspots/timing for the prototype; production reads
    PDRM/DOSM open data via API. The pipeline doesn't change.
16. **"Can this actually deploy? Cost?"** → It's **additive** — retrofits existing
    CCTV (edge module), reads existing police records, sends metadata not video
    (~95% bandwidth saved). No camera replacement. Cost is edge modules + servers,
    not a new camera grid.
17. **"How does it scale to 500 cameras?"** → Edge does the heavy vision locally;
    only tiny JSON metadata hits the server, so the central load stays small. Zones
    are independent → horizontally scalable.
18. **"What's your accuracy?"** → As a prototype we prove the **end-to-end workflow
    and the maths**; accuracy improves via the feedback loop with real data. We won't
    quote a fake number. (Confidence > a fake statistic.)

### D. Ethics, privacy, bias (predictive policing IS controversial — judges will probe)
19. **"Isn't predictive policing racially/income biased — like PredPol?"** → We
    designed against exactly that: HDBSCAN noise-filtering, **decay** prevents
    permanent red zones (the main bias trap), and the feedback loop runs **equity
    audits** — if predictions diverge from reality by area, weights recalibrate. And
    crucially: **it recommends; a human officer decides.**
20. **"Privacy / PDPA?"** → Edge nodes transmit **metadata only, never raw video**;
    face-matching is a **narrow wanted-list**, not mass facial recognition — a hard
    architectural boundary, not a policy promise.
21. **"What if the AI is wrong (false positive/negative)?"** → Probabilistic fusion +
    decay cut false positives; humans confirm every alert; every outcome is logged to
    improve the model. We never auto-arrest — we **inform** a human.
22. **"Could this enable over-surveillance / a police state?"** → It's scoped to
    public-safety hotspots, metadata-only, no facial DB, human-in-the-loop, and
    auditable — the opposite of opaque mass surveillance.

### E. Differentiation & novelty
23. **"What's genuinely novel — isn't this just off-the-shelf tools glued together?"**
    → The novelty is the **fusion**: turning many weak signals into one explainable
    probabilistic score, with **per-event decay** and a **history+live blend**, then
    closing the loop to **dispatch + learning**. The components are proven; the
    *integration and the scoring model* are ours.
24. **"How are you different from existing CCTV / PredPol / ShotSpotter?"** → CCTV
    records; PredPol only predicts; ShotSpotter only detects gunshots. We do
    **predict + detect + fuse + dispatch + learn** in one loop, privacy-first.

### F. Stress / gotcha
25. **"If you were a criminal, how would you beat it?"** → Avoid cameras / act
    normal — true of any system. That's why we fuse multiple signals and history, so
    a single evasion doesn't blind it, and why citizen reports cover CCTV blind spots.
26. **"What's the weakest part of your prototype?"** → Honest: behaviour detection is
    heuristic not deep-pose yet, and patrol GPS is simulated. Both are clearly scoped
    on our roadmap — the architecture already supports them.
27. **"What did YOU build vs. download?"** → Off-the-shelf: YOLO, ByteTrack, the H3
    library, statsmodels. **Ours:** the fusion engine + per-event decay, the zone/risk
    pipeline, the dispatch logic, the data schema, the dashboard, the integration.
28. **"What was the hardest part?"** → (Have a real answer ready — e.g., getting the
    multi-signal fusion + decay to behave realistically, or wiring the live H3 map.)
29. **"Show me it detect something right now."** → Be ready: camera on the knife/bag,
    or `demo_simulate.py`. Never fumble this.

### G. Business / next steps
30. **"Who pays / business model?"** → City/PDRM as a public-safety SaaS on existing
    infrastructure; ROI from existing-CCTV value + reduced response cost.
31. **"What would you build next with more time?"** → Real patrol-GPS integration,
    the citizen mobile app, edge-AI hardware, and pose-based behaviour.
32. **"Is it ready for real use?"** → It's a **working prototype** proving the full
    workflow; production needs real data integration, hardening, and field trials —
    we're upfront about that.

---

## 7. KILLER ONE-LINERS (memorise; drop them naturally)
- *"Running alone = 18%. Running + chased + bag = 79%. That's the whole idea."*
- *"We don't replace the cameras — we give them a brain."*
- *"It recommends; humans decide; it learns from the outcome."*
- *"Change the data source, not the engine."*
- *"Static CCTV depreciates. Ours appreciates."*
- *"Squares lie about distance. Hexagons don't."*
- *"Smart city, safe city."*

---

## 8. THINGS TO NEVER SAY
- ❌ "It's 99% accurate / production-ready / will eliminate crime." (overclaim = death)
- ❌ "We use AI/machine learning" with no specifics. (name the models + why)
- ❌ "It just works" when asked how. (show the formula)
- ❌ Bluffing a number you don't have.
- ❌ "Uhh I'm not sure who did that part." (every member owns the whole system)
- ❌ Badmouthing police or other teams.

---

## 9. POSTER STRATEGY (since you present with a poster)
- **Top third = the hook + one big architecture diagram** (Data → SEE → THINK →
  ACT → LEARN). Judges read top-down; lead with the picture.
- **Center = the fusion formula + the 18%→79% example**, big and readable. This is
  your 40%-criterion centerpiece.
- **One H3 hexagon-map visual** — instantly communicates the innovation.
- **Bottom = impact numbers + "real vs simulated" honesty box** (judges love it).
- **Minimal text, big fonts, KINO title.** A wall of text loses. Point at sections
  as you speak so the poster *guides* your talk.

---

## 10. PRE-COMPETITION CHECKLIST (the day before + the morning of)
- [ ] Laptop charged + charger; don't rely on wifi (use phone hotspot backup).
- [ ] Backend + dashboard launch tested from cold; know the exact commands.
- [ ] Camera tested; knife + bag props packed.
- [ ] **Backup demo video recorded** (map + dispatch + camera).
- [ ] `demo_simulate.py` tested as the no-camera fallback.
- [ ] Each member can answer any question (cross-train on §6).
- [ ] Roles assigned: speaker order + who-owns-which-Q&A.
- [ ] Script timed to ≤ 5:40. Run it 3× out loud.
- [ ] One printed copy of the 6-min script + this Q&A bank.
- [ ] Decide your honest "real vs simulated" sentence and rehearse it word-for-word.

---

## 11. SUGGESTED SPEAKER SPLIT (3 people)
- **Speaker 1 (Problem + Close):** §1 hook, §4 close. Owns *problem/impact/ethics* Q&A.
- **Speaker 2 (The AI brain):** §2 SEE + THINK, the 18%→79% reveal. Owns *AI/maths* Q&A.
- **Speaker 3 (Response + demo):** §2 ACT + §3 prototype/demo driver. Owns
  *system/feasibility/demo* Q&A.
- Everyone can answer everything, but there's a clear first-responder per topic.

---

### The single most important thing
Your strongest, most honest, most memorable asset is the **18% → 79% fusion moment
backed by a working live demo**. Lead the judges to it, land it cleanly, and back
every claim with "real vs simulated" honesty. That combination — real engineering,
shown working, explained simply, owned confidently — is what wins.
