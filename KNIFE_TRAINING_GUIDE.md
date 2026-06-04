# Knife Detection — Complete Beginner Guide (assume zero ML knowledge)

**Goal:** train a model that detects knives, then drop it into the project so the
live camera shows **"WEAPON DETECTED"** and pushes the risk score up.

**You do NOT need to understand machine learning.** Just follow the steps.

> ⚠️ **Train on Google Colab, not your laptop.** Colab gives you a free GPU.
> Training on a normal laptop CPU can take *many hours*; on Colab it's ~20–40 min.

---

## PART A — Get a knife dataset (one time, ~10 min)

1. Open https://roboflow.com and **make a free account**.
2. Open https://universe.roboflow.com and in the search bar type **`knife detection`**.
3. Click a dataset that has **lots of images** (e.g. 1,000+). Look for one already
   labelled with bounding boxes around knives.
4. Click the green **Download Dataset** button → choose format **YOLOv8** →
   choose **"show download code"**.
5. You'll see a code snippet like this — **copy it**, you'll need the 4 values:
   ```python
   rf.workspace("some-workspace").project("knife-xyz").version(3)
   ```
   - workspace = `some-workspace`
   - project   = `knife-xyz`
   - version   = `3`
6. Also copy your **Private API Key** (Roboflow → Settings → API Keys).

✅ **Success looks like:** you have an API key + workspace + project + version number written down.

---

## PART B — Train on Google Colab (free GPU, ~30 min)

1. Go to https://colab.research.google.com → **New notebook**.
2. Turn the GPU on: top menu **Runtime → Change runtime type → Hardware accelerator → T4 GPU → Save**.
3. In the first cell, paste this and press **▶** (the play button):
   ```python
   !pip install ultralytics roboflow
   ```
   **What you should see:** lots of install text ending without red errors.

4. New cell (click **+ Code**), paste this — **replace the 4 values** with yours from Part A:
   ```python
   from roboflow import Roboflow
   rf = Roboflow(api_key="PASTE_YOUR_API_KEY")
   project = rf.workspace("PASTE_WORKSPACE").project("PASTE_PROJECT")
   dataset = project.version(PASTE_VERSION_NUMBER).download("yolov8")
   print("DATA YAML:", dataset.location + "/data.yaml")
   ```
   Press **▶**.
   **What you should see:** a download progress bar, then a line like
   `DATA YAML: /content/knife-xyz-3/data.yaml`. **Copy that path.**

5. New cell, paste this — put the path from step 4 after `data=`:
   ```python
   from ultralytics import YOLO
   model = YOLO("yolov8n.pt")
   model.train(data="/content/knife-xyz-3/data.yaml", epochs=50, imgsz=640)
   ```
   Press **▶**.
   **What you should see:** a table that updates each epoch (1/50, 2/50, …) with
   numbers for `box_loss` going **down** and `mAP50` going **up**.
   **How long:** ~20–40 minutes. You can watch the numbers improve.

   ✅ **Success looks like:** it reaches epoch 50 (or early-stops) and prints
   `Results saved to runs/detect/train`.

6. New cell, paste this to grab your trained model:
   ```python
   from google.colab import files
   files.download("runs/detect/train/weights/best.pt")
   ```
   Press **▶**. Your browser downloads **`best.pt`**.

---

## PART C — Put the model into the project (2 min)

1. Find the downloaded **`best.pt`** (usually in your Downloads folder).
2. **Rename it to** `knife.pt`.
3. Move it into your project's **`models/`** folder:
   ```
   C:\Users\Test\Downloads\Technosapiens\models\knife.pt
   ```

✅ **Success looks like:** the file `models\knife.pt` exists.

That's it — **no code changes**. The system auto-detects this file on startup.

---

## PART D — Verify it works (2 min)

On your laptop (camera packages must be installed — see below), run:
```
python training/verify_knife.py --source 0
```
- Your webcam opens.
- Show a knife (or a picture of one on your phone).

✅ **Success looks like:** a **red box labelled "knife"** appears around it, and
the screen shows **"KNIFE DETECTED"**.

> No knife handy? Test on an image instead:
> `python training/verify_knife.py --source path\to\a_knife_photo.jpg`

---

## PART E — It's now live in the whole system

Next time you start the backend:
```
python run.py
```
you'll see `[DETECTOR] Knife model loaded from ...models\knife.pt`.

Now in the live CCTV feed, a detected knife automatically:
1. draws a red **KNIFE** box,
2. fires a **WEAPON_DETECTED** event (reliability weight **0.9**),
3. pushes the zone **risk score** up,
4. triggers an **alert**,
5. recommends the **nearest patrol** (H3 dispatch).

That's the full **Person + Knife → Risk 95% → Alert → Patrol** demo.

---

## If you'd rather train locally (NOT recommended on a laptop)

```
pip install ultralytics roboflow
python training/prepare_knife_dataset.py --api-key YOUR_KEY --workspace WS --project PROJ --version 3
python training/train_knife.py --data training/knife_dataset/data.yaml --epochs 50
```
`train_knife.py` copies the result to `models/knife.pt` for you automatically.
Expect this to be **very slow** without a GPU.

---

## Camera packages (needed to RUN detection, not to train)

```
pip install opencv-python ultralytics supervision
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `roboflow not installed` | `pip install roboflow` |
| Colab "no GPU" / very slow | Runtime → Change runtime type → T4 GPU |
| Training loss not dropping | Dataset too small/poor — pick a bigger Roboflow dataset |
| `verify` finds nothing | Lower threshold: `--conf 0.25`, or train more epochs |
| System doesn't load knife model | Check the file is exactly `models\knife.pt` |
| Webcam won't open | Close other apps using the camera; try `--source` with an image |

---

## What success looks like overall

> Person detected → Backpack detected → **Knife detected** →
> Risk Score 95% → **Alert** → **Nearest Patrol recommended**

That end-to-end chain is the strongest thing you can show the judges.
