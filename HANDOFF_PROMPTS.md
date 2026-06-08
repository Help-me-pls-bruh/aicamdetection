# New-Laptop Handoff Prompts

Paste **Prompt 1** first (gives context), then **Prompt 2** (runs the map + CCTV).
Both are self-contained — a fresh Claude Code session with only these files will
understand them.

---

## PROMPT 1 — Context handoff (paste this first)

```
You are helping me run an existing, finished project on a fresh laptop. Do NOT
rebuild or redesign anything — the code is complete and working. Just understand it,
then help me set it up and run it when I ask.

PROJECT: "SentinelAI" — a student competition prototype: an AI crime-prevention &
response platform for Kuala Lumpur. It has three parts:
  1) A live MAP DASHBOARD (Streamlit) — a full-KL Uber-H3 hexagon risk map, a live
     incident feed, and a Patrol Dispatch tab (nearest-patrol + ETA).
  2) A CCTV CAMERA DETECTOR (YOLOv8 + ByteTrack) — detects person/bags/vehicles/knife
     on a webcam, classifies behaviours (running, loitering, chasing, fighting,
     crowd anomaly), and flags weapons.
  3) The intelligence behind it: HDBSCAN (spatial hotspots), SARIMA (time forecast),
     and a probabilistic fusion engine that outputs one risk score per zone
     (R_zone = 0.4*P_base + 0.6*P_realtime, with per-event-type decay).

TECH STACK: Python · Flask + SQLite (backend) · Streamlit + Plotly (dashboard) ·
YOLOv8/ultralytics + ByteTrack/supervision + OpenCV (camera) · HDBSCAN · statsmodels
SARIMA · Uber H3.

KEY FILES:
  - run.py                  -> starts the Flask backend (auto-seeds the DB + trains
                               models on first run; takes a few minutes the first time)
  - dashboard/dashboard.py  -> the Streamlit dashboard (the MAP). Talks to the backend
                               on http://localhost:5000. The hexagon Risk Map tab is
                               generated client-side and works even before the backend
                               finishes.
  - test_camera.py          -> the webcam CCTV detector (opens a window; 'q' quits,
                               'a' toggles knife all-angle mode)
  - test_rtsp.py            -> same but for a TP-Link Tapo RTSP CCTV (edit RTSP_URL)
  - requirements.txt        -> all dependencies
  - backend/                -> fusion_engine, historical_engine (HDBSCAN/SARIMA),
                               realtime_detector (YOLO), patrol_dispatch, h3_utils, etc.

STATE / HONESTY: It's a working prototype. Real & running: detection, HDBSCAN, SARIMA,
fusion, H3 dispatch, dashboard. Simulated for the demo: patrol GPS positions and some
live data. The repo is at https://github.com/Help-me-pls-bruh/aicamdetection.git

Acknowledge you understand, and wait for my next instruction.
```

---

## PROMPT 2 — Set up & run the MAP and CCTV (paste after Prompt 1)

```
Set up and run this project on THIS laptop. Assume Python is installed and on PATH
(if not, tell me to reinstall Python with "Add to PATH" ticked). The project files are
in the current folder.

Do the following in order and tell me when each is ready:

1) INSTALL DEPENDENCIES (one time). Run:
   pip install flask flask-cors streamlit plotly pandas numpy scipy requests Pillow scikit-learn hdbscan statsmodels h3 opencv-python ultralytics supervision
   (This is a large download ~300-500 MB because of PyTorch. It's normal.)

2) START THE MAP — backend + dashboard, each in its OWN background process so they
   keep running:
   - Backend:   python run.py
     (First run seeds the database and trains SARIMA — wait until the API at
      http://localhost:5000/api/status responds with HTTP 200. Can take a few minutes.)
   - Dashboard: streamlit run dashboard/dashboard.py --server.port 8501
     Then open http://localhost:8501 . The "Risk Map" tab is the hexagon map; the
     "Patrol Dispatch" tab is the H3 dispatch.

3) START THE CCTV (separate process):
   python test_camera.py
   A window opens with the webcam + live detection. In that window: 'q' = quit,
   'a' = toggle knife all-angle mode. (First run auto-downloads the YOLO model
   yolov8s.pt, ~22 MB.) To start in all-angle mode instead, set the env var
   SENTINEL_KNIFE_TTA=1 before launching.

NOTES / GOTCHAS:
   - Needs a working webcam for the CCTV. For a TP-Link Tapo CCTV, edit RTSP_URL at the
     top of test_rtsp.py and run that instead.
   - Ports: backend = 5000, dashboard = 8501. If a port is "already in use", stop the
     old process first.
   - The hexagon Risk Map works even if the backend is still training.
   - Don't change any code — just install and run.

Confirm each step is up and give me the exact URLs to open.
```

---

## Tip
On the new laptop, first run:  `git clone https://github.com/Help-me-pls-bruh/aicamdetection.git`
then open that folder in VS Code / Claude Code, then paste Prompt 1.
