import json
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query

from db import get_conn, init_db
from models import (
    BoatPositionPointResponse,
    BoatRegisterInput,
    BoatRegisterResponse,
    BoatReport,
    BoatStateResponse,
    DetectionSaved,
    TrashPointResponse,
)

app = FastAPI(title="Marine Trash Detection Middleware")
POSITION_HISTORY_RETENTION_SECONDS = 30 * 60


@app.on_event("startup")
def startup() -> None:
    try:
        init_db()
    except Exception as exc:
        raise RuntimeError(f"Failed to initialize database: {exc}") from exc


def project_detection_to_geo(
    boat_lat: float,
    boat_lon: float,
    boat_heading_deg: float,
    bbox: list[float],
) -> tuple[float, float]:
    _ = boat_heading_deg
    _ = bbox
    return boat_lat, boat_lon


@app.post("/api/boats/register")
def register_boat(body: BoatRegisterInput) -> BoatRegisterResponse:
    boat_id = str(uuid4())
    api_key = str(uuid4())
    created_at = time.time()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO boats (id, name, weight_class, api_key, created_at)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (boat_id, body.name, body.weight_class, api_key, created_at),
            )
        conn.commit()

    return BoatRegisterResponse(
        boat_id=boat_id,
        name=body.name,
        weight_class=body.weight_class,
        api_key=api_key,
    )


@app.post("/api/boats/report")
def report_boat(report: BoatReport) -> dict:
    saved_detections: list[DetectionSaved] = []

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO boat_states (boat_id, gps_lat, gps_lon, heading, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (boat_id) DO UPDATE
                SET
                    gps_lat = EXCLUDED.gps_lat,
                    gps_lon = EXCLUDED.gps_lon,
                    heading = EXCLUDED.heading,
                    timestamp = EXCLUDED.timestamp;
                """,
                (
                    report.boat_id,
                    report.gps_lat,
                    report.gps_lon,
                    report.heading,
                    report.timestamp,
                ),
            )
            cur.execute(
                """
                INSERT INTO boat_positions (boat_id, gps_lat, gps_lon, heading, timestamp)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (
                    report.boat_id,
                    report.gps_lat,
                    report.gps_lon,
                    report.heading,
                    report.timestamp,
                ),
            )
            cur.execute(
                """
                DELETE FROM boat_positions
                WHERE timestamp < %s;
                """,
                (report.timestamp - POSITION_HISTORY_RETENTION_SECONDS,),
            )

            for det in report.detections:
                projected_lat, projected_lon = project_detection_to_geo(
                    boat_lat=report.gps_lat,
                    boat_lon=report.gps_lon,
                    boat_heading_deg=report.heading,
                    bbox=det.bbox,
                )
                detection_id = str(uuid4())

                cur.execute(
                    """
                    INSERT INTO trash_detections (
                        id, boat_id, class_name, confidence, detected_at, bbox, location
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                    );
                    """,
                    (
                        detection_id,
                        report.boat_id,
                        det.class_name,
                        det.confidence,
                        report.timestamp,
                        json.dumps(det.bbox),
                        projected_lon,
                        projected_lat,
                    ),
                )

                saved_detections.append(
                    DetectionSaved(
                        id=detection_id,
                        boat_id=report.boat_id,
                        class_name=det.class_name,
                        confidence=det.confidence,
                        detected_at=report.timestamp,
                        bbox=det.bbox,
                        projected_lat=projected_lat,
                        projected_lon=projected_lon,
                    )
                )

        conn.commit()

    return {"boat_id": report.boat_id, "detections_saved": len(saved_detections), "detections": saved_detections}


@app.get("/api/trash")
def get_trash(
    min_lat: float | None = Query(default=None),
    max_lat: float | None = Query(default=None),
    min_lon: float | None = Query(default=None),
    max_lon: float | None = Query(default=None),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
) -> dict:
    where_parts = ["confidence >= %s"]
    params: list[float] = [min_confidence]

    if None not in (min_lat, max_lat, min_lon, max_lon):
        where_parts.append(
            """
            ST_Intersects(
                location::geometry,
                ST_MakeEnvelope(%s, %s, %s, %s, 4326)
            )
            """
        )
        params.extend([min_lon, min_lat, max_lon, max_lat])

    where_sql = " AND ".join(where_parts)
    query = f"""
        SELECT
            id::text,
            boat_id,
            class_name,
            confidence,
            detected_at,
            ST_Y(location::geometry) AS lat,
            ST_X(location::geometry) AS lon
        FROM trash_detections
        WHERE {where_sql}
        ORDER BY detected_at DESC;
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    points = [
        TrashPointResponse(
            id=row[0],
            boat_id=row[1],
            class_name=row[2],
            confidence=row[3],
            detected_at=row[4],
            lat=row[5],
            lon=row[6],
        )
        for row in rows
    ]
    return {"trash_points": points}


@app.get("/api/boats")
def get_boats() -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    bs.boat_id,
                    bs.gps_lat,
                    bs.gps_lon,
                    bs.heading,
                    bs.timestamp,
                    b.name,
                    b.weight_class
                FROM boat_states bs
                LEFT JOIN boats b ON bs.boat_id = b.id
                ORDER BY bs.timestamp DESC;
                """
            )
            rows = cur.fetchall()

    boats = [
        {
            "boat_id": row[0],
            "gps_lat": row[1],
            "gps_lon": row[2],
            "heading": row[3],
            "timestamp": row[4],
            "name": row[5] if row[5] else row[0],
            "weight_class": row[6] if row[6] else "light",
        }
        for row in rows
    ]
    return {"boats": boats}


@app.get("/api/boats/history")
def get_boat_position_history(
    boat_id: str | None = Query(default=None),
    minutes: int = Query(default=30, ge=1, le=180),
) -> dict:
    min_timestamp = None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(timestamp), 0) FROM boat_states;")
            latest_timestamp = cur.fetchone()[0]
            min_timestamp = latest_timestamp - (minutes * 60)

            if boat_id:
                cur.execute(
                    """
                    SELECT boat_id, gps_lat, gps_lon, heading, timestamp
                    FROM boat_positions
                    WHERE timestamp >= %s AND boat_id = %s
                    ORDER BY timestamp ASC;
                    """,
                    (min_timestamp, boat_id),
                )
            else:
                cur.execute(
                    """
                    SELECT boat_id, gps_lat, gps_lon, heading, timestamp
                    FROM boat_positions
                    WHERE timestamp >= %s
                    ORDER BY boat_id ASC, timestamp ASC;
                    """,
                    (min_timestamp,),
                )
            rows = cur.fetchall()

    points = [
        BoatPositionPointResponse(
            boat_id=row[0],
            gps_lat=row[1],
            gps_lon=row[2],
            heading=row[3],
            timestamp=row[4],
        )
        for row in rows
    ]
    return {"minutes": minutes, "points": points}


@app.get("/api/stats")
def get_stats() -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM trash_detections;")
            total_trash_detected = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM boat_states;")
            active_boats = cur.fetchone()[0]

            cur.execute("SELECT MAX(detected_at) FROM trash_detections;")
            last_detection_time = cur.fetchone()[0]

            cur.execute(
                """
                SELECT class_name, COUNT(*) AS count
                FROM trash_detections
                GROUP BY class_name
                ORDER BY count DESC;
                """
            )
            by_class_rows = cur.fetchall()

    return {
        "total_trash_detected": total_trash_detected,
        "active_boats": active_boats,
        "last_detection_time": last_detection_time,
        "trash_by_class": {class_name: count for class_name, count in by_class_rows},
    }


@app.get("/health")
def health() -> dict:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                _ = cur.fetchone()
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {exc}") from exc
