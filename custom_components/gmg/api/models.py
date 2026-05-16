"""Dataclasses and enums describing the Green Mountain Grills protocol surface."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class PowerState(IntEnum):
    """Power state byte (offset 30) of the status frame."""

    OFF = 0
    ON = 1
    FAN = 2
    COLD_SMOKE = 3


class FireState(IntEnum):
    """Fire state byte (offset 32) of the status frame."""

    DEFAULT = 0
    OFF = 1
    STARTUP = 2
    RUNNING = 3
    COOL_DOWN = 4
    FAIL = 5
    COLD_SMOKE = 198


class WarnCode(IntEnum):
    """Warning code (bytes 24-27) of the status frame."""

    NONE = 0
    FAN_OVERLOAD = 1
    AUGER_OVERLOAD = 2
    IGNITOR_OVERLOAD = 3
    LOW_VOLTAGE = 4
    FAN_DISCONNECT = 5
    AUGER_DISCONNECT = 6
    IGNITOR_DISCONNECT = 7
    LOW_PELLET = 8


@dataclass(frozen=True, slots=True)
class GMGSnapshot:
    """Parsed view of one 36-byte status frame."""

    grill_temp: int
    grill_set_temp: int
    probe_1_temp: int | None
    probe_1_target: int
    probe_2_temp: int | None
    probe_2_target: int
    power_state: PowerState
    fire_state: FireState
    warn_code: WarnCode
    low_pellet: bool
    fan_overload: bool
    auger_overload: bool
    ignitor_overload: bool
    low_voltage: bool
    fan_disconnect: bool
    auger_disconnect: bool
    ignitor_disconnect: bool
    flame_on: bool
    cold_smoke: bool
    hopper_pct: int
    grill_type: int
    profile_time_remaining_s: int
    raw: bytes


@dataclass(frozen=True, slots=True)
class GMGGrillInfo:
    """Identity bundle returned by GMGClient.async_probe."""

    host: str
    serial: str
    firmware: str
    model: str
    model_id: int
    snapshot: GMGSnapshot


@dataclass(frozen=True, slots=True)
class DiscoveredGrill:
    """One unique grill returned by broadcast discovery."""

    host: str
    serial: str
