import base64
import json
import logging
import time
from uuid import uuid4

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from psycopg import errors, sql

from db import get_conn, init_db
from detector import detect
from drift_predictor import predict_drift_days
from models import (
    BoatAdminCreateInput,
    BoatAdminDeleteResponse,
    BoatImageResponse,
    BoatAdminResponse,
    BoatAdminUpdateInput,
    DetectionInput,
    BoatPositionPointResponse,
    BoatRegisterInput,
    BoatRegisterResponse,
    BoatReport,
    DetectionSaved,
    DetectionPointResponse,
)

app = FastAPI(title="Marine Object Detection Middleware")

LABEL_COLORS_BGR = {
    "dolphin": (255, 150, 0),
    "trash": (0, 255, 255),
    "turtle": (0, 200, 0),
    "net": (0, 165, 255),
}
POSITION_HISTORY_RETENTION_SECONDS = 30 * 60
logger = logging.getLogger(__name__)


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


def annotate_image_with_detections(
    image_payload: str,
    detections: list[DetectionInput],
) -> str:
    try:
        image_bytes = base64.b64decode(image_payload)
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            return image_payload

        height, width = image.shape[:2]
        for det in detections:
            x1 = max(0, min(width - 1, int(round(det.bbox[0] * width))))
            y1 = max(0, min(height - 1, int(round(det.bbox[1] * height))))
            x2 = max(0, min(width - 1, int(round(det.bbox[2] * width))))
            y2 = max(0, min(height - 1, int(round(det.bbox[3] * height))))
            if x2 <= x1 or y2 <= y1:
                continue

            color = LABEL_COLORS_BGR.get(det.label, (0, 255, 255))
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            label = f"{det.label} {det.confidence:.2f}"
            (text_width, text_height), baseline = cv2.getTextSize(
                label,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                1,
            )
            label_top = max(0, y1 - text_height - baseline - 6)
            label_bottom = max(0, y1 - 2)
            label_right = min(width - 1, x1 + text_width + 8)

            cv2.rectangle(
                image,
                (x1, label_top),
                (label_right, label_bottom),
                color,
                -1,
            )
            cv2.putText(
                image,
                label,
                (x1 + 4, max(text_height + 2, label_bottom - baseline - 2)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

        success, encoded = cv2.imencode(
            ".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        )
        if not success:
            return image_payload
        return base64.b64encode(encoded.tobytes()).decode("ascii")
    except Exception:
        logger.exception("Failed to annotate detection image")
        return image_payload


@app.post("/api/boats/register")
def register_boat(body: BoatRegisterInput) -> BoatRegisterResponse:
    boat_id = str(uuid4())
    created_at = time.time()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO boats (id, name, weight_class, created_at)
                VALUES (%s, %s, %s, %s);
                """,
                (boat_id, body.name, body.weight_class, created_at),
            )
        conn.commit()

    return BoatRegisterResponse(
        boat_id=boat_id,
        name=body.name,
        weight_class=body.weight_class,
    )


@app.get("/api/admin/boats")
def admin_get_boats() -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    b.id,
                    b.name,
                    b.weight_class,
                    b.created_at,
                    bs.timestamp AS last_reported_at
                FROM boats b
                LEFT JOIN boat_states bs ON bs.boat_id = b.id
                ORDER BY bs.timestamp DESC NULLS LAST, b.created_at DESC;
                """
            )
            rows = cur.fetchall()

    boats = [
        BoatAdminResponse(
            boat_id=row[0],
            name=row[1],
            weight_class=row[2],
            created_at=row[3],
            last_reported_at=row[4],
        )
        for row in rows
    ]
    return {"boats": boats}


@app.post("/api/admin/boats")
def admin_create_boat(body: BoatAdminCreateInput) -> BoatAdminResponse:
    boat_id = body.boat_id.strip() if body.boat_id else str(uuid4())
    if not boat_id:
        raise HTTPException(status_code=400, detail="boat_id cannot be empty")

    created_at = time.time()

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO boats (id, name, weight_class, created_at)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, name, weight_class, created_at;
                    """,
                    (boat_id, body.name, body.weight_class, created_at),
                )
                row = cur.fetchone()
            conn.commit()
    except errors.UniqueViolation as exc:
        raise HTTPException(status_code=409, detail="boat_id already exists") from exc

    if row is None:
        raise RuntimeError("Failed to create boat")

    return BoatAdminResponse(
        boat_id=row[0],
        name=row[1],
        weight_class=row[2],
        created_at=row[3],
        last_reported_at=None,
    )


@app.put("/api/admin/boats/{boat_id}")
def admin_update_boat(boat_id: str, body: BoatAdminUpdateInput) -> BoatAdminResponse:
    if body.name is None and body.weight_class is None:
        raise HTTPException(status_code=400, detail="name or weight_class is required")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE boats
                SET
                    name = COALESCE(%s, name),
                    weight_class = COALESCE(%s, weight_class)
                WHERE id = %s
                RETURNING id, name, weight_class, created_at;
                """,
                (body.name, body.weight_class, boat_id),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="boat not found")

            cur.execute(
                """
                SELECT timestamp
                FROM boat_states
                WHERE boat_id = %s;
                """,
                (boat_id,),
            )
            state_row = cur.fetchone()
        conn.commit()

    return BoatAdminResponse(
        boat_id=row[0],
        name=row[1],
        weight_class=row[2],
        created_at=row[3],
        last_reported_at=state_row[0] if state_row else None,
    )


@app.delete("/api/admin/boats/{boat_id}")
def admin_delete_boat(
    boat_id: str,
    purge_data: bool = Query(default=True),
) -> BoatAdminDeleteResponse:
    deleted_state_rows = 0
    deleted_position_rows = 0
    deleted_detection_rows = 0
    deleted_boat_rows = 0

    with get_conn() as conn:
        with conn.cursor() as cur:
            if purge_data:
                cur.execute("DELETE FROM boat_states WHERE boat_id = %s;", (boat_id,))
                deleted_state_rows = cur.rowcount

                cur.execute(
                    "DELETE FROM boat_positions WHERE boat_id = %s;", (boat_id,)
                )
                deleted_position_rows = cur.rowcount

                cur.execute("DELETE FROM detections WHERE boat_id = %s;", (boat_id,))
                deleted_detection_rows = cur.rowcount

            cur.execute("DELETE FROM boats WHERE id = %s;", (boat_id,))
            deleted_boat_rows = cur.rowcount
        conn.commit()

    deleted_total = (
        deleted_boat_rows
        + deleted_state_rows
        + deleted_position_rows
        + deleted_detection_rows
    )
    if deleted_total == 0:
        raise HTTPException(status_code=404, detail="boat not found")

    return BoatAdminDeleteResponse(
        boat_id=boat_id,
        deleted_boat_rows=deleted_boat_rows,
        deleted_state_rows=deleted_state_rows,
        deleted_position_rows=deleted_position_rows,
        deleted_detection_rows=deleted_detection_rows,
    )


@app.post("/api/boats/report")
def report_boat(report: BoatReport) -> dict:
    saved_detections: list[DetectionSaved] = []
    image_payload = report.image.strip()
    annotated_image_payload = image_payload
    if image_payload.startswith("data:") and "," in image_payload:
        image_payload = image_payload.split(",", 1)[1]
        annotated_image_payload = image_payload

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
            detections = []
            try:
                image_bytes = base64.b64decode(image_payload)
                s = time.perf_counter()
                detections = detect(image_bytes)
                print(f"End detect time {time.perf_counter() - s}")
                print(f"Detections {detections}")
            except Exception:
                logger.exception(
                    "Failed to decode/detect image for boat %s", report.boat_id
                )
            annotated_image_payload = annotate_image_with_detections(
                image_payload=image_payload,
                detections=detections,
            )
            cur.execute(
                """
                UPDATE boats
                SET last_image = %s
                WHERE id = %s;
                """,
                (annotated_image_payload, report.boat_id),
            )

            for det in detections:
                projected_lat, projected_lon = project_detection_to_geo(
                    boat_lat=report.gps_lat,
                    boat_lon=report.gps_lon,
                    boat_heading_deg=report.heading,
                    bbox=det.bbox,
                )
                detection_id = str(uuid4())

                drift_path: list[dict] = []
                if det.label in ("trash", "net"):
                    try:
                        drift_path = predict_drift_days(
                            detected_at=report.timestamp,
                            lat=projected_lat,
                            lon=projected_lon,
                            days=7,
                        )
                    except (Exception, SystemExit):
                        logger.exception(
                            "Failed drift prediction for detection id=%s", detection_id
                        )

                drift_path_json = json.dumps(drift_path) if drift_path else None

                cur.execute(
                    """
                    INSERT INTO detections (
                        id, boat_id, confidence, detected_at, bbox, location, drift_path, label
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                        %s, %s
                    );
                    """,
                    (
                        detection_id,
                        report.boat_id,
                        det.confidence,
                        report.timestamp,
                        json.dumps(det.bbox),
                        projected_lon,
                        projected_lat,
                        drift_path_json,
                        det.label,
                    ),
                )

                saved_detections.append(
                    DetectionSaved(
                        id=detection_id,
                        boat_id=report.boat_id,
                        confidence=det.confidence,
                        detected_at=report.timestamp,
                        bbox=det.bbox,
                        projected_lat=projected_lat,
                        projected_lon=projected_lon,
                        drift_path=drift_path,
                        label=det.label,
                    )
                )

        conn.commit()

    return {
        "boat_id": report.boat_id,
        "detections_saved": len(saved_detections),
        "detections": saved_detections,
    }


@app.get("/api/detections")
def get_detections(
    min_lat: float | None = Query(default=None),
    max_lat: float | None = Query(default=None),
    min_lon: float | None = Query(default=None),
    max_lon: float | None = Query(default=None),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
    since: float | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=5000),
    drift_days: int = Query(default=1, ge=1, le=7),
    include_drift: bool = Query(default=False),
) -> dict:
    where_parts = [sql.SQL("confidence >= %s")]
    params: list[object] = [min_confidence]

    if since is not None:
        where_parts.append(sql.SQL("detected_at >= %s"))
        params.append(since)

    if None not in (min_lat, max_lat, min_lon, max_lon):
        assert min_lat is not None
        assert max_lat is not None
        assert min_lon is not None
        assert max_lon is not None
        where_parts.append(
            sql.SQL("""
            ST_Intersects(
                location::geometry,
                ST_MakeEnvelope(%s, %s, %s, %s, 4326)
            )
            """)
        )
        params.extend([min_lon, min_lat, max_lon, max_lat])

    where_sql = sql.SQL(" AND ").join(where_parts)
    select_drift_sql = (
        sql.SQL("drift_path") if include_drift else sql.SQL("NULL::jsonb AS drift_path")
    )
    limit_sql = sql.SQL("LIMIT %s") if limit is not None else sql.SQL("")
    query = sql.SQL("""
        SELECT
            id::text,
            boat_id,
            confidence,
            detected_at,
            ST_Y(location::geometry) AS lat,
            ST_X(location::geometry) AS lon,
            {select_drift_sql},
            label
        FROM detections
        WHERE {where_sql}
        ORDER BY detected_at DESC
        {limit_sql}
    """).format(
        select_drift_sql=select_drift_sql,
        where_sql=where_sql,
        limit_sql=limit_sql,
    )

    if limit is not None:
        params.append(limit)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    points: list[DetectionPointResponse] = []
    for row in rows:
        cached_drift = row[6] if row[6] else []

        points.append(
            DetectionPointResponse(
                id=row[0],
                boat_id=row[1],
                confidence=row[2],
                detected_at=row[3],
                lat=row[4],
                lon=row[5],
                drift_path=cached_drift,
                label=row[7] if row[7] else "trash",
            )
        )
    return {"detections": points}


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
                    b.weight_class,
                    b.last_image IS NOT NULL AS has_image
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
            "has_image": bool(row[7]),
        }
        for row in rows
    ]
    return {"boats": boats}


@app.get("/api/boats/{boat_id}/image")
def get_boat_image(boat_id: str) -> BoatImageResponse:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT last_image
                FROM boats
                WHERE id = %s;
                """,
                (boat_id,),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="boat not found")

    image = f"data:image/jpeg;base64,{row[0]}" if row[0] else None
    return BoatImageResponse(boat_id=boat_id, image=image)


@app.get("/api/boats/history")
def get_boat_position_history(
    boat_id: str | None = Query(default=None),
    minutes: int = Query(default=30, ge=1, le=180),
) -> dict:
    min_timestamp = None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(timestamp), 0) FROM boat_states;")
            latest_timestamp_row = cur.fetchone()
            if latest_timestamp_row is None:
                latest_timestamp = 0
            else:
                latest_timestamp = latest_timestamp_row[0]
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
            cur.execute("SELECT COUNT(*) FROM detections;")
            total_detections_row = cur.fetchone()
            total_detections = total_detections_row[0] if total_detections_row else 0

            cur.execute("SELECT COUNT(*) FROM boat_states;")
            active_boats_row = cur.fetchone()
            active_boats = active_boats_row[0] if active_boats_row else 0

            cur.execute("SELECT MAX(detected_at) FROM detections;")
            last_detection_time_row = cur.fetchone()
            last_detection_time = (
                last_detection_time_row[0] if last_detection_time_row else None
            )

            cur.execute("SELECT label, COUNT(*) FROM detections GROUP BY label;")
            label_rows = cur.fetchall()

    label_counts = {row[0]: row[1] for row in label_rows}

    return {
        "total_detections": total_detections,
        "active_boats": active_boats,
        "last_detection_time": last_detection_time,
        "label_counts": label_counts,
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
        raise HTTPException(
            status_code=503, detail=f"Database unhealthy: {exc}"
        ) from exc
