# LibreCoach Planned Review Work

This is the active handoff queue. Items include `ha-addons` work and any required `librecoach-node-red` companion work.

Review report baseline: tree as of June 9, 2026. Developers must verify file paths against current code before editing.

## Priority Order

1. BLE reliability and Micro-Air behavior: B-1 through B-6, F-6.
2. Node-RED/Home Assistant entity availability: N-1.
3. Packaging/build safety and dashboard work: D-2, F-4.
4. Lower-risk bridge polish: V-6.

## Difficulty Notes

Most difficult remaining planned work: B-2, because it changes the BLE bridge contract from Micro-Air zone-specific behavior into a generic handler/publisher/command router that can support Hughes and future non-zoned devices without breaking current Micro-Air topics.

The B-series is high priority. It directly affects BLE reliability, Micro-Air user experience, and future Hughes support. The B items also overlap, so they should be sequenced deliberately rather than assigned as unrelated one-off fixes.

Recommended B-series sequence:

1. B-1: collapse duplicate BLE advertisement callbacks.
2. B-2: introduce handler-owned publish/command contracts.
3. B-4: add backoff/offline transition behavior.
4. B-5: make Micro-Air auth failure explicit.
5. B-3/BL-3: add the LibreCoach Tools reset action.
6. B-6: remove HA dry-mode exposure.
7. F-6: add HA diagnostics/buttons after the command/status contracts exist.

## B-1: Duplicate BLE Advertisement Callbacks

Status: Complete in branch `release-integration`. Bridge now registers a single HA Bluetooth callback that iterates handlers; added matched/ignored debug counters. Covered by `librecoach/librecoach_ble/tests/test_ble_bridge.py` (single-callback tests for one and two handlers).

Owner repo: `ha-addons`.

Goal: make BLE scanning scale as more BLE device handlers are added.

Scope:

- `librecoach/librecoach_ble/bridge.py`

Implementation direction:

- Register one Home Assistant Bluetooth callback for the bridge.
- In that callback, iterate enabled handlers and let each handler decide whether the advertisement applies.
- Add optional handler metadata for future narrower matching.
- Add debug counters for ignored and matched advertisements.

Acceptance tests:

- One callback is registered with one handler.
- One callback is registered with Micro-Air plus Hughes.
- Unrelated BLE advertisements do not trigger repeated heavy work.

## B-2: Zone-Centric BLE Publish Path Blocks Hughes

Status: Complete in branch `release-integration`. Added `StateMessage` dataclass and `state_messages(parsed) -> list[StateMessage]` to the handler contract (`devices/base.py`). Micro-Air zone topic construction moved into `MicroAirHandler.state_messages`; the bridge now routes/publishes via `_publish_messages` and never inspects `zones`. Micro-Air topics preserved exactly. Command path publishes verified state for any dict result, not only zoned results. Tests cover unchanged Micro-Air topics, a fake non-zoned handler publishing state, and non-numeric zone keys not crashing the publish loop.

Owner repo: `ha-addons`.

Goal: make the BLE bridge independent of Micro-Air's zone-shaped payloads.

Scope:

- `librecoach/librecoach_ble/bridge.py`
- Existing Micro-Air handler.
- Planned Hughes handler interface.

Implementation direction:

- Define a handler contract such as `state_messages(parsed) -> list[StateMessage]`.
- Move Micro-Air zone topic construction into the Micro-Air handler.
- Add a command contract such as `handle_command(topic_parts, payload)`.
- The bridge should route, publish, and log; it should not inspect `zones`.
- Preserve current Micro-Air MQTT topics.
- Add a fake non-zoned handler test before implementing Hughes.

Acceptance tests:

- Current Micro-Air Home Assistant topics remain unchanged.
- A fake non-zoned handler can publish state.
- Non-numeric Micro-Air keys cannot crash the bridge publish loop.

## B-3 / BL-3: BLE Reset Tool

Status: ha-addons portion complete in branch `release-integration`. Node-RED companion (Tools button) still required. Bridge subscribes to `librecoach/ble/reset_locks`; on receipt it clears only `locked_devices` in `/config/.librecoach-ble-config.json` (credentials/enable flags/other settings preserved), tears down active devices so replacements can be rediscovered and relocked, and publishes `waiting_for_device` per forgotten device. Default lock-on-first-success behavior is unchanged.

Owner repos: `ha-addons` plus `librecoach-node-red`.

Goal: let users replace or re-pair BLE hardware without editing hidden JSON files.

Decision:

- Add a single action in the LibreCoach Tools section.
- Do not build a per-device picker for the first implementation.
- Do not make this an add-on config setting.
- Button label: "Forget BLE Devices" or "Reset Bluetooth Pairing".
- The action clears saved BLE device locks only; it must not clear add-on options, Micro-Air passwords, enable flags, or unrelated BLE settings.

ha-addons implementation direction:

- Add an MQTT command topic, for example `librecoach/ble/reset_locks`.
- When received, remove persisted BLE locked addresses/device IDs from `/config/.librecoach-ble-config.json` while preserving all non-lock settings.
- Restart or immediately reschedule BLE discovery after clearing locks.
- Publish status such as `waiting_for_device` until enabled device types are rediscovered and relocked.
- Keep existing lock behavior by default so nearby devices are not accidentally paired during normal operation.

Node-RED implementation direction:

- Create a Home Assistant button named "Forget BLE Devices" or "Reset Bluetooth Pairing".
- Place it with the other LibreCoach Tools controls, not in a per-device card.
- Button publishes `librecoach/ble/reset_locks`.
- Button help/description should state that it clears saved BLE device locks only and keeps add-on settings/passwords.
- After click, status should show waiting/scanning until devices are rediscovered.

Acceptance tests:

- Locked devices remain locked across restarts until the Tools action is used.
- Tools action clears BLE locks without clearing credentials or enabled flags.
- Bridge returns to scanning and can lock replacement devices after reset.
- Repeated reset clicks are harmless and logged clearly.

## B-4: BLE Poll Backoff And Offline Publishing

Status: Complete in branch `release-integration`. Poll loop now tracks per-device failure count, availability state, last error, and an interruptible backoff sleep. Healthy cadence stays at `BLE_POLL_INTERVAL`; failures use capped backoff `[30, 60, 120, 300]`. Offline is published once on transition (after `OFFLINE_AFTER_FAILURES` connectivity failures); online is published once on recovery. Retries continue forever. Tests cover backoff progression, single offline-on-transition, and online-on-recovery.

Owner repo: `ha-addons`.

Goal: reduce repeated offline spam and unnecessary BLE traffic while still detecting reconnection.

Implementation direction:

- Keep the normal healthy poll interval unless field evidence says otherwise.
- Track per-device failure count, last success, availability state, and retry delay.
- Publish offline only on transition to offline, not every failed retry.
- Use capped backoff, for example 30 seconds, 1 minute, 2 minutes, then 5 minutes max.
- Continue retrying forever while the device/integration is enabled.
- On successful poll, reset failure count/delay and publish online if state changed.
- Do not expose normal poll interval as a user-facing option in the first implementation.

Acceptance tests:

- Healthy device polls at normal cadence.
- Offline transition publishes one offline message.
- Continued failures do not republish offline every loop.
- Retry cadence backs off but continues.
- Device returning after long outage is detected and publishes online.

## B-5: `authenticate()` Always Reports Success

Status: Complete in branch `release-integration`. `MicroAirHandler.authenticate` now performs a cheap `Get Status` read after the password write: a reachable device returning no zone data raises `AuthenticationError` (credentials rejected), while no response raises `BleakError` (connectivity). The bridge surfaces `auth_failed` on the `last_error` topic and marks the device offline immediately, distinct from connectivity backoff; `AuthenticationError` is not retried at full speed inside `_execute_with_lock`. Test covers auth failure marking offline immediately with the `auth_failed` reason.

Owner repo: `ha-addons`.

Goal: surface wrong thermostat passwords as authentication failures.

Scope:

- `librecoach/librecoach_ble/devices/microair.py`
- BLE availability/error status topics.

Implementation direction:

- After password write, perform a cheap authenticated read.
- Validate the response shape or a known status field.
- On failure, publish `auth_failed` status and mark the device unavailable.
- Use B-4 retry backoff to avoid full-speed repeated auth attempts.
- Log auth failure distinctly from range/power/BLE timeout failures.

Acceptance tests:

- Correct password authenticates.
- Wrong password reports auth failure.
- Timeout reports connectivity failure, not auth failure.

## B-6: Micro-Air Dry Fan Mode Mapping

Status: ha-addons portion complete in branch `release-integration`. Node-RED companion (remove `dry` from climate discovery `modes`, drop optimistic dry-mode fan updates, regenerate flow artifacts) still required. ha-addons keeps `dry_fan_mode_num` as parsed/debug data only, now documented inline as protocol/debug data that must not drive an HA dry mode or fan control. The bridge sends no dry-mode commands.

Owner repos: `ha-addons` plus `librecoach-node-red`.

Decision: do not expose Micro-Air dry mode through Home Assistant for now. Dry mode is device-specific dehumidification behavior, not a normal thermostat mode with a confirmed fan-speed command/state contract. Keep dry-related raw parsing only as diagnostics/debugging until real device captures prove a safe HA behavior contract.

Evidence:

- Reference parser at `/home/ted/src/librecoach/ha_EasyTouchRV_MicroAir_MZ/custom_components/micro_air_easytouch_mz/micro_air_easytouch/parser.py` parses `fan_mode_num`, `cool_fan_mode_num`, `heat_fan_mode_num`, `auto_fan_mode_num`.
- Reference and current LibreCoach parsers duplicate `dry_fan_mode_num` at `info[9]`; this does not prove a distinct dry fan setting exists.
- Reference behavior is mixed: dry display reads `dry_fan_mode_num`, while dry mode-change paths send `coolFan`.
- Product decision: avoid exposing ambiguous dry-mode controls in HA.

ha-addons implementation direction:

- Keep raw/diagnostic dry fields if useful, but do not use them to create a HA dry mode or HA fan control.
- If parsed state still includes `dry_fan_mode_num`, document it as protocol/debug data only.
- Do not send dry-mode commands from HA.

Node-RED implementation direction:

- Do not advertise `dry` in Micro-Air climate discovery `modes`.
- Do not publish HA dry-mode fan state or accept dry-mode fan commands.
- Remove optimistic dry-mode fan updates.
- Regenerate flow artifacts using the repo's established flow-splitter workflow.

Reference commits to evaluate before or during implementation:

- `666b222` (2026-01-09): serialized BLE operations, persistent connection, queueing, immediate verification fallback.
- `c4fc63b` and nearby 2026-01-25 commits: startup zone config refresh and MAV fallback.
- `ecf58cb`, `72dbf1f`, `6852953`, `3480921`, `7e1d392` (2026-01-28 through 2026-02-02): auto/manual fan parsing, 128 auto capability, heat fan selection, manual speed fixes.
- `f3c4975` (2026-05-24): optional HVAC-mode target-temperature setting. Only bring this in if LibreCoach users need setting target temp mode other than current HVAC mode.

Acceptance tests:

- Home Assistant does not advertise `dry` in Micro-Air climate `modes`.
- HA cannot send Micro-Air dry-mode commands.
- Switching into or out of other modes does not create a misleading dry fan optimistic update.
- Auto mode still uses `auto_fan_mode_num`.
- Cool mode still uses `cool_fan_mode_num`.
- Any retained raw/debug state that includes duplicated dry fan data is documented as protocol/debug data, not HA control state.

## N-1: Missing Availability Topics

Status: Ready for implementation.

Owner repo: `librecoach-node-red`.

Goal: prevent stale Home Assistant entities from appearing healthy.

Scope:

- `src/tabs/status-routing/status_*.js`
- `src/tabs/victron/victron_create.js`
- `src/tabs/config/create_user_toggles.js`
- BLE/Micro-Air discovery functions as applicable.
- Generated `artifact/flows.json` and tab/function sidecars.

Implementation direction:

- Inventory all MQTT Discovery configs LibreCoach publishes.
- Add appropriate `availability_topic` entries for RV-C, Victron, BLE, and user-toggle entities.
- Use precise status topics where available: bridge/CAN status for CAN-derived entities, BLE availability for BLE entities, Victron status for Victron entities.
- If needed, publish simple derived status topics from Node-RED instead of depending on deferred V-5 JSON status.
- Publish retained availability messages on startup and shutdown/LWT where possible.
- Document topic ownership and expected payloads.

Acceptance tests:

- Add-on stop marks entities unavailable.
- Missing CAN interface marks CAN-derived entities unavailable/degraded if a usable CAN status topic exists.
- BLE offline marks BLE climate entities unavailable.
- Victron disconnected marks Victron entities unavailable.

## D-2: CRLF Strip Runs Over All Non-PNG Files

Status: Complete in branch `release-integration`. `librecoach/Dockerfile` CRLF strip now uses an explicit text-extension whitelist (`.sh .js .json .yaml .yml .md .txt .html .css .py .conf` plus extensionless s6 `run`/`finish`/`type`/`up` files) instead of "everything except .png". Unknown/future binary assets are no longer fed through `sed`.

Owner repo: `ha-addons`.

Goal: avoid corrupting future binary assets during build.

Scope:

- `librecoach/Dockerfile`

Implementation direction:

- Replace broad `find ... ! -name '*.png' ... sed` with a whitelist of text extensions.
- Include `.sh`, `.js`, `.json`, `.yaml`, `.yml`, `.md`, `.txt`, `.html`, `.css`.
- Leave binary unknown extensions untouched.
- Add or update `.gitattributes` in source repos if line-ending normalization should happen before build.

Acceptance tests:

- Known scripts have LF endings.
- Binary test fixture is unchanged by build.
- Existing PNG exclusion becomes unnecessary because binaries are not selected.

## F-4: Lovelace Strategy Dashboard

Status: In progress in branch `feature/f4-lovelace-dashboard`; Node-RED companion may be required.

Owner repo: current active branch is in `ha-addons`; any Node-RED entity metadata work belongs in `librecoach-node-red`.

Goal: provide a generated Home Assistant dashboard that adapts to detected LibreCoach devices.

ha-addons scope:

- Home Assistant dashboard strategy/generated Lovelace package if packaged from this add-on.
- Version dashboard template in the add-on.
- Document refresh/update behavior.

Node-RED scope:

- If the dashboard relies on labels, device metadata, or discovery attributes emitted by Node-RED, add those in `librecoach-node-red`.

Acceptance tests:

- Dashboard works with only CAN entities.
- Dashboard works when BLE/Victron are enabled.
- Missing hardware does not leave broken cards.

## F-6: BLE Offline Alerts And Recovery Controls

Status: ha-addons portion complete in branch `release-integration`. Node-RED companion (diagnostic entities + Tools buttons) still required. Bridge publishes retained per-device `last_success`, `failure_count`, and `last_error` (`none`/`auth_failed`/`connectivity`), and subscribes to `librecoach/ble/+/+/reconnect` (resets failures, drops the connection, retries immediately), `librecoach/ble/+/+/clear_errors` (clears failure/availability state), and `librecoach/ble/reset_locks` (B-3). Auth failure is distinct from connectivity in both `last_error` and the bridge status topic.

Owner repos: `ha-addons` plus `librecoach-node-red`.

Goal: make BLE outages visible and recoverable from Home Assistant.

ha-addons scope:

- Builds on B-3, B-4, and B-5.
- `librecoach/librecoach_ble/bridge.py`
- Publish per-device availability, last_success, failure_count, and last_error.
- Support command topics for reconnect, reset BLE locks, and clear failure state.

Node-RED scope:

- Create BLE diagnostic entities for availability, last_success, failure_count, and last_error.
- Add LibreCoach Tools buttons for reconnect/clear failure state where appropriate.
- Use B-3/BL-3 for the reset-locks button.
- Distinguish auth failure from offline/range/power failures in entity state or attributes.

Acceptance tests:

- BLE offline appears in HA.
- Manual reconnect schedules an immediate retry.
- Reset BLE locks button clears only persisted device locks.
- Auth failure is distinct from connectivity failure.

## V-6: Raw CAN Uses QoS 1

Status: Complete in branch `release-integration`. `can/raw` now publishes at QoS 0 in `can_bridge.py`; commands/statuses/config remain QoS 1. QoS policy documented in `mqtt_client.py.publish` and at the raw publish site.

Owner repo: `ha-addons`.

Goal: reduce MQTT broker overhead for high-rate raw CAN telemetry.

Scope:

- `librecoach/vehicle_bridge/mqtt_client.py`
- `librecoach/vehicle_bridge/can_bridge.py`

Implementation direction:

- Publish `can/raw` at QoS 0.
- Keep commands, statuses, and configuration topics at QoS 1.
- Document topic QoS policy in code comments or docs.

Acceptance tests:

- Node-RED still decodes live CAN frames.
- Command/status delivery still uses QoS 1.
- Broker CPU/load is not worse than before.
