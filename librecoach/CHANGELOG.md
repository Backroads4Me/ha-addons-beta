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

**Hughes Power Watchdog (new)**

- Added an optional Bluetooth integration for Hughes Power Watchdog Gen 1 and
  Gen 2 devices (30A and 50A), with entities for electrical telemetry,
  connection diagnostics, and device availability.
- Added Gen 2 controls for the power relay, neutral detection, and energy reset
  (Gen 1 remains read-only), plus per-device reconnect and clear-error controls.
- Hughes and Micro-Air can now be enabled independently; disabling one releases
  only its own Bluetooth devices and entities.

**Victron**

- Renamed and restructured Victron entity IDs, friendly names, units, and paths.
- Added a writable AC input current limit (number entity).
- Victron entities now report unavailable when the GX device is offline instead
  of showing stale values, and the GX MQTT connection stays disconnected while
  the integration is disabled.
- Disabling Victron now reliably removes every retained Victron entity, including
  ones left behind by older versions.

**Micro-Air thermostats**

- Climate modes are now derived from each thermostat's reported capabilities.
- More reliable Bluetooth connections, retries, and recovery after transient
  failures; BLE monitoring no longer blocks Home Assistant startup or shutdown.
- Added per-device availability, last-success, failure-count, and last-error
  diagnostics; outdoor temperature now handles unavailable readings cleanly.

**RV-C and generator**

- Added generator start/stop commands and running, active-demand,
  demand-summary, and coolant-temperature entities.
- RV-C entities now report unavailable when the CAN interface is offline.
- Improved GeoBridge startup behavior and RV-C network time-sync reliability.

**Startup, upgrades, and recovery**

- Startup now fails fast with a clear message instead of continuing in a
  partially deployed state.
- A missing Home Assistant MQTT integration no longer causes a restart loop;
  LibreCoach waits, reports what is needed, and resumes when MQTT is available.
- Local Node-RED flow edits are backed up to
  `/config/librecoach-backups/<timestamp>/` before being overwritten, and
  user-added `package.json` dependencies are preserved across updates.
- LibreCoach-managed Node-RED installs are now recognized on upgrade without a
  false "takeover" prompt, and integration state survives a Node-RED reinstall.

**Configuration and credentials**

- MQTT usernames and passwords containing spaces or special characters now work
  everywhere; credentials with newline characters are rejected with a clear error.
- Added the Hughes enable option, reorganized integration settings, clarified
  RV-C time-sync wording, and marked MQTT credentials and CAN interface as
  advanced settings.
- Removed the unused beta-features option.

**Dashboard and entity tools**

- Improved the AI dashboard prompts (standard and Mushroom cards), entity
  exports, and formatting, including guidance for coaches without Victron
  hardware.

**Other fixes and improvements**

- Numerous startup-hardening, Bluetooth cleanup safety, and build
  reproducibility fixes. `configuration.yaml` is now backed up before any
  automated cleanup, and enabling or disabling an integration no longer restarts
  Home Assistant just to release Bluetooth devices.

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

### 1.2.16 (Apr 3, 2026)

- Prevented dimmer capability detection from being lost after updates or restarts
- Added standard RV-C thermostat climate entity support with Home Assistant control
- Removed duplicate naming in water heater entities
- Added beta support for wireless panel signal status, available only when beta testing is enabled in config

#### 1.2.15 (Mar 28, 2026)

- Corrected a AquaHot water heater bug

#### 1.2.14 (Mar 17, 2026)

- Added heat source presets for Micro-Air thermostats (Heat Pump, Furnace, etc.)
- Heat source selection persists across off/on cycles

#### 1.2.13 (Mar 16, 2026)

- Improved Aqua-Hot zone control decoding
- Fixed Victron device icon bug
- Added setpoint range validation to floor heat level discovery

#### 1.2.12 (Mar 6, 2026)

- Added Aqua-Hot per-zone heating status
- Fixed recording export download link

#### 1.2.11 (Mar 6, 2026)

- Bug fixes

#### 1.2.10 (Mar 5, 2026)

- Added support for water heater, furnace, AC loads (load shedding) and additional light types
- Added generator demand status
- Improved recording capability
- Bug fixes and performance improvements

#### 1.2.9 (Mar 3, 2026)

- Added new beta capabilities that can be enabled on the config tab
  - Added support for additional light types (beta)
  - Added additional Aqua-Hot support (beta)
  - Added water heater support (beta)
  - Added furnace support (beta)
- Improved efficiency for better performance on older devices

#### 1.2.8 (Mar 1, 2026)

- Performance tuning

#### 1.2.7 (Feb 28, 2026)

**⚠️ Check your tank names ⚠️** Black and gray tank labels were previously swapped in some installations and now corrected.

- Fixed tank black/gray sensor assignment
- Added additional tank support

#### 1.2.0 (Feb 26, 2026)

- Added GeoBridge for automatic home location tracking
- Added MQTT-driven BLE lifecycle (no HA restart needed for enable/disable)
- Added autonomous cleanup (Suicide Pattern) for uninstall scenarios
- Added weekly scheduled Docker rebuild for base image security patches
- Fixed base image mismatch (addon-base instead of base)
- Fixed preserve-mode transition when toggling prevent_flow_updates
- Removed mqtt_host, mqtt_port, mqtt_topic, and can_bitrate config options
- Removed host_dbus dependency (BLE now uses HA integration)

#### 1.1.10 (Feb 21, 2026)

- Refined Micro-Air integration

#### 1.1.8 (Feb 20, 2026)

- Added Victron write capability
- Fixed integration hash check

#### 1.1.7 (Feb 20, 2026)

- Moved Bluetooth from add-on to native HA integration for improved reliability
- Removed standalone bridge and dbus dependency

#### 1.1.6 (Feb 19, 2026)

- CAN-to-MQTT Bridge add-on no longer required (auto-disabled)
- Added Micro-Air EasyTouch Bluetooth integration
- Victron integration can now be disabled
- Fixed RV-C polling and watchdog takeover issue

#### 1.0.3 (Feb 15, 2026)

- Start add-on once after update to enable auto-start
- Added Configuration Export / Import
- Add-on stays running for automatic updates

#### 1.0.0 – 1.0.2 (Feb 13–14, 2026)

- Added light dimming support
- Added Victron GX support
- Option to disable Victron

#### 0.9.x (Jan–Feb 2026)

- Major MQTT credential handling overhaul
- Bundled Node-RED credentials system
- Multiple CAN-MQTT bridge connection and logging fixes

#### 0.9.0 (Jan 16, 2026)

- Rebranded from RV Link to LibreCoach

#### 0.8.x (Jan 2026)

- Added MQTT setup validation and diagnostics
- Multiple CAN-MQTT and Mosquitto reliability fixes
- Initial public releases
