import argparse
import base64
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from vision.vision import decode_image_bytes, detect_image, summarize_results

DEFAULT_API_BASE = os.getenv("HOLOOCEAN_API_BASE", "http://localhost:8900")
DEFAULT_OUTPUT_IMAGE = Path("runs") / "holoocean" / "latest.jpg"
DEFAULT_PREDICT_DIR = Path("runs") / "holoocean" / "predict"
DEFAULT_BACKEND_API_BASE = os.getenv("BACKEND_API_BASE", "http://10.50.52.60:8000") #http://localhost:8000"
DEFAULT_BOAT_ID_FILE = Path("runs") / "holoocean" / "boat_id.txt"
DEBUG_ENABLED = os.getenv("CLIENT_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
DEFAULT_FAKE_GPS_ORIGIN_LAT = float(os.getenv("FAKE_GPS_ORIGIN_LAT", "35.2"))
DEFAULT_FAKE_GPS_ORIGIN_LON = float(os.getenv("FAKE_GPS_ORIGIN_LON", "-74.8"))
DEFAULT_FAKE_GPS_MILES_PER_SIM_METER = float(
    os.getenv("FAKE_GPS_MILES_PER_SIM_METER", "100.0")
)
DEFAULT_FAKE_GPS_REFERENCE_POSITION = (
    float(os.getenv("FAKE_GPS_REFERENCE_X", "-18.03758430480957")),
    float(os.getenv("FAKE_GPS_REFERENCE_Y", "1.8304139375686646")),
    float(os.getenv("FAKE_GPS_REFERENCE_Z", "0.17063309252262115")),
)


def fetch_latest_frame(api_base: str, wait_ms: int = 5000) -> dict[str, Any]:
    query = urlencode({"wait_ms": wait_ms, "include_image": "true"})
    url = f"{api_base.rstrip('/')}/latest?{query}"

    try:
        with urlopen(url) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HoloOcean API request failed: {exc.code} {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach HoloOcean API at {url}: {exc.reason}") from exc

    image_base64 = payload.pop("image_jpeg_base64", None)
    if not image_base64:
        raise RuntimeError("HoloOcean API did not return image_jpeg_base64")

    payload["image_bytes"] = base64.b64decode(image_base64)
    return payload


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    # Keep stdout limited to the exact JSON body being sent.
    print(json.dumps(payload, indent=2), flush=True)
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {url} failed: {exc.code} {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach backend API at {url}: {exc.reason}") from exc


def debug(message: str) -> None:
    if not DEBUG_ENABLED:
        return
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[client {timestamp}] {message}", file=sys.stderr, flush=True)


def write_image(image_bytes: bytes, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)
    return output_path


def synthetic_gps_from_position(position: list[float] | None) -> dict[str, Any] | None:
    if not position or len(position) < 2:
        return None

    ref_x, ref_y, ref_z = DEFAULT_FAKE_GPS_REFERENCE_POSITION
    sim_x, sim_y = float(position[0]), float(position[1])
    sim_z = float(position[2]) if len(position) >= 3 else 0.0

    delta_x_miles = (sim_x - ref_x) * DEFAULT_FAKE_GPS_MILES_PER_SIM_METER
    delta_y_miles = (sim_y - ref_y) * DEFAULT_FAKE_GPS_MILES_PER_SIM_METER

    miles_per_degree_lat = 69.0
    miles_per_degree_lon = 69.0 * max(
        0.01, abs(math.cos(math.radians(DEFAULT_FAKE_GPS_ORIGIN_LAT)))
    )

    lat = DEFAULT_FAKE_GPS_ORIGIN_LAT + (delta_y_miles / miles_per_degree_lat)
    lon = DEFAULT_FAKE_GPS_ORIGIN_LON + (delta_x_miles / miles_per_degree_lon)

    return {
        "coords": [lat, lon],
        "altitude_offset_m": sim_z - ref_z,
        "origin": [DEFAULT_FAKE_GPS_ORIGIN_LAT, DEFAULT_FAKE_GPS_ORIGIN_LON],
        "reference_position": list(DEFAULT_FAKE_GPS_REFERENCE_POSITION),
        "miles_per_sim_meter": DEFAULT_FAKE_GPS_MILES_PER_SIM_METER,
        "note": "Synthetic GPS derived from sim position, anchored off the North Carolina coast.",
    }


def load_cached_boat_id(path: Path) -> str | None:
    if not path.exists():
        return None
    boat_id = path.read_text(encoding="utf-8").strip()
    return boat_id or None


def cache_boat_id(path: Path, boat_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{boat_id}\n", encoding="utf-8")


def register_boat(backend_base: str, name: str, weight_class: str) -> dict[str, Any]:
    url = f"{backend_base.rstrip('/')}/api/boats/register"
    return post_json(url, {"name": name, "weight_class": weight_class})


def ensure_boat_id(
    *,
    backend_base: str,
    explicit_boat_id: str | None,
    boat_id_file: Path,
    boat_name: str,
    weight_class: str,
) -> tuple[str, dict[str, Any] | None]:
    if explicit_boat_id:
        return explicit_boat_id, None

    cached_boat_id = load_cached_boat_id(boat_id_file)
    if cached_boat_id:
        return cached_boat_id, None

    registration = register_boat(backend_base, boat_name, weight_class)
    boat_id = str(registration["boat_id"])
    cache_boat_id(boat_id_file, boat_id)
    return boat_id, registration


def flatten_detections(detection_summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for result in detection_summary:
        for detection in result.get("detections", []):
            flattened.append(
                {
                    "confidence": float(detection["confidence"]),
                    "bbox": [float(value) for value in detection["xyxy"]],
                }
            )
    return flattened


def send_backend_report(
    *,
    backend_base: str,
    boat_id: str,
    frame: dict[str, Any],
    gps: list[float],
    detection_summary: list[dict[str, Any]],
) -> dict[str, Any]:
    url = f"{backend_base.rstrip('/')}/api/boats/report"
    payload = {
        "boat_id": boat_id,
        "timestamp": float(frame.get("unix_time_s") or 0.0),
        "gps_lat": float(gps[0]),
        "gps_lon": float(gps[1]),
        "heading": float(frame.get("bearing_deg") or 0.0),
        "detections": flatten_detections(detection_summary),
    }
    return post_json(url, payload)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch the latest HoloOcean frame and pose metadata, then run YOLO detection."
    )
    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help=f"HoloOcean API base URL (default: {DEFAULT_API_BASE})",
    )
    parser.add_argument(
        "--backend-base",
        default=DEFAULT_BACKEND_API_BASE,
        help="Backend API base URL. If set, register/report boat data to backend.",
    )
    parser.add_argument(
        "--boat-id",
        help="Existing backend boat_id. If omitted, client loads one from disk or registers a new boat.",
    )
    parser.add_argument(
        "--boat-id-file",
        default=str(DEFAULT_BOAT_ID_FILE),
        help=f"Where to cache the backend boat_id (default: {DEFAULT_BOAT_ID_FILE})",
    )
    parser.add_argument(
        "--boat-name",
        default="HoloOcean Boat",
        help="Boat name used when registering with the backend",
    )
    parser.add_argument(
        "--weight-class",
        default="medium",
        help="Boat weight class used when registering with the backend",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=5000,
        help="How long to wait for a frame from HoloOcean (default: 5000)",
    )
    parser.add_argument(
        "--weights",
        help="Path to YOLO weights. Defaults to trained trash model if present.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Detection confidence threshold (default: 0.25)",
    )
    parser.add_argument(
        "--output-image",
        default=str(DEFAULT_OUTPUT_IMAGE),
        help=f"Where to save the fetched image (default: {DEFAULT_OUTPUT_IMAGE})",
    )
    parser.add_argument(
        "--predict-dir",
        default=str(DEFAULT_PREDICT_DIR),
        help=f"Where to save annotated predictions (default: {DEFAULT_PREDICT_DIR})",
    )
    parser.add_argument(
        "--predict-name",
        default="latest",
        help="Prediction run name inside predict-dir (default: latest)",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display detections in a window",
    )
    parser.add_argument(
        "--no-save-predictions",
        action="store_true",
        help="Skip saving annotated prediction images",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Continuously fetch, detect, and optionally report to the backend",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=5.0,
        help="Delay between loop iterations when --loop is set (default: 5.0)",
    )
    return parser


def run_once(args: argparse.Namespace, cached_backend_boat_id: str | None) -> tuple[dict[str, Any], str | None]:
    frame = fetch_latest_frame(args.api_base, wait_ms=args.wait_ms)
    debug(
        "Fetched frame "
        f"tick={frame.get('tick')} image_key={frame.get('image_key')} "
        f"position={frame.get('position')}"
    )
    output_image = write_image(frame["image_bytes"], Path(args.output_image))
    decoded_image = decode_image_bytes(frame["image_bytes"])
    predict_dir = Path(args.predict_dir).resolve()
    synthetic_gps = synthetic_gps_from_position(frame.get("position"))
    if synthetic_gps is not None:
        debug(
            "Synthetic GPS "
            f"lat={synthetic_gps['coords'][0]:.6f} lon={synthetic_gps['coords'][1]:.6f}"
        )

    results = detect_image(
        decoded_image,
        weights=args.weights,
        conf=args.conf,
        save=not args.no_save_predictions,
        show=args.show,
        project=predict_dir,
        name=args.predict_name,
    )
    detection_summary = summarize_results(results)
    debug(
        "Detection summary "
        f"images={len(detection_summary)} detections={len(flatten_detections(detection_summary))}"
    )

    backend_boat_id = cached_backend_boat_id
    backend_registration = None
    backend_report = None
    if args.backend_base:
        if synthetic_gps is None:
            raise RuntimeError("Cannot report to backend without synthetic GPS coordinates")
        backend_boat_id, backend_registration = ensure_boat_id(
            backend_base=args.backend_base,
            explicit_boat_id=args.boat_id,
            boat_id_file=Path(args.boat_id_file),
            boat_name=args.boat_name,
            weight_class=args.weight_class,
        )
        if backend_registration is not None:
            debug(
                f"Registered backend boat_id={backend_boat_id} "
                f"name={backend_registration.get('name')} weight_class={backend_registration.get('weight_class')}"
            )
        else:
            debug(f"Using backend boat_id={backend_boat_id}")
        backend_report = send_backend_report(
            backend_base=args.backend_base,
            boat_id=backend_boat_id,
            frame=frame,
            gps=synthetic_gps["coords"],
            detection_summary=detection_summary,
        )
        debug(
            f"Reported boat_id={backend_boat_id} "
            f"detections_saved={backend_report.get('detections_saved')}"
        )

    payload = {
        "tick": frame["tick"],
        "unix_time_s": frame.get("unix_time_s"),
        "image_source": frame["image_source"],
        "image_key": frame["image_key"],
        "camera_key": frame.get("camera_key"),
        "pose_key": frame.get("pose_key"),
        "pose_matrix": frame.get("pose_matrix"),
        "position": frame.get("position"),
        "gps": None if synthetic_gps is None else synthetic_gps["coords"],
        "gps_key": "synthetic_from_position",
        "gps_meta": synthetic_gps,
        "angles_deg": frame.get("angles_deg"),
        "bearing_deg": frame.get("bearing_deg"),
        "saved_image": str(output_image),
        "detections": detection_summary,
        "backend_boat_id": backend_boat_id,
        "backend_registration": backend_registration,
        "backend_report": backend_report,
    }
    return payload, backend_boat_id


def main() -> None:
    args = _build_parser().parse_args()
    backend_boat_id = None
    iteration = 0
    debug(
        f"Client starting backend_baseloop={args.loop} interval_seconds={args.interval_seconds} "
        f"backend_base={args.backend_base or 'none'}"
    )

    while True:
        iteration += 1
        debug(f"Starting iteration={iteration}")
        try:
            _, backend_boat_id = run_once(args, backend_boat_id)
        except Exception as exc:
            debug(f"Iteration failed iteration={iteration} error={exc}")
            if not args.loop:
                raise

        if not args.loop:
            break

        debug(
            f"Sleeping interval_seconds={args.interval_seconds} "
            f"boat_id={backend_boat_id or 'none'}"
        )
        time.sleep(max(args.interval_seconds, 0.0))


if __name__ == "__main__":
    main()
