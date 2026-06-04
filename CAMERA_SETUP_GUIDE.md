# Camera & Detection — Complete Step-by-Step Guide

From "code is written" to "live demo working", in order. Follow top to bottom.

> You are here: all code is written and compiles. The only missing pieces are
> (1) installing the camera packages, (2) plugging in a camera, (3) (optional)
> training the knife model.

---

## 3-MONTH TIMELINE (suggested)

| When | Goal |
|---|---|
| **Month 1** | Webcam detection working → RTSP camera working → full dashboard demo |
| **Month 2** | Knife model trained (Colab) → integrated → weapon alerts working |
| **Month 3** | Polish, staged demo scenarios, slides, rehearse the presentation |

---

## STEP 1 — Install the camera packages (~10 min, one time)

Open a terminal in the project folder and run:

```powershell
pip install opencv-python ultralytics supervision
```

✅ **Success:** it finishes with no red errors. (This also installs PyTorch, the
engine YOLO runs on — that's why it's a bigger download.)

---

## STEP 2 — Test your laptop webcam (~5 min)

```powershell
python test_camera.py
```

- A window opens showing your webcam.
- The **first run downloads the YOLO model** (`yolov8s.pt`, a few seconds).
- You should see **green boxes around people**, and boxes around bags / chairs /
  phones if they're in view.
- Press **`q`** to quit.

✅ **Success:** boxes track you as you move. This proves detection + tracking work.

> Laptop too slow / laggy? Use the smaller model just for the demo:
> ```powershell
> $env:SENTINEL_YOLO_MODEL = "yolov8n.pt"
> python test_camera.py
> ```

---

## STEP 3 — Set up the TP-Link Tapo C200 camera (~20 min)

1. Install the **Tapo** app on your phone → create account → add the camera to **WiFi**.
2. Confirm live video works in the app.
3. Enable RTSP: **Tapo app → your camera → Settings (gear) → Advanced Settings →
   Camera Account** → create a username + password (write them down).
4. Find the camera's **IP address**:
   - Easiest: install the **Fing** app on your phone → scan network → find "Tapo".
   - Or check your router's admin page (connected devices).
   - Example: `192.168.0.101`
5. Your RTSP link is:
   ```
   rtsp://USERNAME:PASSWORD@CAMERA_IP:554/stream2
   ```
   (`stream2` = lower resolution = smoother for AI. `stream1` = HD.)

---

## STEP 4 — Verify the camera in VLC FIRST (~5 min)

**Do this before touching code** — it isolates camera problems from code problems.

1. Install **VLC Media Player**.
2. VLC → **Media → Open Network Stream** → paste your `rtsp://...stream2` URL → Play.

✅ **Success:** you see live video in VLC.
❌ If VLC fails: the problem is the camera/WiFi/credentials, **not** the code. Fix
that before continuing (recheck username/password, IP, that RTSP is enabled).

---

## STEP 5 — Run AI detection on the Tapo camera (~5 min)

1. Open `test_rtsp.py`, edit **line 21** with your real URL:
   ```python
   RTSP_URL = "rtsp://USERNAME:PASSWORD@CAMERA_IP:554/stream2"
   ```
2. Run:
   ```powershell
   python test_rtsp.py
   ```

✅ **Success:** a window shows the Tapo feed with detection boxes. This is the
"real CCTV + AI" moment that impresses judges. Press `q` to quit.

(The code auto-reconnects if WiFi briefly drops — that's already built in.)

---

## STEP 6 — Run the FULL system (camera inside the dashboard)

Two terminals:

```powershell
# Terminal 1 — backend
python run.py
```
```powershell
# Terminal 2 — dashboard
streamlit run dashboard/dashboard.py
```

Then in the browser (http://localhost:8501):
1. Go to the **CCTV Monitor** tab.
2. Choose **Webcam** (index 0) or **RTSP Camera** (paste your URL).
3. Click **Start Camera**.

✅ **Success:** live feed + detections inside the dashboard, and detected events
flow into the **risk score → alerts → H3 patrol dispatch**.

---

## STEP 7 — (Month 2) Add knife detection

Follow **KNIFE_TRAINING_GUIDE.md** (separate file). Summary:
1. Get a knife dataset from Roboflow (free).
2. Train on **Google Colab** (free GPU, ~30 min).
3. Download `best.pt`, rename to `knife.pt`, put it in the `models/` folder.
4. Restart `python run.py` — it auto-loads the model and starts emitting
   **WEAPON_DETECTED** events.

✅ **Success:** showing a knife draws a red **KNIFE** box and spikes the risk score.

---

## STEP 8 — (Month 3) Stage your demo scenarios

Use friends/props in front of the camera:

| Scenario | What judges see |
|---|---|
| Normal walking | Risk ~5% (green) |
| Someone running | Risk ~35% (yellow) |
| Person chasing another | Risk ~80% (orange) → ALERT |
| Knife shown | Risk ~95% (red) → WEAPON alert → nearest patrol dispatched |

No camera during the talk? Run `python demo_simulate.py` — it plays these
scenarios automatically so the dashboard lights up.

---

## Quick troubleshooting

| Problem | Fix |
|---|---|
| `No module named cv2` | `pip install opencv-python ultralytics supervision` |
| Webcam laggy | `$env:SENTINEL_YOLO_MODEL = "yolov8n.pt"` then run |
| RTSP won't open in code | Make sure it plays in **VLC** first |
| Stream keeps dropping | Use `stream2`, keep camera on strong WiFi |
| Knife model not loading | File must be exactly `models\knife.pt`, then restart `run.py` |

---

## The full chain you're building

```
Camera → YOLO detection (person, bags, vehicles, knife)
       → ByteTrack tracking → behaviour analysis
       → risk score → alert → Uber H3 nearest-patrol dispatch → dashboard
```
