# LibreCoach Completed Review Work

These items are implemented in separate branch `release-integration` unless noted. Verify before merge/release. C-6 is not listed here because its Node-RED readiness publisher remains planned in `/home/ted/src/librecoach/librecoach-node-red/REVIEW-IMPLEMENTATION-PLANNED.md`.

Review report baseline: tree as of June 9, 2026.

## C-1: `set -e` Is Inert

Status: Complete in branch `release-integration`.

Owner repo: `ha-addons`.

Goal: make startup failures fail deterministically instead of continuing in partial deployment state.

Acceptance tests:

- Missing bundled Node-RED project aborts startup with a clear log.
- Invalid JSON for Supervisor option updates aborts startup.
- Forced `openssl` failure does not leave silently corrupted `flows_cred.json`.

## C-2: Node-RED `credential_secret` Backup Can Be Destroyed

Status: Complete in branch `release-integration`.

Owner repo: `ha-addons`.

Goal: preserve the user's original Node-RED `credential_secret` across all LibreCoach restarts.

Acceptance tests:

- First takeover creates `/data/.backup_credential_secret`.
- Second restart does not overwrite the backup.
- Existing old-path backup under `/share/.librecoach/` is migrated once.
- Restore instructions still decrypt the user's original pre-LibreCoach `flows_cred.json`.

## C-3: MQTT Auth Args Break With Whitespace

Status: Complete in branch `release-integration`.

Owner repo: `ha-addons`.

Goal: support valid MQTT usernames and passwords without shell word splitting.

Acceptance tests:

- MQTT password containing spaces works.
- MQTT password containing shell metacharacters works.
- No-auth mode still works with an empty auth array.

## C-4: `sed` Credential Injection Corrupts `settings.js`

Status: Complete in branch `release-integration`.

Owner repo: `ha-addons`.

Goal: inject MQTT credentials into deployed Node-RED `settings.js` without replacement corruption.

Acceptance tests:

- Passwords containing `|`, `&`, backslash, quotes, spaces, and dollar signs do not corrupt `settings.js`.
- Passwords containing newlines produce a clear validation error.

## C-5: Intentional Node-RED Flow Overwrite

Status: Complete in branch `release-integration`.

Owner repo: `ha-addons`.

Goal: keep LibreCoach-owned flow overwrite as the default product model while reducing surprise when users edit Node-RED directly.

Acceptance tests:

- Normal LibreCoach update still refreshes flows.
- Edited flows are backed up before overwrite.
- `prevent_flow_updates` still prevents flow replacement.

## C-7: BLE Integration Cleanup Can Edit `configuration.yaml` Too Aggressively

Status: Complete in branch `release-integration`.

Owner repo: `ha-addons`.

Goal: prevent destructive cleanup when Supervisor responses are incomplete during startup/update.

Acceptance tests:

- Empty add-on list does not trigger cleanup.
- Healthy Supervisor plus repeated confirmed absence can still clean up.
- Backup is created before any `configuration.yaml` edit.

## C-8: MQTT Integration Gate Crash Loop

Status: Complete in branch `release-integration`.

Owner repo: `ha-addons`.

Goal: pause setup without causing Supervisor watchdog restarts.

Acceptance tests:

- Missing MQTT integration no longer produces an add-on crash loop.
- Installing/configuring MQTT while waiting resumes setup.
- Watchdog is enabled only after successful setup.
