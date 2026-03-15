import os
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg import errors


def require_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    return database_url


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(require_database_url())
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS boat_states (
                        boat_id TEXT PRIMARY KEY,
                        gps_lat DOUBLE PRECISION NOT NULL,
                        gps_lon DOUBLE PRECISION NOT NULL,
                        heading DOUBLE PRECISION NOT NULL,
                        timestamp DOUBLE PRECISION NOT NULL
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS detections (
                        id UUID PRIMARY KEY,
                        boat_id TEXT NOT NULL,
                        confidence DOUBLE PRECISION NOT NULL,
                        detected_at DOUBLE PRECISION NOT NULL,
                        bbox JSONB NOT NULL,
                        location GEOGRAPHY(POINT, 4326) NOT NULL,
                        drift_path JSONB
                    );
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE detections
                    ADD COLUMN IF NOT EXISTS label TEXT NOT NULL DEFAULT 'trash';
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS boats (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        weight_class TEXT NOT NULL,
                        created_at DOUBLE PRECISION NOT NULL,
                        last_image TEXT
                    );
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE boats
                    ADD COLUMN IF NOT EXISTS last_image TEXT;
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS boat_positions (
                        id BIGSERIAL PRIMARY KEY,
                        boat_id TEXT NOT NULL,
                        gps_lat DOUBLE PRECISION NOT NULL,
                        gps_lon DOUBLE PRECISION NOT NULL,
                        heading DOUBLE PRECISION NOT NULL,
                        timestamp DOUBLE PRECISION NOT NULL
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_detection_location_gist
                    ON detections USING GIST (location);
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_detection_detected_at
                    ON detections (detected_at DESC);
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_boat_positions_timestamp
                    ON boat_positions (timestamp DESC);
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_boat_positions_boat_timestamp
                    ON boat_positions (boat_id, timestamp DESC);
                    """
                )
            except errors.InsufficientPrivilege:
                conn.rollback()
                # Fallback for least-privileged app users: require pre-provisioned schema.
                cur.execute(
                    """
                    SELECT
                        to_regclass('public.boat_states') IS NOT NULL AS has_boat_states,
                        to_regclass('public.detections') IS NOT NULL AS has_detections,
                        to_regclass('public.boat_positions') IS NOT NULL AS has_boat_positions,
                        to_regclass('public.boats') IS NOT NULL AS has_boats;
                    """
                )
                schema_row = cur.fetchone()
                if schema_row is None:
                    raise RuntimeError("Failed to verify database schema")
                has_boat_states, has_detections, has_boat_positions, has_boats = (
                    schema_row
                )
                if not (
                    has_boat_states
                    and has_detections
                    and has_boat_positions
                    and has_boats
                ):
                    raise RuntimeError(
                        "Database user lacks schema-create privileges and required tables are missing. "
                        "Run schema.sql using a privileged role, then restart the API."
                    )
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'boats'
                          AND column_name = 'last_image'
                    );
                    """
                )
                last_image_row = cur.fetchone()
                if last_image_row is None:
                    raise RuntimeError("Failed to verify boats.last_image")
                has_last_image_column = last_image_row[0]
                if not has_last_image_column:
                    raise RuntimeError(
                        "Database schema is missing boats.last_image. "
                        "Run schema.sql using a privileged role, then restart the API."
                    )
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'detections'
                          AND column_name = 'label'
                    );
                    """
                )
                label_row = cur.fetchone()
                if label_row is None:
                    raise RuntimeError("Failed to verify detections.label")
                has_label_column = label_row[0]
                if not has_label_column:
                    raise RuntimeError(
                        "Database schema is missing detections.label. "
                        "Run schema.sql using a privileged role, then restart the API."
                    )
        conn.commit()
