import argparse
import os
from io import BytesIO
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEIGHTS = PROJECT_ROOT / "runs" / "detect" / "trash" / "train" / "weights" / "best.pt"
FALLBACK_WEIGHTS = Path(__file__).resolve().parent / "yolo26n.pt"


def resolve_weights_path(weights: str | os.PathLike[str] | None = None) -> Path:
    if weights is not None:
        path = Path(weights).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if not path.exists():
            raise FileNotFoundError(f"YOLO weights not found: {path}")
        return path

    for candidate in (DEFAULT_WEIGHTS, FALLBACK_WEIGHTS):
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "No YOLO weights found. Checked "
        f"{DEFAULT_WEIGHTS} and {FALLBACK_WEIGHTS}."
    )


@lru_cache(maxsize=4)
def load_model(weights: str | None = None) -> Any:
    try:
        from ultralytics import YOLO
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "ultralytics is not installed in the active Python environment"
        ) from exc
    model_path = resolve_weights_path(weights)
    return YOLO(str(model_path))


def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    if hasattr(cv2, "imdecode"):
        array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if image is not None:
            return image

    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Could not decode image bytes: cv2.imdecode is unavailable and Pillow is not installed"
        ) from exc

    with Image.open(BytesIO(image_bytes)) as image:
        rgb = np.array(image.convert("RGB"))
    return rgb[:, :, ::-1].copy()


def detect_image(
    image: str | os.PathLike[str] | np.ndarray,
    *,
    weights: str | os.PathLike[str] | None = None,
    conf: float = 0.25,
    save: bool = False,
    show: bool = False,
    project: str | os.PathLike[str] | None = None,
    name: str | None = None,
    exist_ok: bool = True,
    verbose: bool = False,
) -> list[Any]:
    model = load_model(str(resolve_weights_path(weights)))
    prediction_kwargs: dict[str, Any] = {
        "source": image,
        "conf": conf,
        "save": save,
        "show": show,
        "exist_ok": exist_ok,
        "verbose": verbose,
    }
    if project is not None:
        prediction_kwargs["project"] = str(project)
    if name is not None:
        prediction_kwargs["name"] = name
    return model.predict(**prediction_kwargs)


def summarize_results(results: list[Any]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for index, result in enumerate(results):
        boxes = getattr(result, "boxes", None)
        count = 0 if boxes is None else len(boxes)
        detections: list[dict[str, Any]] = []
        if boxes is not None:
            names = getattr(result, "names", {})
            for box in boxes:
                cls_id = int(box.cls[0].item())
                detections.append(
                    {
                        "class_id": cls_id,
                        "class_name": names.get(cls_id, str(cls_id)),
                        "confidence": float(box.conf[0].item()),
                        "xyxy": [float(value) for value in box.xyxy[0].tolist()],
                    }
                )
        summary.append(
            {
                "image_index": index,
                "path": str(getattr(result, "path", "")),
                "detections": detections,
                "count": count,
            }
        )
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run YOLO detection on an image.")
    parser.add_argument("source", help="Image path")
    parser.add_argument("--weights", help="Path to YOLO weights")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--save", action="store_true", help="Save annotated predictions")
    parser.add_argument("--show", action="store_true", help="Display predictions")
    parser.add_argument("--project", help="Prediction output project directory")
    parser.add_argument("--name", help="Prediction run name")
    parser.add_argument("--verbose", action="store_true", help="Enable YOLO verbose output")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    results = detect_image(
        args.source,
        weights=args.weights,
        conf=args.conf,
        save=args.save,
        show=args.show,
        project=args.project,
        name=args.name,
        verbose=args.verbose,
    )
    for result in summarize_results(results):
        print(result)


if __name__ == "__main__":
    main()
