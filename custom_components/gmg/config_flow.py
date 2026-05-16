"""Config flow for the Green Mountain Grills integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import dhcp
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .api import (
    DiscoveredGrill,
    GMGClient,
    GMGConnectionError,
    GMGError,
    GMGProtocolError,
    GMGServerModeError,
    GMGTimeoutError,
    async_discover,
)
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import GMGConfigEntry


class GMGConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Green Mountain Grills."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._discovered: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        return self.async_show_menu(
            step_id="user", menu_options=["scan", "manual"]
        )

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle LAN discovery."""
        configured = self._async_current_ids()
        discovered = await async_discover(timeout=3.0)
        candidates = [g for g in discovered if g.serial not in configured]

        if not candidates:
            return self.async_abort(reason="no_devices_found")

        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input["selected_host"]
            result = await self._async_probe_and_create(host, DEFAULT_PORT)
            if result is not None:
                return result
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="scan",
            data_schema=self._scan_schema(candidates),
            errors=errors,
        )

    @staticmethod
    def _scan_schema(candidates: list[DiscoveredGrill]) -> vol.Schema:
        """Build the schema for the scan step."""
        options = [
            {
                "value": grill.host,
                "label": f"{grill.host} (serial: {grill.serial})",
            }
            for grill in candidates
        ]
        return vol.Schema(
            {
                vol.Required("selected_host"): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            }
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual host entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = int(user_input[CONF_PORT])
            result, errors = await self._async_probe_or_errors(host, port)
            if result is not None:
                return result

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): TextSelector(),
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): NumberSelector(
                    NumberSelectorConfig(min=1, max=65535, mode="box")
                ),
            }
        )
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)

        return self.async_show_form(
            step_id="manual",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_dhcp(
        self, discovery_info: dhcp.DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle DHCP discovery."""
        host = discovery_info.ip
        client = GMGClient(host=host)
        try:
            info = await client.async_probe()
        except GMGError:
            await self._safe_close(client)
            return self.async_abort(reason="cannot_connect")
        await self._safe_close(client)

        await self.async_set_unique_id(info.serial)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self._discovered = {
            "host": host,
            "serial": info.serial,
            "model": info.model,
            "firmware": info.firmware,
        }
        self.context["title_placeholders"] = {"name": f"GMG {info.serial}"}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered device."""
        if user_input is None:
            self._set_confirm_only()
            return self.async_show_form(
                step_id="discovery_confirm",
                description_placeholders={
                    "name": self.context["title_placeholders"]["name"],
                    "host": self._discovered["host"],
                    "model": self._discovered["model"],
                },
            )

        return self.async_create_entry(
            title=self.context["title_placeholders"]["name"],
            data={
                CONF_HOST: self._discovered["host"],
                CONF_PORT: DEFAULT_PORT,
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure an existing entry."""
        entry: GMGConfigEntry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = int(user_input[CONF_PORT])
            client = GMGClient(host=host, port=port)
            try:
                info = await client.async_probe()
            except GMGServerModeError:
                await self._safe_close(client)
                return self.async_abort(reason="server_mode_enabled")
            except (GMGConnectionError, GMGTimeoutError):
                errors["base"] = "cannot_connect"
            except GMGProtocolError:
                errors["base"] = "invalid_response"
            except GMGError:
                LOGGER.exception("Unexpected error probing %s:%s", host, port)
                errors["base"] = "unknown"
            else:
                await self._safe_close(client)
                await self.async_set_unique_id(info.serial)
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_HOST: host, CONF_PORT: port},
                )

            await self._safe_close(client)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): TextSelector(),
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): NumberSelector(
                    NumberSelectorConfig(min=1, max=65535, mode="box")
                ),
            }
        )
        suggested = user_input if user_input is not None else dict(entry.data)
        schema = self.add_suggested_values_to_schema(schema, suggested)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    async def _async_probe_or_errors(
        self, host: str, port: int
    ) -> tuple[ConfigFlowResult | None, dict[str, str]]:
        """Probe a grill and either create an entry or return errors."""
        errors: dict[str, str] = {}
        client = GMGClient(host=host, port=port)
        try:
            info = await client.async_probe()
        except GMGServerModeError:
            await self._safe_close(client)
            return self.async_abort(reason="server_mode_enabled"), errors
        except (GMGConnectionError, GMGTimeoutError):
            errors["base"] = "cannot_connect"
        except GMGProtocolError:
            errors["base"] = "invalid_response"
        except GMGError:
            LOGGER.exception("Unexpected error probing %s:%s", host, port)
            errors["base"] = "unknown"
        else:
            await self._safe_close(client)
            await self.async_set_unique_id(info.serial)
            self._abort_if_unique_id_configured(
                updates={CONF_HOST: host, CONF_PORT: port}
            )
            return (
                self.async_create_entry(
                    title=f"GMG {info.serial}",
                    data={CONF_HOST: host, CONF_PORT: port},
                ),
                errors,
            )

        await self._safe_close(client)
        return None, errors

    async def _async_probe_and_create(
        self, host: str, port: int
    ) -> ConfigFlowResult | None:
        """Probe and create or return ``None`` if it failed."""
        result, _errors = await self._async_probe_or_errors(host, port)
        return result

    @staticmethod
    async def _safe_close(client: GMGClient) -> None:
        """Close a client, ignoring close-time errors."""
        try:
            await client.async_close()
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: GMGConfigEntry,
    ) -> GMGOptionsFlow:
        """Return the options flow handler."""
        return GMGOptionsFlow()


class GMGOptionsFlow(OptionsFlowWithReload):
    """Handle the options flow for Green Mountain Grills."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=1,
                        unit_of_measurement="s",
                        mode="box",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                schema, self.config_entry.options
            ),
        )
