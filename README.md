# SentinelAI — AI Crime Prevention & Response Platform

A competition prototype that turns CCTV into a full crime-prevention pipeline:

```
CCTV (webcam / TP-Link Tapo RTSP)
      ↓
YOLO object detection (person, bags, vehicles, knife) + ByteTrack tracking
      ↓
Behaviour analysis (running, chasing, loitering, fighting, crowd anomaly)
      ↓
DeepFace wanted-person matching
      ↓
Probabilistic Risk Fusion Engine
      ↓
Alert system (HIGH / CRITICAL)
      ↓
Uber H3 spatial indexing → nearest patrol dispatch (distance + ETA)
      ↓
SQLite database  →  Flask API  →  Streamlit dashboard
```

## Core intelligence

- **HDBSCAN** — spatial crime hotspot clustering (`P_spatial`)
- **SARIMA** — temporal crime forecasting (`P_time`)
- **Risk fusion** — `R_zone = 0.4·P_base + 0.6·P_realtime` with per-event-type decay
- **Uber H3** — hexagonal indexing for patrol coverage + nearest-unit dispatch

## Quick start

```bash
# 1. install (dashboard + analytics + H3 patrol only — fast)
pip install flask flask-cors streamlit plotly pandas numpy scipy requests Pillow scikit-learn hdbscan statsmodels h3

# 2. run backend
python run.py

# 3. run dashboard (new terminal)
streamlit run dashboard/dashboard.py
```

Open http://localhost:8501

### Add the live camera (optional)

```bash
pip install opencv-python ultralytics supervision
python test_camera.py        # webcam test
python test_rtsp.py          # Tapo RTSP test (edit RTSP_URL first)
```

### Add knife detection (optional)

See **[KNIFE_TRAINING_GUIDE.md](KNIFE_TRAINING_GUIDE.md)** — a zero-ML, Colab-based
walkthrough. Drop the trained `models/knife.pt` in and it activates automatically.

## Project layout

| Folder | What's inside |
|---|---|
| `backend/` | Flask API, fusion/historical engines, detector, patrol dispatch, H3 utils |
| `dashboard/` | Streamlit operations dashboard |
| `database/` | SQLite manager + synthetic data seeder |
| `cameras/` | Webcam / RTSP stream manager |
| `training/` | Knife model dataset prep + training + verify scripts |
| `models/` | Trained weights (e.g. `knife.pt`) |

> **Prototype note:** patrol units use simulated GPS positions. The architecture
> scales to real patrol feeds — only the data source changes.

## Full install

```bash
pip install -r requirements.txt
```
