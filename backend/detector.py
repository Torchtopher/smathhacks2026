import logging
import os

import cv2
import numpy as np

from models import DetectionInput

logger = logging.getLogger(__name__)

_model = None
_model_loaded = False


def _get_model():
    global _model, _model_loaded
    if _model_loaded:
        return _model
    _model_loaded = True
    model_path = os.environ.get("YOLO_MODEL_PATH", "model.pt")
    if not os.path.isfile(model_path):
        logger.warning("YOLO model not found at %s — detections disabled", model_path)
        return None
    try:
        from ultralytics import YOLO
        _model = YOLO(model_path)
    except Exception:
        logger.exception("Failed to load YOLO model from %s", model_path)
    return _model


def detect(image_bytes: bytes) -> list[DetectionInput]:
    model = _get_model()
    if model is None:
        return []
    try:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            logger.warning("Failed to decode image")
            return []
        results = model.predict(source=img, conf=0.25, verbose=False)
        detections: list[DetectionInput] = []
        for result in results:
            h, w = result.orig_shape
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                detections.append(DetectionInput(
                    confidence=conf,
                    bbox=[x1 / w, y1 / h, x2 / w, y2 / h],
                ))
        return detections
    except Exception:
        logger.exception("YOLO inference failed")
        return []
