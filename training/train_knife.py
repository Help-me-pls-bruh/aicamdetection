"""
STEP 2 of knife training: fine-tune YOLOv8 on the knife dataset.

Run (locally or in Google Colab):
    python training/train_knife.py --data path/to/data.yaml --epochs 50

When it finishes, the best model is AUTOMATICALLY copied to:
    models/knife.pt
which the live system loads on its own (no code changes needed).

TIME ESTIMATE:
    - With a GPU (Google Colab free T4):  ~15-40 min for 50 epochs
    - On a CPU laptop:                    SLOW (many hours) - use Colab instead!
"""

import os
import shutil
import argparse

HERE = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(HERE)
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="path to data.yaml from step 1")
    ap.add_argument("--base-model", default="yolov8n.pt",
                    help="base model to fine-tune (yolov8n is fastest to train)")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default=None, help="'0' for GPU, 'cpu', or leave blank for auto")
    args = ap.parse_args()

    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics not installed. Run:  pip install ultralytics")
        return

    if not os.path.exists(args.data):
        print(f"[ERROR] data.yaml not found: {args.data}")
        print("        Run training/prepare_knife_dataset.py first.")
        return

    print(f"[TRAIN] Base model : {args.base_model}")
    print(f"[TRAIN] Dataset    : {args.data}")
    print(f"[TRAIN] Epochs     : {args.epochs}  | imgsz {args.imgsz}  | batch {args.batch}")

    model = YOLO(args.base_model)
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=os.path.join(HERE, "runs"),
        name="knife",
        exist_ok=True,
        patience=15,        # early-stop if no improvement
    )

    # Locate the best weights Ultralytics produced.
    best = os.path.join(HERE, "runs", "knife", "weights", "best.pt")
    if not os.path.exists(best):
        save_dir = getattr(results, "save_dir", None)
        if save_dir:
            cand = os.path.join(str(save_dir), "weights", "best.pt")
            if os.path.exists(cand):
                best = cand

    if os.path.exists(best):
        os.makedirs(MODELS_DIR, exist_ok=True)
        dest = os.path.join(MODELS_DIR, "knife.pt")
        shutil.copy(best, dest)
        print("\n=============================================")
        print(f"  SUCCESS. Trained model copied to:\n    {dest}")
        print("  The live system will load it automatically.")
        print("  Verify it with:")
        print("    python training/verify_knife.py --source 0")
        print("=============================================")
    else:
        print("[WARN] Training finished but best.pt was not found.")
        print(f"       Check {os.path.join(HERE, 'runs', 'knife', 'weights')}")


if __name__ == "__main__":
    main()
