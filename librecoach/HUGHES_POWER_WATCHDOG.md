# Hughes Power Watchdog BLE Bridge

LibreCoach can connect directly to supported Hughes Power Watchdog surge
protectors through Home Assistant's Bluetooth stack. Enable the bridge with
**Enable Hughes Power Watchdog Integration** in the LibreCoach add-on options.
The option defaults to off and disabling it releases the device's BLE connection.

## Supported Devices

- Gen 1 devices advertising as `PMD*`, `PWS*`, or `PMS*` are monitoring-only.
- Gen 2 devices advertising as `WD_V5*` through `WD_V9*` or `WD_E5*` through
  `WD_E9*` support monitoring and commands.
- 30A single-line and 50A dual-line telemetry frames are decoded.
- Booster fields on V8/V9/E8/E9 devices are exposed in the bridge payload but
  remain experimental until validated on physical booster hardware.

Hughes devices permit only one BLE connection. The Hughes mobile application
cannot stay connected while LibreCoach owns the connection. Disable the add-on
option before using the mobile application.

## MQTT Contract

Telemetry is published as JSON to:

```text
librecoach/ble/hughes/{mac}/state
```

The payload includes protocol and capability fields, line voltage/current/power,
frequency, cumulative energy, error information, relay/neutral state for V2, and
optional booster values.

The bridge uses the standard LibreCoach BLE availability and diagnostics topics:

```text
librecoach/ble/hughes/{mac}/available
librecoach/ble/hughes/{mac}/last_success
librecoach/ble/hughes/{mac}/failure_count
librecoach/ble/hughes/{mac}/last_error
librecoach/bridge/hughes/{mac}
```

V2 commands are accepted as JSON on:

```text
librecoach/ble/hughes/{mac}/set
```

Supported command payloads are:

```json
{"command":"relay","value":true}
{"command":"neutral_detection","value":false}
{"command":"reset_energy"}
```

Gen 1 command payloads are rejected because the known command writes are ignored
by those devices.

## Current Phase Boundary

This implementation provides the add-on BLE-to-MQTT bridge only. It does not yet
create Home Assistant sensors, switches, or buttons. Those entities require the
separate LibreCoach Node-RED tab, which is intentionally deferred.
