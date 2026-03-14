import os
import threading
import time
from base64 import b64encode
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

import holoocean


def find_camera_key(state: dict) -> Optional[str]:
    for key, value in state.items():
        if isinstance(value, np.ndarray) and value.ndim >= 3 and "camera" in key.lower():
            return key
    return None


def find_gps_key(state: dict) -> Optional[str]:
    for key, value in state.items():
        if isinstance(value, np.ndarray) and "gps" in key.lower():
            return key
    return None


def to_float_list(value: np.ndarray) -> list[float]:
    arr = np.asarray(value).astype(np.float64).reshape(-1)
    return [float(x) for x in arr.tolist()]


@dataclass
class FrameData:
    jpeg: Optional[bytes] = None
    camera_key: Optional[str] = None
    gps_key: Optional[str] = None
    gps: Optional[list[float]] = None
    tick: int = 0
    unix_time_s: float = 0.0
    error: Optional[str] = None


class HoloOceanCameraService:
    def __init__(self, scenario: str, jpeg_quality: int = 80):
        self.scenario = scenario
        self.jpeg_quality = int(np.clip(jpeg_quality, 1, 100))
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._ready = threading.Condition(self._lock)
        self._frame = FrameData()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="holoocean-camera", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        try:
            with holoocean.make(self.scenario) as env:
                camera_key = None
                gps_key = None
                tick = 0
                down_command = np.array([-10, -10, -10, -10, 0, 0, 0, 0], dtype=np.float32)
                should_send_command = True

                if hasattr(env, "_agent") and getattr(env, "_agent") is not None:
                    agent_name = env._agent.name
                elif hasattr(env, "agents") and getattr(env, "agents"):
                    agent_name = next(iter(env.agents.keys()))
                else:
                    agent_name = None

                while not self._stop_event.is_set():
                    if should_send_command and agent_name is not None:
                        try:
                            env.act(agent_name, down_command)
                        except Exception:
                            should_send_command = False

                    state = env.tick()
                    tick += 1

                    if camera_key is None:
                        camera_key = find_camera_key(state)
                        if camera_key is None:
                            continue
                    if gps_key is None:
                        gps_key = find_gps_key(state)

                    if camera_key not in state:
                        continue

                    frame = state[camera_key][:, :, :3]
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    ok, encoded = cv2.imencode(
                        ".jpg",
                        frame_bgr,
                        [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality],
                    )
                    if not ok:
                        continue

                    gps = None
                    if gps_key is not None and gps_key in state:
                        gps = to_float_list(state[gps_key])

                    with self._ready:
                        self._frame = FrameData(
                            jpeg=encoded.tobytes(),
                            camera_key=camera_key,
                            gps_key=gps_key,
                            gps=gps,
                            tick=tick,
                            unix_time_s=time.time(),
                            error=None,
                        )
                        self._ready.notify_all()

        except Exception as exc:
            with self._ready:
                self._frame.error = str(exc)
                self._ready.notify_all()

    def latest_frame(self, wait_ms: int = 0) -> FrameData:
        deadline = time.time() + max(wait_ms, 0) / 1000.0
        with self._ready:
            while self._frame.jpeg is None and self._frame.error is None:
                remaining = deadline - time.time()
                if wait_ms <= 0 or remaining <= 0:
                    break
                self._ready.wait(timeout=remaining)
            return FrameData(
                jpeg=self._frame.jpeg,
                camera_key=self._frame.camera_key,
                gps_key=self._frame.gps_key,
                gps=self._frame.gps,
                tick=self._frame.tick,
                unix_time_s=self._frame.unix_time_s,
                error=self._frame.error,
            )


# SCENARIO = os.getenv("HOLOOCEAN_SCENARIO", "PierHarbor-HoveringCamera")
SCENARIO = os.getenv("HOLOOCEAN_SCENARIO", "OpenWater-HoveringCamera")

JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "80"))
camera_service = HoloOceanCameraService(scenario=SCENARIO, jpeg_quality=JPEG_QUALITY)


@asynccontextmanager
async def lifespan(_: FastAPI):
    camera_service.start()
    try:
        yield
    finally:
        camera_service.stop()


app = FastAPI(title="HoloOcean Camera API", lifespan=lifespan)


@app.get("/health")
def health():
    frame = camera_service.latest_frame(wait_ms=0)
    return {
        "scenario": SCENARIO,
        "ready": frame.jpeg is not None,
        "camera_key": frame.camera_key,
        "gps_key": frame.gps_key,
        "gps": frame.gps,
        "tick": frame.tick,
        "error": frame.error,
    }


@app.get("/latest.jpg")
def latest_jpg(wait_ms: int = 0):
    frame = camera_service.latest_frame(wait_ms=wait_ms)
    if frame.error:
        raise HTTPException(status_code=500, detail=frame.error)
    if frame.jpeg is None:
        raise HTTPException(status_code=503, detail="No frame available yet")
    return Response(
        content=frame.jpeg,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, max-age=0",
            "X-HoloOcean-Tick": str(frame.tick),
            "X-HoloOcean-Camera-Key": str(frame.camera_key or ""),
            "X-HoloOcean-GPS-Key": str(frame.gps_key or ""),
            "X-HoloOcean-GPS": ",".join(str(v) for v in (frame.gps or [])),
        },
    )


@app.get("/latest")
def latest(wait_ms: int = 0, include_image: bool = False):
    frame = camera_service.latest_frame(wait_ms=wait_ms)
    if frame.error:
        raise HTTPException(status_code=500, detail=frame.error)
    if frame.jpeg is None:
        raise HTTPException(status_code=503, detail="No frame available yet")

    body = {
        "tick": frame.tick,
        "unix_time_s": frame.unix_time_s,
        "camera_key": frame.camera_key,
        "gps_key": frame.gps_key,
        "gps": frame.gps,
    }
    if include_image:
        body["image_jpeg_base64"] = b64encode(frame.jpeg).decode("ascii")
    return body


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
