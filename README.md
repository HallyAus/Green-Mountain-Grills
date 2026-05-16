# Green Mountain Grills for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Hassfest](https://github.com/hallyaus/Green-Mountain-Grills/actions/workflows/validate.yml/badge.svg)](https://github.com/hallyaus/Green-Mountain-Grills/actions/workflows/validate.yml)
[![Tests](https://github.com/hallyaus/Green-Mountain-Grills/actions/workflows/test.yml/badge.svg)](https://github.com/hallyaus/Green-Mountain-Grills/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![HA min version](https://img.shields.io/badge/Home%20Assistant-2026.1%2B-41BDF5.svg)](https://www.home-assistant.io/)

Control and monitor Green Mountain Grills WiFi-enabled pellet smokers
directly from Home Assistant - locally, over your own LAN, with no cloud
dependency.

## Features

- Full **climate** entity for the grill with setpoint, current temperature,
  HVAC mode, preset for Cold Smoke, and on/off control.
- **Sensor** entities for grill temperature, probe 1, probe 2, profile time
  remaining, firmware version, signal warnings, and the last-warn code.
- **Binary sensor** entities for flame-on, low-pellet, fan / auger / ignitor
  faults, and Cold Smoke active.
- **Number** entities for probe 1 and probe 2 targets, with the correct
  150-550 degF / 32-257 degF ranges.
- **Button** entities for Power On, Power Off, and Cold Smoke.
- **Services** for setting setpoints, targeting probes, and starting Cold
  Smoke, all exposed in the Developer Tools service picker.
- Built-in **diagnostics** download for issue reporting.
- **Repair issues** for the most common failure modes - notably the
  Server Mode interlock - with clickable fix-flows.
- Full **translations** scaffolding (English ships in-box; others are
  populated as community translations land).
- Targets the **Platinum** Home Assistant integration quality scale: strict
  typing, async-only, full config flow, options flow, reconfigure flow,
  DHCP discovery, and comprehensive test coverage.

## Supported models

See [docs/MODELS.md](docs/MODELS.md) for the full controller matrix.

## Installation

See [docs/INSTALL.md](docs/INSTALL.md) for step-by-step instructions,
including how to disable Server Mode in the GMG mobile app.

## Configuration

The integration has no YAML configuration; everything is set up through the
UI.

- **Auto-discovery** broadcasts on UDP `8080` and lists every grill that
  responds.
- **DHCP discovery** offers a one-click setup when Home Assistant sees a
  matching MAC prefix on the network.
- **Manual entry** is available for routed networks where broadcast
  discovery is not viable.
- **Options**: a single *scan interval* slider (default `30` seconds; the UI
  warns below `5`).

## Entities

| Platform        | Entity                                | Notes                                                   |
|-----------------|---------------------------------------|---------------------------------------------------------|
| `climate`       | Grill                                 | Setpoint 150-550 degF, Cold Smoke preset.               |
| `sensor`        | Grill temperature                     | degF / degC (HA unit system).                           |
| `sensor`        | Probe 1 / Probe 2                     | `None` when unplugged (89 degF sentinel).               |
| `sensor`        | Probe 1 target / Probe 2 target       | Echoes setpoint.                                        |
| `sensor`        | Profile time remaining                | Seconds.                                                |
| `sensor`        | Hopper percent (diagnostic)           | Only reported by some firmwares.                        |
| `sensor`        | Firmware version (diagnostic)         |                                                         |
| `sensor`        | Last warn code (diagnostic)           |                                                         |
| `binary_sensor` | Flame on                              |                                                         |
| `binary_sensor` | Low pellets                           |                                                         |
| `binary_sensor` | Fan / auger / ignitor fault           | One per fault class.                                    |
| `binary_sensor` | Cold Smoke active                     |                                                         |
| `number`        | Probe 1 target / Probe 2 target       | 32-257 degF.                                            |
| `number`        | Grill setpoint                        | 150-550 degF.                                           |
| `button`        | Power On                              |                                                         |
| `button`        | Power Off                             |                                                         |
| `button`        | Cold Smoke                            |                                                         |

## Services

| Service                  | Fields                                | Notes                                  |
|--------------------------|---------------------------------------|----------------------------------------|
| `gmg.set_grill_temp`     | `entity_id`, `temperature`            | 150-550 degF.                          |
| `gmg.set_probe_target`   | `entity_id`, `probe` (1 or 2), `temperature` | 32-257 degF.                    |
| `gmg.power_on`           | `entity_id`                           |                                        |
| `gmg.power_off`          | `entity_id`                           |                                        |
| `gmg.cold_smoke`         | `entity_id`                           | Equivalent to power-on with profile.   |

## Automation examples

### Notify when the grill reaches its setpoint

```yaml
automation:
  - alias: "Grill reached setpoint"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.gmg_grill_temperature
        above: 224
    conditions:
      - condition: state
        entity_id: binary_sensor.gmg_flame_on
        state: "on"
    actions:
      - action: notify.mobile_app
        data:
          message: "Grill is up to temp - load the meat."
```

### Alert on low pellets

```yaml
automation:
  - alias: "GMG low pellets"
    triggers:
      - trigger: state
        entity_id: binary_sensor.gmg_low_pellets
        to: "on"
        for: "00:01:00"
    actions:
      - action: notify.mobile_app
        data:
          message: "GMG hopper is low - top it up before the next session."
```

### Auto-off when meat probe hits its target

```yaml
automation:
  - alias: "GMG auto-off on probe done"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.gmg_probe_1
        above: 164
    actions:
      - action: button.press
        target:
          entity_id: button.gmg_power_off
      - action: notify.mobile_app
        data:
          message: "Probe 1 hit target. Grill is shutting down."
```

### Pre-heat on a schedule

```yaml
automation:
  - alias: "GMG pre-heat at 17:00"
    triggers:
      - trigger: time
        at: "17:00:00"
    actions:
      - action: button.press
        target:
          entity_id: button.gmg_power_on
      - delay: "00:00:30"
      - action: climate.set_temperature
        target:
          entity_id: climate.gmg_grill
        data:
          temperature: 225
```

## Troubleshooting

See the troubleshooting tree in [docs/INSTALL.md](docs/INSTALL.md). The
single most common cause of "no devices found" is the grill being in Server
Mode; the second is a VLAN that does not forward UDP broadcasts.

To collect a debug bundle:

1. Enable debug logging for the integration (`logger:` block in
   `configuration.yaml`).
2. Reproduce the issue.
3. Download diagnostics from the integration's device page.
4. Open an issue with both.

## Development / contributing

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.test.txt
ruff check .
ruff format --check .
mypy custom_components/gmg
pytest
```

CI runs the same commands on every push and pull request. Pull requests
should add or update tests for any behavioural change.

## License

[MIT](LICENSE). Copyright 2026 hallyaus.
