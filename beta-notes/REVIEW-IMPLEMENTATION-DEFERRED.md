# LibreCoach Deferred Review Work

These items are intentionally outside the active work queue.

Review report baseline: tree as of June 9, 2026. Preserve the notes so future work can resume without re-triage.

## V-1: Filter Summary Computed But Not Logged

Status: Deferred.

Owner repo: `ha-addons`.

Goal: make configured DGN filtering visible in logs.

Reason to defer: low user impact unless field debugging needs filter visibility.

## V-2: Blocking `subprocess.run` In Async Stop

Status: Deferred.

Owner repo: `ha-addons`.

Goal: avoid blocking the event loop during shutdown.

Reason to defer: defensive shutdown reliability work; useful if add-on stops hang or leave CAN state messy, but not currently a high-priority user-facing issue.

## V-3: Silent CAN Payload Truncation

Status: Deferred.

Owner repo: `ha-addons`.

Goal: reject malformed outbound RV-C payloads clearly.

Reason to defer: important guardrail for malformed command payloads, but lower priority than BLE and HA usability work.

## V-4: GeoBridge Startup Blocks Bridge Startup

Status: Deferred.

Owner repo: `ha-addons`.

Goal: let the bridge report status and handle shutdown even when Home Assistant geo data is not ready.

Reason to defer: useful if GeoBridge delays startup or shutdown, but geo is not central to current user workflows.

## V-5: Missing Degraded-Mode Status

Status: Deferred; Node-RED companion deferred.

Owner repos: `ha-addons` plus `librecoach-node-red`.

Goal: expose per-module bridge health instead of a bare retained `online`.

Reason to defer: broader health/diagnostic work is deferred. N-1 can still add direct availability topics without depending on this JSON status model.

## N-4: Preserve Mode Never Refreshes `flows_cred.json`

Status: Deferred.

Owner repo: `ha-addons`.

Goal: preserve user flow edits while keeping required LibreCoach credentials current.

Reason to defer: only matters if `prevent_flow_updates` / preserve mode is an actively supported user workflow. If preserve mode is dev-only or rare, this can wait.

## D-1: Pin `librecoach-node-red` For Release Builds

Status: Deferred.

Owner repo: `ha-addons`.

Goal: keep development builds convenient while making published add-on images reproducible and traceable.

Reason to defer: useful release hygiene, but not necessary for current feature/handoff work.

## F-1: Coach Health Availability

Status: Deferred; Node-RED companion deferred.

Owner repos: `ha-addons` plus `librecoach-node-red`.

Goal: give users a clear health view and notifications when LibreCoach subsystems are disconnected or degraded.

Reason to defer: broad product feature that depends on several lower-level status contracts.

## F-2: CAN Bus Health Monitoring With Self-Healing

Status: Deferred; Node-RED companion deferred.

Owner repos: `ha-addons` plus `librecoach-node-red`.

Goal: detect CAN bus failures, expose useful diagnostics, and attempt conservative recovery.

Reason to defer: valuable but larger than current active queue.

## F-7: One-Click Diagnostics Bundle

Status: Deferred.

Owner repo: `ha-addons`.

Goal: create a safe support artifact without exposing secrets.

Reason to defer: supportability feature, not required for current BLE and HA entity work.

## F-8: Automation Blueprint Pack

Status: Deferred.

Owner repo: likely docs/add-on packaging; verify final packaging repo before implementation.

Goal: provide optional RV-specific Home Assistant blueprints after users configure devices.

Reason to defer: optional workflow feature after core entities and controls stabilize.

## F-10: Unknown-DGN Crowdsourcing Pipeline

Status: Deferred.

Owner repo: `ha-addons` for capture/diagnostics; docs/GitHub template repo may also be involved.

Goal: help users capture unknown RV-C traffic and submit useful decoder evidence.

Reason to defer: maintainer/community workflow feature, not current product-critical work.
