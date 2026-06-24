# LibreCoach Review Implementation Status

## Outstanding

Work that is not yet fully complete for the 2.0.0 release. The `ha-addons` portion of each item is
done in branch `release-integration` unless noted; what remains is mostly `librecoach-node-red`
companion work plus the in-progress Lovelace dashboard.

### F-4: Lovelace Strategy Dashboard

Status: In progress in branch `feature/f4-lovelace-dashboard`; Node-RED companion may be required.

Owner repo: `ha-addons` (active branch); any Node-RED entity metadata work belongs in
`librecoach-node-red`.

Goal: provide a generated Home Assistant dashboard that adapts to detected LibreCoach devices.

ha-addons scope:

- Home Assistant dashboard strategy/generated Lovelace package if packaged from this add-on.
- Version dashboard template in the add-on.
- Document refresh/update behavior.

Node-RED scope:

- If the dashboard relies on labels, device metadata, or discovery attributes emitted by Node-RED,
  add those in `librecoach-node-red`.

Acceptance tests:

- Dashboard works with only CAN entities.
- Dashboard works when BLE/Victron are enabled.
- Missing hardware does not leave broken cards.

---

## Deferred

Intentionally outside the active work queue. Preserve so future work can resume without re-triage.

### V-1: Filter Summary Computed But Not Logged

Owner repo: `ha-addons`. Goal: make configured DGN filtering visible in logs.
Reason to defer: low user impact unless field debugging needs filter visibility.

### V-2: Blocking `subprocess.run` In Async Stop

Owner repo: `ha-addons`. Goal: avoid blocking the event loop during shutdown.
Reason to defer: defensive shutdown reliability; useful if stops hang or leave CAN state messy.

### V-3: Silent CAN Payload Truncation

Owner repo: `ha-addons`. Goal: reject malformed outbound RV-C payloads clearly.
Reason to defer: important guardrail, but lower priority than BLE and HA usability work.

### V-4: GeoBridge Startup Blocks Bridge Startup

Owner repo: `ha-addons`. Goal: let the bridge report status and handle shutdown even when Home
Assistant geo data is not ready.
Reason to defer: useful if GeoBridge delays startup/shutdown, but geo is not central to current workflows.

### V-5: Missing Degraded-Mode Status

Owner repos: `ha-addons` plus `librecoach-node-red`. Goal: expose per-module bridge health instead
of a bare retained `online`.
Reason to defer: broader health/diagnostic work is deferred. N-1 can still add direct availability
topics without depending on this JSON status model.

### N-4: Preserve Mode Never Refreshes `flows_cred.json`

Owner repo: `ha-addons`. Goal: preserve user flow edits while keeping required LibreCoach
credentials current.
Reason to defer: only matters if `prevent_flow_updates` / preserve mode is an actively supported
user workflow.

### F-1: Coach Health Availability

Owner repos: `ha-addons` plus `librecoach-node-red`. Goal: give users a clear health view and
notifications when LibreCoach subsystems are disconnected or degraded.
Reason to defer: broad product feature that depends on several lower-level status contracts.

### F-2: CAN Bus Health Monitoring With Self-Healing

Owner repos: `ha-addons` plus `librecoach-node-red`. Goal: detect CAN bus failures, expose
diagnostics, and attempt conservative recovery.
Reason to defer: valuable but larger than current active queue.

### F-7: One-Click Diagnostics Bundle

Owner repo: `ha-addons`. Goal: create a safe support artifact without exposing secrets.
Reason to defer: supportability feature, not required for current BLE and HA entity work.

### F-8: Automation Blueprint Pack

Owner repo: docs/add-on packaging (verify final packaging repo). Goal: provide optional RV-specific
Home Assistant blueprints after users configure devices.
Reason to defer: optional workflow feature after core entities and controls stabilize.

### F-10: Unknown-DGN Crowdsourcing Pipeline

Owner repo: `ha-addons` for capture/diagnostics; docs/GitHub template repo may also be involved.
Goal: help users capture unknown RV-C traffic and submit useful decoder evidence.
Reason to defer: maintainer/community workflow feature, not current product-critical work.

---

## Completed (shipped in 2.0.0)

Implemented in branch `release-integration` unless noted. Retained as a reference index; full
acceptance-test detail was dropped when the per-status files were consolidated.

- **N-1** — Missing availability topics: `availability_topic` entries added for RV-C, Victron, BLE, and user-toggle entities in `librecoach-node-red`; retained availability published on startup/LWT.
- **B-3 / BL-3** — BLE Reset Tool (Node-RED companion): "Forget BLE Devices" button added to LibreCoach Tools; publishes `librecoach/ble/reset_locks`; clears device locks without affecting credentials or enabled flags.
- **B-6** — Micro-Air Dry Fan Mode Mapping (Node-RED companion): `dry` removed from climate discovery `modes`; dry-mode fan state and commands not published or accepted; no optimistic dry updates.
- **F-6** — BLE Offline Alerts And Recovery Controls (Node-RED companion): BLE diagnostic entities for availability, last_success, failure_count, and last_error added; reconnect/clear-errors buttons in LibreCoach Tools; auth failure distinguished from connectivity failure.
- **D-1** — Pin `librecoach-node-red` for release builds (reproducible image from pinned commit).
- **C-1** — `set -e` made effective; startup failures now abort deterministically.
- **C-2** — Node-RED `credential_secret` backup preserved across restarts and migrated from old path.
- **C-3** — MQTT auth args handle whitespace and shell metacharacters.
- **C-4** — `settings.js` credential injection no longer corrupts on special characters; newlines rejected.
- **C-5** — Edited Node-RED flows backed up before LibreCoach overwrite; `prevent_flow_updates` honored.
- **C-7** — BLE `configuration.yaml` cleanup gated on healthy Supervisor + confirmed absence; backup first.
- **C-8** — Missing MQTT integration pauses setup without watchdog crash loop.
- **B-1** — Single BLE advertisement callback iterating handlers.
- **B-2** — BLE publish path decoupled from Micro-Air zone shape (`StateMessage` contract).
- **B-3 / BL-3** — ha-addons reset-locks command topic (Node-RED button outstanding above).
- **B-4** — BLE poll backoff and offline-on-transition publishing.
- **B-5** — Micro-Air `authenticate()` surfaces wrong-password auth failures distinctly.
- **B-6** — ha-addons keeps dry fields debug-only, sends no dry commands (Node-RED outstanding above).
- **D-2** — Dockerfile CRLF strip uses a text-extension whitelist instead of "everything but .png".
- **F-6** — ha-addons publishes BLE diagnostics + recovery command topics (Node-RED entities outstanding above).
- **V-6** — `can/raw` published at QoS 0; commands/statuses/config remain QoS 1.

> Note: **C-6** (Node-RED readiness publisher) was tracked in
> `librecoach-node-red/REVIEW-IMPLEMENTATION-PLANNED.md`; verify its status in that repo.
