"""
Test RTSP connection with TP-Link Tapo C200/C210.
Edit the RTSP_URL below with your camera's credentials.
Press 'q' to quit.
"""

import os
# Force RTSP over TCP before OpenCV/FFMPEG loads (Tapo drops frames over UDP).
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

import cv2
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from backend.realtime_detector import RealtimeDetector

# ============================================================
#  EDIT THIS with your TP-Link Tapo camera details:
#  Format: rtsp://username:password@CAMERA_IP:554/stream1
#  - stream1 = high quality
#  - stream2 = low quality (better for AI processing)
# ============================================================
RTSP_URL = "rtsp://Technosapiens:Technosapiens123@172.18.98.166:554/stream2"


def open_stream(url):
    """Open the RTSP stream with the FFMPEG backend and a 1-frame buffer."""
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap or not cap.isOpened():
        if cap:
            cap.release()
        return None
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass
    return cap


def main():
    print("=" * 50)
    print("  SentinelAI - RTSP Camera Test")
    print(f"  Connecting to: {RTSP_URL}")
    print("  Press 'q' to quit")
    print("=" * 50)

    detector = RealtimeDetector(
        camera_location={"lat": 3.1466, "lon": 101.7108}
    )

    cap = open_stream(RTSP_URL)
    if cap is None:
        print("[ERROR] Cannot connect to RTSP stream.")
        print("Check:")
        print("  1. Camera is on and connected to WiFi")
        print("  2. RTSP is enabled in Tapo app")
        print("  3. IP address is correct")
        print("  4. Username/password are correct")
        print("  5. The same URL works in VLC first")
        return

    print("[OK] RTSP stream connected. Running AI detection...")

    consecutive_failures = 0
    MAX_FAILURES = 30  # ~1s of dropped frames before reconnecting

    while True:
        ret, frame = cap.read()

        if not ret or frame is None:
            consecutive_failures += 1
            if consecutive_failures < MAX_FAILURES:
                time.sleep(0.03)
                continue
            print("[WARN] Stream lost. Reconnecting...")
            cap.release()
            cap = None
            attempts = 0
            while cap is None:
                cap = open_stream(RTSP_URL)
                if cap is None:
                    attempts += 1
                    backoff = min(2 + attempts * 2, 15)
                    print(f"[WARN] Reconnect {attempts} failed. Retrying in {backoff}s...")
                    time.sleep(backoff)
            print("[OK] Reconnected.")
            consecutive_failures = 0
            continue

        consecutive_failures = 0

        annotated, events = detector.process_frame(frame)

        for event in events:
            print(f"  [EVENT] {event['event_type']} "
                  f"({event['confidence_score']:.0%}) "
                  f"- {event.get('details', '')}")

        cv2.imshow("SentinelAI - RTSP CCTV", annotated)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()
    print(f"\n[DONE] Total events: {len(detector.detected_events)}")


if __name__ == "__main__":
    main()
