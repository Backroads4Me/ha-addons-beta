### 2.0.0 (Jun 24, 2026)

This release adds a Hughes Power Watchdog Bluetooth integration, reworks
Victron entity naming, and hardens startup, upgrades, and credential handling.

**⚠️ Breaking change — Victron entities are recreated**

Victron entity IDs and naming have been reworked. Upgrading requires the
existing Victron entities to be deleted and recreated with new IDs, so their
history and any dashboard, automation, script, scene, or template references to
them do **not** carry over automatically.

- Before upgrading: create a full Home Assistant backup and note which Victron
  entities your dashboards and automations use.
- After upgrading: let LibreCoach start with Victron enabled, then disable the
  Victron integration, save, and restart to remove the old entities; re-enable,
  save, and restart to create the new ones. Then update any cards, automations,
  scripts, scenes, and templates that referenced the old Victron entity IDs, and
  regenerate the AI dashboard prompt if you use it.
- Victron is now **disabled by default** on new installations; enable it after
  configuring MQTT on your Victron GX device.

✨ New

- Hughes Power Watchdog Gen 1 and Gen 2 Bluetooth integration (30A and 50A) with electrical telemetry, diagnostics, and availability
- Hughes Gen 2 controls for the power relay, neutral detection, and energy reset (Gen 1 is read-only)
- Per-device reconnect and clear-error controls for Hughes
- Generator start/stop commands and running, active-demand, demand-summary, and coolant-temperature entities
- Writable AC input current limit for Victron (number entity)
- Per-device availability, last-success, failure-count, and last-error diagnostics for Micro-Air

🐛 Fixes

- MQTT credentials with spaces or special characters now work everywhere; newline characters are rejected with a clear error
- Missing HA MQTT integration no longer causes a restart loop — LibreCoach waits and resumes when MQTT is ready
- Dimmer and light state persists correctly across upgrades; dimmable lights no longer revert to simple on/off after an update
- LibreCoach-managed Node-RED installs recognized on upgrade without a false takeover prompt
- Integration state now survives a Node-RED reinstall
- Disabling Victron now removes every retained entity, including ones left behind by older versions
- BLE monitoring no longer blocks HA startup or shutdown

🚀 Improvements

- Startup fails fast with a clear message instead of continuing in a partially deployed state
- Node-RED flow edits backed up to `/config/librecoach-backups/<timestamp>/` before overwrite; `package.json` dependencies preserved across updates
- Hughes and Micro-Air can be enabled independently; disabling one releases only its own devices and entities
- Victron entities report unavailable when the GX device is offline instead of showing stale values
- Victron GX MQTT connection stays disconnected while the integration is disabled
- Micro-Air climate modes derived from each thermostat's reported capabilities
- More reliable Micro-Air Bluetooth connections, retries, and recovery after transient failures
- RV-C entities report unavailable when the CAN interface is offline
- Improved GeoBridge startup and RV-C network time-sync reliability
- `configuration.yaml` backed up before any automated cleanup
- Enabling or disabling an integration no longer restarts HA just to release Bluetooth devices
- Improved AI dashboard prompts (standard and Mushroom cards) and entity exports, including guidance for coaches without Victron

🛠️ Configuration

- Added Hughes enable option; reorganized integration settings; clarified RV-C time-sync wording
- Marked MQTT credentials and CAN interface as advanced settings
- Removed the unused beta-features option

### 1.2.20 (Jun 7, 2026)

**Fixes**

- Fixed Node-RED failing to start on fresh installations
- Fixed version numbering error (1.2.2 should have been 1.2.19)

### 1.2.2 (Jun 5, 2026)

- Added RV-C Network Time Sync: periodically broadcasts system time to the RV-C network. Disabled by default; enable in add-on configuration
- Added AI Dashboard Prompt export: generates a structured LLM prompt for AI-assisted dashboard creation
- Added Solar Controller support
- Enhanced AquaHot 2 integration with updated command encoding and expanded zone support
- Added HA Entity Export: view and export a list of all discovered Home Assistant entities

**Fixes**

- Fixed MQTT broker authentication failures after clean installs
- Fixed dimmer state handling in HA status publishers
- Fixed water pump and autofill status update reporting
- Fixed color mode not matching discovery state on first publish

