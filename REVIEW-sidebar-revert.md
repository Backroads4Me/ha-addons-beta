# Review: Revert Settings Sidebar to config.yaml

## Summary

The beta addon previously moved several configuration options (geo, victron, microair, beta toggles) out of `config.yaml` into a custom ingress sidebar UI served by a Python HTTP server. This change reverts to the standard HA `config.yaml` approach while preserving all non-sidebar beta improvements (GeoBridge, curl timeouts, Mosquitto optimization, suicide pattern, flows hash tracking).

## What Changed

### 1. `config.yaml`

- **Removed** all ingress lines (`ingress: true`, `ingress_port: 8099`, `ingress_panel: true`, `panel_icon`, `panel_title`)
- **Added** `host_dbus: true` (restored from prod — needed for BLE/BlueZ D-Bus access)
- **Added** config options to `options:` and `schema:` sections: `geo_enabled`, `geo_device_tracker_primary`, `geo_device_tracker_secondary`, `geo_update_threshold`, `microair_enabled`, `microair_email`, `microair_password`, `ble_scan_interval`, `victron_enabled`, `beta_enabled`
- **Did NOT add back** `mqtt_topic_raw`, `mqtt_topic_send`, `mqtt_topic_status`, `can_bitrate` (staying hardcoded)
- Option order matches the sidebar UI section order: GPS → Micro-Air → Victron → Beta → Node-RED → Debug → MQTT → CAN

**Verify:**
- [ ] Every key in `options:` has a matching key in `schema:`
- [ ] Schema types are correct (bool for toggles, `str?` for optional strings, `password?` for passwords, `int(min,max)?` for optional integers)
- [ ] No ingress-related lines remain
- [ ] `host_dbus: true` is present

### 2. `translations/en.yaml`

- **Added** translation entries for all restored config options
- Labels and descriptions match the sidebar UI wording (e.g., "Enable Automated GPS Location Updates", not "Enable Geo Bridge")
- Entry order matches `config.yaml` option order

**Verify:**
- [ ] Every key in `config.yaml` `options:` has a matching entry in `translations/en.yaml`
- [ ] Labels are user-friendly and match the sidebar's original wording

### 3. `vehicle_bridge/main.py`

- **Removed** `import os`
- **Removed** `SETTINGS_PATH = "/data/librecoach-settings.json"`
- **Simplified** `_load_config()` to only read `/data/options.json` (no more merge with settings file)
- **Kept** `from geo_bridge import GeoBridge` and `GeoBridge(config, mqtt)` in modules list

**Verify:**
- [ ] No references to `librecoach-settings.json` or `SETTINGS_PATH`
- [ ] No `import os`
- [ ] `_load_config()` reads only `/data/options.json`
- [ ] GeoBridge import and instantiation are intact

### 4. `run.sh`

- **Removed** `SETTINGS_FILE="/data/librecoach-settings.json"` variable
- **Removed** entire migration block (~40 lines) that created the settings file from `options.json`
- **Removed** `jq` reads from `$SETTINGS_FILE` for `VICTRON_ENABLED`, `BETA_ENABLED`, `MICROAIR_ENABLED`
- **Changed** to `bashio::config` reads (lines 30-32): `VICTRON_ENABLED`, `BETA_ENABLED`, `MICROAIR_ENABLED`
- **Changed** Phase 1.5 BLE section: `MICROAIR_PASSWORD`, `MICROAIR_EMAIL`, `BLE_SCAN_INTERVAL` now use `bashio::config` instead of `jq` from settings file
- **Removed** `"ingress_panel":true` from the self-options API call (line 344)
- **Kept** all other beta improvements: curl timeouts on `api_call`, Mosquitto config-change optimization, suicide pattern slug injection, flows hash tracking, `mark_nodered_managed "$FLOWS_HASH"` with hash parameter

**Verify:**
- [ ] No references to `SETTINGS_FILE`, `librecoach-settings.json`, or `jq ... "$SETTINGS_FILE"` anywhere in the file
- [ ] `VICTRON_ENABLED`, `BETA_ENABLED`, `MICROAIR_ENABLED` use `bashio::config` (lines 30-32)
- [ ] `MICROAIR_PASSWORD`, `MICROAIR_EMAIL`, `BLE_SCAN_INTERVAL` use `bashio::config` (Phase 1.5 section)
- [ ] Self-options API call is `'{"boot":"auto","watchdog":true}'` with no `ingress_panel` (line 344)
- [ ] `api_call` still has `--connect-timeout 5 -m 30` curl flags
- [ ] Suicide pattern slug injection is intact (`OWNER_SLUG` + `sed` on line 376-377)
- [ ] `FLOWS_HASH` and `mark_nodered_managed "$FLOWS_HASH"` are intact
- [ ] `get_flows_hash` / `get_managed_hash` functions are intact

### 5. `Dockerfile`

- **Removed** `COPY settings_server /opt/settings_server`
- **Removed** `/opt/settings_server` from the CRLF strip `find` command

**Verify:**
- [ ] No references to `settings_server` anywhere in the file
- [ ] CRLF strip `find` command lists: `/etc/s6-overlay /etc/cont-init.d /opt/vehicle_bridge /opt/librecoach-project /opt/librecoach_ble`

### 6. `rootfs/` — File Structure

**Added:**
- `rootfs/etc/cont-init.d/verify-dbus.sh` — D-Bus socket verification script (copied from prod)

**Deleted:**
- `rootfs/etc/s6-overlay/s6-rc.d/settings-server/` (entire directory)
- `rootfs/etc/s6-overlay/s6-rc.d/user/contents.d/settings-server` (file)

**Verify:**
- [ ] `verify-dbus.sh` exists and checks for `/run/dbus/system_bus_socket`
- [ ] No `settings-server` directory under `s6-rc.d/`
- [ ] No `settings-server` file under `user/contents.d/`
- [ ] `vehicle-bridge` service files are intact (run, finish, type, dependencies.d/)

### 7. `settings_server/` — Deleted

The entire `settings_server/` directory has been deleted (server.py, static/index.html, static/app.js, static/style.css).

**Verify:**
- [ ] Directory does not exist

## Preserved Beta Improvements (should NOT have been touched)

These features were added in the beta alongside the sidebar but are independent of it:

- [ ] **GeoBridge** — `vehicle_bridge/geo_bridge.py` exists, imported in `main.py`, instantiated in modules list
- [ ] **Curl timeouts** — `api_call` in `run.sh` uses `--connect-timeout 5 -m 30`
- [ ] **Mosquitto config optimization** — Mosquitto only restarts if config actually changed
- [ ] **Suicide pattern** — `OWNER_SLUG` slug injection into init-nodered.sh
- [ ] **Flows hash tracking** — `get_flows_hash`, `get_managed_hash`, `FLOWS_HASH`, `mark_nodered_managed "$FLOWS_HASH"`

## Grep Sanity Checks

Run these from `ha-addons-beta/librecoach/` to confirm no stale references:

```bash
# Should return NO results:
grep -r "SETTINGS_FILE" .
grep -r "librecoach-settings" .
grep -r "settings_server" .
grep -r "ingress" .
grep -r "8099" .
grep -r "panel_icon" .
grep -r "panel_title" .

# Should return results (confirming preserved features):
grep -r "geo_bridge" .          # GeoBridge import + instantiation
grep -r "bashio::config" run.sh # All config reads use bashio
grep -r "FLOWS_HASH" run.sh     # Flows hash tracking
grep -r "OWNER_SLUG" run.sh     # Suicide pattern
grep -r "connect-timeout" run.sh # Curl timeouts
```
