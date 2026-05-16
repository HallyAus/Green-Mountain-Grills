# GMG Local UDP Protocol Reference

This document describes the wire protocol used by Green Mountain Grills (GMG)
WiFi-enabled pellet smokers when operating in local LAN mode. It is the
specification that this integration implements.

## Overview

- **Transport:** UDP, port `8080`, on the LAN.
- **Framing:** Datagrams contain short ASCII commands and either ASCII or
  fixed-length binary responses. There is no length prefix; one request
  produces exactly one response.
- **Security:** None. No TLS, no authentication, no per-device pairing key.
  Any host on the same broadcast domain can issue commands.
- **Endianness:** All multi-byte numeric fields in the binary status frame are
  **little-endian unsigned integers**.
- **Connectivity model:** Point-to-point Wi-Fi between Home Assistant and the
  grill controller. The integration only works when the controller's
  **Server Mode is disabled**. When Server Mode is enabled the controller
  routes traffic through the vendor cloud (AWS) and ignores LAN UDP traffic
  entirely.

## Discovery

Discovery is a broadcast probe followed by unicast replies.

1. The client sends the 3-byte ASCII command `UL!`
   (hex `55 4C 21`) to UDP `255.255.255.255:8080`.
2. Each grill on the broadcast domain responds (unicast, from its own
   port 8080) with an ASCII payload whose first three bytes are `GMG` followed
   by a serial number, e.g. `GMG12345678`.
3. The client should listen for replies for **1-2 seconds**, then close the
   socket.
4. Responses are **deduplicated by serial number**; the same physical grill
   may emit multiple replies if there is more than one network interface.

## Command set

All commands are ASCII. `dd dd dd` is a three-byte zero-padded decimal
temperature in Fahrenheit (for example `225` -> `32 32 35`). All commands are
terminated by the literal byte `!` (`0x21`).

| Command (ASCII) | Bytes (hex)               | Purpose                                | Response                          |
|-----------------|---------------------------|----------------------------------------|-----------------------------------|
| `UR001!`        | `55 52 30 30 31 21`       | Poll full status                       | 36-byte binary status frame       |
| `UL!`           | `55 4C 21`                | Get serial number / discovery probe    | ASCII, starts with `GMG`          |
| `UN!`           | `55 4E 21`                | Get firmware version                   | ASCII version string              |
| `UT###!`        | `55 54 dd dd dd 21`       | Set grill setpoint (degF, zero-padded) | echoed status frame               |
| `UF###!`        | `55 46 dd dd dd 21`       | Set probe 1 target (degF)              | echoed status frame               |
| `Uf###!`        | `55 66 dd dd dd 21`       | Set probe 2 target (degF, lowercase f) | echoed status frame               |
| `UK001!`        | `55 4B 30 30 31 21`       | Power on                               | status frame                      |
| `UK002!`        | `55 4B 30 30 32 21`       | Power on in Cold Smoke mode            | status frame                      |
| `UK004!`        | `55 4B 30 30 34 21`       | Power off                              | status frame                      |

Notes:

- The case of the probe-2 command (`Uf`, lowercase) is significant. Uppercase
  `UF` is probe 1; lowercase `Uf` is probe 2.
- Several controller firmwares accept a `UR001!` poll while powered off and
  return a frame with `power_state = 0`. Do not assume a poll failure means
  the grill is off.
- The grill does not echo the originating command back; it just responds with
  the same shape of frame regardless of which command triggered it.

## Status frame layout (36 bytes)

The full poll response (`UR001!`) is always 36 bytes. Offsets are zero-based.

| Offset | Length | Field                          | Type         | Notes                                                                 |
|-------:|-------:|--------------------------------|--------------|-----------------------------------------------------------------------|
|   0    |   2    | Header / command echo          | bytes        | First byte echoes the command class. Validate as a sanity check only. |
|   2    |   2    | Grill temperature              | uint16 LE    | Degrees F. `0` while warming up from cold.                            |
|   4    |   2    | Probe 1 temperature            | uint16 LE    | Degrees F. **`89` is the sentinel for "unplugged"**.                  |
|   6    |   2    | Grill setpoint                 | uint16 LE    | Degrees F.                                                            |
|   8    |   1    | API version                    | uint8        | Bumped by controller firmware revs.                                   |
|   9    |   3    | Build / firmware sub-info      | bytes        | Vendor-defined; not parsed.                                           |
|  12    |   2    | Probe 2 temperature            | uint16 LE    | Degrees F. `89` sentinel as for probe 1.                              |
|  14    |   2    | Probe 2 setpoint               | uint16 LE    | Degrees F.                                                            |
|  16    |   4    | Profile time remaining         | uint32 LE    | Seconds. `0` when no profile is active.                               |
|  20    |   4    | Warn code                      | uint32 LE    | See WarnCode table. LSB is the active code.                           |
|  24    |   2    | Probe 1 setpoint               | uint16 LE    | Degrees F.                                                            |
|  26    |   1    | Power state                    | uint8        | See PowerState table.                                                 |
|  27    |   1    | Grill mode                     | uint8        | Reserved; mirrors profile state.                                      |
|  28    |   1    | Fire state                     | uint8        | See FireState table. `198` indicates Cold Smoke.                      |
|  29    |   1    | Hopper / pellet percent        | uint8        | Range `0..100`. Not all controllers populate this.                    |
|  30    |   1    | Profile end byte               | uint8        | `1` if a profile finished and is awaiting acknowledgement.            |
|  31    |   1    | Grill type                     | uint8        | See [MODELS.md](MODELS.md) for the mapping.                           |
|  32    |   4    | Reserved                       | bytes        | Zero on all observed firmwares.                                       |

## Enumerations

### PowerState (offset 26)

| Value | Meaning            |
|------:|--------------------|
|     0 | Off                |
|     1 | On                 |
|     2 | Fan-only / venting |
|     3 | Cold Smoke active  |

### FireState (offset 28)

| Value | Meaning                |
|------:|------------------------|
|     0 | Idle                   |
|     1 | Igniting               |
|     2 | Heating up             |
|     3 | Running (flame on)     |
|     4 | Cooling down           |
|     5 | Error / fault          |
|   198 | Cold Smoke (no flame)  |

`flame_on` is reported as `True` when `FireState in {1, 2, 3}`.

### WarnCode (offset 20, low byte)

| Value | Meaning                  |
|------:|--------------------------|
|     0 | None                     |
|     1 | Low voltage              |
|     2 | Fan overload             |
|     3 | Auger overload           |
|     4 | Ignitor overload         |
|     5 | Fan disconnect           |
|     6 | Auger disconnect         |
|     7 | Ignitor disconnect       |
|     8 | Low pellet hopper        |
|   128 | Low pellet hopper (alias)|

The value `128` is an older firmware alias for "low pellet". Treat both `8`
and `128` as the same condition.

## Special values

- **Probe sentinel:** A reading of exactly `89 degF` indicates the probe is
  unplugged. The integration surfaces this as `None` rather than `89`.
- **Probe upper guard:** Readings above approximately `557 degF` (`0x0245`)
  are physically impossible for the supplied thermistor and indicate a wiring
  fault. The integration discards them.
- **Setpoint validation:**
  - Grill setpoint: `150 <= T <= 550` degF.
  - Probe target: `32 <= T <= 257` degF.
  - Out-of-range values are rejected client-side; the controller does not
    validate.

## Reliability rules

- Each request is retried up to **5 times** with a per-attempt timeout of
  **1 second**.
- A polling cadence of **5 seconds or slower** is recommended. The controller
  is single-threaded over UDP and can drop packets under tighter loops.
- Setpoint commands are idempotent. Repeating `UT225!` is safe.
- After a successful `UK00x!` power command, wait at least one poll cycle
  before issuing the next state-changing command; the controller updates its
  internal state asynchronously.

## Server Mode interlock

When the controller's Server Mode is enabled, it routes all traffic through
the vendor cloud and the LAN socket stops responding. The integration
detects this as follows:

1. A host that previously responded stops responding to all 5 retries.
2. The host is still reachable on the network (ICMP / ARP succeed).
3. After two consecutive poll cycles in this state, a Home Assistant repair
   issue is raised: `server_mode_enabled`.

The repair tells the user to disable Server Mode in the GMG mobile
application and re-add the integration. There is no LAN command that can
disable Server Mode remotely.

## Sources

The protocol description above was assembled from publicly observable
behaviour of the GMG controllers and from the vendor's own documentation:

- Green Mountain Grills product pages -
  <https://greenmountaingrills.com/>
- GMG Server Mode documentation -
  <https://www.greenmountaingrills.com/server-mode/>
- GMG WiFi App page -
  <https://www.greenmountaingrills.com/wifi-app/>
- Home Assistant community discussion thread (general background) -
  <https://community.home-assistant.io/t/green-mountain-grill/149007>

Public community implementations exist that document the same wire format
and are useful as cross-references when validating new firmware behaviour:

- <https://github.com/brandenc40/green-mountain-grill> - Go reference, byte
  map and enumerations.
- <https://github.com/FeatherKing/grillsrv> - Go reference, command
  construction and Wi-Fi provisioning command.
- <https://github.com/toddq/grillsrv> - Go reference, more recent fork.
- <https://github.com/Aenima4six2/gmg> - JavaScript client; includes a
  controller emulator that is useful for testing without hardware.

This integration is an independent implementation; it does not copy, fork,
or derive code from any of the projects above. The references are listed
because they document the same publicly observable protocol.
