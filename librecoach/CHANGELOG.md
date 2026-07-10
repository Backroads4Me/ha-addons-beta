### 1.3.4

✨ New

- Add additional Victron entities:
  - system `/Dc/Battery/TimeToGo` and `/SystemState/State`
  - battery `/ConsumedAmphours` and `/Alarms/LowVoltage`
  - solarcharger `/History/Daily/0/Yield` for solar yield today
  - MultiPlus `/Ac/ActiveIn/Connected`
  - MultiPlus `/Alarms/LowBattery`, `/Alarms/Overload`, and `/Alarms/HighTemperature`
- Add synthetic MultiPlus power-flow sensors for dashboard cards:
  - Charge Power (`/Dc/0/ChargePower`)
  - Inverter Power (`/Dc/0/InverterPower`)
  - Total Output Power (`/TotalOutputPower`)

🛠️ Improvements

- Improve Aqua-Hot 100/200 series support, including quiet mode and interior heating priority state confirmation
- Victron sensors now publish friendly labels such as `Inverting` and `Ok`
- Victron energy sensors now publish `total_increasing` state class for Home Assistant energy tracking
- Preserve add-on options and Node-RED persistent context in `/share/.librecoach-preserve` from both beta and prod installs

🐛 Fixes

- Micro-Air fan modes now map manual/cycled high and low values correctly
- Micro-Air heat source presets and optimistic updates now better match supported device capabilities
- DC dimmer and driver status decoding is more defensive around missing instances

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
