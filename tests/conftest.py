"""Shared pytest fixtures for the GMG test suite."""
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gmg.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: object) -> None:
    """Enable loading custom_components/ in HA test rig."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a representative config entry for the GMG integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="GMG12345678",
        title="GMG GMG12345678",
        data={"host": "192.0.2.10", "port": 8080},
        options={"scan_interval": 30},
        version=1,
        minor_version=1,
    )


@pytest.fixture
def mock_grill_info():
    """Return a populated GMGGrillInfo for use in tests."""
    from custom_components.gmg.api import (
        FireState,
        GMGGrillInfo,
        GMGSnapshot,
        PowerState,
        WarnCode,
    )

    snap = GMGSnapshot(
        grill_temp=225,
        grill_set_temp=225,
        probe_1_temp=140,
        probe_1_target=165,
        probe_2_temp=None,
        probe_2_target=145,
        power_state=PowerState.ON,
        fire_state=FireState.RUNNING,
        warn_code=WarnCode.NONE,
        low_pellet=False,
        fan_overload=False,
        auger_overload=False,
        ignitor_overload=False,
        low_voltage=False,
        fan_disconnect=False,
        auger_disconnect=False,
        ignitor_disconnect=False,
        flame_on=True,
        cold_smoke=False,
        hopper_pct=80,
        grill_type=3,
        profile_time_remaining_s=0,
        raw=b"\x00" * 36,
    )
    return GMGGrillInfo(
        host="192.0.2.10",
        serial="GMG12345678",
        firmware="1.4.0",
        model="Peak Prime 2.0",
        model_id=3,
        snapshot=snap,
    )


@pytest.fixture
def mock_client(mock_grill_info) -> Generator[MagicMock, None, None]:
    """Patch GMGClient everywhere it is imported and yield the mock instance."""
    with patch("custom_components.gmg.GMGClient", autospec=True) as cls, patch(
        "custom_components.gmg.config_flow.GMGClient", new=cls
    ):
        inst = cls.return_value
        inst.host = "192.0.2.10"
        inst.port = 8080
        inst.serial = mock_grill_info.serial
        inst.firmware = mock_grill_info.firmware
        inst.model = mock_grill_info.model
        inst.model_id = mock_grill_info.model_id
        inst.mac = None
        inst.async_probe = AsyncMock(return_value=mock_grill_info)
        inst.async_poll = AsyncMock(return_value=mock_grill_info.snapshot)
        inst.async_set_grill_temp = AsyncMock()
        inst.async_set_probe_target = AsyncMock()
        inst.async_power_on = AsyncMock()
        inst.async_power_off = AsyncMock()
        inst.async_cold_smoke = AsyncMock()
        inst.async_close = AsyncMock()
        yield inst
