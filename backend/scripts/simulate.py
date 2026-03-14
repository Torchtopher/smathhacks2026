#!/usr/bin/env python3

import argparse
import json
import math
import random
import time
import urllib.request

SPEED_KN = 5
HEADING_DRIFT_MAX = 30


def make_report(boat_id: str, lat: float, lon: float, heading: float) -> dict:
    detections = []
    if random.random() < 0.20:
        for _ in range(random.randint(1, 3)):
            x = round(random.uniform(0.05, 0.7), 3)
            y = round(random.uniform(0.05, 0.7), 3)
            w = round(random.uniform(0.05, 0.25), 3)
            h = round(random.uniform(0.05, 0.25), 3)
            detections.append({
                "confidence": round(random.uniform(0.5, 0.99), 2),
                "bbox": [x, y, x + w, y + h],
            })

    return {
        "boat_id": boat_id,
        "timestamp": time.time(),
        "gps_lat": lat,
        "gps_lon": lon,
        "heading": heading,
        "detections": detections,
    }


def move(lat: float, lon: float, heading: float, dt: float):
    """Advance position by dt seconds at SPEED_KN knots, with random heading drift."""
    heading = (heading + random.uniform(-HEADING_DRIFT_MAX, HEADING_DRIFT_MAX)) % 360
    dist_nm = SPEED_KN * (dt / 3600)
    dist_deg = dist_nm / 60  # 1 nm ≈ 1 arcminute
    lat += dist_deg * math.cos(math.radians(heading))
    lon += dist_deg * math.sin(math.radians(heading)) / max(math.cos(math.radians(lat)), 0.01)
    return lat, lon, heading


def send(url: str, report: dict):
    data = json.dumps(report).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read())
            n = body.get("detections_saved", 0)
            det_info = f" ({n} detections)" if n else ""
            print(f"  [{report['boat_id'][:8]}] lat={report['gps_lat']:.5f} lon={report['gps_lon']:.5f} hdg={report['heading']:.0f}{det_info}")
    except Exception as e:
        print(f"  [{report['boat_id'][:8]}] ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(description="Simulate boats sending reports")
    parser.add_argument("--boat", action="append", required=True, metavar="BOAT_ID",
                        help="boat API key (can be repeated)")
    parser.add_argument("--interval", type=float, default=3, help="seconds between reports (default: 3)")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--lat", type=float, default=35.0, help="starting latitude (default: 35.0)")
    parser.add_argument("--lon", type=float, default=-55.0, help="starting longitude (default: -55.0)")
    args = parser.parse_args()

    report_url = f"{args.url.rstrip('/')}/api/boats/report"

    boats = []
    for boat_id in args.boat:
        lat = args.lat + random.uniform(-0.01, 0.01)
        lon = args.lon + random.uniform(-0.01, 0.01)
        heading = random.uniform(0, 360)
        boats.append({"id": boat_id, "lat": lat, "lon": lon, "heading": heading})

    print(f"Simulating {len(boats)} boat(s), reporting every {args.interval}s to {report_url}")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            for boat in boats:
                report = make_report(boat["id"], boat["lat"], boat["lon"], boat["heading"])
                send(report_url, report)
                boat["lat"], boat["lon"], boat["heading"] = move(
                    boat["lat"], boat["lon"], boat["heading"], args.interval
                )
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
