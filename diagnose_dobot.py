"""Timeout-bounded, read-only Dobot serial diagnostic.

This sends exactly one GetPose request (command ID 10).  It contains no motion,
homing, queue, suction, or configuration commands.
"""
from __future__ import annotations

import argparse
import struct
import sys
import time

import serial


GET_POSE = bytes((0xAA, 0xAA, 0x02, 0x0A, 0x00, 0xF6))


def hex_bytes(data: bytes) -> str:
    return data.hex(" ").upper() if data else "<none>"


def read_until_deadline(port: serial.Serial, seconds: float) -> bytes:
    """Collect received bytes without reading beyond a fixed overall deadline."""
    response = bytearray()
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        waiting = port.in_waiting
        chunk = port.read(waiting or 1)
        if chunk:
            response.extend(chunk)
            # A complete Dobot frame is AA AA, length, body, checksum.
            start = response.find(b"\xAA\xAA")
            if start >= 0 and len(response) >= start + 3:
                expected_size = start + response[start + 2] + 4
                if len(response) >= expected_size:
                    return bytes(response)
    return bytes(response)


def extract_frame(data: bytes) -> bytes | None:
    start = data.find(b"\xAA\xAA")
    if start < 0 or len(data) < start + 3:
        return None
    size = data[start + 2] + 4
    if len(data) < start + size:
        return None
    return data[start:start + size]


def report_pose(frame: bytes) -> bool:
    body_length = frame[2]
    command_id, control = frame[3], frame[4]
    expected_checksum = (-sum(frame[3:-1])) & 0xFF
    checksum_valid = frame[-1] == expected_checksum
    print(f"PASS: received complete frame ({len(frame)} bytes; declared body {body_length} bytes).")
    print(f"Frame: {hex_bytes(frame)}")
    print(f"Command ID: {command_id}; control: 0x{control:02X}; checksum: "
          f"{'valid' if checksum_valid else 'INVALID'}")

    params = frame[5:-1]
    if command_id != 10:
        print("WARN: reply is valid framing but is not a GetPose response.")
        return False
    if len(params) != 32:
        print(f"WARN: GetPose response should have 32 data bytes, got {len(params)}.")
        return False
    if not checksum_valid:
        print("FAIL: refusing to decode a response with an invalid checksum.")
        return False

    x, y, z, r, j1, j2, j3, j4 = struct.unpack("<8f", params)
    print("PASS: decoded pose")
    print(f"  position: x={x:.3f}, y={y:.3f}, z={z:.3f}, r={r:.3f}")
    print(f"  joints:   j1={j1:.3f}, j2={j2:.3f}, j3={j3:.3f}, j4={j4:.3f}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only, timeout-bounded Dobot GetPose diagnostic")
    parser.add_argument("--port", default="COM9", help="serial port (default: %(default)s)")
    parser.add_argument("--timeout", type=float, default=2.0, help="overall reply deadline in seconds")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    print(f"Opening {args.port} at 115200 8N1 with finite timeouts...")
    try:
        with serial.Serial(args.port, baudrate=115200, bytesize=serial.EIGHTBITS,
                           parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                           timeout=0.2, write_timeout=1.0) as port:
            print(f"PASS: opened {port.name}")
            port.reset_input_buffer()
            print(f"Sending read-only GetPose request: {hex_bytes(GET_POSE)}")
            port.write(GET_POSE)
            port.flush()
            response = read_until_deadline(port, args.timeout)
    except serial.SerialException as error:
        print(f"FAIL: serial error: {error}")
        return 1
    except serial.SerialTimeoutException as error:
        print(f"FAIL: write timed out: {error}")
        return 1

    print(f"Raw bytes received: {hex_bytes(response)}")
    frame = extract_frame(response)
    if frame is None:
        print(f"FAIL: no complete Dobot frame arrived within {args.timeout:.1f} seconds.")
        return 1
    return 0 if report_pose(frame) else 1


if __name__ == "__main__":
    sys.exit(main())
