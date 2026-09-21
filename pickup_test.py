"""Single vertical Dobot pickup-and-release test with explicit safe coordinates."""
from __future__ import annotations

import argparse
import sys
import time

from dobot_client import DobotError, DobotMotionClient


def print_pose(label: str, robot: DobotMotionClient) -> None:
    pose = robot.get_pose()
    print(f"{label}: x={pose.x:.3f}, y={pose.y:.3f}, z={pose.z:.3f}, theta={pose.r:.3f}")


def wait_step(robot: DobotMotionClient, command_index: int, label: str, timeout: float) -> None:
    print(f"{label} (queued command {command_index})...")
    robot.wait_for_command(command_index, timeout=timeout)
    print(f"PASS: {label}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded, one-block vertical Dobot pickup test")
    parser.add_argument("--port", default="COM9")
    parser.add_argument("--x", type=float, required=True, help="block-centre X coordinate in mm")
    parser.add_argument("--y", type=float, required=True, help="block-centre Y coordinate in mm")
    parser.add_argument("--pickup-z", type=float, required=True, help="cup-to-block contact Z coordinate in mm")
    parser.add_argument("--safe-z", type=float, required=True, help="clearance Z above the block in mm")
    parser.add_argument("--release-z", type=float, required=True,
                        help="safe support-surface Z where the block is released in mm")
    parser.add_argument("--theta", type=float, default=0.0, help="tool rotation in degrees")
    parser.add_argument("--step-timeout", type=float, default=20.0, help="deadline per move in seconds")
    parser.add_argument("--hold-seconds", type=float, default=2.0, help="time to hold the raised block")
    parser.add_argument("--run", action="store_true", help="permit pickup motion and suction")
    args = parser.parse_args()

    if args.safe_z <= max(args.pickup_z, args.release_z):
        parser.error("--safe-z must be greater than both pickup and release Z (Dobot Z increases upward).")
    if args.step_timeout <= 0 or args.hold_seconds < 0:
        parser.error("Timeout and hold duration must be non-negative, with timeout greater than zero.")

    target = (f"x={args.x:.3f}, y={args.y:.3f}, pickup-z={args.pickup_z:.3f}, "
              f"release-z={args.release_z:.3f}, safe-z={args.safe_z:.3f}")
    print("Plan: approach vertically, lower, suction on, lift, lower to the support surface, release, lift clear.")
    print(f"Target: {target}, theta={args.theta:.3f}")
    if not args.run:
        print("Dry run only. Verify the coordinates with a clear workspace, then add --run.")
        return 0

    suction_enabled = False
    try:
        with DobotMotionClient(args.port, reply_timeout=2.0) as robot:
            print_pose("Pose before pickup", robot)
            if input("Type PICKUP to run this one vertical pickup test: ").strip() != "PICKUP":
                print("Pickup cancelled; only the read-only pose query was sent.")
                return 0

            robot.prepare_motion_queue()
            try:
                wait_step(robot, robot.move_ptp(args.x, args.y, args.safe_z, args.theta),
                          "approach at safe height", args.step_timeout)
                wait_step(robot, robot.move_ptp(args.x, args.y, args.pickup_z, args.theta),
                          "lower to pickup height", args.step_timeout)
                wait_step(robot, robot.set_suction(True), "enable suction", 5.0)
                suction_enabled = True
                time.sleep(0.5)  # Give the cup time to seal before lifting.
                wait_step(robot, robot.move_ptp(args.x, args.y, args.safe_z, args.theta),
                          "lift to safe height", args.step_timeout)
                if args.hold_seconds:
                    print(f"Holding at safe height for {args.hold_seconds:.1f} seconds...")
                    time.sleep(args.hold_seconds)
                wait_step(robot, robot.move_ptp(args.x, args.y, args.release_z, args.theta),
                          "lower to release height", args.step_timeout)
                wait_step(robot, robot.set_suction(False), "release suction", 5.0)
                suction_enabled = False
                wait_step(robot, robot.move_ptp(args.x, args.y, args.safe_z, args.theta),
                          "lift clear after release", args.step_timeout)
                print_pose("Pose after pickup", robot)
                print("PASS: pickup-and-release sequence completed.")
            finally:
                if suction_enabled:
                    try:
                        wait_step(robot, robot.set_suction(False), "safety release", 5.0)
                    except DobotError as cleanup_error:
                        print(f"WARNING: could not confirm suction OFF: {cleanup_error}")
    except DobotError as error:
        print(f"FAIL: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
