"""Bounded, suction-only Dobot test. It sends no movement or home command."""
from __future__ import annotations

import argparse
import sys
import time

from dobot_client import DobotError, DobotMotionClient


def print_pose(robot: DobotMotionClient) -> None:
    pose = robot.get_pose()
    print(f"Current pose: x={pose.x:.3f}, y={pose.y:.3f}, z={pose.z:.3f}, theta={pose.r:.3f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded Dobot suction-only test")
    parser.add_argument("--port", default="COM9")
    parser.add_argument("--seconds", type=float, default=2.0, help="vacuum-on duration (default: %(default)s)")
    parser.add_argument("--run", action="store_true", help="permit suction output commands")
    args = parser.parse_args()
    if args.seconds <= 0 or args.seconds > 10:
        parser.error("--seconds must be greater than 0 and at most 10.")

    print(f"Plan: show pose, enable suction for {args.seconds:.1f}s, then disable it. No axis motion is sent.")
    if not args.run:
        print("Dry run only. Add --run when the cup and workspace are ready.")
        return 0

    try:
        with DobotMotionClient(args.port, reply_timeout=2.0) as robot:
            suction_enabled = False
            try:
                print_pose(robot)
                if input("Type SUCTION to enable vacuum briefly: ").strip() != "SUCTION":
                    print("Suction cancelled; only the read-only pose query was sent.")
                    return 0
                robot.prepare_motion_queue()
                on_index = robot.set_suction(True)
                robot.wait_for_command(on_index, timeout=5.0)
                suction_enabled = True
                print("Suction ON.")
                time.sleep(args.seconds)
                off_index = robot.set_suction(False)
                robot.wait_for_command(off_index, timeout=5.0)
                suction_enabled = False
                print("PASS: suction OFF.")
            finally:
                # The serial port is still open here, so a failed test gets a
                # best-effort release before the context manager closes it.
                if suction_enabled:
                    try:
                        robot.prepare_motion_queue()
                        off_index = robot.set_suction(False)
                        robot.wait_for_command(off_index, timeout=5.0)
                        print("Safety cleanup: suction OFF.")
                    except DobotError as cleanup_error:
                        print(f"WARNING: could not confirm suction OFF: {cleanup_error}")
    except DobotError as error:
        print(f"FAIL: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
