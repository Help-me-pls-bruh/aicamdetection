"""
Quick test: Opens webcam with YOLOv8 person detection + ByteTrack tracking.
Run this FIRST to verify your setup works.
Press 'q' to quit.
"""

import cv2
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from backend.realtime_detector import RealtimeDetector


def main():
    print("=" * 50)
    print("  SentinelAI - Camera Test")
    print("  Press 'q' to quit  |  Press 'a' to toggle knife all-angle mode")
    print("=" * 50)

    detector = RealtimeDetector(
        camera_location={"lat": 3.1466, "lon": 101.7108}
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Cannot open webcam. Check camera connection.")
        return

    print("[OK] Webcam opened. Running YOLO detection...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        annotated, events = detector.process_frame(frame)

        for event in events:
            print(f"  [EVENT] {event['event_type']} "
                  f"(confidence: {event['confidence_score']:.0%}) "
                  f"- {event.get('details', '')}")

        cv2.imshow("SentinelAI - Camera Test", annotated)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        # Clicking the window's X button closes everything too
        if cv2.getWindowProperty("SentinelAI - Camera Test", cv2.WND_PROP_VISIBLE) < 1:
            break
        if key == ord("a"):
            detector.knife_tta = not detector.knife_tta
            state = "ON (best angles, slower)" if detector.knife_tta else "OFF (faster)"
            print(f"[TOGGLE] Knife all-angle augmentation: {state}")

    cap.release()
    cv2.destroyAllWindows()
    print("\n[DONE] Camera test finished.")
    print(f"Total events detected: {len(detector.detected_events)}")


if __name__ == "__main__":
    main()
