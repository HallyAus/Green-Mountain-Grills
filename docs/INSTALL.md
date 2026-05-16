# Installation

## Prerequisites

- Home Assistant Core **2026.1.0** or newer.
- HACS installed and operational.
- A Green Mountain Grills smoker with a WiFi-capable controller (see
  [MODELS.md](MODELS.md)).
- The grill and Home Assistant must be on the **same Layer 2 broadcast
  domain** (same VLAN / SSID). UDP broadcast is required for discovery.
- The grill's **Server Mode must be disabled**. See "Disabling Server Mode"
  below.

## Disabling Server Mode

Server Mode routes all controller traffic through the vendor cloud and
disables the LAN protocol this integration depends on.

1. Open the GMG mobile application.
2. Connect to the grill.
3. Open **Settings -> WiFi Settings** (the exact label varies by app
   version).
4. Toggle **Server Mode** to **Off**.
5. Reconnect the grill to your home network in **local mode**.

If Server Mode cannot be toggled in the app, fully power-cycle the controller
and try again. Some firmwares require a reboot before the toggle is honoured.

## Install via HACS (custom repository)

1. In Home Assistant, open **HACS -> Integrations**.
2. Open the three-dot menu in the top right and choose **Custom
   repositories**.
3. Add the GitHub URL of this repository, choose **Integration** as the
   category, and click **Add**.
4. Search HACS for **Green Mountain Grills** and install.
5. Restart Home Assistant.

## Add the integration

1. Open **Settings -> Devices & Services**.
2. Click **Add Integration** and search for **Green Mountain Grills**.
3. Choose one of:
   - **Auto-discover**: the integration broadcasts and lists any grills
     that respond. Select your grill and confirm.
   - **Manual**: enter the grill's IP address and port (default `8080`).
4. The integration will probe the grill, fetch its serial and firmware, and
   create a device with the appropriate entities for the controller
   generation.

## DHCP discovery

If the grill is announced over DHCP with a MAC prefix that matches GMG's
allocation, Home Assistant will surface a discovery card in **Settings ->
Devices & Services** automatically. Click **Configure** to confirm.

## Reconfigure (IP change)

If the grill's IP address changes (DHCP lease expired, router replaced):

1. Open the integration entry in **Settings -> Devices & Services**.
2. Click the three-dot menu and choose **Reconfigure**.
3. Enter the new IP. The serial number is used as the unique identifier, so
   the existing entities and history are preserved.

You can avoid this entirely by giving the grill a DHCP reservation in your
router.

## Options

The integration exposes one option:

- **Scan interval** (seconds, default `30`). The controller is bandwidth-
  constrained; values below `5` are not recommended and the UI will warn.

## Troubleshooting: "no devices found"

Work through the list in order:

1. **Server Mode** is the most common cause. Confirm it is **off** in the
   GMG mobile app.
2. **Same VLAN.** The discovery probe is a UDP broadcast and will not cross
   subnets. Move Home Assistant and the grill to the same VLAN, or relay
   broadcasts (`udp-broadcast-relay`, `igmpproxy`) to the grill's VLAN.
3. **Firewall.** Confirm UDP port `8080` is open between Home Assistant and
   the grill in both directions.
4. **Wireless isolation.** Many consumer routers default to "AP isolation"
   or "guest network isolation" on the 2.4 GHz band the grill uses. Disable
   it for the SSID the grill is on.
5. **mDNS / multicast filtering.** Some managed switches drop broadcast UDP
   in their default config; check IGMP snooping settings.
6. **Manual entry.** As a diagnostic step, try adding the grill with its IP
   directly. If manual entry works but discovery does not, the problem is
   broadcast forwarding, not the integration.
7. **Controller responsiveness.** Power-cycle the grill. The Prime 2.0
   controller occasionally hangs its WiFi stack after long uptimes.

If none of the above resolves the issue, enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.gmg: debug
```

and open an issue with the resulting log.
