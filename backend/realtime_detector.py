"""
Real-Time CCTV Detection System
Stage 1: Object Detection & Tracking (YOLOv8 + ByteTrack)
Stage 2: Behavioural Classification
  - Running / directional urgency
  - Physical altercation (fighting / grappling)
  - Crowd surge or dispersal anomaly
  - Extended loitering in sensitive zones
  - Pursuer-target spatial relationship (chasing)
"""

import os
try:
    import cv2
except ImportError:
    cv2 = None
import numpy as np
import time
from datetime import datetime
from collections import defaultdict, deque

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    print("[WARN] ultralytics not installed. YOLO disabled.")

try:
    import supervision as sv
    HAS_SUPERVISION = True
except ImportError:
    HAS_SUPERVISION = False
    print("[WARN] supervision not installed. ByteTrack fallback.")

PERSON_CLASS_ID = 0

# ---- Object detection configuration (Phase 1: detection-quality only) ----
# Model is auto-selected by hardware but can be overridden:
#   set env var  SENTINEL_YOLO_MODEL=yolov8m.pt  (or yolo11s.pt, etc.)
# Accuracy/speed ladder (slowest+most accurate -> fastest+least):
#   yolov8x  >  yolov8l  >  yolov8m  >  yolov8s  >  yolov8n
YOLO_MODEL_ENV = os.environ.get("SENTINEL_YOLO_MODEL", "auto").strip()

# COCO class id -> (label, min_confidence, draw_color_BGR)
# Per-class thresholds: small items (bags) need a lower bar than big/static ones.
OBJECT_CLASSES = {
    24: ("backpack",   0.35, (0, 200, 255)),
    26: ("handbag",    0.35, (0, 200, 255)),
    28: ("suitcase",   0.40, (0, 200, 255)),
    56: ("chair",      0.45, (170, 170, 170)),
    2:  ("car",        0.40, (255, 120, 0)),
    3:  ("motorcycle", 0.40, (255, 120, 0)),
}
# COCO also ships a "knife" class (id 43). We treat it as a weapon out-of-the-box
# so a kitchen/chef knife is detected even before any custom model is trained.
COCO_KNIFE_CLASS_ID = 43
COCO_KNIFE_CONF = 0.25  # lower = catches more knife angles (more sensitive)
# Test-time augmentation = best angle coverage but ~2-3x slower (laggy on CPU).
# OFF by default for smooth FPS. Set SENTINEL_KNIFE_TTA=1 to turn it on.
KNIFE_TTA = os.environ.get("SENTINEL_KNIFE_TTA", "0") == "1"

OBJECT_CLASS_IDS = list(OBJECT_CLASSES.keys())
DETECT_CLASS_IDS = [PERSON_CLASS_ID] + OBJECT_CLASS_IDS + [COCO_KNIFE_CLASS_ID]

# Detection thresholds.
# GLOBAL_CONF is a low gate so small objects survive YOLO's first pass; the
# real, stricter thresholds are applied per-class afterwards. PERSON_CONF is
# kept at 0.5 so the tracker receives exactly the same quality of person
# detections as before (tracking logic unchanged).
GLOBAL_CONF = 0.25
PERSON_CONF = 0.50
IOU_NMS = 0.45
IMG_SIZE = int(os.environ.get("SENTINEL_YOLO_IMGSZ", "640"))  # 640 default; 960 = better small-object accuracy, slower

# ---- Custom fine-tuned model (Phase 2) ----
# Drop a fine-tuned model at models/knife.pt and it activates automatically.
# It may be SINGLE-class (just knife) or MULTI-class (e.g. knife, bag, wallet).
# The model's own class names are used. Classes whose name is a weapon
# (knife/gun/...) fire the WEAPON_DETECTED event + red box; every other class
# (bag, wallet, ...) is shown as a normal named object.
KNIFE_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "models", "knife.pt"
)
KNIFE_CONF = float(os.environ.get("SENTINEL_KNIFE_CONF", "0.45"))
KNIFE_CHECK_INTERVAL = 3  # run the custom model every N frames (perf)

# Class names (from the custom model) that count as weapons.
WEAPON_LABELS = {"knife", "gun", "pistol", "rifle", "firearm", "weapon", "machete"}
CUSTOM_OBJECT_COLOR = (0, 220, 120)  # green-ish box for custom non-weapon items

SPEED_RUNNING_THRESHOLD = 60
SPEED_CHASING_THRESHOLD = 50
LOITER_TIME_THRESHOLD = 120
LOITER_RADIUS = 50
CROWD_THRESHOLD = 8
FIGHT_DISTANCE_THRESHOLD = 40
FIGHT_SPEED_THRESHOLD = 30

# Simple motion gate: above this the person is "moving", below it they're "still".
# (We label by motion only — not by how fast.)
MOTION_THRESHOLD = 8  # pixels/second


class PersonTracker:
    def __init__(self, track_id):
        self.track_id = track_id
        self.positions = deque(maxlen=90)
        self.timestamps = deque(maxlen=90)
        self.speeds = deque(maxlen=30)
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.bbox = None

    def update(self, cx, cy, bbox):
        now = time.time()
        self.positions.append((cx, cy))
        self.timestamps.append(now)
        self.last_seen = now
        self.bbox = bbox

        if len(self.positions) >= 2:
            dx = self.positions[-1][0] - self.positions[-2][0]
            dy = self.positions[-1][1] - self.positions[-2][1]
            dt = self.timestamps[-1] - self.timestamps[-2]
            if dt > 0:
                speed = np.sqrt(dx ** 2 + dy ** 2) / dt
                self.speeds.append(speed)

    @property
    def avg_speed(self):
        if not self.speeds:
            return 0.0
        return np.mean(list(self.speeds)[-10:])

    @property
    def is_moving(self):
        """Motion only: True if the person is moving at all, False if still."""
        return self.avg_speed > MOTION_THRESHOLD

    @property
    def duration(self):
        return self.last_seen - self.first_seen

    @property
    def movement_radius(self):
        if len(self.positions) < 2:
            return 0.0
        positions = list(self.positions)
        center_x = np.mean([p[0] for p in positions])
        center_y = np.mean([p[1] for p in positions])
        distances = [np.sqrt((p[0] - center_x) ** 2 + (p[1] - center_y) ** 2) for p in positions]
        return max(distances) if distances else 0.0

    @property
    def center(self):
        if self.positions:
            return self.positions[-1]
        return (0, 0)

    @property
    def direction(self):
        if len(self.positions) < 5:
            return (0, 0)
        recent = list(self.positions)[-5:]
        dx = recent[-1][0] - recent[0][0]
        dy = recent[-1][1] - recent[0][1]
        mag = np.sqrt(dx ** 2 + dy ** 2)
        if mag > 0:
            return (dx / mag, dy / mag)
        return (0, 0)


class RealtimeDetector:
    def __init__(self, camera_location=None):
        self.model = None
        self.tracker = None
        self.person_trackers = {}
        self.detected_events = []
        self.frame_count = 0
        self.camera_location = camera_location or {"lat": 3.1466, "lon": 101.7108}
        self.device = "cpu"
        self.object_detections = []   # latest non-person objects (bags, cars, ...)
        self.object_counts = {}       # label -> count for the current frame
        self.custom_model = None      # optional fine-tuned model (knife/bag/wallet...)
        self.knife_detections = []    # latest weapon boxes for drawing (red)

        if HAS_YOLO:
            model_name = self._select_model()
            self.model = YOLO(model_name)
            print(f"[DETECTOR] YOLO model '{model_name}' loaded on {self.device}.")

            # Optional fine-tuned custom model (activates only if the file exists).
            if os.path.exists(KNIFE_MODEL_PATH):
                try:
                    self.custom_model = YOLO(KNIFE_MODEL_PATH)
                    classes = list(self.custom_model.names.values())
                    print(f"[DETECTOR] Custom model loaded from {KNIFE_MODEL_PATH}. "
                          f"Classes: {classes}")
                except Exception as e:
                    print(f"[DETECTOR] Failed to load custom model: {e}")
            else:
                print("[DETECTOR] No custom model yet (models/knife.pt). "
                      "Using base COCO detection only.")

        if HAS_SUPERVISION:
            self.tracker = sv.ByteTrack(
                track_activation_threshold=0.25,
                lost_track_buffer=30,
                minimum_matching_threshold=0.8,
                frame_rate=30,
            )
            print("[DETECTOR] ByteTrack tracker initialized.")

    def _select_model(self):
        """
        Pick the most accurate YOLO model the hardware can run in real time.
        - explicit override via SENTINEL_YOLO_MODEL wins
        - GPU available -> yolov8m (accurate)
        - CPU only       -> yolov8s (good accuracy, still real-time on a laptop)
        """
        try:
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            self.device = "cpu"

        if YOLO_MODEL_ENV and YOLO_MODEL_ENV.lower() != "auto":
            return YOLO_MODEL_ENV
        # CPU -> small (good accuracy incl. suitcase/bags). GPU -> medium.
        # Override with SENTINEL_YOLO_MODEL=yolov8n.pt for faster/lower accuracy.
        return "yolov8m.pt" if self.device == "cuda" else "yolov8s.pt"

    def process_frame(self, frame):
        """Process a single video frame. Returns annotated frame + detected events."""
        self.frame_count += 1
        events = []

        if self.model is None:
            return frame, events

        # Detect person + key objects in one pass. Low global conf so small
        # objects survive; per-class thresholds applied afterwards. imgsz/device
        # tuned for the available hardware.
        results = self.model(
            frame, verbose=False,
            conf=GLOBAL_CONF, iou=IOU_NMS,
            classes=DETECT_CLASS_IDS,
            imgsz=IMG_SIZE,
            device=self.device,
            half=(self.device == "cuda"),
            agnostic_nms=False,
        )[0]

        if HAS_SUPERVISION:
            detections = sv.Detections.from_ultralytics(results)

            # Collect non-person objects (bags/cars/chairs...) for drawing + counts.
            self._process_object_detections(detections)

            # Persons only, gated at PERSON_CONF, fed to the tracker (UNCHANGED).
            if len(detections) > 0 and detections.class_id is not None:
                person_mask = detections.class_id == PERSON_CLASS_ID
                if detections.confidence is not None:
                    person_mask = person_mask & (detections.confidence >= PERSON_CONF)
                person_det = detections[person_mask]
            else:
                person_det = detections
            if len(person_det) > 0:
                person_det = self.tracker.update_with_detections(person_det)
                self._update_trackers(person_det)
        else:
            self._update_trackers_basic(results)
            self._process_object_detections_basic(results)

        if self.frame_count % 5 == 0:
            events = self._analyze_behaviors()

        # Custom model + weapon detection.
        # If a fine-tuned custom model is present, use it (knife->weapon,
        # other classes like bag/wallet -> named objects). Otherwise fall back
        # to COCO's built-in "knife" class from the base model.
        if self.frame_count % KNIFE_CHECK_INTERVAL == 0:
            if self.custom_model is not None:
                events.extend(self._detect_custom(frame))
            else:
                events.extend(self._coco_weapon_events(frame, results))

        annotated = self._draw_annotations(frame)
        return annotated, events

    def _coco_weapon_events(self, frame, results):
        """
        Knife (COCO class 43) treated as a weapon — no custom training needed.
        By default we REUSE the main detection (`results`) so there is NO second
        YOLO inference — keeps FPS high. Only if SENTINEL_KNIFE_TTA=1 do we run a
        dedicated augmented pass (best angles, but slower).
        Emits WEAPON_DETECTED events and fills knife_detections (red boxes).
        """
        events = []
        self.knife_detections = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if KNIFE_TTA:
            try:
                r = self.model(
                    frame, classes=[COCO_KNIFE_CLASS_ID], conf=COCO_KNIFE_CONF,
                    imgsz=IMG_SIZE, augment=True, device=self.device, verbose=False,
                )[0]
                boxes = getattr(r, "boxes", None)
            except Exception:
                boxes = None
        else:
            boxes = getattr(results, "boxes", None)  # reuse main inference (fast)

        if boxes is None:
            return events
        for box in boxes:
            cid = int(box.cls[0]) if box.cls is not None else -1
            if cid != COCO_KNIFE_CLASS_ID:
                continue
            conf = float(box.conf[0]) if box.conf is not None else 0.0
            if conf < COCO_KNIFE_CONF:
                continue
            bbox = box.xyxy[0].cpu().numpy()
            self.knife_detections.append(
                {"bbox": bbox, "conf": round(conf, 2), "label": "KNIFE"}
            )
            events.append({
                "event_type": "WEAPON_DETECTED",
                "confidence_score": round(conf, 2),
                "latitude": self.camera_location["lat"],
                "longitude": self.camera_location["lon"],
                "timestamp": now_str,
                "source": "CCTV_AI",
                "details": f"Knife detected (confidence {conf:.0%})",
            })
        self.detected_events.extend(events)
        return events

    def _detect_custom(self, frame):
        """
        Run the fine-tuned custom model. Uses the model's own class names:
          - weapon classes (knife/gun/...) -> WEAPON_DETECTED event + red box
          - any other class (bag, wallet...) -> named object (drawn + counted)
        """
        events = []
        self.knife_detections = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cr = self.custom_model(
                frame, verbose=False, conf=KNIFE_CONF,
                imgsz=IMG_SIZE, device=self.device,
            )[0]
        except Exception:
            return events

        boxes = getattr(cr, "boxes", None)
        if boxes is None:
            return events

        names = self.custom_model.names  # {class_id: name}
        for box in boxes:
            conf = float(box.conf[0]) if box.conf is not None else 0.0
            if conf < KNIFE_CONF:
                continue
            cid = int(box.cls[0]) if box.cls is not None else -1
            label = str(names.get(cid, "object")).lower()
            bbox = box.xyxy[0].cpu().numpy()

            if label in WEAPON_LABELS:
                self.knife_detections.append(
                    {"bbox": bbox, "conf": round(conf, 2), "label": label.upper()}
                )
                events.append({
                    "event_type": "WEAPON_DETECTED",
                    "confidence_score": round(conf, 2),
                    "latitude": self.camera_location["lat"],
                    "longitude": self.camera_location["lon"],
                    "timestamp": now_str,
                    "source": "CCTV_AI",
                    "details": f"{label.title()} detected (confidence {conf:.0%})",
                })
            else:
                # Named custom object (e.g. bag, wallet) — append to the object
                # lists already populated this frame by the base COCO model.
                self.object_detections.append({
                    "label": label, "conf": round(conf, 2),
                    "bbox": bbox, "color": CUSTOM_OBJECT_COLOR,
                })
                self.object_counts[label] = self.object_counts.get(label, 0) + 1

        self.detected_events.extend(events)
        return events

    def _update_trackers(self, detections):
        active_ids = set()
        for i in range(len(detections)):
            bbox = detections.xyxy[i]
            track_id = int(detections.tracker_id[i]) if detections.tracker_id is not None else i

            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2

            if track_id not in self.person_trackers:
                self.person_trackers[track_id] = PersonTracker(track_id)
            self.person_trackers[track_id].update(cx, cy, bbox)
            active_ids.add(track_id)

        stale = [tid for tid in self.person_trackers if tid not in active_ids
                 and time.time() - self.person_trackers[tid].last_seen > 5]
        for tid in stale:
            del self.person_trackers[tid]

    def _update_trackers_basic(self, results):
        boxes = results.boxes
        if boxes is None:
            return
        for i, box in enumerate(boxes):
            bbox = box.xyxy[0].cpu().numpy()
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            track_id = i
            if track_id not in self.person_trackers:
                self.person_trackers[track_id] = PersonTracker(track_id)
            self.person_trackers[track_id].update(cx, cy, bbox)

    def _analyze_behaviors(self):
        events = []
        trackers = list(self.person_trackers.values())
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for tracker in trackers:
            if tracker.avg_speed > SPEED_RUNNING_THRESHOLD:
                confidence = min(tracker.avg_speed / (SPEED_RUNNING_THRESHOLD * 2), 0.95)
                events.append({
                    "event_type": "SUSPICIOUS_RUNNING",
                    "confidence_score": round(confidence, 2),
                    "latitude": self.camera_location["lat"],
                    "longitude": self.camera_location["lon"],
                    "timestamp": now_str,
                    "source": "CCTV_AI",
                    "track_id": tracker.track_id,
                    "details": f"Person #{tracker.track_id} moving fast",
                })

        for tracker in trackers:
            if tracker.duration > LOITER_TIME_THRESHOLD and tracker.movement_radius < LOITER_RADIUS:
                confidence = min(tracker.duration / (LOITER_TIME_THRESHOLD * 3), 0.85)
                events.append({
                    "event_type": "LOITERING",
                    "confidence_score": round(confidence, 2),
                    "latitude": self.camera_location["lat"],
                    "longitude": self.camera_location["lon"],
                    "timestamp": now_str,
                    "source": "CCTV_AI",
                    "track_id": tracker.track_id,
                    "details": f"Person #{tracker.track_id} loitering for {tracker.duration:.0f}s",
                })

        for i, t1 in enumerate(trackers):
            for t2 in trackers[i + 1:]:
                if t1.avg_speed > SPEED_CHASING_THRESHOLD and t2.avg_speed > SPEED_CHASING_THRESHOLD:
                    dx = t1.center[0] - t2.center[0]
                    dy = t1.center[1] - t2.center[1]
                    dist = np.sqrt(dx ** 2 + dy ** 2)

                    if dist < 200:
                        d1 = t1.direction
                        d2 = t2.direction
                        dot = d1[0] * d2[0] + d1[1] * d2[1]
                        if dot > 0.5:
                            confidence = min((dot * t1.avg_speed) / (SPEED_CHASING_THRESHOLD * 3), 0.9)
                            events.append({
                                "event_type": "PERSON_CHASING",
                                "confidence_score": round(confidence, 2),
                                "latitude": self.camera_location["lat"],
                                "longitude": self.camera_location["lon"],
                                "timestamp": now_str,
                                "source": "CCTV_AI",
                                "track_id": f"{t1.track_id}->{t2.track_id}",
                                "details": f"Person #{t1.track_id} chasing #{t2.track_id}",
                            })

        for i, t1 in enumerate(trackers):
            for t2 in trackers[i + 1:]:
                dx = t1.center[0] - t2.center[0]
                dy = t1.center[1] - t2.center[1]
                dist = np.sqrt(dx ** 2 + dy ** 2)

                if (dist < FIGHT_DISTANCE_THRESHOLD and
                        t1.avg_speed > FIGHT_SPEED_THRESHOLD and
                        t2.avg_speed > FIGHT_SPEED_THRESHOLD):
                    d1 = t1.direction
                    d2 = t2.direction
                    dot = d1[0] * d2[0] + d1[1] * d2[1]
                    if dot < -0.3:
                        confidence = min(0.5 + (t1.avg_speed + t2.avg_speed) / 200, 0.9)
                        events.append({
                            "event_type": "ASSAULT",
                            "confidence_score": round(confidence, 2),
                            "latitude": self.camera_location["lat"],
                            "longitude": self.camera_location["lon"],
                            "timestamp": now_str,
                            "source": "CCTV_AI",
                            "track_id": f"{t1.track_id}<>{t2.track_id}",
                            "details": f"Possible fight between #{t1.track_id} and #{t2.track_id}",
                        })

        if len(trackers) >= CROWD_THRESHOLD:
            speeds = [t.avg_speed for t in trackers]
            avg_crowd_speed = np.mean(speeds) if speeds else 0
            if avg_crowd_speed > 30:
                confidence = min(len(trackers) / 15, 0.9)
                events.append({
                    "event_type": "CROWD_ANOMALY",
                    "confidence_score": round(confidence, 2),
                    "latitude": self.camera_location["lat"],
                    "longitude": self.camera_location["lon"],
                    "timestamp": now_str,
                    "source": "CCTV_AI",
                    "details": f"Crowd anomaly: {len(trackers)} people",
                })

        self.detected_events.extend(events)
        return events

    def _draw_annotations(self, frame):
        # Draw non-person objects first so person/behaviour boxes render on top.
        self._draw_objects(frame)

        for tracker in self.person_trackers.values():
            if tracker.bbox is None:
                continue
            x1, y1, x2, y2 = [int(v) for v in tracker.bbox]

            # Motion only — moving vs still (no speed magnitude).
            if tracker.is_moving:
                color = (0, 255, 0)
                label = f"#{tracker.track_id} person/moving"
            else:
                color = (0, 200, 255)
                label = f"#{tracker.track_id} person/still"

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            if len(tracker.positions) > 1:
                pts = [(int(p[0]), int(p[1])) for p in list(tracker.positions)[-20:]]
                for j in range(1, len(pts)):
                    cv2.line(frame, pts[j - 1], pts[j], color, 1)

        self._draw_knives(frame)

        person_count = len(self.person_trackers)
        cv2.putText(frame, f"person(movable): {person_count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        if self.knife_detections:
            cv2.putText(frame, f"!! WEAPON DETECTED ({len(self.knife_detections)}) !!",
                        (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        if self.object_counts:
            obj_summary = ", ".join(f"{k}:{v}" for k, v in self.object_counts.items())
            cv2.putText(frame, f"Objects: {obj_summary}", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 255), 2)

        cv2.putText(frame, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        return frame

    def _process_object_detections(self, detections):
        """Collect non-person objects (supervision path), applying per-class thresholds."""
        objects, counts = [], {}
        if len(detections) > 0 and detections.class_id is not None:
            for i in range(len(detections)):
                cid = int(detections.class_id[i])
                if cid not in OBJECT_CLASSES:
                    continue
                label, min_conf, color = OBJECT_CLASSES[cid]
                conf = float(detections.confidence[i]) if detections.confidence is not None else 1.0
                if conf < min_conf:
                    continue
                objects.append({"label": label, "conf": round(conf, 2),
                                "bbox": detections.xyxy[i], "color": color})
                counts[label] = counts.get(label, 0) + 1
        self.object_detections = objects
        self.object_counts = counts

    def _process_object_detections_basic(self, results):
        """Collect non-person objects (no-supervision fallback path)."""
        objects, counts = [], {}
        boxes = getattr(results, "boxes", None)
        if boxes is not None:
            for box in boxes:
                cid = int(box.cls[0]) if box.cls is not None else -1
                if cid not in OBJECT_CLASSES:
                    continue
                label, min_conf, color = OBJECT_CLASSES[cid]
                conf = float(box.conf[0]) if box.conf is not None else 1.0
                if conf < min_conf:
                    continue
                bbox = box.xyxy[0].cpu().numpy()
                objects.append({"label": label, "conf": round(conf, 2),
                                "bbox": bbox, "color": color})
                counts[label] = counts.get(label, 0) + 1
        self.object_detections = objects
        self.object_counts = counts

    def _draw_objects(self, frame):
        """Draw boxes + labels for detected non-person objects."""
        if cv2 is None:
            return frame
        for obj in self.object_detections:
            try:
                x1, y1, x2, y2 = [int(v) for v in obj["bbox"]]
            except (ValueError, TypeError):
                continue
            color = obj["color"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{obj['label']} {obj['conf']:.0%}",
                        (x1, max(y1 - 8, 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return frame

    def _draw_knives(self, frame):
        """Draw prominent red boxes around detected knives/weapons."""
        if cv2 is None:
            return frame
        for k in self.knife_detections:
            try:
                x1, y1, x2, y2 = [int(v) for v in k["bbox"]]
            except (ValueError, TypeError):
                continue
            label = k.get("label", "KNIFE")
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.putText(frame, f"{label} {k['conf']:.0%}", (x1, max(y1 - 8, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        return frame

    def get_object_counts(self):
        return dict(self.object_counts)

    def get_object_detections(self):
        return [
            {"label": o["label"], "conf": o["conf"]}
            for o in self.object_detections
        ]

    def get_person_count(self):
        return len(self.person_trackers)

    def get_recent_events(self, n=20):
        return self.detected_events[-n:]

    def reset(self):
        self.person_trackers.clear()
        self.detected_events.clear()
        self.object_detections = []
        self.object_counts = {}
        self.knife_detections = []
        self.frame_count = 0
