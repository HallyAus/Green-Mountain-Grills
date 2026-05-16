"""Async UDP client for a single Green Mountain Grills controller.

Each request opens and closes its own ``asyncio`` datagram endpoint. The
controller is single-threaded and there is no measurable benefit to keeping a
long-lived socket, while ephemeral sockets keep request concurrency trivial
(every call has its own protocol instance and waiter).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Final, cast

from .const import (
    CMD_FIRMWARE,
    CMD_POWER_OFF,
    CMD_POWER_ON,
    CMD_COLD_SMOKE,
    CMD_SERIAL,
    CMD_STATUS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_PORT,
    DEFAULT_REQUEST_TIMEOUT,
    SERIAL_PREFIX,
    STATUS_FRAME_LEN,
)
from .exceptions import (
    GMGConnectionError,
    GMGProtocolError,
    GMGServerModeError,
    GMGTimeoutError,
)
from .models import GMGGrillInfo, GMGSnapshot
from .protocol import (
    encode_set_grill_temp,
    encode_set_probe_target,
    is_status_frame,
    model_name_for,
    parse_status_frame,
)

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


class _DatagramReplyProtocol(asyncio.DatagramProtocol):
    """Capture the first datagram received on the endpoint."""

    def __init__(self) -> None:
        self.future: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = cast(asyncio.DatagramTransport, transport)

    def datagram_received(self, data: bytes, addr: tuple[str | object, int]) -> None:
        if not self.future.done():
            self.future.set_result(data)

    def error_received(self, exc: Exception) -> None:
        if not self.future.done():
            self.future.set_exception(exc)

    def connection_lost(self, exc: Exception | None) -> None:
        if self.future.done():
            return
        if exc is None:
            self.future.set_exception(
                ConnectionError("datagram endpoint closed before reply")
            )
        else:
            self.future.set_exception(exc)


class GMGClient:
    """Stateful façade for one grill at one ``(host, port)`` pair."""

    host: str
    port: int
    serial: str | None
    firmware: str | None
    model: str
    model_id: int | None
    mac: str | None

    def __init__(
        self,
        host: str,
        *,
        port: int = DEFAULT_PORT,
        request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        if max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        if request_timeout <= 0:
            raise ValueError("request_timeout must be > 0")
        self.host = host
        self.port = port
        self._request_timeout = request_timeout
        self._max_retries = max_retries
        self.serial = None
        self.firmware = None
        self.model = "Unknown"
        self.model_id = None
        self.mac = None
        self._lock = asyncio.Lock()

    async def async_close(self) -> None:
        """No long-lived resources are held; provided for API symmetry."""
        return None

    async def _request(self, payload: bytes, *, expect_status: bool) -> bytes:
        """Send ``payload`` with retry and return the raw reply bytes."""
        loop = asyncio.get_running_loop()
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            transport: asyncio.DatagramTransport | None = None
            try:
                transport, proto = await loop.create_datagram_endpoint(
                    _DatagramReplyProtocol,
                    local_addr=("0.0.0.0", 0),
                    remote_addr=(self.host, self.port),
                )
            except OSError as err:
                last_exc = err
                _LOGGER.debug(
                    "create_datagram_endpoint(%s:%s) failed on attempt %d: %s",
                    self.host,
                    self.port,
                    attempt,
                    err,
                )
                continue

            try:
                try:
                    transport.sendto(payload)
                except OSError as err:
                    last_exc = err
                    _LOGGER.debug(
                        "sendto(%s:%s) failed on attempt %d: %s",
                        self.host,
                        self.port,
                        attempt,
                        err,
                    )
                    continue

                try:
                    data = await asyncio.wait_for(
                        proto.future, timeout=self._request_timeout
                    )
                except asyncio.TimeoutError as err:
                    last_exc = err
                    _LOGGER.debug(
                        "timeout awaiting reply from %s:%s (attempt %d/%d) for %r",
                        self.host,
                        self.port,
                        attempt,
                        self._max_retries,
                        payload,
                    )
                    continue
                except OSError as err:
                    last_exc = err
                    _LOGGER.debug(
                        "OSError awaiting reply from %s:%s on attempt %d: %s",
                        self.host,
                        self.port,
                        attempt,
                        err,
                    )
                    continue

                if expect_status and not is_status_frame(data):
                    last_exc = GMGProtocolError(
                        f"unexpected reply ({len(data)} bytes): {data!r}"
                    )
                    _LOGGER.debug(
                        "rejecting reply from %s:%s on attempt %d: %s",
                        self.host,
                        self.port,
                        attempt,
                        last_exc,
                    )
                    continue
                return data
            finally:
                if not proto.future.done():
                    proto.future.cancel()
                elif not proto.future.cancelled():
                    # Drain any unconsumed exception so asyncio doesn't log it
                    # as "Future exception was never retrieved" once the
                    # endpoint is torn down on the next loop tick.
                    proto.future.exception()
                if transport is not None:
                    transport.close()

        if isinstance(last_exc, GMGProtocolError):
            raise last_exc
        if isinstance(last_exc, asyncio.TimeoutError) or last_exc is None:
            # Retries exhausted at the timeout boundary on a host we tried to
            # reach — bubble up the dedicated Server Mode signal so the
            # integration can offer the right repair flow.
            raise GMGServerModeError(
                f"no reply from {self.host}:{self.port} after "
                f"{self._max_retries} attempts"
            ) from last_exc
        raise GMGConnectionError(
            f"socket error talking to {self.host}:{self.port}: {last_exc}"
        ) from last_exc

    async def async_poll(self) -> GMGSnapshot:
        """Send ``UR001!`` and return the parsed snapshot."""
        async with self._lock:
            data = await self._request(CMD_STATUS, expect_status=True)
        snapshot = parse_status_frame(data)
        self.model_id = snapshot.grill_type
        self.model = model_name_for(snapshot.grill_type)
        return snapshot

    async def _request_ascii(self, payload: bytes) -> str:
        data = await self._request(payload, expect_status=False)
        return data.decode("ascii", errors="replace").strip()

    async def async_probe(self) -> GMGGrillInfo:
        """Identify the grill: serial, firmware, and current snapshot."""
        async with self._lock:
            serial_reply = await self._request(CMD_SERIAL, expect_status=False)
            firmware_reply = await self._request(CMD_FIRMWARE, expect_status=False)
            status_reply = await self._request(CMD_STATUS, expect_status=True)

        if not serial_reply.startswith(SERIAL_PREFIX):
            raise GMGProtocolError(
                f"serial reply did not start with {SERIAL_PREFIX!r}: {serial_reply!r}"
            )

        serial = serial_reply.decode("ascii", errors="replace").strip()
        firmware = firmware_reply.decode("ascii", errors="replace").strip()
        snapshot = parse_status_frame(status_reply)

        self.serial = serial
        self.firmware = firmware
        self.model_id = snapshot.grill_type
        self.model = model_name_for(snapshot.grill_type)

        return GMGGrillInfo(
            host=self.host,
            serial=serial,
            firmware=firmware,
            model=self.model,
            model_id=snapshot.grill_type,
            snapshot=snapshot,
        )

    async def async_set_grill_temp(self, fahrenheit: int) -> None:
        """Set the grill setpoint in °F (150-550)."""
        payload = encode_set_grill_temp(fahrenheit)
        async with self._lock:
            await self._request(payload, expect_status=True)

    async def async_set_probe_target(self, probe: int, fahrenheit: int) -> None:
        """Set probe 1 (``UF``) or probe 2 (``Uf``) target in °F (32-257)."""
        payload = encode_set_probe_target(probe, fahrenheit)
        async with self._lock:
            await self._request(payload, expect_status=True)

    async def async_power_on(self) -> None:
        """Power on (``UK001!``)."""
        async with self._lock:
            await self._request(CMD_POWER_ON, expect_status=True)

    async def async_power_off(self) -> None:
        """Power off (``UK004!``)."""
        async with self._lock:
            await self._request(CMD_POWER_OFF, expect_status=True)

    async def async_cold_smoke(self) -> None:
        """Enter cold-smoke mode (``UK002!``)."""
        async with self._lock:
            await self._request(CMD_COLD_SMOKE, expect_status=True)


# Re-exported for symmetry; consumers should use the module-level names.
__all__ = [
    "GMGClient",
    "STATUS_FRAME_LEN",
    "GMGConnectionError",
    "GMGTimeoutError",
    "GMGServerModeError",
    "GMGProtocolError",
]
