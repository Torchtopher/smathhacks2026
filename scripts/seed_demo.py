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

# Safe open-water bounding boxes: (lat_min, lat_max, lon_min, lon_max, region_name)
OCEAN_REGIONS = [
    # North Atlantic — off US East Coast
    (30.0, 38.0, -77.0, -65.0, "N Atlantic West"),
    # Mid Atlantic — open ocean
    (25.0, 40.0, -55.0, -35.0, "Mid Atlantic"),
    # North Atlantic — off Europe
    (43.0, 52.0, -20.0, -8.0, "N Atlantic East"),
    # Caribbean Sea — open water south of islands
    (12.0, 17.0, -80.0, -65.0, "Caribbean"),
    # Gulf of Mexico — central deep water
    (24.0, 28.0, -92.0, -86.0, "Gulf of Mexico"),
    # Mediterranean — open water
    (34.0, 38.0, 5.0, 20.0, "Mediterranean"),
    # North Sea
    (54.0, 58.0, 1.0, 6.0, "North Sea"),
    # South Atlantic
    (-35.0, -15.0, -30.0, -5.0, "S Atlantic"),
    # Indian Ocean — central
    (-20.0, -5.0, 60.0, 80.0, "Indian Ocean"),
    # Arabian Sea
    (10.0, 18.0, 58.0, 68.0, "Arabian Sea"),
    # Bay of Bengal — central
    (8.0, 15.0, 82.0, 90.0, "Bay of Bengal"),
    # South China Sea — open water
    (8.0, 16.0, 112.0, 118.0, "South China Sea"),
    # North Pacific — off Japan
    (28.0, 36.0, 140.0, 155.0, "N Pacific West"),
    # Central North Pacific
    (20.0, 35.0, -170.0, -140.0, "Central N Pacific"),
    # East Pacific — off US West Coast
    (30.0, 40.0, -135.0, -125.0, "E Pacific"),
    # South Pacific
    (-35.0, -20.0, -140.0, -110.0, "S Pacific"),
    # Tasman Sea
    (-38.0, -30.0, 155.0, 165.0, "Tasman Sea"),
    # Southern Ocean
    (-55.0, -45.0, -60.0, -30.0, "Southern Ocean"),
    # Norwegian Sea
    (62.0, 67.0, -2.0, 8.0, "Norwegian Sea"),
    # Philippine Sea
    (15.0, 25.0, 125.0, 138.0, "Philippine Sea"),
]

BOAT_ADJECTIVES = [
    "Sea", "Ocean", "Storm", "Iron", "Silver", "Blue", "Dark", "Swift",
    "Coral", "Deep", "Salt", "Tide", "Misty", "Cold", "Wild", "Brave",
    "Rusty", "Golden", "Gray", "Crimson", "Jade", "Pearl", "Amber", "Steel",
]
BOAT_NOUNS = [
    "Wanderer", "Runner", "Scout", "Breeze", "Current", "Horizon", "Dancer",
    "Wake", "Spirit", "Voyager", "Mariner", "Drifter", "Pursuit", "Arrow",
    "Serpent", "Falcon", "Anchor", "Compass", "Tempest", "Venture", "Striker",
]
WEIGHT_CLASSES = ["light", "medium", "heavy"]
NUM_BOATS = 500


def generate_boats(n: int):
    """Generate n boats spread across safe ocean regions."""
    used_names: set[str] = set()
    boats = []
    for i in range(n):
        region = random.choice(OCEAN_REGIONS)
        lat_min, lat_max, lon_min, lon_max, _ = region
        lat = round(random.uniform(lat_min, lat_max), 4)
        lon = round(random.uniform(lon_min, lon_max), 4)
        heading = random.randint(0, 359)
        wc = random.choice(WEIGHT_CLASSES)

        # Generate a unique name
        while True:
            name = f"{random.choice(BOAT_ADJECTIVES)} {random.choice(BOAT_NOUNS)}"
            if name not in used_names:
                used_names.add(name)
                break
        boat_id = f"boat-{i + 1:04d}"
        boats.append((boat_id, name, wc, lat, lon, heading))
    return boats

LABELS = ["trash"] * 8 + ["net"] * 5 + ["dolphin"] * 4 + ["turtle"] * 3  # ~40/25/20/15%

TRAIL_POINTS = 60
TRAIL_INTERVAL_S = 30  # seconds between trail points
TRAIL_STEP_DEG = 0.01  # ~1.1km per step → ~66km total trail


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
        cur_lat -= math.cos(rad) * TRAIL_STEP_DEG + (random.random() - 0.5) * 0.002
        cur_lon -= math.sin(rad) * TRAIL_STEP_DEG + (random.random() - 0.5) * 0.002
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
        cur_lat += -0.08 + (random.random() - 0.5) * 0.04
        cur_lon += 0.10 + (random.random() - 0.5) * 0.04
    return path


def random_bbox():
    x1, y1 = random.random() * 0.6, random.random() * 0.6
    return [round(x1, 3), round(y1, 3), round(x1 + 0.1 + random.random() * 0.3, 3), round(y1 + 0.1 + random.random() * 0.3, 3)]


def seed(truncate: bool = True):
    now = time.time()
    boats = generate_boats(NUM_BOATS)
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
            for i, (boat_id, name, weight_class, *_) in enumerate(boats):
                created_at = now - random.uniform(86400 * 30, 86400 * 365)
                last_image = images[i % len(images)] if images else None
                cur.execute(
                    "INSERT INTO boats (id, name, weight_class, created_at, last_image) VALUES (%s, %s, %s, %s, %s)",
                    (boat_id, name, weight_class, created_at, last_image),
                )
            print(f"Inserted {len(boats)} boats.")

            # -- trails + boat_states --
            total_positions = 0
            for boat_id, _name, _wc, lat, lon, heading in boats:
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
            print(f"Inserted {len(boats)} boat_states and {total_positions} boat_positions.")

            # -- detections --
            det_count = 0
            for boat_id, _name, _wc, lat, lon, _heading in boats:
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
