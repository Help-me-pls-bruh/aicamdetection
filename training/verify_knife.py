"""
STEP 3 of knife training: check that the trained model actually detects knives.

Run on your webcam:
    python training/verify_knife.py --source 0

Run on a test image (or a folder of images):
    python training/verify_knife.py --source path/to/knife_photo.jpg

A window opens with red boxes around detected knives. Press 'q' to quit.
SUCCESS = it draws a box labelled "knife" around a knife you show it.
"""

import os
import argparse

HERE = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(HERE)
DEFAULT_MODEL = os.path.join(PROJECT_ROOT, "models", "knife.pt")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--source", default="0", help="'0' for webcam, or an image/folder path")
    ap.add_argument("--conf", type=float, default=0.45)
    args = ap.parse_args()

    try:
        import cv2
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] Need opencv-python + ultralytics. Run:")
        print("        pip install opencv-python ultralytics")
        return

    if not os.path.exists(args.model):
        print(f"[ERROR] Model not found: {args.model}")
        print("        Train it first with training/train_knife.py")
        return

    model = YOLO(args.model)
    print(f"[VERIFY] Loaded {args.model}. Classes: {model.names}")

    # Image / folder mode
    if args.source != "0" and os.path.exists(args.source):
        results = model(args.source, conf=args.conf)
        total = 0
        for r in results:
            n = len(r.boxes) if r.boxes is not None else 0
            total += n
            out = r.plot()
            cv2.imshow("Knife Verify (press any key)", out)
            cv2.waitKey(0)
        print(f"[VERIFY] Detected {total} knife box(es) across the image(s).")
        cv2.destroyAllWindows()
        return

    # Webcam mode
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Cannot open webcam.")
        return
    print("[VERIFY] Webcam open. Show a knife. Press 'q' to quit.")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        res = model(frame, conf=args.conf, verbose=False)[0]
        annotated = res.plot()
        if res.boxes is not None and len(res.boxes) > 0:
            cv2.putText(annotated, "KNIFE DETECTED", (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
        cv2.imshow("Knife Verify (press q)", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
