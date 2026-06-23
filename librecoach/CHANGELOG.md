### Unreleased

**Configuration**

- Changed the Victron integration to opt-in for new installations; existing saved configuration is preserved

**Hughes Power Watchdog BLE bridge**

- Added default-off Bluetooth telemetry support for Hughes Power Watchdog Gen 1 and Gen 2 devices, including 30A and 50A models
- Added V2 relay, neutral-detection, and energy-reset command bridging over MQTT; Gen 1 remains read-only
- Added independent Micro-Air and Hughes enable controls so disabling one integration releases only its BLE devices
- Added protocol fixtures and lifecycle tests; Home Assistant entity creation remains deferred to the planned Node-RED work

**Fixes (startup hardening, review items C-1 … C-8)**

- Startup failures now abort deterministically with clear logs instead of continuing with partial deployment state (`set -e` was inert)
- The original Node-RED `credential_secret` backup now lives in add-on private `/data` storage and can no longer be destroyed by restarts; existing backups are migrated automatically
- MQTT usernames/passwords containing spaces or shell metacharacters now work throughout; values with newlines are rejected with a clear error
- MQTT credential injection into `settings.js` no longer uses `sed` and cannot corrupt the file; a failed `flows_cred.json` re-encryption can no longer leave a corrupted file behind
- Local edits to Node-RED flows are backed up to `/config/librecoach-backups/<timestamp>/` before LibreCoach overwrites them; user-added `package.json` dependencies are preserved across updates
- Startup now waits for LibreCoach flows to report ready via the retained `librecoach/nodered/ready` topic instead of only an open Node-RED port (requires a flow version that publishes the topic; older flows fall back to the previous port-open behavior after 90 seconds)
- The BLE integration's automated cleanup now requires a healthy Supervisor and repeated confirmations spread across hours, and backs up `configuration.yaml` before editing it
- A missing MQTT integration no longer causes a crash loop: the add-on stays alive, polls, and resumes setup automatically; the self-watchdog is enabled only after a successful setup

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
