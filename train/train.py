"""Train YOLOv8 on marine life dataset."""

import os
from pathlib import Path

import yaml
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "dataset"
IMAGES_DIR = DATASET / "images" / "train"
LABELS_DIR = DATASET / "labels" / "train"

CLASS_NAMES = {0: "dolphin", 1: "trash", 2: "turtle", 3: "net"}


def setup_dataset():
    """Create dataset/ directory with symlinks to images and labels."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_DIR.mkdir(parents=True, exist_ok=True)

    # Symlink images
    for png in ROOT.glob("*.png"):
        link = IMAGES_DIR / png.name
        if not link.exists():
            link.symlink_to(png)

    # Symlink labels
    src_labels = ROOT / "annotations" / "labels" / "train"
    for txt in src_labels.glob("*.txt"):
        link = LABELS_DIR / txt.name
        if not link.exists():
            link.symlink_to(txt)

    # Write data.yaml
    data_yaml = DATASET / "data.yaml"
    data = {
        "path": str(DATASET),
        "train": "images/train",
        "val": "images/train",
        "names": CLASS_NAMES,
    }
    data_yaml.write_text(yaml.dump(data, default_flow_style=False))

    return data_yaml


def main():
    data_yaml = setup_dataset()
    print(f"Dataset ready at {DATASET}")
    print(f"  Images: {len(list(IMAGES_DIR.iterdir()))}")
    print(f"  Labels: {len(list(LABELS_DIR.iterdir()))}")

    model = YOLO("yolov8s.pt")
    model.train(
        data=str(data_yaml),
        epochs=100,
        imgsz=640,
        batch=-1,
        project=str(ROOT / "runs"),
    )


if __name__ == "__main__":
    main()
