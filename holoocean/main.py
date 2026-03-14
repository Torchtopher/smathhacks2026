import argparse

import holoocean
import numpy as np

try:
    import cv2
except ImportError as exc:
    raise SystemExit(
        "OpenCV is required for display. Install with: pip install opencv-python"
    ) from exc


def find_camera_key(state: dict) -> str | None:
    for key, value in state.items():
        if isinstance(value, np.ndarray) and value.ndim >= 3 and "camera" in key.lower():
            return key
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Display the default HoloOcean camera in an OpenCV window."
    )
    parser.add_argument(
        "--scenario",
        default="PierHarbor-HoveringCamera",
        help="HoloOcean scenario name (default: PierHarbor-HoveringCamera)",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=10_000,
        help="Maximum number of ticks before exit (default: 10000)",
    )
    args = parser.parse_args()

    with holoocean.make(args.scenario) as env:
        camera_key = None
        print(f"Running scenario: {args.scenario}")
        print("Press q or Esc in the camera window to exit.")

        for _ in range(args.ticks):
            state = env.tick()

            if camera_key is None:
                camera_key = find_camera_key(state)
                if camera_key is None:
                    continue
                print(f"Using camera sensor: {camera_key}")
                cv2.namedWindow("HoloOcean Camera", cv2.WINDOW_NORMAL)

            if camera_key not in state:
                continue

            frame = state[camera_key]
            frame_rgb = frame[:, :, :3]
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            cv2.imshow("HoloOcean Camera", frame_bgr)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
