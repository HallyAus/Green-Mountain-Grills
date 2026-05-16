"""Frame parsing helpers for the Green Mountain Grills wire protocol.

The controller listens on UDP/8080 and accepts ASCII commands terminated with
``!``. The poll command ``UR001!`` returns a 36-byte little-endian binary
frame; all other commands echo a status frame or an ASCII payload. This module
contains only pure parsing/encoding logic; I/O lives in :mod:`client` and
:mod:`discovery`.
"""

from __future__ import annotations

import struct
from typing import Final

from .const import (
    GRILL_TEMP_MAX,
    GRILL_TEMP_MIN,
    LOW_PELLET_ALT_VALUE,
    PROBE_TEMP_MAX,
    PROBE_TEMP_MIN,
    PROBE_UNPLUGGED_SENTINEL,
    STATUS_FRAME_LEN,
    STATUS_HEADER,
)
from .exceptions import GMGInvalidValueError, GMGProtocolError
from .models import FireState, GMGSnapshot, PowerState, WarnCode

# The grill_type byte → human name mapping is heuristic; the vendor does not
# publish a stable table. Override via a future config option at the
# integration layer rather than editing this dict.
MODEL_NAMES: Final[dict[int, str]] = {
    0: "Davy Crockett",
    1: "Trek",
    2: "Daniel Boone",
    3: "Jim Bowie",
    4: "Ledge",
    5: "Peak",
    6: "Ledge Prime+",
    7: "Peak Prime+",
    8: "Trek Prime 2.0",
    9: "Ledge Prime 2.0",
    10: "Peak Prime 2.0",
    11: "Daniel Boone Prime+",
    12: "Jim Bowie Prime+",
    13: "Daniel Boone Prime 2.0",
    14: "Jim Bowie Prime 2.0",
    15: "Trek Prime+",
}

DEFAULT_MODEL_NAME: Final[str] = "Green Mountain Grill"


def model_name_for(grill_type: int) -> str:
    """Return a human-readable model name for a grill_type byte."""
    return MODEL_NAMES.get(grill_type, DEFAULT_MODEL_NAME)


def _probe_or_none(value: int) -> int | None:
    if value == PROBE_UNPLUGGED_SENTINEL:
        return None
    return value


def parse_status_frame(data: bytes) -> GMGSnapshot:
    """Parse a 36-byte status frame into a :class:`GMGSnapshot`."""
    if len(data) < STATUS_FRAME_LEN:
        raise GMGProtocolError(
            f"status frame too short: got {len(data)} bytes, need {STATUS_FRAME_LEN}"
        )
    if data[0:2] != STATUS_HEADER:
        raise GMGProtocolError(
            f"status frame header mismatch: {data[0:2]!r} != {STATUS_HEADER!r}"
        )

    frame = data[:STATUS_FRAME_LEN]

    grill_temp = int.from_bytes(frame[2:4], "little")
    probe_1_temp_raw = int.from_bytes(frame[4:6], "little")
    grill_set_temp = int.from_bytes(frame[6:8], "little")

    probe_2_temp_raw = int.from_bytes(frame[16:18], "little")
    probe_2_target = int.from_bytes(frame[18:20], "little")

    profile_time_remaining_s = int.from_bytes(frame[20:24], "little")
    warn_raw = int.from_bytes(frame[24:28], "little")

    probe_1_target = int.from_bytes(frame[28:30], "little")

    power_state_raw = frame[30]
    fire_state_raw = frame[32]
    hopper_pct = frame[33]
    grill_type = frame[35]

    try:
        power_state = PowerState(power_state_raw)
    except ValueError:
        power_state = PowerState.OFF

    try:
        fire_state = FireState(fire_state_raw)
    except ValueError:
        fire_state = FireState.DEFAULT

    warn_value = warn_raw & 0xFFFF_FFFF
    low_pellet = warn_value == WarnCode.LOW_PELLET or warn_value == LOW_PELLET_ALT_VALUE
    try:
        warn_code = WarnCode(warn_value) if warn_value != LOW_PELLET_ALT_VALUE else WarnCode.LOW_PELLET
    except ValueError:
        warn_code = WarnCode.NONE

    return GMGSnapshot(
        grill_temp=grill_temp,
        grill_set_temp=grill_set_temp,
        probe_1_temp=_probe_or_none(probe_1_temp_raw),
        probe_1_target=probe_1_target,
        probe_2_temp=_probe_or_none(probe_2_temp_raw),
        probe_2_target=probe_2_target,
        power_state=power_state,
        fire_state=fire_state,
        warn_code=warn_code,
        low_pellet=low_pellet,
        fan_overload=warn_code == WarnCode.FAN_OVERLOAD,
        auger_overload=warn_code == WarnCode.AUGER_OVERLOAD,
        ignitor_overload=warn_code == WarnCode.IGNITOR_OVERLOAD,
        low_voltage=warn_code == WarnCode.LOW_VOLTAGE,
        fan_disconnect=warn_code == WarnCode.FAN_DISCONNECT,
        auger_disconnect=warn_code == WarnCode.AUGER_DISCONNECT,
        ignitor_disconnect=warn_code == WarnCode.IGNITOR_DISCONNECT,
        flame_on=fire_state == FireState.RUNNING,
        cold_smoke=(
            power_state == PowerState.COLD_SMOKE or fire_state == FireState.COLD_SMOKE
        ),
        hopper_pct=hopper_pct,
        grill_type=grill_type,
        profile_time_remaining_s=profile_time_remaining_s,
        raw=bytes(frame),
    )


def _ensure_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GMGInvalidValueError(f"{name} must be an int, got {type(value).__name__}")
    return value


def encode_set_grill_temp(fahrenheit: int) -> bytes:
    """Validate and encode a ``UT###!`` grill setpoint command."""
    value = _ensure_int(fahrenheit, "fahrenheit")
    if not GRILL_TEMP_MIN <= value <= GRILL_TEMP_MAX:
        raise GMGInvalidValueError(
            f"grill setpoint {value} out of range "
            f"[{GRILL_TEMP_MIN}, {GRILL_TEMP_MAX}]"
        )
    return f"UT{value:03d}!".encode("ascii")


def encode_set_probe_target(probe: int, fahrenheit: int) -> bytes:
    """Validate and encode a ``UF###!`` (probe 1) or ``Uf###!`` (probe 2) command."""
    probe_idx = _ensure_int(probe, "probe")
    if probe_idx not in (1, 2):
        raise GMGInvalidValueError(f"probe must be 1 or 2, got {probe_idx}")
    value = _ensure_int(fahrenheit, "fahrenheit")
    if not PROBE_TEMP_MIN <= value <= PROBE_TEMP_MAX:
        raise GMGInvalidValueError(
            f"probe setpoint {value} out of range "
            f"[{PROBE_TEMP_MIN}, {PROBE_TEMP_MAX}]"
        )
    letter = "F" if probe_idx == 1 else "f"
    return f"U{letter}{value:03d}!".encode("ascii")


def is_status_frame(data: bytes) -> bool:
    """Cheap predicate used by the client to decide if a reply is a status frame."""
    return len(data) >= STATUS_FRAME_LEN and data[0:2] == STATUS_HEADER


# Re-exported for callers that need to dissect a raw frame without going via
# :func:`parse_status_frame` (diagnostics, tests).
_STATUS_STRUCT_HINT: Final[str] = (
    "header[2] grill_t[H] probe1_t[H] grill_set[H] api_ver[B] rsvd[7B] "
    "probe2_t[H] probe2_tgt[H] profile_s[I] warn[I] probe1_tgt[H] power[B] "
    "mode[B] fire[B] hopper[B] profile_end[B] grill_type[B]"
)

_ = struct  # keep struct importable for future use without losing the symbol
