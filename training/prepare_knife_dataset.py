"""
STEP 1 of knife training: get a knife dataset ready for YOLO.

Two ways to use this:

  (A) ROBOFLOW (recommended - easiest):
      1. Make a free account at https://roboflow.com
      2. Go to https://universe.roboflow.com and search "knife detection"
      3. Open a dataset -> Download -> YOLOv8 -> "show download code"
         You'll get something like:
            rf.workspace("xxx").project("yyy").version(3).download("yolov8")
      4. Put your API key + those names below (or pass as arguments) and run:
            python training/prepare_knife_dataset.py --api-key YOUR_KEY \
                   --workspace xxx --project yyy --version 3

  (B) MANUAL: if you already downloaded a YOLO-format dataset, put it in
      training/knife_dataset/ (with train/ valid/ folders and a data.yaml),
      then just run:  python training/prepare_knife_dataset.py --manual

The script prints the path to data.yaml — you pass that to train_knife.py.
"""

import os
import argparse

HERE = os.path.dirname(__file__)
DEFAULT_DIR = os.path.join(HERE, "knife_dataset")


def via_roboflow(api_key, workspace, project, version, fmt="yolov8"):
    try:
        from roboflow import Roboflow
    except ImportError:
        print("[ERROR] roboflow not installed. Run:  pip install roboflow")
        return None

    rf = Roboflow(api_key=api_key)
    proj = rf.workspace(workspace).project(project)
    dataset = proj.version(int(version)).download(fmt, location=DEFAULT_DIR)
    data_yaml = os.path.join(dataset.location, "data.yaml")
    print(f"[OK] Dataset downloaded to: {dataset.location}")
    return data_yaml


def via_manual():
    data_yaml = os.path.join(DEFAULT_DIR, "data.yaml")
    if not os.path.exists(data_yaml):
        print(f"[ERROR] No data.yaml found in {DEFAULT_DIR}")
        print("        Place your YOLO-format dataset there (train/, valid/, data.yaml).")
        return None
    print(f"[OK] Found manual dataset: {data_yaml}")
    return data_yaml


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", default=os.environ.get("ROBOFLOW_API_KEY", ""))
    ap.add_argument("--workspace", default="")
    ap.add_argument("--project", default="")
    ap.add_argument("--version", default="1")
    ap.add_argument("--manual", action="store_true")
    args = ap.parse_args()

    if args.manual:
        data_yaml = via_manual()
    elif args.api_key and args.workspace and args.project:
        data_yaml = via_roboflow(args.api_key, args.workspace, args.project, args.version)
    else:
        print("Provide either --manual OR (--api-key --workspace --project --version).")
        print("See the instructions at the top of this file.")
        return

    if data_yaml:
        print("\n=============================================")
        print("  NEXT STEP — train the model with:")
        print(f'  python training/train_knife.py --data "{data_yaml}"')
        print("=============================================")


if __name__ == "__main__":
    main()
