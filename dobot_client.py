"""Minimal, timeout-bounded Dobot Magician client.

``DobotClient`` intentionally implements only the read-only GetPose command.
The separately named ``DobotMotionClient`` is for explicit, reviewed home/PTP
tests and is never used by the main application.
"""
from __future__ import annotations

import struct
import time
from dataclasses import dataclass

import serial


class DobotError(RuntimeError):
    """Base error for a bounded Dobot protocol operation."""


class DobotTimeoutError(DobotError):
    """The robot did not send a complete valid reply before the deadline."""


@dataclass(frozen=True)
class Pose:
    x: float
    y: float
    z: float
    r: float
    j1: float
    j2: float
    j3: float
    j4: float


def build_packet(command_id: int, control: int = 0, params: bytes = b"") -> bytes:
    """Build a Dobot protocol packet: AA AA, body length, body, checksum."""
    if not 0 <= command_id <= 0xFF or not 0 <= control <= 0xFF:
        raise ValueError("Command ID and control must fit in one byte.")
    body = bytes((command_id, control)) + params
    if len(body) > 0xFF:
        raise ValueError("Packet body is too long.")
    return b"\xAA\xAA" + bytes((len(body),)) + body + bytes(((-sum(body)) & 0xFF,))


class DobotClient:
    """A context-managed, read-only Dobot serial client with finite deadlines."""

    def __init__(self, port: str = "COM9", *, reply_timeout: float = 2.0) -> None:
        if reply_timeout <= 0:
            raise ValueError("reply_timeout must be positive.")
        self.port_name = port
        self.reply_timeout = reply_timeout
        self._port: serial.Serial | None = None

    def open(self) -> None:
        if self._port is not None:
            return
        try:
            self._port = serial.Serial(
                self.port_name,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.2,
                write_timeout=1.0,
            )
        except serial.SerialException as error:
            raise DobotError(f"Could not open {self.port_name}: {error}") from error

    def close(self) -> None:
        if self._port is not None:
            self._port.close()
            self._port = None

    def __enter__(self) -> "DobotClient":
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_pose(self) -> Pose:
        """Send one read-only GetPose command (ID 10) and decode its response."""
        frame = self._request(command_id=10)
        params = frame[5:-1]
        if len(params) != 32:
            raise DobotError(f"GetPose returned {len(params)} data bytes; expected 32.")
        return Pose(*struct.unpack("<8f", params))

    def _request(self, *, command_id: int, control: int = 0, params: bytes = b"") -> bytes:
        if self._port is None:
            raise DobotError("Dobot client is not open.")
        packet = build_packet(command_id, control, params)
        try:
            self._port.reset_input_buffer()
            self._port.write(packet)
            self._port.flush()
        except (serial.SerialException, serial.SerialTimeoutException) as error:
            raise DobotError(f"Could not write Dobot command {command_id}: {error}") from error

        response = self._read_frame()
        if response[3] != command_id:
            raise DobotError(f"Expected reply ID {command_id}, received {response[3]}.")
        return response

    def _read_frame(self) -> bytes:
        """Read through a deadline, tolerate leading noise, and validate checksum."""
        assert self._port is not None
        buffer = bytearray()
        deadline = time.monotonic() + self.reply_timeout
        while time.monotonic() < deadline:
            try:
                chunk = self._port.read(self._port.in_waiting or 1)
            except serial.SerialException as error:
                raise DobotError(f"Could not read {self.port_name}: {error}") from error
            if not chunk:
                continue
            buffer.extend(chunk)
            header = buffer.find(b"\xAA\xAA")
            if header < 0:
                buffer[:] = buffer[-1:]
                continue
            if len(buffer) < header + 3:
                continue
            frame_size = header + buffer[header + 2] + 4
            if len(buffer) < frame_size:
                continue
            frame = bytes(buffer[header:frame_size])
            if frame[-1] != ((-sum(frame[3:-1])) & 0xFF):
                raise DobotError("Received a frame with an invalid checksum.")
            return frame
        raise DobotTimeoutError(
            f"No complete Dobot reply arrived on {self.port_name} within {self.reply_timeout:.1f} seconds."
        )


class DobotMotionClient(DobotClient):
    """Bounded commands for deliberate homing and single PTP movement tests.

    Callers must provide their own physical safeguards and confirmation. This
    class has no suction or other end-effector controls.
    """

    def clear_queue(self) -> None:
        self._request(command_id=245, control=0x01)

    def start_queue_execution(self) -> None:
        self._request(command_id=240, control=0x01)

    def prepare_motion_queue(self) -> None:
        """Discard stale queued work before allowing the new test command."""
        self.clear_queue()
        self.start_queue_execution()

    def home(self) -> int:
        """Queue a home command and return its queue index."""
        return self._queue_index(self._request(command_id=31, control=0x03))

    def move_ptp(self, x: float, y: float, z: float, r: float = 0.0) -> int:
        """Queue one MOVJ XYZ point-to-point command and return its queue index."""
        mode_movj_xyz = 0x01
        params = bytes((mode_movj_xyz,)) + struct.pack("<4f", x, y, z, r)
        return self._queue_index(self._request(command_id=84, control=0x03, params=params))

    def set_suction(self, enabled: bool) -> int:
        """Queue a suction-cup on/off command; this never moves an axis."""
        params = bytes((0x01, int(enabled)))
        return self._queue_index(self._request(command_id=62, control=0x03, params=params))

    def queued_command_index(self) -> int:
        return self._queue_index(self._request(command_id=246))

    def wait_for_command(self, command_index: int, *, timeout: float, poll_interval: float = 0.25) -> None:
        """Wait only until a finite deadline for a queued command to complete."""
        if timeout <= 0:
            raise ValueError("timeout must be positive.")
        deadline = time.monotonic() + timeout
        last_index = -1
        while time.monotonic() < deadline:
            last_index = self.queued_command_index()
            if last_index >= command_index:
                return
            time.sleep(min(poll_interval, max(0.0, deadline - time.monotonic())))
        raise DobotTimeoutError(
            f"Queued command {command_index} did not finish within {timeout:.1f} seconds "
            f"(last completed index: {last_index})."
        )

    @staticmethod
    def _queue_index(frame: bytes) -> int:
        params = frame[5:-1]
        if len(params) < 4:
            raise DobotError("Queued-command reply did not include a four-byte queue index.")
        return struct.unpack_from("<I", params)[0]
