CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS boat_states (
    boat_id TEXT PRIMARY KEY,
    gps_lat DOUBLE PRECISION NOT NULL,
    gps_lon DOUBLE PRECISION NOT NULL,
    heading DOUBLE PRECISION NOT NULL,
    timestamp DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS trash_detections (
    id UUID PRIMARY KEY,
    boat_id TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    detected_at DOUBLE PRECISION NOT NULL,
    bbox JSONB NOT NULL,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    drift_path JSONB
);

CREATE TABLE IF NOT EXISTS boats (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    weight_class TEXT NOT NULL,
    created_at DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS boat_positions (
    id BIGSERIAL PRIMARY KEY,
    boat_id TEXT NOT NULL,
    gps_lat DOUBLE PRECISION NOT NULL,
    gps_lon DOUBLE PRECISION NOT NULL,
    heading DOUBLE PRECISION NOT NULL,
    timestamp DOUBLE PRECISION NOT NULL
);

DO $$
BEGIN
    IF to_regclass('public.trash_detections') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS idx_trash_location_gist
        ON trash_detections USING GIST (location);

        CREATE INDEX IF NOT EXISTS idx_trash_detected_at
        ON trash_detections (detected_at DESC);
    END IF;

    IF to_regclass('public.boat_positions') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS idx_boat_positions_timestamp
        ON boat_positions (timestamp DESC);

        CREATE INDEX IF NOT EXISTS idx_boat_positions_boat_timestamp
        ON boat_positions (boat_id, timestamp DESC);
    END IF;
END $$;
