### 1.4.6 (Jul 30, 2026)

✨ New

- Publish a retained RV-C entity map (`rvc/entity-map`) joining MQTT discovery, the Home Assistant entity registry, and Home Assistant states

### 1.4.5 (Jul 29, 2026)

✨ New

- Publish the complete CAN raw stream

### 1.4.4 (Jul 29, 2026)

🐛 Fixes

- Publish CAN acknowledgement (ACK/NACK) frames onto the raw and timestamped MQTT streams for diagnostic visibility, alongside the existing high-rate status filters

### 1.4.3 (Jul 29, 2026)

✨ New

- Preserve CAN timestamps and route RV-C DM_RV and J1939 DM1 (FECA) separately

### 1.4.2 (Jul 26, 2026)

✨ New

- Route DM_RV messages to `can/diagnostics`

🛠️ Improvements

- Drop armv7 architecture support

### 1.4.1 (Jul 11, 2026)

🐛 Fixes

- corrected AquaHot water temperature and coolant temp display
- fixed AquaHot electric-only operation toggle
- rounded generator coolant temperature to a whole °F

### 1.4.0 (Jul 10, 2026)

✨ New

- Add additional Victron entities:
  - battery time-to-go, consumed amp-hours, and low-voltage alarm
  - solarcharger yield today
  - MultiPlus alarms and shore power connected states
  - MultiPlus Charge Power, Inverter Power and Total Output Power

🛠️ Improvements

- Improve Aqua-Hot 100/200 series support, including quiet mode and interior heating priority state confirmation
- Victron sensors now publish friendly labels such as `Inverting` and `Ok`
- Victron energy sensors now publish `total_increasing` state class for Home Assistant energy tracking

🐛 Fixes

- Micro-Air fan modes now map manual/cycled high and low values correctly
- Micro-Air heat source presets and optimistic updates now better match supported device capabilities

### 1.3.3 (Jun 28, 2026)

🐛 Fixes

- Persist DC_DRIVER based lights dimmer capability

### 1.3.2 (Jun 27, 2026)

🐛 Fixes

- DC dimmer capability now self-heals if it fails to report correctly

### 1.3.0 (Jun 26, 2026)

> ⚠️ **Victron entity naming update:** Entity names were restructured to correctly
> handle multiple devices of the same type. If your dashboards, automations, scripts,
> scenes, or templates reference Victron entity IDs directly, they will need to be
> updated after upgrading.

✨ New

- Hughes Power Watchdog Bluetooth integration
- Generator start/stop via HA switch entities, with run-status and fault sensors

🛠️ Improvements

- Victron entities report unavailable when the GX device is offline instead of showing stale values
- Victron integration correctly handles multiple devices of the same type
- RV-C entities report unavailable when the CAN interface is offline instead of showing stale values
- Enabling or disabling an integration no longer restarts HA just to release Bluetooth devices
- Improved AI dashboard prompts and entity exports

🐛 Fixes

- Dimmer and light state persists correctly across upgrades
- Integration state now survives a Node-RED reinstall
- GeoBridge startup and RV-C network time-sync are more reliable
- BLE monitoring no longer blocks HA startup or shutdown
