import argparse

import cv2
import holoocean

def main() -> None:
    parser = argparse.ArgumentParser(description="Live ViewportCapture viewer for HoloOcean.")
    parser.add_argument("--scenario", default="OpenWater-HoveringCamera")
    parser.add_argument("--sensor", default="ViewportCapture")

    # VERY IMPORTANT, MUST 1000% MATCH THE CONFIG SIZE, IF NOT YOU ARE COOKED, OUT OF BOUNDS READ
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument(
        "--show-viewport",
        action="store_true",
        help="Show native HoloOcean viewport window (can introduce resize tearing).",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    with holoocean.make(
        scenario_name=args.scenario,
        window_res=(args.height, args.width),
        show_viewport=args.show_viewport,
        verbose=args.verbose,
    ) as env:
        cv2.namedWindow("ViewportCapture", cv2.WINDOW_NORMAL)
        print(
            f"scenario={args.scenario} sensor={args.sensor} "
            f"window={args.width}x{args.height} show_viewport={args.show_viewport}"
        )
        print("Press q or Esc to exit.")

        first = True
        while True:
            state = env.tick()

            if args.sensor not in state:
                if first:
                    print(f"Sensor '{args.sensor}' not found. State keys: {list(state.keys())}")
                    first = False
                continue

            frame = state[args.sensor]
            if first:
                print(f"frame shape={tuple(frame.shape)} dtype={frame.dtype}")
                first = False

            if frame.ndim == 3 and frame.shape[2] == 4:
                # ViewportCapture in this build is BGRA.
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            else:
                # RGBCamera sensors are RGB.
                frame_bgr = cv2.cvtColor(frame[:, :, :3], cv2.COLOR_RGB2BGR)
            cv2.imshow("ViewportCapture", frame_bgr)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
