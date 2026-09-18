"""Deliberate Dobot home test. This script moves the arm only with --run."""
from __future__ import annotations

import argparse
import sys

from dobot_client import DobotError, DobotMotionClient


def print_pose(label: str, robot: DobotMotionClient) -> None:
    pose = robot.get_pose()
    print(f"{label}: x={pose.x:.3f}, y={pose.y:.3f}, z={pose.z:.3f}, theta={pose.r:.3f}")
    print(f"          j1={pose.j1:.3f}, j2={pose.j2:.3f}, j3={pose.j3:.3f}, j4={pose.j4:.3f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded Dobot homing test")
    parser.add_argument("--port", default="COM9")
    parser.add_argument("--timeout", type=float, default=120.0, help="home completion deadline in seconds")
    parser.add_argument("--run", action="store_true", help="permit the home command")
    args = parser.parse_args()

    print("Plan: print pose, clear stale queued commands, start the queue, home, wait, print pose.")
    if not args.run:
        print("Dry run only. Add --run when the workspace is clear and you are ready.")
        return 0
    try:
        with DobotMotionClient(args.port, reply_timeout=2.0) as robot:
            print_pose("Pose before home", robot)
            if input("Type HOME to send the homing command: ").strip() != "HOME":
                print("Home cancelled; only the read-only pose query was sent.")
                return 0
            robot.prepare_motion_queue()
            command_index = robot.home()
            print(f"Home queued as command {command_index}; waiting up to {args.timeout:.0f} seconds...")
            robot.wait_for_command(command_index, timeout=args.timeout)
            print_pose("Pose after home", robot)
            print("PASS: home command completed.")
    except DobotError as error:
        print(f"FAIL: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
