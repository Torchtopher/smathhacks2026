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
                    CREATE TABLE IF NOT EXISTS trash_detections (
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
                    CREATE TABLE IF NOT EXISTS boats (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        weight_class TEXT NOT NULL,
                        created_at DOUBLE PRECISION NOT NULL
                    );
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
                        to_regclass('public.trash_detections') IS NOT NULL AS has_trash_detections,
                        to_regclass('public.boat_positions') IS NOT NULL AS has_boat_positions,
                        to_regclass('public.boats') IS NOT NULL AS has_boats;
                    """
                )
                has_boat_states, has_trash_detections, has_boat_positions, has_boats = cur.fetchone()
                if not (has_boat_states and has_trash_detections and has_boat_positions and has_boats):
                    raise RuntimeError(
                        "Database user lacks schema-create privileges and required tables are missing. "
                        "Run schema.sql using a privileged role, then restart the API."
                    )
        conn.commit()
