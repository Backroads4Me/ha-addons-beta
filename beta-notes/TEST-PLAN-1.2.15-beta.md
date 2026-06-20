# LibreCoach 1.2.15-beta — Release Test Plan

Everything to verify for the 1.2.15 beta cycle in a **test** Home Assistant instance. Each section
says **where to look in Home Assistant, what you should actually see, and how to tell it passed** —
not just the underlying technical change.

Released together from two repos:
- **ha-addons / librecoach** — startup hardening, BLE bridge hardening + new **Hughes Power
  Watchdog** device, Micro-Air parsing, vehicle/geo bridge.
- **librecoach-node-red** (`main`, merged this cycle) — Node-RED readiness (C-6), per-source
  availability (N-1), BLE recovery (F-6), generator refinements, Victron keep-alive, Micro-Air
  climate, Hughes flow.

> Beta images use the `-beta` suffix and install **side by side** with production. LibreCoach
> entities are grouped into **devices** under *Settings → Devices & Services → Devices* (e.g.
> **Generator**, **Hughes Autoformers**, tanks, climates), all with manufacturer **LibreCoach**.

---

## Pre-test setup

1. **Confirm the build:** GitHub Actions on `ha-addons-beta` built the `-beta` image for 1.2.15.
2. **Install:** in the test HA, add/refresh the **beta** repository and install/upgrade **LibreCoach
   (beta)** to **1.2.15**. Keep production LibreCoach stopped to avoid CAN/MQTT contention.
3. **Open three things and keep them visible:**
   - **Addon log:** *Settings → Add-ons → LibreCoach (beta) → Log.*
   - **Devices list:** *Settings → Devices & Services → Devices*, filtered to **LibreCoach**.
   - **(Optional) MQTT Explorer** for topic-level confirmation: `librecoach/nodered/ready`,
     `librecoach/nodered/status`, `can/status`, `librecoach/ble/#`.
4. Mark anything you can't physically exercise (no generator, no Hughes unit, etc.) as **N/A**.

---

## 1. Startup hardening (C-1 … C-8)

**What you'll see:** a clean, readable startup in the addon **Log**, and the addon recovering
gracefully instead of crash-looping when something is wrong.

| # | Do this | What you should see | Pass |
|---|---|---|---|
| 1.1 | Set a deliberately bad `mqtt_pass`, restart | Log prints a **clear error and stops** at that step — not a wall of cascading errors or a half-started addon | ☐ |
| 1.2 | Restart the addon several times | Node-RED flows keep their saved credentials every time; Log shows the `credential_secret` backup being **found/migrated**, never "regenerating" repeatedly | ☐ |
| 1.3 | Set `mqtt_user`/`mqtt_pass` with spaces & symbols (e.g. `my user`, `p@ss word!`) | Addon still connects to MQTT; entities populate. A password with an actual newline is **rejected with a clear message** | ☐ |
| 1.5 | Hand-edit a flow in Node-RED, then restart addon | Before overwrite, a backup folder appears at `/config/librecoach-backups/<timestamp>/`; any extra npm packages you added are still installed | ☐ |
| 1.7 | (Only if testing BLE cleanup) | Cleanup does **not** fire immediately — it needs a healthy Supervisor and repeated confirmations over hours; `configuration.yaml` is backed up first | ☐ |
| 1.8 | Remove/disable the MQTT integration, start addon | Addon **stays running** and keeps polling instead of crash-looping; when you re-add MQTT it **resumes automatically** | ☐ |

## 2. Node-RED readiness — the headline fix (C-6)

**What you'll see in the Log:** during startup, after "Node-RED port is open" you should see
**`LibreCoach flows are ready`** — meaning the addon waited for the flows to truly come up, not
just for the port. You should **not** see the fallback warning `…no readiness message on
librecoach/nodered/ready after 90s`.

- ☐ Log shows **"LibreCoach flows are ready"** (the success path), within a few seconds — not the 90s timeout fallback.
- ☐ Entities appear reliably on first boot (no missing entities that only show up after a second restart — the race this fix targets).
- ☐ Restart Node-RED/addon: readiness is re-announced and entities re-populate.
- *(MQTT check, optional:* retained `librecoach/nodered/ready` holds JSON with `ready`, `version`, `updated_at`.)*

## 3. Per-source availability (N-1) — applies to EVERY entity

**What you'll see:** when a data source drops, the affected LibreCoach entities go **"Unavailable"**
in HA (greyed out, dashboard cards show *Unavailable*) instead of silently showing a stale last
value. When the source returns they go **available** again.

- ☐ Disconnect/stop the **CAN** source (or publish `can/status` offline): RV-C entities across
  several devices flip to **Unavailable** — check a **spread** of types (a tank, a climate, a DC
  load, generator), not just one.
- ☐ Stop **Node-RED**: entities flip to **Unavailable** (they depend on `librecoach/nodered/status`).
- ☐ Restore each source: entities return to **available** with live values.
- ☐ No entity is stuck permanently Unavailable after a normal restart.

> This change touched every status publisher (tanks, furnace, lock, panel signal, solar, water
> heater, AquaHot, DC loads/dimmers, thermostat, water pump, autofill, battery, AC load, floor
> heat, shade, generator). Spot-check a variety so a single passing entity isn't mistaken for all.

## 4. Generator (RV-C)

**Where:** the **Generator** device. **What you'll see** while the generator runs vs. off:

- ☐ A **"Generator Running"** binary sensor now shows **On/Off** correctly (including a real *Off* —
  previously it never appeared as its own entity).
- ☐ New **"Generator Demand"** sensor and **"Generator Demand Active"** binary sensor appear and
  track whether the system is calling for the generator.
- ☐ **"Generator Coolant Temp"** shows the **real temperature in °F** while running — **~160 °F is
  normal/expected**. It should no longer read a flat **0** when idle. ⚠️ Note: this entity is only
  **created the first time** coolant rises above **100 °F**, so on a stone-cold start it may not
  appear until the engine warms — that's intended.
- ☐ Stopping/no-demand actually stops the genset (regression check on the demand-byte fix).
- ☐ Quiet-time and fault sensors still report.

## 5. Micro-Air thermostat (BLE + climate)

**Where:** the Micro-Air **climate** entity / thermostat card.

- ☐ The thermostat card shows the correct **mode** and any **fault** state accurately as you change modes.
- ☐ Changing setpoint/mode on the card takes effect; the card updates **immediately** (optimistic),
  then settles to the device's reported state.
- ☐ Heat-source presets still work and survive an off→on cycle.

## 6. BLE recovery controls (F-6)

**Where:** BLE recovery control(s) surfaced in HA (button/switch on the relevant BLE device).

- ☐ Power-cycle or move a BLE device out of range so it drops, then **trigger recovery** from HA —
  the device **reconnects without restarting the whole addon**.
- ☐ No tight reconnect crash-loop in the Log during the drop.

## 7. Hughes Power Watchdog (NEW — surge protector / power monitor)

**Requires a Hughes Power Watchdog** (V1 models `PMD/PWS/PMS`, or V2 `WD_*`). Set
`hughes_enabled: true` in the addon **Configuration** tab, save, restart.

**Where:** a new **"Hughes Autoformers"** device. **What you'll see:**

- ☐ With `hughes_enabled` **off**: **no** Hughes entities exist.
- ☐ With it **on**: the unit connects (see Log), and you get live electrical entities such as
  **Output Voltage**, current, power, energy, and **Combined Shore Power** — values track real load.
- ☐ Any supported controls (e.g. energy reset / relay) work from HA.
- ☐ Booster models (`V8/E8/V9/E9`) are recognized if you have one.

## 8. Victron

**Where:** the Victron device(s).

- ☐ Victron entities stay **live and available** over time — the keep-alive should prevent them
  going stale/Unavailable during a quiet period.
- ☐ Values decode correctly.

## 9. Vehicle / Geo bridge

- ☐ `can/status` reflects the CAN link (drives §3 availability).
- ☐ If `geo_enabled`: a device-tracker/position updates within the configured threshold.

## 10. Config toggles

**Where:** addon **Configuration** tab.

- ☐ **`rvc_time_sync_enabled`** is present and works (time-sync broadcast on/off).
- ☐ **`hughes_enabled`** is present and gates §7.
- ☐ Existing toggles unchanged: `microair_enabled`, `victron_enabled`, `beta_enabled`,
  `confirm_nodered_takeover`, `prevent_flow_updates`, `debug_logging`.

## 11. Regression smoke test

**Where:** browse the LibreCoach devices and your existing dashboard.

- ☐ Existing entities still report and control: tanks, thermostats/climate, AquaHot zones, solar
  controller, DC dimmers/loads, water pump/autofill, locks, shades, floor heat.
- ☐ No duplicate-named entities; nothing stuck Unavailable after a clean start.
- ☐ Entity export / AI dashboard prompt export still works.

---

## Sign-off

- ☐ All non-N/A items pass in the test HA instance.
- ☐ Addon Log is clean of unexpected errors across start → run → restart.
- ☐ Decision recorded: promote to production (`ha-addons`) or iterate.
