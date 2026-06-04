# models/

Put trained model weights here.

- `knife.pt` — fine-tuned YOLO knife/weapon detector.
  When this file exists, the live system (`backend/realtime_detector.py`)
  loads it automatically and starts emitting `WEAPON_DETECTED` events.
  It is created for you by `training/train_knife.py`.

The base COCO models (`yolov8s.pt`, etc.) download automatically on first run
and do NOT need to be placed here.
