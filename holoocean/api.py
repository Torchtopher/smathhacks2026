import os
import threading
import time
import logging
import traceback
import math
from base64 import b64encode
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

import holoocean

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("holoocean_api")


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def find_viewport_key(state: dict, preferred_name: str) -> Optional[str]:
    if preferred_name in state and isinstance(state[preferred_name], np.ndarray):
        if state[preferred_name].ndim >= 3:
            return preferred_name

    if "ViewportCapture" in state and isinstance(state["ViewportCapture"], np.ndarray):
        if state["ViewportCapture"].ndim >= 3:
            return "ViewportCapture"

    for key, value in state.items():
        if isinstance(value, np.ndarray) and value.ndim >= 3 and "viewport" in key.lower():
            return key
    return None


def find_camera_key(state: dict) -> Optional[str]:
    for key, value in state.items():
        if isinstance(value, np.ndarray) and value.ndim >= 3 and "camera" in key.lower():
            return key
    return None


def find_pose_key(state: dict, preferred_name: str) -> Optional[str]:
    if preferred_name in state:
        candidate = as_pose_matrix(state[preferred_name])
        if candidate is not None:
            return preferred_name

    for key, value in state.items():
        if "pose" not in key.lower():
            continue
        if as_pose_matrix(value) is not None:
            return key

    for key, value in state.items():
        if as_pose_matrix(value) is not None:
            return key

    return None


def select_agent_state(
    raw_state: dict,
    preferred_agent_name: Optional[str],
) -> tuple[dict, Optional[str]]:
    """Pick a sensor dictionary from either single-agent or multi-agent tick output."""
    if not isinstance(raw_state, dict):
        return {}, preferred_agent_name

    if preferred_agent_name is not None:
        preferred_state = raw_state.get(preferred_agent_name)
        if isinstance(preferred_state, dict):
            return preferred_state, preferred_agent_name

    nested_states: list[tuple[str, dict]] = [
        (agent_name, agent_state)
        for agent_name, agent_state in raw_state.items()
        if isinstance(agent_state, dict)
    ]
    if nested_states:
        for agent_name, agent_state in nested_states:
            if find_viewport_key(agent_state, "ViewportCapture") is not None:
                return agent_state, agent_name
            if find_camera_key(agent_state) is not None:
                return agent_state, agent_name
        return nested_states[0][1], nested_states[0][0]

    return raw_state, preferred_agent_name


def get_agent_sensor_state(raw_state: dict, agent_name: Optional[str]) -> dict:
    if not isinstance(raw_state, dict):
        return {}

    if agent_name is not None:
        named_state = raw_state.get(agent_name)
        if isinstance(named_state, dict):
            return named_state

    nested_states = [value for value in raw_state.values() if isinstance(value, dict)]
    if nested_states:
        return nested_states[0]

    return raw_state


def to_float_list(value: np.ndarray) -> list[float]:
    arr = np.asarray(value).astype(np.float64).reshape(-1)
    return [float(x) for x in arr.tolist()]


def as_pose_matrix(value: np.ndarray) -> Optional[np.ndarray]:
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape == (4, 4):
        return arr
    if arr.size == 16:
        return arr.reshape(4, 4)
    return None


def euler_zyx_deg_from_rotation(rotation: np.ndarray) -> tuple[float, float, float]:
    # ZYX intrinsic convention:
    # yaw (Z), pitch (Y), roll (X).
    sy = math.sqrt(rotation[0, 0] ** 2 + rotation[1, 0] ** 2)
    singular = sy < 1e-6
    if not singular:
        roll = math.atan2(rotation[2, 1], rotation[2, 2])
        pitch = math.atan2(-rotation[2, 0], sy)
        yaw = math.atan2(rotation[1, 0], rotation[0, 0])
    else:
        roll = math.atan2(-rotation[1, 2], rotation[1, 1])
        pitch = math.atan2(-rotation[2, 0], sy)
        yaw = 0.0
    return math.degrees(roll), math.degrees(pitch), math.degrees(yaw)


def build_differential_command(
    buffer_shape: tuple[int, ...],
    forward: float,
    diff: float,
) -> np.ndarray:
    command = np.zeros(buffer_shape, dtype=np.float32)
    flat = command.reshape(-1)
    action_size = int(flat.size)

    if action_size == 1:
        flat[0] = forward
    elif action_size == 2:
        flat[0] = forward - diff
        flat[1] = forward + diff
    elif action_size >= 4:
        flat[0] = forward - diff
        flat[1] = forward + diff
        flat[2] = forward - diff
        flat[3] = forward + diff
    else:
        flat[:] = forward

    return command


def build_circle_command(buffer_shape: tuple[int, ...]) -> np.ndarray:
    forward = float(os.getenv("CIRCLE_THRUST", "220.0"))
    # Smaller diff -> wider turn radius.
    diff = float(os.getenv("CIRCLE_DIFF", "25.0"))
    return build_differential_command(buffer_shape, forward=forward, diff=diff)


def build_line_command(buffer_shape: tuple[int, ...], tick: int) -> np.ndarray:
    forward = float(os.getenv("LINE_THRUST", "220.0"))
    half_period_ticks = max(1, int(os.getenv("LINE_HALF_PERIOD_TICKS", "420")))
    direction = 1.0 if ((tick // half_period_ticks) % 2) == 0 else -1.0
    return build_differential_command(buffer_shape, forward=direction * forward, diff=0.0)


@dataclass
class FrameData:
    jpeg: Optional[bytes] = None
    image_key: Optional[str] = None
    image_source: str = "viewport"
    pose_key: Optional[str] = None
    capture_agent_name: Optional[str] = None
    capture_agent_index: Optional[int] = None
    viewport_agent_name: Optional[str] = None
    viewport_agent_index: Optional[int] = None
    pose_matrix: Optional[list[list[float]]] = None
    position: Optional[list[float]] = None
    angles_deg: Optional[dict[str, float]] = None
    bearing_deg: Optional[float] = None
    tick: int = 0
    unix_time_s: float = 0.0
    error: Optional[str] = None
    error_traceback: Optional[str] = None


class HoloOceanViewportService:
    def __init__(
        self,
        scenario_name: str,
        viewport_sensor_name: str,
        pose_sensor_name: str,
        viewport_width: int,
        viewport_height: int,
        holoocean_verbose: bool,
        holoocean_show_viewport: bool,
        jpeg_quality: int = 80,
    ):
        self.scenario_name = scenario_name
        self.viewport_sensor_name = viewport_sensor_name
        self.pose_sensor_name = pose_sensor_name
        self.viewport_width = int(viewport_width)
        self.viewport_height = int(viewport_height)
        self.holoocean_verbose = bool(holoocean_verbose)
        self.holoocean_show_viewport = bool(holoocean_show_viewport)
        self.jpeg_quality = int(np.clip(jpeg_quality, 1, 100))

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._ready = threading.Condition(self._lock)
        self._frame = FrameData()
        self._agent_names: list[str] = []
        self._requested_viewport_agent_index: Optional[int] = None

    def _validate_agent_index_locked(self, agent_index: int) -> None:
        if agent_index < -1:
            raise ValueError("agent_index must be -1 or >= 0")
        if agent_index == -1:
            return
        if self._agent_names and agent_index >= len(self._agent_names):
            raise ValueError(
                f"agent_index {agent_index} is out of range for {len(self._agent_names)} agents"
            )

    def set_viewport_agent_index(self, agent_index: int) -> None:
        with self._ready:
            self._validate_agent_index_locked(agent_index)
            self._requested_viewport_agent_index = agent_index
            self._ready.notify_all()

    def agent_names(self) -> list[str]:
        with self._ready:
            return list(self._agent_names)

    def requested_viewport_agent(self) -> tuple[Optional[int], Optional[str]]:
        with self._ready:
            index = self._requested_viewport_agent_index
            names = list(self._agent_names)
        if index is None or index < 0 or index >= len(names):
            return index, None
        return index, names[index]

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="holoocean-viewport", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        try:
            with holoocean.make(
                scenario_name=self.scenario_name,
                window_res=(self.viewport_height, self.viewport_width),
                verbose=self.holoocean_verbose,
                show_viewport=self.holoocean_show_viewport,
            ) as env:
                if hasattr(env, "_agent") and getattr(env, "_agent") is not None:
                    act_agent_name = env._agent.name
                elif hasattr(env, "agents") and getattr(env, "agents"):
                    act_agent_name = next(iter(env.agents.keys()))
                else:
                    raise RuntimeError("No controllable agent found in scenario")

                agent = env.agents.get(act_agent_name)
                if agent is None:
                    raise RuntimeError(f"Agent '{act_agent_name}' was not found in environment")
                logger.info(
                    "Using scenario sensors for agent '%s': %s",
                    act_agent_name,
                    ", ".join(agent.sensors.keys()),
                )
                agent_names = list(env.agents.keys())
                agent_index_by_name = {name: idx for idx, name in enumerate(agent_names)}
                if not agent_names:
                    raise RuntimeError("No agents found in environment")
                logger.info("Available agents: %s", ", ".join(agent_names))

                image_key = None
                image_source = "unknown"
                pose_key = None
                capture_agent_name = act_agent_name
                capture_agent_index = agent_index_by_name.get(capture_agent_name)
                logged_capture_agent_switch = False
                active_viewport_agent_name = None
                active_viewport_agent_index = None
                viewport_switch_settle_ticks = max(
                    0, int(os.getenv("VIEWPORT_SWITCH_SETTLE_TICKS", "1"))
                )
                remaining_settle_ticks = 0
                tick = 0
                logged_frame_shape = False

                default_circle_agent = agent_names[0]
                default_line_agent = agent_names[1] if len(agent_names) > 1 else agent_names[0]
                circle_agent_name = os.getenv("CIRCLE_AGENT_NAME", default_circle_agent)
                if circle_agent_name not in env.agents:
                    logger.warning(
                        "CIRCLE_AGENT_NAME='%s' not found; using '%s'",
                        circle_agent_name,
                        default_circle_agent,
                    )
                    circle_agent_name = default_circle_agent
                line_agent_name = os.getenv("LINE_AGENT_NAME", default_line_agent)
                if line_agent_name not in env.agents:
                    logger.warning(
                        "LINE_AGENT_NAME='%s' not found; using '%s'",
                        line_agent_name,
                        default_line_agent,
                    )
                    line_agent_name = default_line_agent
                if line_agent_name == circle_agent_name and len(agent_names) > 1:
                    for candidate in agent_names:
                        if candidate != circle_agent_name:
                            line_agent_name = candidate
                            break

                motion_profiles: dict[str, str] = {circle_agent_name: "circle"}
                motion_profiles[line_agent_name] = "line"
                motion_buffer_shapes: dict[str, tuple[int, ...]] = {}
                disabled_motion_agents: set[str] = set()
                for motion_agent_name, profile in motion_profiles.items():
                    motion_agent = env.agents.get(motion_agent_name)
                    if motion_agent is None:
                        logger.warning(
                            "Skipping motion profile '%s' for missing agent '%s'",
                            profile,
                            motion_agent_name,
                        )
                        disabled_motion_agents.add(motion_agent_name)
                        continue
                    try:
                        buffer_shape = tuple(motion_agent.action_space.buffer_shape)
                        motion_buffer_shapes[motion_agent_name] = buffer_shape
                        logger.info(
                            "Motion profile agent='%s' profile='%s' action_shape=%s",
                            motion_agent_name,
                            profile,
                            buffer_shape,
                        )
                    except Exception:
                        logger.exception(
                            "Could not infer action size for '%s'; disabling motion profile '%s'",
                            motion_agent_name,
                            profile,
                        )
                        disabled_motion_agents.add(motion_agent_name)

                missing_viewport_ticks = 0
                max_missing_viewport_ticks = int(os.getenv("MAX_MISSING_VIEWPORT_TICKS", "300"))
                has_seen_viewport_frame = False
                with self._ready:
                    self._agent_names = list(agent_names)
                    if (
                        self._requested_viewport_agent_index is not None
                        and self._requested_viewport_agent_index >= len(agent_names)
                    ):
                        logger.warning(
                            "Requested viewport agent index %s is out of range; clearing request",
                            self._requested_viewport_agent_index,
                        )
                        self._requested_viewport_agent_index = None
                    self._ready.notify_all()

                while not self._stop_event.is_set():
                    for motion_agent_name, profile in motion_profiles.items():
                        if motion_agent_name in disabled_motion_agents:
                            continue
                        buffer_shape = motion_buffer_shapes.get(motion_agent_name)
                        if buffer_shape is None:
                            continue
                        try:
                            if profile == "circle":
                                motion_command = build_circle_command(buffer_shape)
                            else:
                                motion_command = build_line_command(buffer_shape, tick=tick)
                            env.act(motion_agent_name, motion_command)
                        except Exception:
                            logger.exception(
                                "env.act failed for agent '%s' with profile '%s'; disabling it",
                                motion_agent_name,
                                profile,
                            )
                            disabled_motion_agents.add(motion_agent_name)

                    state = env.tick()
                    tick += 1

                    with self._ready:
                        requested_viewport_agent_index = self._requested_viewport_agent_index
                    if requested_viewport_agent_index == -1:
                        requested_viewport_agent_index = None
                    requested_viewport_agent_name = None
                    target_pose_key = None
                    target_pose = None
                    if requested_viewport_agent_index is not None:
                        if requested_viewport_agent_index >= len(agent_names):
                            requested_viewport_agent_index = len(agent_names) - 1
                        requested_viewport_agent_name = agent_names[requested_viewport_agent_index]

                        target_agent_state = get_agent_sensor_state(
                            state, requested_viewport_agent_name
                        )
                        target_pose_key = find_pose_key(target_agent_state, self.pose_sensor_name)
                        if target_pose_key is not None and target_pose_key in target_agent_state:
                            target_pose = as_pose_matrix(target_agent_state[target_pose_key])

                        if requested_viewport_agent_index != active_viewport_agent_index:
                            active_viewport_agent_index = requested_viewport_agent_index
                            active_viewport_agent_name = requested_viewport_agent_name
                            remaining_settle_ticks = viewport_switch_settle_ticks
                            logger.info(
                                "Viewport target agent changed to '%s' (index=%d)",
                                active_viewport_agent_name,
                                active_viewport_agent_index,
                            )

                        if target_pose is not None:
                            viewport_position = to_float_list(target_pose[:3, 3])
                            roll, pitch, yaw = euler_zyx_deg_from_rotation(target_pose[:3, :3])
                            try:
                                env.move_viewport(
                                    viewport_position,
                                    [float(roll), float(pitch), float(yaw)],
                                )
                            except Exception:
                                logger.exception(
                                    "move_viewport failed for agent '%s' (index=%d)",
                                    requested_viewport_agent_name,
                                    requested_viewport_agent_index,
                                )
                    else:
                        active_viewport_agent_name = None
                        active_viewport_agent_index = None
                        remaining_settle_ticks = 0

                    sensor_state, resolved_agent_name = select_agent_state(
                        state, capture_agent_name
                    )
                    if resolved_agent_name is not None:
                        capture_agent_name = resolved_agent_name
                        capture_agent_index = agent_index_by_name.get(capture_agent_name)
                    if (
                        not logged_capture_agent_switch
                        and capture_agent_name is not None
                        and capture_agent_name != act_agent_name
                    ):
                        logger.info(
                            "Reading capture sensors from '%s' while controlling '%s'",
                            capture_agent_name,
                            act_agent_name,
                        )
                        logged_capture_agent_switch = True

                    if image_key is None:
                        image_key = find_viewport_key(sensor_state, self.viewport_sensor_name)
                        if image_key is not None:
                            image_source = "viewport"
                        else:
                            image_key = find_camera_key(sensor_state)
                            if image_key is not None:
                                image_source = "camera"
                    if pose_key is None:
                        pose_key = find_pose_key(sensor_state, self.pose_sensor_name)
                    resolved_pose_key = pose_key

                    if image_key is None or image_key not in sensor_state:
                        if not has_seen_viewport_frame:
                            missing_viewport_ticks += 1
                        if (
                            not has_seen_viewport_frame
                            and missing_viewport_ticks >= max_missing_viewport_ticks
                        ):
                            raise RuntimeError(
                                "ViewportCapture data not found. Ensure viewport sensor is configured "
                                "and CaptureWidth/CaptureHeight match window_width/window_height."
                            )
                        continue

                    if remaining_settle_ticks > 0:
                        remaining_settle_ticks -= 1
                        continue

                    frame = sensor_state[image_key]
                    if not logged_frame_shape:
                        logger.info(
                            "First frame source=%s key=%s shape=%s dtype=%s",
                            image_source,
                            image_key,
                            tuple(frame.shape),
                            frame.dtype,
                        )
                        logged_frame_shape = True
                    if frame.ndim == 3 and frame.shape[2] == 4 and image_source == "viewport":
                        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    else:
                        frame_bgr = cv2.cvtColor(frame[:, :, :3], cv2.COLOR_RGB2BGR)
                    ok, encoded = cv2.imencode(
                        ".jpg",
                        frame_bgr,
                        [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality],
                    )
                    if not ok:
                        continue

                    has_seen_viewport_frame = True
                    missing_viewport_ticks = 0

                    pose_matrix = None
                    position = None
                    angles_deg = None
                    bearing_deg = None
                    raw_pose = target_pose
                    if raw_pose is not None:
                        resolved_pose_key = target_pose_key
                    elif pose_key is not None and pose_key in sensor_state:
                        raw_pose = as_pose_matrix(sensor_state[pose_key])
                    if raw_pose is not None:
                        rotation = raw_pose[:3, :3]
                        roll, pitch, yaw = euler_zyx_deg_from_rotation(rotation)
                        pose_matrix = raw_pose.astype(np.float64).tolist()
                        position = to_float_list(raw_pose[:3, 3])
                        angles_deg = {
                            "roll": float(roll),
                            "pitch": float(pitch),
                            "yaw": float(yaw),
                        }
                        bearing_deg = float((yaw + 360.0) % 360.0)

                    with self._ready:
                        self._frame = FrameData(
                            jpeg=encoded.tobytes(),
                            image_key=image_key,
                            image_source=image_source,
                            pose_key=resolved_pose_key,
                            capture_agent_name=capture_agent_name,
                            capture_agent_index=capture_agent_index,
                            viewport_agent_name=active_viewport_agent_name,
                            viewport_agent_index=active_viewport_agent_index,
                            pose_matrix=pose_matrix,
                            position=position,
                            angles_deg=angles_deg,
                            bearing_deg=bearing_deg,
                            tick=tick,
                            unix_time_s=time.time(),
                            error=None,
                            error_traceback=None,
                        )
                        self._ready.notify_all()

        except Exception as exc:
            tb = traceback.format_exc()
            logger.error("Background capture thread failed: %s", exc)
            logger.debug("Background capture traceback:\n%s", tb)
            with self._ready:
                self._frame.error = str(exc)
                self._frame.error_traceback = tb
                self._ready.notify_all()

    def latest_frame(self, wait_ms: int = 0, agent_index: Optional[int] = None) -> FrameData:
        deadline = time.time() + max(wait_ms, 0) / 1000.0
        if agent_index is not None:
            self.set_viewport_agent_index(agent_index)
        try:
            with self._ready:
                while self._frame.jpeg is None and self._frame.error is None:
                    remaining = deadline - time.time()
                    if wait_ms <= 0 or remaining <= 0:
                        break
                    self._ready.wait(timeout=remaining)
                while (
                    agent_index is not None
                    and agent_index >= 0
                    and self._frame.error is None
                    and self._frame.jpeg is not None
                    and self._frame.viewport_agent_index != agent_index
                ):
                    remaining = deadline - time.time()
                    if wait_ms <= 0 or remaining <= 0:
                        break
                    self._ready.wait(timeout=remaining)
                return FrameData(
                    jpeg=self._frame.jpeg,
                    image_key=self._frame.image_key,
                    image_source=self._frame.image_source,
                    pose_key=self._frame.pose_key,
                    capture_agent_name=self._frame.capture_agent_name,
                    capture_agent_index=self._frame.capture_agent_index,
                    viewport_agent_name=self._frame.viewport_agent_name,
                    viewport_agent_index=self._frame.viewport_agent_index,
                    pose_matrix=self._frame.pose_matrix,
                    position=self._frame.position,
                    angles_deg=self._frame.angles_deg,
                    bearing_deg=self._frame.bearing_deg,
                    tick=self._frame.tick,
                    unix_time_s=self._frame.unix_time_s,
                    error=self._frame.error,
                    error_traceback=self._frame.error_traceback,
                )
        finally:
            # agent_index targeting is one-shot so free camera control is not continuously overridden.
            if agent_index is not None:
                with self._ready:
                    if self._requested_viewport_agent_index == agent_index:
                        self._requested_viewport_agent_index = None
                        self._ready.notify_all()


# SCENARIO = os.getenv("HOLOOCEAN_SCENARIO", "OpenWater-HoveringCamera")
SCENARIO = os.getenv("HOLOOCEAN_SCENARIO", "SLAMCloud-test")

VIEWPORT_SENSOR_NAME = os.getenv("VIEWPORT_SENSOR_NAME", "ViewportCapture")
POSE_SENSOR_NAME = os.getenv("POSE_SENSOR_NAME", "PoseSensor")
VIEWPORT_WIDTH = int(os.getenv("VIEWPORT_WIDTH", "1280"))
VIEWPORT_HEIGHT = int(os.getenv("VIEWPORT_HEIGHT", "720"))
HOLOOCEAN_VERBOSE = env_bool("HOLOOCEAN_VERBOSE", False)
HOLOOCEAN_SHOW_VIEWPORT = env_bool("HOLOOCEAN_SHOW_VIEWPORT", True)
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "90"))

viewport_service = HoloOceanViewportService(
    scenario_name=SCENARIO,
    viewport_sensor_name=VIEWPORT_SENSOR_NAME,
    pose_sensor_name=POSE_SENSOR_NAME,
    viewport_width=VIEWPORT_WIDTH,
    viewport_height=VIEWPORT_HEIGHT,
    holoocean_verbose=HOLOOCEAN_VERBOSE,
    holoocean_show_viewport=HOLOOCEAN_SHOW_VIEWPORT,
    jpeg_quality=JPEG_QUALITY,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    viewport_service.start()
    try:
        yield
    finally:
        viewport_service.stop()


app = FastAPI(title="HoloOcean Viewport API", lifespan=lifespan)


@app.get("/health")
def health():
    frame = viewport_service.latest_frame(wait_ms=0)
    requested_agent_index, requested_agent_name = viewport_service.requested_viewport_agent()
    agent_names = viewport_service.agent_names()
    return {
        "scenario": SCENARIO,
        "viewport_sensor_name": VIEWPORT_SENSOR_NAME,
        "pose_sensor_name": POSE_SENSOR_NAME,
        "viewport_width": VIEWPORT_WIDTH,
        "viewport_height": VIEWPORT_HEIGHT,
        "num_agents": len(agent_names),
        "agents": agent_names,
        "requested_viewport_agent_index": requested_agent_index,
        "requested_viewport_agent_name": requested_agent_name,
        "viewport_agent_index": frame.viewport_agent_index,
        "viewport_agent_name": frame.viewport_agent_name,
        "capture_agent_index": frame.capture_agent_index,
        "capture_agent_name": frame.capture_agent_name,
        "holoocean_verbose": HOLOOCEAN_VERBOSE,
        "holoocean_show_viewport": HOLOOCEAN_SHOW_VIEWPORT,
        "ready": frame.jpeg is not None,
        "image_source": frame.image_source,
        "image_key": frame.image_key,
        "camera_key": frame.image_key,
        "pose_key": frame.pose_key,
        "pose_matrix": frame.pose_matrix,
        "position": frame.position,
        "angles_deg": frame.angles_deg,
        "bearing_deg": frame.bearing_deg,
        "tick": frame.tick,
        "error": frame.error,
        "error_traceback": frame.error_traceback,
    }


@app.get("/agents")
def agents():
    requested_agent_index, requested_agent_name = viewport_service.requested_viewport_agent()
    agent_names = viewport_service.agent_names()
    return {
        "agents": [{"index": index, "name": name} for index, name in enumerate(agent_names)],
        "requested_viewport_agent_index": requested_agent_index,
        "requested_viewport_agent_name": requested_agent_name,
    }


@app.get("/latest.jpg")
def latest_jpg(wait_ms: int = 0, agent_index: Optional[int] = None):
    try:
        frame = viewport_service.latest_frame(wait_ms=wait_ms, agent_index=agent_index)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if frame.error:
        raise HTTPException(status_code=500, detail=frame.error)
    if frame.jpeg is None:
        raise HTTPException(status_code=503, detail="No frame available yet")
    if agent_index is not None and agent_index >= 0 and frame.viewport_agent_index != agent_index:
        raise HTTPException(
            status_code=503,
            detail=(
                "Frame for requested agent index is not ready yet; "
                "increase wait_ms and retry"
            ),
        )

    position_values = frame.position or []
    angles = frame.angles_deg or {}
    angles_header = ""
    if angles:
        angles_header = ",".join(
            [
                str(angles.get("roll", "")),
                str(angles.get("pitch", "")),
                str(angles.get("yaw", "")),
            ]
        )
    return Response(
        content=frame.jpeg,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, max-age=0",
            "X-HoloOcean-Tick": str(frame.tick),
            "X-HoloOcean-Image-Source": frame.image_source,
            "X-HoloOcean-Image-Key": str(frame.image_key or ""),
            "X-HoloOcean-Camera-Key": str(frame.image_key or ""),
            "X-HoloOcean-Pose-Key": str(frame.pose_key or ""),
            "X-HoloOcean-Capture-Agent-Index": (
                "" if frame.capture_agent_index is None else str(frame.capture_agent_index)
            ),
            "X-HoloOcean-Capture-Agent-Name": str(frame.capture_agent_name or ""),
            "X-HoloOcean-Viewport-Agent-Index": (
                "" if frame.viewport_agent_index is None else str(frame.viewport_agent_index)
            ),
            "X-HoloOcean-Viewport-Agent-Name": str(frame.viewport_agent_name or ""),
            "X-HoloOcean-Position": ",".join(str(v) for v in position_values),
            "X-HoloOcean-Angles-Deg": angles_header,
            "X-HoloOcean-Bearing-Deg": (
                "" if frame.bearing_deg is None else str(frame.bearing_deg)
            ),
        },
    )


@app.get("/latest")
def latest(wait_ms: int = 0, include_image: bool = False, agent_index: Optional[int] = None):
    try:
        frame = viewport_service.latest_frame(wait_ms=wait_ms, agent_index=agent_index)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if frame.error:
        raise HTTPException(status_code=500, detail=frame.error)
    if frame.jpeg is None:
        raise HTTPException(status_code=503, detail="No frame available yet")
    if agent_index is not None and agent_index >= 0 and frame.viewport_agent_index != agent_index:
        raise HTTPException(
            status_code=503,
            detail=(
                "Frame for requested agent index is not ready yet; "
                "increase wait_ms and retry"
            ),
        )

    body = {
        "tick": frame.tick,
        "unix_time_s": frame.unix_time_s,
        "image_source": frame.image_source,
        "image_key": frame.image_key,
        "camera_key": frame.image_key,
        "pose_key": frame.pose_key,
        "capture_agent_name": frame.capture_agent_name,
        "capture_agent_index": frame.capture_agent_index,
        "viewport_agent_name": frame.viewport_agent_name,
        "viewport_agent_index": frame.viewport_agent_index,
        "pose_matrix": frame.pose_matrix,
        "position": frame.position,
        "angles_deg": frame.angles_deg,
        "bearing_deg": frame.bearing_deg,
    }
    if include_image:
        body["image_jpeg_base64"] = b64encode(frame.jpeg).decode("ascii")
    return body


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8900")),
        reload=False,
    )
