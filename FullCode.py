"""Windows Dobot cube-stacking prototype.

The default is camera-only. Motion requires --execute and a second confirmation.
No homing command is used by this program.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2 as cv
import numpy as np

from dobot_client import DobotClient, Pose

DEFAULT_PORT = os.environ.get("DOBOT_PORT", "COM9")
DEFAULT_CAMERA_INDEX = int(os.environ.get("DOBOT_CAMERA_INDEX", 1))
CALIBRATION_PATH = Path(__file__).with_name("calibration.json")
VALID_COLOURS = ("R", "G", "B", "Y")


@dataclass(frozen=True)
class Calibration:
    """Centre reference and one grid-cell step, both in millimetres."""
    home: tuple[float, float, float]
    gap: tuple[float, float, float]

    @classmethod
    def load(cls, path: Path) -> "Calibration":
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
        try:
            home = tuple(float(value) for value in data["home"])
            gap = tuple(float(value) for value in data["gap"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid calibration file: {path}") from error
        if len(home) != 3 or len(gap) != 3:
            raise ValueError("Calibration home and gap must each contain x, y, z.")
        return cls(home, gap)

    def save(self, path: Path) -> None:
        with path.open("w", encoding="utf-8") as file:
            json.dump({"home": self.home, "gap": self.gap}, file, indent=2)

    def position(self, grid_x: float, grid_y: float, grid_z: float) -> tuple[float, float, float]:
        return tuple(self.home[i] + factor * self.gap[i]
                     for i, factor in enumerate((grid_x, grid_y, grid_z)))


def classify_colour(hsv: np.ndarray) -> str:
    hue, saturation, value = (float(component) for component in hsv)
    if value < 50 or saturation < 40:
        return "N"
    if 0 <= hue <= 10 or 160 <= hue <= 179:
        return "R"
    if 20 <= hue <= 35:
        return "Y"
    if 36 <= hue <= 85:
        return "G"
    if 86 <= hue <= 125:
        return "B"
    return "?"


def detect_grid(frame: np.ndarray) -> tuple[np.ndarray, list[tuple[tuple[int, int], tuple[int, int]]]]:
    height, width = frame.shape[:2]
    half, border = 55, 26
    centre_x, centre_y = width // 2, height // 2
    offsets = (-(2 * half + border), 0, 2 * half + border)
    rectangles = [
        ((centre_x + col - half - border // 2, centre_y + row - half - border // 2),
         (centre_x + col + half + border // 2, centre_y + row + half + border // 2))
        for row in offsets for col in offsets
    ]
    colours = np.full((3, 3), "?", dtype="U1")
    hsv_frame = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
    for index, (top_left, bottom_right) in enumerate(rectangles):
        x = int(np.clip((top_left[0] + bottom_right[0]) // 2, 0, width - 1))
        y = int(np.clip((top_left[1] + bottom_right[1]) // 2, 0, height - 1))
        patch = hsv_frame[max(0, y - 6):y + 7, max(0, x - 6):x + 7]
        colours[index // 3, index % 3] = classify_colour(patch.mean(axis=(0, 1)))
    return colours, rectangles


def capture_grid(camera_index: int) -> np.ndarray:
    """Return the grid shown when the user presses q; this never opens COM ports."""
    camera = cv.VideoCapture(camera_index, cv.CAP_DSHOW)
    if not camera.isOpened():
        raise RuntimeError(f"Cannot open camera {camera_index}; try --camera-index 0 or 1.")
    print("Camera ready. Align the board and press q to accept the detected grid.")
    try:
        while True:
            received, frame = camera.read()
            if not received:
                raise RuntimeError("Cannot read a frame from the camera.")
            colours, rectangles = detect_grid(frame)
            for index, (top_left, bottom_right) in enumerate(rectangles):
                x = (top_left[0] + bottom_right[0]) // 2
                y = (top_left[1] + bottom_right[1]) // 2
                row, column = divmod(index, 3)
                cv.rectangle(frame, top_left, bottom_right, (0, 0, 225), 2)
                cv.putText(frame, colours[row, column], (x - 8, y + 18),
                           cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv.LINE_AA)
            cv.imshow("Dobot grid preview (q = accept)", frame)
            if cv.waitKey(1) & 0xFF == ord("q"):
                return colours
    finally:
        camera.release()
        cv.destroyAllWindows()


class Robot:
    """Read-only robot connection with finite serial timeouts."""
    def __init__(self, port: str) -> None:
        self.port = port
        self.device: DobotClient | None = None

    def connect(self) -> None:
        print(f"Connecting to Dobot at {self.port}...")
        self.device = DobotClient(self.port, reply_timeout=2.0)
        self.device.open()
        print("Dobot serial connection opened with finite timeouts.")

    def close(self) -> None:
        if self.device is not None:
            self.device.close()
            self.device = None

    def pose(self) -> Pose:
        if self.device is None:
            raise RuntimeError("Robot is not connected.")
        return self.device.get_pose()

    def move_to(self, x: float, y: float, z: float, r: float = 0) -> None:
        raise RuntimeError("Motion is disabled: this client implements read-only pose queries only.")

    def suck(self, enabled: bool) -> None:
        raise RuntimeError("Suction is disabled: this client implements read-only pose queries only.")


GRID_COORDINATES = {
    (0, 0): (1, -1), (0, 1): (1, 0), (0, 2): (1, 1),
    (1, 0): (0, -1), (1, 1): (0, 0), (1, 2): (0, 1),
    (2, 0): (-1, -1), (2, 1): (-1, 0), (2, 2): (-1, 1),
}


def find_blocks(grid: np.ndarray, requested: Iterable[str]) -> list[tuple[str, int, int]]:
    remaining = grid.copy()
    selected = []
    for colour in requested:
        locations = np.argwhere(remaining == colour)
        if not len(locations):
            raise ValueError(f"No unused {colour} block was found in the detected grid.")
        row, column = (int(value) for value in locations[0])
        selected.append((colour, row, column))
        remaining[row, column] = "0"
    return selected


def execute_stack(robot: Robot, calibration: Calibration, blocks: list[tuple[str, int, int]]) -> None:
    """The only function that sends movement/suction commands."""
    for level, (colour, row, column) in enumerate(blocks, start=1):
        grid_x, grid_y = GRID_COORDINATES[(row, column)]
        pick_x, pick_y, _ = calibration.position(grid_x, grid_y, 0)
        safe_z = calibration.position(grid_x, grid_y, level + 0.5)[2]
        pickup_z = calibration.position(grid_x, grid_y, 1)[2]
        place_x, place_y, place_z = calibration.position(0, 0, level)
        print(f"Moving {colour} from ({row}, {column}) to stack level {level}.")
        robot.move_to(pick_x, pick_y, safe_z)
        robot.move_to(pick_x, pick_y, pickup_z)
        robot.suck(True)
        robot.move_to(pick_x, pick_y, safe_z)
        robot.move_to(place_x, place_y, safe_z)
        robot.move_to(place_x, place_y, place_z)
        robot.suck(False)
        robot.move_to(place_x, place_y, safe_z)


def calibrate(robot: Robot, path: Path) -> None:
    """Save two manually-positioned poses; it sends pose queries only."""
    input("Manually place the arm at the centre reference, then press Enter: ")
    home_pose = robot.pose()
    input("Manually place it one grid step at (+1, +1, +1), then press Enter: ")
    reference_pose = robot.pose()
    home = (home_pose.x, home_pose.y, home_pose.z)
    gap = tuple(reference_pose[i] - home[i] for i in range(3))
    Calibration(home, gap).save(path)
    print(f"Saved calibration to {path}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Windows Dobot cube-stacking prototype")
    parser.add_argument("--port", default=DEFAULT_PORT, help="Dobot port (default: %(default)s)")
    parser.add_argument("--camera-index", type=int, default=DEFAULT_CAMERA_INDEX)
    parser.add_argument("--colours", nargs=4, metavar="COLOUR", help="Stack colours, bottom to top")
    parser.add_argument("--calibrate", action="store_true", help="Record manual pose readings only")
    parser.add_argument("--execute", action="store_true", help="Allow motion after typed confirmation")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    grid = capture_grid(args.camera_index)
    print("Detected grid:\n", grid)
    if args.execute:
        raise RuntimeError(
            "--execute is intentionally disabled. The new timeout-safe client is read-only; "
            "motion commands must be reviewed and added in a separate step."
        )
    if not args.calibrate and not args.execute:
        print("Camera-only run complete. No serial port was opened.")
        return
    robot = Robot(args.port)
    try:
        robot.connect()
        if args.calibrate:
            calibrate(robot, CALIBRATION_PATH)
    finally:
        robot.close()


if __name__ == "__main__":
    main()
