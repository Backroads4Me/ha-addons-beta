### 1.7.0 (Aug 28, 2026)

✨ New

- Supported TM-102-family input modules now expose their RV-C digital inputs as binary sensors, named by module and connector pin once the module identifies itself
- LibreCoach identifies RV-C nodes through their reported product information, improving device names while keeping names stable across firmware updates

🛠️ Improvements

- The import notification now opens the import page directly, without asking the owner to sign in again
- First-start MQTT setup now notifies the user as soon as Home Assistant confirms action is required, reports Home Assistant API outages separately, shows continuing progress, and retries notifications that could not be delivered
- Interrupted LibreCoach-owned Node-RED installations resume safely without being mistaken for an existing user installation; the LibreCoach watchdog remains disabled until setup completes
- The AI dashboard prompt omits diagnostic-only entities, keeping generated dashboards focused on useful coach controls and status
- Entity discovery repairs stale records more reliably, including obsolete Victron component types and entity-map entries left by earlier configurations
- Migration notifications are limited to stored records that need user attention and clear themselves when the issue no longer exists

🐛 Fixes

- The top of the capital C in the LibreCoach startup logo aligns with the rest of the letter
- Installing Node-RED on a new system no longer fails when the download takes longer than 30 seconds; LibreCoach waits for the Home Assistant Supervisor to finish and reports a real reason if the install genuinely fails
- A Node-RED add-on that is installed but was never configured or started is adopted automatically instead of asking permission to overwrite flows that do not exist
- Dashboard generator starts now register as generator demand, preventing the AGS from stopping the generator because no active demand was recorded
- Transfer switches that stop reporting become unavailable instead of retaining stale source and electrical readings
- RV-C diagnostics and SAE J1939 traffic are classified separately, preventing overlapping data pages from decoding frames as the wrong protocol
- RV-C devices that share a source address remain distinct when their extended data-page identity differs
- Entity-map recovery can resolve stale Home Assistant discovery records without abandoning the rest of the map
- Configuration export download links now work on any Home Assistant address and port, instead of only the default one
- Configuration exports retain the RV details entered on the export page
- Configuration import always reports its result, including when Home Assistant never answers for some entities, instead of leaving the import page waiting
- The import notification's "Open Import Page" link now opens the import page
- Digital inputs become unavailable when their input module stops reporting, instead of holding the reading it last sent
- Input modules that never answer a status request are rested and retried later rather than asked every 20 seconds forever
- A Node-RED add-on that was configured only with a login is no longer treated as unconfigured, so its authentication is left alone
- An interrupted install is only resumed while it is recent, so a Node-RED the owner installed later is asked about rather than adopted
- Lights that report their state through a dimmer no longer refuse commands when an older installation also recorded them as component drivers

### 1.6.0 (Aug 21, 2026)

✨ New

- Automatic transfer switch support: RV-C enabled transfer switches now report which source is in use. Sources are labeled Generator and Shore where the coach reports them.
- Victron alarms that report warning separately from alarm now appear as problem sensors
- Supported Gen 2 Hughes Power Watchdogs now expose per-line electrical and fault diagnostics, stored error history, neutral monitoring, shore-power relay control, and backlight control

🛠️ Improvements

- Tank levels hold steady: a tank sitting on a sender boundary no longer flips back and forth
- Redundant prefixes removed from LibreCoach system entity names
- Victron entities keep their identity when a GX service restarts
- Further refined Victron rounding to keep readings at a sensible precision

🐛 Fixes

- Micro-Air diagnostic entities no longer duplicate on multi-zone thermostats
- Furnace commands now reach the furnace
- Dimmers no longer report on while their actual state is unknown
- Generator engine load now reports the correct percentage
- Sensor faults and out-of-range readings across RV-C entities now show as unavailable instead of implausible numbers
- More reliable address claim and RV-C polling, which improves how consistently devices answer on the bus

### 1.5.2 (Aug 19, 2026)

Released with an incorrect version number and superseded by 1.6.0. It carried new
features, which make it a minor release rather than a patch. Everything it
contained is listed under 1.6.0 above.

### 1.5.1 (Aug 8, 2026)

🐛 Fixes

- Victron readings are now rounded to a precision appropriate for their metric to prevent database bloat.

### 1.5.0 (Aug 2, 2026)

> ⚠️ **Some Victron sensors changed type:** Victron readings that are only on or off, such as alarms and shore power connected, now use `binary_sensor` entity IDs instead of `sensor.` Dashboards and automations that reference them need to be updated after upgrading.

✨ New

- Additional Victron measurements, including battery, solar, inverter/charger, and generator current, plus more AC power readings
- Victron custom device names set on the GX are now used in Home Assistant, making multiple devices of the same type easier to tell apart

🛠️ Improvements

- MQTT delivery is more dependable for Home Assistant discovery, states, and commands
- Improved Aqua-Hot status reporting for both native and Silverleaf-interfaced systems
- Victron battery time-to-go now reports in hours, and reports unavailable when the GX is not calculating a remaining time
- Entities recover on their own after an MQTT reconnect instead of staying unavailable until a restart

🐛 Fixes

- Corrected RV-C decoding across several entities; unavailable and out-of-range readings now display correctly
- Victron entities no longer freeze at their last reading when a value is missing or non-numeric

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
