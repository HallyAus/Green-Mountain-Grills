"""Broadcast UDP discovery for Green Mountain Grills controllers.

A single ``UL!`` datagram is sent to the configured broadcast address; every
reply whose payload begins with ``b"GMG"`` is treated as a distinct grill,
keyed by source IP for de-duplication.
"""

from __future__ import annotations

import asyncio
import logging
import socket
from typing import Final, cast

from .const import (
    CMD_SERIAL,
    DEFAULT_BROADCAST,
    DEFAULT_DISCOVERY_TIMEOUT,
    DEFAULT_PORT,
    SERIAL_PREFIX,
)
from .models import DiscoveredGrill

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    """Collect every datagram received until the caller stops the endpoint."""

    def __init__(self) -> None:
        self.replies: list[tuple[bytes, tuple[str, int]]] = []
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = cast(asyncio.DatagramTransport, transport)

    def datagram_received(self, data: bytes, addr: tuple[str | object, int]) -> None:
        host = addr[0] if isinstance(addr[0], str) else str(addr[0])
        port = int(addr[1])
        self.replies.append((data, (host, port)))

    def error_received(self, exc: Exception) -> None:
        _LOGGER.debug("discovery socket error: %s", exc)


async def async_discover(
    timeout: float = DEFAULT_DISCOVERY_TIMEOUT,
    *,
    broadcast: str = DEFAULT_BROADCAST,
    port: int = DEFAULT_PORT,
) -> list[DiscoveredGrill]:
    """Broadcast ``UL!`` and return unique grills heard within ``timeout`` seconds."""
    if timeout <= 0:
        raise ValueError("timeout must be > 0")

    loop = asyncio.get_running_loop()

    transport, proto = await loop.create_datagram_endpoint(
        _DiscoveryProtocol,
        local_addr=("0.0.0.0", 0),
        allow_broadcast=True,
    )

    try:
        sock: socket.socket | None = transport.get_extra_info("socket")
        if sock is not None:
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            except OSError as err:
                _LOGGER.debug("failed to set SO_BROADCAST: %s", err)

        try:
            transport.sendto(CMD_SERIAL, (broadcast, port))
        except OSError as err:
            _LOGGER.debug("broadcast sendto(%s:%s) failed: %s", broadcast, port, err)
            return []

        await asyncio.sleep(timeout)
    finally:
        transport.close()

    seen: dict[str, DiscoveredGrill] = {}
    for data, (addr_host, _addr_port) in proto.replies:
        if not data.startswith(SERIAL_PREFIX):
            continue
        if addr_host in seen:
            continue
        serial = data.decode("ascii", errors="replace").strip()
        seen[addr_host] = DiscoveredGrill(host=addr_host, serial=serial)

    return list(seen.values())
