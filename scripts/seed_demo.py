#!/usr/bin/env python3
"""Seed the Okeanos database with realistic demo data off the NC coast."""

import argparse
import base64
import glob
import json
import math
import os
import random
import time
import uuid

import psycopg

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
TRAIN_DIR = os.path.join(PROJECT_ROOT, "train")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://smathhacks:smathhacks@localhost:5432/smathhacks",
)

BOATS = [
    # All positions are open water off the NC Outer Banks / Cape Lookout area
    # lat ~33.8–34.5, lon ~-76.8 to -75.8 (well offshore, no land)
    ("boat-001", "Sea Wanderer", "light", 34.10, -76.20, 45),
    ("boat-002", "Lobster King", "heavy", 34.25, -76.05, 120),
    ("boat-003", "Tide Runner", "light", 34.40, -76.40, 200),
    ("boat-004", "Atlantic Scout", "heavy", 33.95, -76.10, 310),
    ("boat-005", "Harbor Breeze", "light", 34.50, -76.30, 85),
    ("boat-006", "Deep Current", "heavy", 34.05, -76.50, 160),
    # 4 new boats
    ("boat-007", "Misty Horizon", "medium", 34.20, -75.90, 270),
    ("boat-008", "Nor'easter", "medium", 34.35, -76.55, 30),
    ("boat-009", "Kelp Dancer", "light", 33.85, -76.00, 140),
    ("boat-010", "Iron Wake", "heavy", 34.45, -76.70, 190),
]

LABELS = ["trash"] * 8 + ["net"] * 5 + ["dolphin"] * 4 + ["turtle"] * 3  # ~40/25/20/15%

TRAIL_POINTS = 60
TRAIL_INTERVAL_S = 30  # seconds between trail points


def load_train_images() -> list[str]:
    """Load all PNGs from train/ as base64 strings."""
    images = []
    for path in sorted(glob.glob(os.path.join(TRAIN_DIR, "*.png"))):
        with open(path, "rb") as f:
            images.append(base64.b64encode(f.read()).decode("ascii"))
    return images


def generate_trail(lat: float, lon: float, heading: float, now: float):
    """Generate 60 trail points working backward from now."""
    rad = math.radians(heading)
    points = []
    cur_lat, cur_lon = lat, lon
    for i in range(TRAIL_POINTS):
        ts = now - i * TRAIL_INTERVAL_S
        points.append((cur_lat, cur_lon, heading, ts))
        # Step backward (opposite of heading) with jitter
        cur_lat -= math.cos(rad) * 0.0003 + (random.random() - 0.5) * 0.00005
        cur_lon -= math.sin(rad) * 0.0003 + (random.random() - 0.5) * 0.00005
    return points


def generate_drift_path(lat: float, lon: float):
    """Generate 15-point drift path over 7 days at 12h intervals, drifting SE."""
    path = []
    cur_lat, cur_lon = lat, lon
    for i in range(15):
        path.append({
            "lat": round(cur_lat, 6),
            "lon": round(cur_lon, 6),
            "time_offset_hours": i * 12,
        })
        cur_lat += -0.004 + (random.random() - 0.5) * 0.002
        cur_lon += 0.005 + (random.random() - 0.5) * 0.002
    return path


def random_bbox():
    x1, y1 = random.random() * 0.6, random.random() * 0.6
    return [round(x1, 3), round(y1, 3), round(x1 + 0.1 + random.random() * 0.3, 3), round(y1 + 0.1 + random.random() * 0.3, 3)]


def seed(truncate: bool = True):
    now = time.time()
    images = load_train_images()
    if images:
        print(f"Loaded {len(images)} images from train/")
    else:
        print("Warning: no images found in train/, boats will have no last_image")

    conn = psycopg.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            if truncate:
                cur.execute(
                    "TRUNCATE boat_positions, boat_states, detections, boats CASCADE"
                )
                print("Truncated all tables.")

            # -- boats --
            for i, (boat_id, name, weight_class, *_) in enumerate(BOATS):
                created_at = now - random.uniform(86400 * 30, 86400 * 365)
                last_image = images[i % len(images)] if images else None
                cur.execute(
                    "INSERT INTO boats (id, name, weight_class, created_at, last_image) VALUES (%s, %s, %s, %s, %s)",
                    (boat_id, name, weight_class, created_at, last_image),
                )
            print(f"Inserted {len(BOATS)} boats.")

            # -- trails + boat_states --
            total_positions = 0
            for boat_id, _name, _wc, lat, lon, heading in BOATS:
                trail = generate_trail(lat, lon, heading, now)
                # Most recent point → boat_states
                cur.execute(
                    "INSERT INTO boat_states (boat_id, gps_lat, gps_lon, heading, timestamp) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (boat_id, trail[0][0], trail[0][1], trail[0][2], trail[0][3]),
                )
                # All points → boat_positions
                for p_lat, p_lon, p_heading, p_ts in trail:
                    cur.execute(
                        "INSERT INTO boat_positions (boat_id, gps_lat, gps_lon, heading, timestamp) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (boat_id, p_lat, p_lon, p_heading, p_ts),
                    )
                    total_positions += 1
            print(f"Inserted {len(BOATS)} boat_states and {total_positions} boat_positions.")

            # -- detections --
            det_count = 0
            for boat_id, _name, _wc, lat, lon, _heading in BOATS:
                n_dets = random.randint(2, 4)
                for _ in range(n_dets):
                    label = random.choice(LABELS)
                    det_lat = lat + (random.random() - 0.5) * 0.04
                    det_lon = lon + (random.random() - 0.5) * 0.04
                    confidence = round(random.uniform(0.70, 0.95), 2)
                    detected_at = now - random.uniform(0, 4 * 3600)
                    bbox = random_bbox()
                    drift_path = (
                        generate_drift_path(det_lat, det_lon)
                        if label in ("trash", "net")
                        else None
                    )
                    cur.execute(
                        "INSERT INTO detections (id, boat_id, label, confidence, detected_at, bbox, location, drift_path) "
                        "VALUES (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)",
                        (
                            str(uuid.uuid4()),
                            boat_id,
                            label,
                            confidence,
                            detected_at,
                            json.dumps(bbox),
                            det_lon,  # lon first for ST_MakePoint
                            det_lat,
                            json.dumps(drift_path) if drift_path else None,
                        ),
                    )
                    det_count += 1
            print(f"Inserted {det_count} detections.")

        conn.commit()
        print("Done — committed all data.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Okeanos demo data")
    parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="Skip truncating tables before inserting",
    )
    args = parser.parse_args()
    seed(truncate=not args.no_truncate)
