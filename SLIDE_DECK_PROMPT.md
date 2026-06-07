# SentinelAI — Slide Deck Pack (for Claude design)

Two parts:
- **PART A** — the 5 screenshots to capture yourself (full quality), and which slide each goes on.
- **PART B** — the paste-ready prompt for Claude design (copy everything in the code block).

---

## PART A — Screenshots to capture (do this first)

Both apps are running right now. Use **Win + Shift + S** (Windows Snipping) to grab
each, save them with the names below, then drop them onto the matching slide.

| Save as | What to capture | Goes on slide |
|---|---|---|
| `01_hexmap.png` | Dashboard **Risk Map tab** — the full KL hexagon map (green + amber + red) | Title + Slide 7 |
| `02_camera.png` | The **camera window** — a person with green `person/moving` box (+ a `bag` box if possible) | Slide 6 |
| `03_knife.png` | The **camera window** — holding the knife, red `KNIFE` + "WEAPON DETECTED" | Slide 6 / 10 |
| `04_dispatch.png` | Dashboard **Patrol Dispatch tab** — hex heatmap + the red **ACTIVE INCIDENT** card (click "Recommend Patrol" first) | Slide 11 |
| `05_feed.png` | Dashboard **LIVE INCIDENT FEED** panel (the coloured event cards) | Slide 10 |

> Tip: maximise the browser / camera window before snipping so the images are crisp.
> For the knife shot, turn ON all-angle mode (press `a`) and hold the knife clearly.

---

## PART B — Paste this whole block into Claude design

```
Create a modern, professional 12-slide presentation deck for a smart-city AI
competition in Malaysia. 

TEAM: Technosapiens.   PROJECT: SentinelAI.   THEME LINE: "Smart-city = Safe-city".
TAGLINE: "The Waze for Crime — a real-time AI system that prevents crime before it
happens, not after."

VISUAL STYLE:
- Dark "command-center" theme: deep navy / near-black backgrounds (#0b1f3a, #0f172a),
  white text, with risk-colour accents: green #1e9e57 (safe), amber #f5a524 (medium),
  red #e11d48 (high). A blue gradient accent (#13315c → #1d4e89).
- Bold, condensed display font for titles (art-deco / "KINO" style); clean sans-serif
  for body. Big headings, minimal text per slide, lots of breathing room.
- Each slide: a short title, 2–4 concise bullets or one key statement, and space for
  one image where marked [IMAGE].
- Footer on every slide: "Technosapiens · SentinelAI" + slide number.

SLIDES:

1) TITLE
   - Big: "SENTINEL AI"
   - Sub: "Crime Prevention & Response Platform"  ·  "Smart-city = Safe-city"
   - Small: "The Waze for Crime — prevent crime before it happens, not after."
   - [IMAGE: full-screen faded background = hexagon risk map (01_hexmap.png)]

2) THE PROBLEM
   - Title: "Crime in KL is predictable — our response isn't"
   - Bullets: 2,000+ snatch-thefts in KL (2019); ~77% of break-ins at night; crime
     clusters in known districts.  |  CCTV only RECORDS — it doesn't prevent.  |
     Police data, CCTV & transit sit in SEPARATE SILOS.  |  Policing is REACTIVE —
     help arrives after the crime.

3) OUR SOLUTION — A CLOSED-LOOP, SELF-LEARNING SYSTEM
   - Statement: "Not a CCTV add-on — a 5-layer intelligence loop."
   - 5 layers as a horizontal flow: Edge Layer → Ingestion Layer → AI Engine →
     Storage Layer → Application Layer.  Note: "Edge cameras analyse locally and
     send only metadata."

4) ONE LANGUAGE FOR EVERYTHING (Data Standardisation)
   - Title: "Every source speaks one format"
   - Inputs: CCTV · Police DB · Citizen reports · Maps  →  unified schema.
   - Show the schema as a chip/code line:
     [ zone_id · latitude · longitude · timestamp · event_type · confidence_score · source ]

5) THE AI ENGINE — THREE INTELLIGENCES
   - Title: "Three streams of intelligence, fused into one"
   - Three cards: (1) Real-time Vision (what's happening) · (2) HDBSCAN Hotspots
     (where) · (3) SARIMA Forecast (when).

6) INTELLIGENCE 1 — REAL-TIME COMPUTER VISION
   - Title: "It sees — YOLOv8 + ByteTrack"
   - Bullets: YOLOv8 (COCO) detects objects; ByteTrack gives each person a unique ID.
   - "5 behaviours classified: Running · Fighting · Crowd surge · Loitering · Chasing"
   - Key line: "These aren't treated as crimes — they're evidence that feeds the risk score."
   - [IMAGE: 02_camera.png and/or 03_knife.png]

7) INTELLIGENCE 2 — HDBSCAN SPATIAL HOTSPOTS
   - Title: "It learns WHERE — HDBSCAN on 36 months of crime data"
   - Bullets: Finds naturally-shaped crime clusters; filters isolated noise that would
     distort the map.
   - Contrast box: "HDBSCAN (density-based) vs K-Means (centroid-based) — real crime is
     messy and irregular, so density wins."
   - [IMAGE: 01_hexmap.png]

8) INTELLIGENCE 3 — SARIMA TEMPORAL FORECAST
   - Title: "It learns WHEN — SARIMA crime rhythms"
   - Bullets: Weekday vehicle-theft patterns; festive-season spikes.
   - Key line: "Predicts where risk will rise in the next 15–30 minutes."
   - Tagline under: "Now the system knows WHAT, WHERE and WHEN."

9) THE CORE — PROBABILISTIC FUSION (R_zone)
   - Title: "One explainable risk score per zone"
   - Big formula: R_zone = P_base + P_realtime + C_context
   - Three small definitions: P_base = HDBSCAN + SARIMA (history) · P_realtime = live
     CCTV + citizen reports · C_context = time of day, crowd density, recency.
   - Line: "Traditional systems make officers decide what matters. SentinelAI fuses it
     automatically."

10) FUSION IN ACTION
    - Title: "Weak signals → one trustworthy alarm"
    - Big comparison: "Running alone = <20% → ignored"  vs  "Running + chased + bag =
      70–85% → CRITICAL"
    - Note: "Per-event redundancy decay — each event fades on its own timer, so no false
      alarms and no permanently-red zones."
    - [IMAGE: 05_feed.png]

11) IT ACTS — UBER H3 PATROL DISPATCH
    - Title: "From risk score to the nearest patrol"
    - Bullets: City tiled into Uber H3 hexagons (0.72–5.16 km² / 530–1400 m); every cell
      has 6 equidistant neighbours → consistent, accurate spatial analysis.
    - Key line: "When a zone crosses the risk threshold, SentinelAI auto-finds the nearest
      available patrol and generates a dispatch."
    - [IMAGE: 04_dispatch.png]

12) IT LEARNS — CONTINUOUS FEEDBACK LOOP  /  CLOSE
    - Title: "It gets smarter every cycle"
    - Bullets: Officers log true / false positive → feedback loop → models retrain →
      historical database updates.
    - Closing line (big): "Static CCTV depreciates. SentinelAI appreciates."
    - Footer statement: "Smart-city = Safe-city."

Keep text tight and punchy — this deck supports a 6-minute spoken presentation, so the
slides should reinforce, not repeat, the speaker. Use icons where helpful.
```

---

## Notes
- If Claude design can't take images directly, generate the deck first, then drop your
  5 screenshots onto the slides marked [IMAGE].
- Want a lighter theme instead of dark? Change the VISUAL STYLE block's colours.
