"""Run trained YOLOv8 model on an image."""

import argparse

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Run marine life detection on an image")
    parser.add_argument("image", help="Path to the image file")
    parser.add_argument("model", help="Path to model weights (.pt file)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    args = parser.parse_args()

    model = YOLO(args.model)
    results = model(args.image, conf=args.conf, save=False)

    for result in results:
        for box in result.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            label = result.names[cls]
            coords = box.xyxy[0].tolist()
            print(f"{label} ({conf:.2f}): [{coords[0]:.0f}, {coords[1]:.0f}, {coords[2]:.0f}, {coords[3]:.0f}]")
        result.show()


if __name__ == "__main__":
    main()
