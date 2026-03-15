#!/usr/bin/env python3
"""Demo client that sends random training images to the backend for detection."""

import argparse
import base64
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BACKEND_BASE = os.getenv("BACKEND_API_BASE", "http://localhost:8000")
DEFAULT_IMAGE_DIR = Path(__file__).resolve().parent.parent / "train"
DEBUG_ENABLED = os.getenv("CLIENT_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def debug(message: str) -> None:
    if not DEBUG_ENABLED:
        return
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[demo_client {timestamp}] {message}", file=sys.stderr, flush=True)


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    payload_for_log = dict(payload)
    image_value = payload_for_log.get("image")
    if isinstance(image_value, str):
        payload_for_log["image"] = f"<redacted base64 image, {len(image_value)} chars>"
    print(json.dumps(payload_for_log, indent=2), flush=True)
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


def register_boat(backend_base: str, name: str, weight_class: str) -> str:
    url = f"{backend_base.rstrip('/')}/api/boats/register"
    result = post_json(url, {"name": name, "weight_class": weight_class})
    return str(result["boat_id"])


def send_backend_report(
    *,
    backend_base: str,
    boat_id: str,
    timestamp: float,
    gps_lat: float,
    gps_lon: float,
    heading: float,
    image_bytes: bytes,
) -> dict[str, Any]:
    url = f"{backend_base.rstrip('/')}/api/boats/report"
    payload = {
        "boat_id": boat_id,
        "timestamp": timestamp,
        "gps_lat": gps_lat,
        "gps_lon": gps_lon,
        "heading": heading,
        "image": base64.b64encode(image_bytes).decode("ascii"),
    }
    return post_json(url, payload)


def pick_random_image(image_dir: Path) -> Path:
    patterns = ["*.png", "*.jpg", "*.jpeg"]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(image_dir.glob(pattern))
    if not files:
        raise RuntimeError(f"No image files found in {image_dir}")
    return random.choice(files)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Demo client that sends random training images to the backend."
    )
    parser.add_argument(
        "--image-dir",
        default=str(DEFAULT_IMAGE_DIR),
        help=f"Directory to pick random images from (default: {DEFAULT_IMAGE_DIR})",
    )
    parser.add_argument(
        "--backend-base",
        default=DEFAULT_BACKEND_BASE,
        help=f"Backend API base URL (default: {DEFAULT_BACKEND_BASE})",
    )
    parser.add_argument(
        "--boat-id",
        help="Existing backend boat_id. If provided, skips registration.",
    )
    parser.add_argument(
        "--boat-name",
        default="Demo Boat",
        help="Boat name used when registering with the backend",
    )
    parser.add_argument(
        "--weight-class",
        default="medium",
        help="Boat weight class used when registering with the backend",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Continuously send random images to the backend",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=5.0,
        help="Delay between loop iterations when --loop is set (default: 5.0)",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    image_dir = Path(args.image_dir)
    if not image_dir.is_dir():
        print(f"Error: image directory does not exist: {image_dir}", file=sys.stderr)
        sys.exit(1)

    if args.boat_id:
        boat_id = args.boat_id
        debug(f"Using provided boat_id={boat_id}")
    else:
        boat_id = register_boat(args.backend_base, args.boat_name, args.weight_class)
        debug(f"Registered boat_id={boat_id}")

    iteration = 0
    debug(
        f"Demo client starting loop={args.loop} interval_seconds={args.interval_seconds} "
        f"backend_base={args.backend_base} image_dir={image_dir}"
    )

    while True:
        iteration += 1
        debug(f"Starting iteration={iteration}")
        try:
            image_path = pick_random_image(image_dir)
            image_bytes = image_path.read_bytes()
            debug(f"Selected image: {image_path.name} ({len(image_bytes)} bytes)")

            gps_lat = 35.2 + random.uniform(-0.05, 0.05)
            gps_lon = -74.8 + random.uniform(-0.05, 0.05)
            heading = random.uniform(0, 360)

            report = send_backend_report(
                backend_base=args.backend_base,
                boat_id=boat_id,
                timestamp=time.time(),
                gps_lat=gps_lat,
                gps_lon=gps_lon,
                heading=heading,
                image_bytes=image_bytes,
            )
            debug(f"Report sent, detections_saved={report.get('detections_saved')}")

        except Exception as exc:
            print(f"Iteration {iteration} failed: {exc}", file=sys.stderr, flush=True)
            if not args.loop:
                raise

        if not args.loop:
            break

        debug(f"Sleeping {args.interval_seconds}s")
        time.sleep(max(args.interval_seconds, 0.0))


if __name__ == "__main__":
    main()
