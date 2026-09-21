"""Camera-only HSV inspection tool for tuning Dobot grid colour detection."""
from __future__ import annotations

import argparse

import cv2 as cv
import numpy as np

from FullCode import detect_grid, preprocess_frame, sample_patch_hsv


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect HSV values sampled from the 3x3 block grid")
    parser.add_argument("--camera-index", type=int, default=2)
    args = parser.parse_args()

    camera = cv.VideoCapture(args.camera_index, cv.CAP_DSHOW)
    if not camera.isOpened():
        raise RuntimeError(f"Cannot open camera {args.camera_index}; try 0 or 1.")

    print("Place blocks in the grid. Press q to print the preprocessed HSV values and exit.")
    last_samples: list[tuple[int, int, float, float, float, str]] = []
    try:
        while True:
            received, frame = camera.read()
            if not received:
                raise RuntimeError("Cannot read a frame from the camera.")
            colours, rectangles = detect_grid(frame)
            hsv_frame = cv.cvtColor(preprocess_frame(frame), cv.COLOR_BGR2HSV)
            height, width = frame.shape[:2]
            samples = []

            for index, (top_left, bottom_right) in enumerate(rectangles):
                x = int(np.clip((top_left[0] + bottom_right[0]) // 2, 0, width - 1))
                y = int(np.clip((top_left[1] + bottom_right[1]) // 2, 0, height - 1))
                hue, saturation, value = (float(component) for component in sample_patch_hsv(hsv_frame, x, y))
                row, column = divmod(index, 3)
                detected = colours[row, column]
                samples.append((row, column, hue, saturation, value, detected))
                cv.rectangle(frame, top_left, bottom_right, (0, 0, 225), 2)
                label = f"{detected} H{hue:.0f} S{saturation:.0f} V{value:.0f}"
                cv.putText(frame, label, (top_left[0] + 5, top_left[1] + 22),
                           cv.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv.LINE_AA)

            last_samples = samples
            cv.imshow("HSV tuner (q = print values and exit)", frame)
            if cv.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        camera.release()
        cv.destroyAllWindows()

    print("Sampled grid HSV values:")
    for row, column, hue, saturation, value, detected in last_samples:
        print(f"  cell ({row}, {column}): H={hue:.1f}, S={saturation:.1f}, V={value:.1f} -> {detected}")


if __name__ == "__main__":
    main()
