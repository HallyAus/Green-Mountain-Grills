"""Tests for the GMG config, options and reconfigure flows."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.components import dhcp
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gmg.api import (
    GMGConnectionError,
    GMGServerModeError,
)
from custom_components.gmg.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def _start_user_flow(hass: HomeAssistant) -> dict:
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_flow_menu_then_manual_success(
    hass: HomeAssistant, mock_client
) -> None:
    """Walk: user menu -> manual -> happy path -> entry created."""
    result = await _start_user_flow(hass)

    if result["type"] == data_entry_flow.FlowResultType.MENU:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "manual"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.0.2.10", "port": 8080}
    )
    await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "GMG12345678"
    assert "GMG12345678" in result["title"]
    assert result["data"]["host"] == "192.0.2.10"


async def test_user_flow_cannot_connect(hass: HomeAssistant, mock_client) -> None:
    """A connection error should re-show the form with an error."""
    mock_client.async_probe.side_effect = GMGConnectionError("boom")

    result = await _start_user_flow(hass)
    if result["type"] == data_entry_flow.FlowResultType.MENU:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "manual"}
        )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.0.2.99", "port": 8080}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]


async def test_user_flow_server_mode(hass: HomeAssistant, mock_client) -> None:
    """Server-mode error aborts the flow with a known reason."""
    mock_client.async_probe.side_effect = GMGServerModeError("server mode on")

    result = await _start_user_flow(hass)
    if result["type"] == data_entry_flow.FlowResultType.MENU:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "manual"}
        )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.0.2.10", "port": 8080}
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "server_mode_enabled"


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_client, mock_config_entry: MockConfigEntry
) -> None:
    """If an entry with the same unique_id exists, abort."""
    mock_config_entry.add_to_hass(hass)

    result = await _start_user_flow(hass)
    if result["type"] == data_entry_flow.FlowResultType.MENU:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "manual"}
        )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.0.2.10", "port": 8080}
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_dhcp_discovery_creates_entry(hass: HomeAssistant, mock_client) -> None:
    """A DHCP discovery should walk through confirm and create an entry."""
    discovery = dhcp.DhcpServiceInfo(
        ip="192.0.2.10",
        hostname="gmg-grill",
        macaddress="aa:bb:cc:dd:ee:ff",
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_DHCP}, data=discovery
    )

    if result["type"] == data_entry_flow.FlowResultType.FORM:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "GMG12345678"
    assert result["data"]["host"] == "192.0.2.10"


async def test_dhcp_discovery_updates_existing(
    hass: HomeAssistant, mock_client, mock_config_entry: MockConfigEntry
) -> None:
    """DHCP that matches an existing serial should update its host."""
    mock_config_entry.add_to_hass(hass)
    discovery = dhcp.DhcpServiceInfo(
        ip="192.0.2.55",
        hostname="gmg-grill",
        macaddress="aa:bb:cc:dd:ee:ff",
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_DHCP}, data=discovery
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] in {"already_configured", "updated"}
    assert mock_config_entry.data["host"] == "192.0.2.55"


async def test_reconfigure_flow_success(
    hass: HomeAssistant, mock_client, mock_config_entry: MockConfigEntry
) -> None:
    """Reconfigure flow should update the host on the existing entry."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.0.2.99", "port": 8080}
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data["host"] == "192.0.2.99"


async def test_options_flow_sets_scan_interval(
    hass: HomeAssistant, mock_client, mock_config_entry: MockConfigEntry
) -> None:
    """Options flow should accept and persist a new scan interval."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"scan_interval": 15}
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["scan_interval"] == 15


@pytest.fixture(autouse=True)
def _silence_async_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid running the full platform setup chain during flow tests."""
    async def _ok(*_args: object, **_kwargs: object) -> bool:
        return True

    monkeypatch.setattr(
        "custom_components.gmg.async_setup_entry", _ok, raising=False
    )
