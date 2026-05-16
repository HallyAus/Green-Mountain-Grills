# Supported Models

Green Mountain Grills has used several controller generations across the
product line. This integration targets WiFi-capable controllers that respond
to the local UDP protocol described in [PROTOCOL.md](PROTOCOL.md).

## Model matrix

| Model (2026 name)    | Legacy name         | Controller | WiFi LAN | Probes | Min/Max degF |
|----------------------|---------------------|------------|----------|-------:|--------------|
| Trek Prime 2.0       | Davy Crockett (later)| Prime 2.0  | Yes (also BT) | 2 | 150 / 550 |
| Ledge Prime 2.0      | Daniel Boone        | Prime 2.0  | Yes      |      2 | 150 / 550    |
| Peak Prime 2.0       | Jim Bowie           | Prime 2.0  | Yes      |      2 | 150 / 550    |
| Ledge Prime+         | DB Prime+           | Prime+     | Yes      |      2 | 150 / 550    |
| Peak Prime+          | JB Prime+           | Prime+     | Yes      |      2 | 150 / 550    |
| Davy Crockett (legacy)| -                  | G1         | Yes      |      1 | 150 / 550    |

The integration auto-detects the controller from the `grill_type` byte in the
status frame (offset 31) and exposes only the entities that the controller
supports - for example, only one probe entity is created on a G1-controller
Davy Crockett.

## Features not exposed over WiFi

The local UDP protocol does not expose the following, even on the latest
controllers. They remain controllable only through the physical control
panel or the vendor mobile application:

- **Grill light toggle** - the light is wired to a physical switch.
- **Pellet hopper level** as a percentage - only the binary
  *low-pellet* warning is reported reliably. The hopper-percent byte exists
  in the status frame but is unpopulated on many firmwares; the integration
  reports it as a diagnostic value only.
- **Smart Smoke** setting - read-only on the controller.
- **Multi-stage cook profile upload** - profiles can be authored in the
  vendor app and synced to the controller through the cloud, but there is
  no LAN command to push a profile. The integration does not implement
  profile authoring.

## Local mode required

All supported models must be operating in **local WiFi mode** with **Server
Mode disabled**. See [INSTALL.md](INSTALL.md) for the steps to disable Server
Mode if the grill is currently bound to the vendor cloud.
