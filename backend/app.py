"""
Flask API Backend - connects all SentinelAI modules.
Provides REST endpoints for the Streamlit dashboard.
"""

import sys
import os
import threading
import time
import base64
from datetime import datetime
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

# Force RTSP over TCP BEFORE OpenCV/FFMPEG loads — Tapo streams drop frames
# badly over the default UDP transport. Must be set before cv2.VideoCapture.
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    print("[WARN] opencv-python not installed. Camera features disabled.")


def _open_capture(source):
    """
    Open a video source robustly.
    - RTSP (string starting with 'rtsp'): use the FFMPEG backend + small buffer
      so we always read the freshest frame and don't accumulate latency.
    - Webcam (int index): open normally.
    Returns an opened cv2.VideoCapture, or None if it could not be opened.
    """
    is_rtsp = isinstance(source, str) and source.lower().startswith("rtsp")

    if is_rtsp:
        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
    else:
        cap = cv2.VideoCapture(source)

    if not cap or not cap.isOpened():
        if cap:
            cap.release()
        return None

    # Keep only the latest frame — prevents lag build-up on network streams.
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass

    if is_rtsp:
        # stream2 (low-res) is best for YOLO; cap the decode size as a safety net.
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    return cap

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.db_manager import (
    init_database, get_all_zones, get_historical_crimes,
    get_active_realtime_events, get_recent_alerts, get_connection,
    backfill_crime_h3, get_patrols, get_recent_dispatches,
    get_crime_h3_intensity, update_patrol_status,
)
from database.seed_data import seed_historical_data
from backend.zone_manager import ZoneManager
from backend.historical_engine import HistoricalEngine
from backend.fusion_engine import FusionEngine
from backend.alert_system import AlertSystem
from backend.feedback_loop import FeedbackLoop
from backend.data_ingestion import ingest_realtime_event
from backend.patrol_dispatch import PatrolDispatch
from backend.h3_utils import cell_to_boundary, cell_to_latlng

if HAS_CV2:
    from backend.realtime_detector import RealtimeDetector
    from backend.face_recognition_engine import FaceRecognitionEngine
else:
    RealtimeDetector = None
    FaceRecognitionEngine = None

app = Flask(__name__)
CORS(app)

zone_manager = ZoneManager()
historical_engine = HistoricalEngine()
fusion_engine = FusionEngine()
alert_system = AlertSystem()
feedback_loop = FeedbackLoop(fusion_engine, historical_engine)
patrol_dispatch = PatrolDispatch()
detector = None
face_engine = FaceRecognitionEngine() if FaceRecognitionEngine else None

camera_active = False
camera_source = 0
latest_frame = None
latest_frame_lock = threading.Lock()


def initialize_system():
    print("=" * 60)
    print("  SentinelAI - Crime Prevention System")
    print("  Initializing...")
    print("=" * 60)

    init_database()
    zone_manager.create_grid_zones()
    seed_historical_data()
    backfill_crime_h3()           # assign H3 cells to any events missing one
    patrol_dispatch.seed_patrols()  # simulated patrol units (prototype)
    historical_engine.train_all()
    print("[SYSTEM] Initialization complete.\n")


def risk_computation_loop():
    """Background thread: recompute zone risks every 60 seconds."""
    while True:
        try:
            if historical_engine.needs_retraining(hours=24):
                historical_engine.train_all()

            p_base_all = historical_engine.get_p_base_all_zones()
            results = fusion_engine.compute_all_zones(p_base_all)

            for zone_id, result in results.items():
                if result["risk_level"] in ("HIGH", "CRITICAL"):
                    events = get_active_realtime_events(zone_id, minutes=15)
                    alert = alert_system.check_and_alert(
                        zone_id, result["r_zone"], result["risk_level"], events
                    )
                    # Auto-dispatch: on a fresh alert, recommend the nearest patrol.
                    if alert:
                        clat, clon = zone_manager.get_zone_center(zone_id)
                        patrol_dispatch.recommend_dispatch(
                            clat, clon, zone_id=zone_id,
                            risk_score=result["r_zone"], store=True,
                        )
        except Exception as e:
            print(f"[RISK LOOP] Error: {e}")

        time.sleep(60)


def camera_processing_loop():
    """
    Background thread: process camera frames for detection.

    Video-input layer only. Handles webcam (int index) and RTSP (Tapo C200/C210)
    with automatic reconnect and graceful tolerance of temporary network drops.
    The detection / tracking / fusion / alert logic below is unchanged.
    """
    global detector, latest_frame, camera_active

    if not HAS_CV2:
        return

    while True:
        if not camera_active or detector is None:
            time.sleep(1)
            continue

        # --- Open the source, retrying with backoff (RTSP can be slow to come up) ---
        cap = None
        open_attempts = 0
        while camera_active and cap is None:
            cap = _open_capture(camera_source)
            if cap is None:
                open_attempts += 1
                backoff = min(2 + open_attempts * 2, 15)
                print(f"[CAM] Cannot open source '{camera_source}' "
                      f"(attempt {open_attempts}). Retrying in {backoff}s...")
                time.sleep(backoff)

        if cap is None:
            continue

        print(f"[CAM] Connected to source: {camera_source}")
        consecutive_failures = 0
        MAX_FAILURES = 30  # ~1s of dropped frames before we force a reconnect

        while camera_active:
            ret, frame = cap.read()

            # --- Graceful handling of temporary network interruptions ---
            if not ret or frame is None:
                consecutive_failures += 1
                if consecutive_failures < MAX_FAILURES:
                    time.sleep(0.03)
                    continue
                print("[CAM] Stream lost. Reconnecting...")
                cap.release()
                cap = None
                reconnect_attempts = 0
                while camera_active and cap is None:
                    cap = _open_capture(camera_source)
                    if cap is None:
                        reconnect_attempts += 1
                        backoff = min(2 + reconnect_attempts * 2, 15)
                        print(f"[CAM] Reconnect attempt {reconnect_attempts} "
                              f"failed. Retrying in {backoff}s...")
                        time.sleep(backoff)
                if cap is None:
                    break
                print("[CAM] Reconnected.")
                consecutive_failures = 0
                continue

            consecutive_failures = 0

            # One bad frame must never kill the camera thread — skip it instead.
            try:
                annotated, events = detector.process_frame(frame)

                if face_engine:
                    face_events = face_engine.check_frame(
                        frame, detector.frame_count,
                        detector.camera_location
                    )
                    events.extend(face_events)

                for event in events:
                    p_event = fusion_engine.compute_p_event(
                        event.get("confidence_score", 0.5),
                        event.get("event_type", "SUSPICIOUS_ACTIVITY"),
                    )
                    ingest_realtime_event(
                        event, zone_manager, p_event=p_event, camera_id="CAM_0"
                    )

                    if event.get("event_type") == "FACE_MATCH_WANTED":
                        alert_system.check_wanted_person_alert(event)

                with latest_frame_lock:
                    _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    latest_frame = buffer.tobytes()
            except Exception as e:
                print(f"[CAM] Frame processing error (frame skipped): {e}")

        if cap is not None:
            cap.release()
        time.sleep(1)


@app.route("/api/status")
def system_status():
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "zones_loaded": len(zone_manager.zones),
        "camera_active": camera_active,
        "last_training": historical_engine.last_trained.isoformat() if historical_engine.last_trained else None,
    })


@app.route("/api/zones")
def api_zones():
    zones = get_all_zones()
    return jsonify(zones)


@app.route("/api/zones/risk")
def api_zones_risk():
    conn = get_connection()
    rows = conn.execute(
        """SELECT zone_id, center_lat, center_lon, p_spatial, p_time,
           p_base, p_realtime, r_zone, risk_level, last_updated
           FROM zones WHERE r_zone > 0 ORDER BY r_zone DESC"""
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/zones/<zone_id>/risk")
def api_zone_risk_detail(zone_id):
    conn = get_connection()
    zone = conn.execute("SELECT * FROM zones WHERE zone_id = ?", (zone_id,)).fetchone()
    events = get_active_realtime_events(zone_id, minutes=15)
    history = conn.execute(
        """SELECT * FROM zone_risk_history WHERE zone_id = ?
           ORDER BY timestamp DESC LIMIT 100""",
        (zone_id,),
    ).fetchall()
    conn.close()

    if not zone:
        return jsonify({"error": "Zone not found"}), 404

    return jsonify({
        "zone": dict(zone),
        "active_events": events,
        "risk_history": [dict(h) for h in history],
    })


@app.route("/api/crimes")
def api_crimes():
    zone_id = request.args.get("zone_id")
    limit = int(request.args.get("limit", 100))
    conn = get_connection()
    if zone_id:
        rows = conn.execute(
            "SELECT * FROM crime_events WHERE zone_id = ? ORDER BY timestamp DESC LIMIT ?",
            (zone_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM crime_events ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/crimes/stats")
def api_crime_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as cnt FROM crime_events").fetchone()["cnt"]
    by_type = conn.execute(
        """SELECT event_type, COUNT(*) as cnt FROM crime_events
           GROUP BY event_type ORDER BY cnt DESC"""
    ).fetchall()
    by_zone = conn.execute(
        """SELECT zone_id, COUNT(*) as cnt FROM crime_events
           GROUP BY zone_id ORDER BY cnt DESC LIMIT 20"""
    ).fetchall()
    recent_24h = conn.execute(
        """SELECT COUNT(*) as cnt FROM crime_events
           WHERE timestamp >= datetime('now', '-1 day')"""
    ).fetchone()["cnt"]
    conn.close()

    return jsonify({
        "total_crimes": total,
        "recent_24h": recent_24h,
        "by_type": [dict(r) for r in by_type],
        "top_zones": [dict(r) for r in by_zone],
    })


@app.route("/api/alerts")
def api_alerts():
    limit = int(request.args.get("limit", 50))
    alerts = get_recent_alerts(limit)
    return jsonify(alerts)


@app.route("/api/alerts/active")
def api_active_alerts():
    return jsonify(alert_system.get_active_alerts())


@app.route("/api/realtime/events")
def api_realtime_events():
    zone_id = request.args.get("zone_id")
    events = get_active_realtime_events(zone_id, minutes=15)
    return jsonify(events)


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    data = request.json
    alert_id = data.get("alert_id")
    zone_id = data.get("zone_id")
    label = data.get("label")
    notes = data.get("notes", "")

    if label not in ("TRUE_CRIME", "FALSE_ALARM"):
        return jsonify({"error": "Invalid label"}), 400

    # The feedback table references alerts(alert_id) — reject unknown IDs
    # with a clear message instead of a foreign-key 500.
    conn = get_connection()
    alert_exists = conn.execute(
        "SELECT 1 FROM alerts WHERE alert_id = ?", (alert_id,)
    ).fetchone()
    conn.close()
    if not alert_exists:
        return jsonify({"error": f"Alert {alert_id} not found"}), 404

    result = feedback_loop.process_feedback(alert_id, zone_id, label, notes)
    return jsonify(result)


@app.route("/api/feedback/stats")
def api_feedback_stats():
    return jsonify(feedback_loop.get_accuracy_stats())


@app.route("/api/camera/start", methods=["POST"])
def api_camera_start():
    global camera_active, camera_source, detector
    if not HAS_CV2:
        return jsonify({"error": "Camera unavailable — install opencv-python, ultralytics"}), 503
    data = request.json or {}
    source = data.get("source", 0)
    lat = data.get("lat", 3.1466)
    lon = data.get("lon", 101.7108)

    camera_source = source
    detector = RealtimeDetector(camera_location={"lat": lat, "lon": lon})
    camera_active = True
    return jsonify({"status": "started", "source": str(source)})


@app.route("/api/camera/stop", methods=["POST"])
def api_camera_stop():
    global camera_active
    camera_active = False
    return jsonify({"status": "stopped"})


@app.route("/api/camera/feed")
def api_camera_feed():
    def generate():
        while True:
            with latest_frame_lock:
                frame = latest_frame
            if frame:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            time.sleep(0.033)

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/camera/snapshot")
def api_camera_snapshot():
    with latest_frame_lock:
        frame = latest_frame
    if frame:
        encoded = base64.b64encode(frame).decode("utf-8")
        return jsonify({"image": encoded, "timestamp": datetime.now().isoformat()})
    return jsonify({"error": "No frame available"}), 404


@app.route("/api/camera/detections")
def api_camera_detections():
    if detector:
        return jsonify({
            "person_count": detector.get_person_count(),
            "object_counts": detector.get_object_counts(),
            "recent_events": detector.get_recent_events(20),
            "face_matches": face_engine.get_recent_matches(10) if face_engine else [],
        })
    return jsonify({"person_count": 0, "object_counts": {}, "recent_events": [], "face_matches": []})


@app.route("/api/report", methods=["POST"])
def api_citizen_report():
    data = request.json
    event = {
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": data.get("event_type", "SUSPICIOUS_ACTIVITY"),
        "confidence_score": 0.6,
        "source": "USER_APP",
    }
    p_event = fusion_engine.compute_p_event(0.6, event["event_type"])
    success, result = ingest_realtime_event(event, zone_manager, p_event=p_event)
    return jsonify({"success": success, "zone_id": result})


@app.route("/api/patrols")
def api_patrols():
    """List all (simulated) patrol units with position, H3 cell and status."""
    return jsonify(get_patrols())


@app.route("/api/patrols/coverage")
def api_patrol_coverage():
    """
    Per-patrol H3 coverage zones, with hexagon boundaries for map drawing.
    """
    coverage = patrol_dispatch.get_all_coverage()
    out = []
    for patrol_id, info in coverage.items():
        cells = []
        for cell in info["cells"]:
            cells.append({"h3_index": cell, "boundary": cell_to_boundary(cell)})
        out.append({
            "patrol_id": patrol_id,
            "name": info["name"],
            "center_cell": info["center_cell"],
            "cell_count": info["cell_count"],
            "cells": cells,
        })
    return jsonify(out)


@app.route("/api/h3/intensity")
def api_h3_intensity():
    """Crime intensity per H3 cell (for the hexagon hotspot heatmap)."""
    raw = get_crime_h3_intensity(limit_cells=int(request.args.get("limit", 250)))
    out = []
    for row in raw:
        cell = row["h3_index"]
        lat, lon = cell_to_latlng(cell)
        out.append({
            "h3_index": cell,
            "crime_count": row["crime_count"],
            "center_lat": lat,
            "center_lon": lon,
            "boundary": cell_to_boundary(cell),
        })
    return jsonify(out)


@app.route("/api/dispatch/recommend", methods=["POST"])
def api_dispatch_recommend():
    """
    Recommend the nearest patrol for an incident.
    Accepts either explicit {lat, lon} or a {zone_id} (uses the zone centre).
    """
    data = request.json or {}
    lat = data.get("lat")
    lon = data.get("lon")
    zone_id = data.get("zone_id")
    risk_score = data.get("risk_score", 0.0)
    alert_id = data.get("alert_id")

    if (lat is None or lon is None) and zone_id:
        conn = get_connection()
        row = conn.execute(
            "SELECT center_lat, center_lon, r_zone FROM zones WHERE zone_id = ?",
            (zone_id,),
        ).fetchone()
        conn.close()
        if row:
            lat, lon = row["center_lat"], row["center_lon"]
            if not risk_score:
                risk_score = row["r_zone"] or 0.0

    if lat is None or lon is None:
        return jsonify({"success": False, "reason": "Provide lat/lon or a valid zone_id."}), 400

    result = patrol_dispatch.recommend_dispatch(
        float(lat), float(lon), zone_id=zone_id,
        risk_score=float(risk_score), alert_id=alert_id, store=True,
    )
    return jsonify(result)


@app.route("/api/dispatches")
def api_dispatches():
    """Recent dispatch recommendations."""
    limit = int(request.args.get("limit", 50))
    return jsonify(get_recent_dispatches(limit))


@app.route("/api/patrols/<patrol_id>/status", methods=["POST"])
def api_patrol_status(patrol_id):
    """Update a patrol's status (AVAILABLE / DISPATCHED / BUSY)."""
    data = request.json or {}
    status = data.get("status", "AVAILABLE")
    update_patrol_status(patrol_id, status)
    return jsonify({"patrol_id": patrol_id, "status": status})


def start_server(host="0.0.0.0", port=5000):
    initialize_system()

    risk_thread = threading.Thread(target=risk_computation_loop, daemon=True)
    risk_thread.start()

    cam_thread = threading.Thread(target=camera_processing_loop, daemon=True)
    cam_thread.start()

    print(f"\n[SERVER] Flask API running at http://localhost:{port}")
    print(f"[SERVER] Dashboard: run 'streamlit run dashboard/dashboard.py'\n")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    start_server()
