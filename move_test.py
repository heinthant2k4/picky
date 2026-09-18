"""Deliberate one-way Dobot PTP move test. This script has no default target."""
from __future__ import annotations

import argparse
import sys

from dobot_client import DobotError, DobotMotionClient


def print_pose(label: str, robot: DobotMotionClient) -> None:
    pose = robot.get_pose()
    print(f"{label}: x={pose.x:.3f}, y={pose.y:.3f}, z={pose.z:.3f}, theta={pose.r:.3f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded single Dobot MOVJ XYZ test")
    parser.add_argument("--port", default="COM9")
    parser.add_argument("--x", type=float, required=True, help="safe target X in mm")
    parser.add_argument("--y", type=float, required=True, help="safe target Y in mm")
    parser.add_argument("--z", type=float, required=True, help="safe target Z in mm")
    parser.add_argument("--theta", type=float, default=0.0, help="target rotation in degrees")
    parser.add_argument("--timeout", type=float, default=30.0, help="completion deadline in seconds")
    parser.add_argument("--run", action="store_true", help="permit the movement command")
    args = parser.parse_args()

    target = f"x={args.x:.3f}, y={args.y:.3f}, z={args.z:.3f}, theta={args.theta:.3f}"
    print(f"Plan: clear stale queued commands and execute one MOVJ XYZ move to {target}.")
    if not args.run:
        print("Dry run only. Select a known-clear target, then add --run.")
        return 0
    try:
        with DobotMotionClient(args.port, reply_timeout=2.0) as robot:
            print_pose("Pose before move", robot)
            if input("Type MOVE to send this one movement command: ").strip() != "MOVE":
                print("Move cancelled; only the read-only pose query was sent.")
                return 0
            robot.prepare_motion_queue()
            command_index = robot.move_ptp(args.x, args.y, args.z, args.theta)
            print(f"Move queued as command {command_index}; waiting up to {args.timeout:.0f} seconds...")
            robot.wait_for_command(command_index, timeout=args.timeout)
            print_pose("Pose after move", robot)
            print("PASS: movement command completed.")
    except DobotError as error:
        print(f"FAIL: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
