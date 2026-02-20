# Plan: LibreCoach BLE Integration (Generic Bluetooth Bridge)

## Goal

Build a generic BLE-to-MQTT bridge as an HA custom integration that the add-on
installs automatically. MicroAir EasyTouch is the first device handler, but the
architecture supports adding other BLE devices (OneControl, Truma, etc.) later.

Users install the add-on and it just works — no HACS, no GitHub account.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  LibreCoach Add-on Container                        │
│                                                     │
│  run.sh (orchestrator)                              │
│    Phase 1.5: Install librecoach_ble integration    │  ← NEW
│               Write config to /config/              │
│                                                     │
│  vehicle_bridge/main.py (s6 service)                │
│    - CanBridge (CAN → MQTT)                         │
│    - MicroAirBridge REMOVED                         │  ← CHANGED
│                                                     │
│  /opt/librecoach_ble/  (bundled integration files)  │  ← NEW
│                                                     │
└──────────────┬──────────────────────────────────────┘
               │ copies to /config/custom_components/
               ▼
┌─────────────────────────────────────────────────────┐
│  Home Assistant Core                                │
│                                                     │
│  custom_components/librecoach_ble/                  │
│    __init__.py          ← integration entry point   │
│    const.py             ← shared constants          │
│    bridge.py            ← generic BLE-MQTT manager  │
│    manifest.json                                    │
│    devices/                                         │
│      __init__.py        ← device registry           │
│      base.py            ← abstract base class       │
│      microair.py        ← MicroAir handler+parser   │
│      (future: onecontrol.py, truma.py, etc.)        │
│                                                     │
│  HA Bluetooth Integration                           │
│    Routes BLE through best adapter/proxy auto       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## File Structure

```
ha-addons-beta/librecoach/
├── librecoach_ble/                    ← NEW directory (bundled integration)
│   ├── __init__.py                    ← integration entry point
│   ├── manifest.json                  ← HA integration manifest
│   ├── const.py                       ← shared constants, MQTT topic templates
│   ├── bridge.py                      ← generic BLE-MQTT bridge manager
│   └── devices/
│       ├── __init__.py                ← device handler registry
│       ├── base.py                    ← abstract base class for device handlers
│       └── microair.py               ← MicroAir EasyTouch (protocol + parser)
├── config.yaml                        ← MODIFIED (add config:rw)
├── Dockerfile                         ← MODIFIED (bundle integration, drop dbus-next)
├── run.sh                             ← MODIFIED (add Phase 1.5)
└── vehicle_bridge/
    ├── main.py                        ← MODIFIED (remove MicroAir import)
    └── microair_bridge.py             ← DELETE (replaced by integration)
```

---

## Detailed File Specifications

### 1. `librecoach_ble/const.py`

Shared constants used across the integration.

```python
DOMAIN = "librecoach_ble"
CONFIG_PATH = "/config/.librecoach-ble-config.json"

# Base MQTT topic prefix — device handlers build on this
MQTT_BASE = "librecoach/ble"

# Topic templates (handlers fill in {device_type} and {address})
#   e.g. "librecoach/ble/microair/78:e3:6d:fc:5e:ce/state"
TOPIC_STATE     = MQTT_BASE + "/{device_type}/{address}/state"
TOPIC_SET       = MQTT_BASE + "/{device_type}/{address}/set"
TOPIC_AVAILABLE = MQTT_BASE + "/{device_type}/{address}/available"
TOPIC_BRIDGE    = "librecoach/bridge/{device_type}/{address}"
```

---

### 2. `librecoach_ble/devices/base.py` — Abstract base class

Defines the contract every device handler must implement.

```python
from abc import ABC, abstractmethod

class BleDeviceHandler(ABC):
    """Base class for LibreCoach BLE device handlers."""

    # --- Class-level attributes (set by each subclass) ---

    @staticmethod
    @abstractmethod
    def device_type() -> str:
        """Short identifier used in MQTT topics. e.g. 'microair'"""

    @staticmethod
    @abstractmethod
    def match_name(name: str) -> bool:
        """Return True if the BLE advertisement name belongs to this handler.
        Called during device discovery.
        Example: name.startswith("EasyTouch")
        """

    # --- Instance methods ---

    @abstractmethod
    async def poll(self, client) -> dict | None:
        """Connect, authenticate, read status.
        `client` is a connected BleakClient.
        Return parsed state dict, or None on failure.
        """

    @abstractmethod
    async def handle_command(self, client, command: dict) -> bool:
        """Handle an inbound MQTT command.
        `client` is a connected BleakClient.
        `command` is the parsed JSON from the MQTT /set topic.
        Return True on success.
        """

    @abstractmethod
    def parse_status(self, raw: dict) -> dict:
        """Parse raw device JSON into the state dict published to MQTT.
        Pure function — no BLE or async needed.
        """
```

**Design notes:**
- `client` is a connected `BleakClient` passed in by the bridge manager.
  The handler does NOT manage connections — the bridge does.
- `match_name()` is a static/class method used during discovery to route
  advertisements to the right handler.
- Handlers are stateless per-call. Persistent state (zone configs, auth status)
  lives on the handler instance, which the bridge creates once per device.

---

### 3. `librecoach_ble/devices/__init__.py` — Device handler registry

```python
"""Device handler registry.

To add a new device type:
1. Create a new module in this directory (e.g. onecontrol.py)
2. Implement a class that extends BleDeviceHandler
3. Import and add it to DEVICE_HANDLERS below
"""
from .microair import MicroAirHandler

# All registered device handlers — bridge iterates this for discovery matching
DEVICE_HANDLERS = [
    MicroAirHandler,
]
```

Adding a future device = create the file, add one import line here. That's it.

---

### 4. `librecoach_ble/devices/microair.py` — MicroAir handler

This file contains everything MicroAir-specific:
- BLE protocol (UUIDs, authentication, read/write pattern)
- Status parser (copied from stable `microair_bridge.py` lines 521-618)
- Command builder
- Constants (mode maps, fan maps, heat type maps)

```python
import json
import asyncio
import logging
from .base import BleDeviceHandler

_LOGGER = logging.getLogger(__name__)

# --- MicroAir-specific constants ---

UUIDS = {
    "service":     "000000ff-0000-1000-8000-00805f9b34fb",
    "passwordCmd": "0000dd01-0000-1000-8000-00805f9b34fb",
    "jsonCmd":     "0000ee01-0000-1000-8000-00805f9b34fb",
    "jsonReturn":  "0000ff01-0000-1000-8000-00805f9b34fb",
}

MODE_NUM_TO_MODE = {
    0: "off", 1: "fan_only", 2: "cool", 3: "heat", 4: "heat",
    5: "heat", 6: "dry", 7: "heat", 8: "auto", 9: "auto",
    10: "auto", 11: "auto", 12: "heat",
}

HEAT_TYPE_REVERSE = {
    5: "Heat Pump", 4: "Furnace", 3: "Gas Furnace",
    7: "Heat Strip", 12: "Electric Heat",
}

FAN_MODE_MAP = {0: "off", 1: "low", 2: "high", 3: "medium", 128: "auto"}


class MicroAirHandler(BleDeviceHandler):

    def __init__(self, address, config):
        self.address = address
        self._password = (config.get("microair_password") or "").strip()
        self._email = (config.get("microair_email") or "").strip()
        self._authenticated = False
        self._zone_configs = {}    # populated by _fetch_zone_config on first poll
        self._zone_config_fetched = False

    @staticmethod
    def device_type() -> str:
        return "microair"

    @staticmethod
    def match_name(name: str) -> bool:
        return name.startswith("EasyTouch")

    async def poll(self, client) -> dict | None:
        """Authenticate, fetch zone config (once), send Get Status, read and parse."""
        # 1. Authenticate (password write to passwordCmd)
        if self._password and not self._authenticated:
            await client.write_gatt_char(
                UUIDS["passwordCmd"],
                self._password.encode("utf-8"),
                response=True,
            )
            await asyncio.sleep(1.0)
            self._authenticated = True

        # 2. Fetch zone configs on first successful connection
        #    Zone configs (MAV, FA, SPL, MA) tell us how many zones exist
        #    and their min/max temp limits. They don't change at runtime.
        if not self._zone_config_fetched:
            await self._fetch_zone_config(client)

        # 3. Write command to jsonCmd
        cmd = json.dumps({"Type": "Get Status"}).encode("utf-8")
        await client.write_gatt_char(UUIDS["jsonCmd"], cmd, response=True)

        # 4. Wait, then read response from jsonReturn (DIFFERENT characteristic)
        await asyncio.sleep(1.0)
        result = await client.read_gatt_char(UUIDS["jsonReturn"])
        if not result:
            return None

        raw = json.loads(bytes(result).decode("utf-8"))
        return self.parse_status(raw)

    async def _fetch_zone_config(self, client) -> None:
        """Fetch zone configuration (MAV, FA, SPL, MA) from the device.

        Called once on first successful connection. Results are cached on the
        instance and reused for all subsequent polls and commands.

        Zone config fields:
        - MAV: max available zones (determines which zones to poll)
        - FA:  zone feature availability flags
        - SPL: setpoint limits (min/max temps per zone)
        - MA:  mode availability per zone

        See stable microair_bridge.py _parse_zone_configs() for the parsing logic.
        """
        try:
            cmd = json.dumps({"Type": "Get Config"}).encode("utf-8")
            await client.write_gatt_char(UUIDS["jsonCmd"], cmd, response=True)
            await asyncio.sleep(1.0)
            result = await client.read_gatt_char(UUIDS["jsonReturn"])
            if result:
                config_data = json.loads(bytes(result).decode("utf-8"))
                # Parse MAV, SPL, etc. and store in self._zone_configs
                # Copy parsing logic from stable microair_bridge.py
                self._zone_configs = config_data
                self._zone_config_fetched = True
                _LOGGER.info("Fetched zone config for %s: %d zones",
                             self.address, config_data.get("MAV", 1))
        except Exception as exc:
            _LOGGER.warning("Failed to fetch zone config for %s: %s",
                            self.address, exc)
            # Will retry on next poll cycle

    async def handle_command(self, client, command: dict) -> bool:
        """Write a command dict to the device."""
        if self._password and not self._authenticated:
            await client.write_gatt_char(
                UUIDS["passwordCmd"],
                self._password.encode("utf-8"),
                response=True,
            )
            await asyncio.sleep(1.0)
            self._authenticated = True

        cmd_bytes = json.dumps(command).encode("utf-8")
        await client.write_gatt_char(UUIDS["jsonCmd"], cmd_bytes, response=True)
        return True

    def parse_status(self, status: dict) -> dict:
        """Parse EasyTouch JSON status into zones with readable state."""
        # (Copy _parse_status + _select_fan_mode from stable microair_bridge.py)
        # See ha-addons/librecoach/vehicle_bridge/microair_bridge.py lines 521-618
        # Returns: {"available_zones": [0], "zones": {0: {...zone_state...}}}
        ...
```

**CRITICAL BLE protocol note for the junior dev:**
- Write command → `jsonCmd` characteristic (0000ee01)
- Read response → `jsonReturn` characteristic (0000ff01)
- These are DIFFERENT characteristics. Do NOT try to read the response from
  the write return value — that's just a BLE ACK.
- Must `await asyncio.sleep(1.0)` between write and read to give the device
  time to prepare its response.

---

### 5. `librecoach_ble/bridge.py` — Generic BLE-MQTT bridge manager

This is the core orchestrator. It:
- Discovers BLE devices via HA Bluetooth advertisements
- Matches them to device handlers
- Manages poll loops per device
- Publishes state to MQTT
- Subscribes to MQTT commands and routes them to handlers

```python
import asyncio
import json
import logging

from bleak_retry_connector import establish_connection, BleakClientWithServiceCache
from homeassistant.components.bluetooth import (
    async_ble_device_from_address,
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothServiceInfoBleak,
    async_register_callback,
)
from homeassistant.core import HomeAssistant

from .const import TOPIC_STATE, TOPIC_SET, TOPIC_AVAILABLE, TOPIC_BRIDGE
from .devices import DEVICE_HANDLERS

_LOGGER = logging.getLogger(__name__)

class BleBridgeManager:
    """Manages discovered BLE devices, their poll loops, and MQTT communication."""

    def __init__(self, hass: HomeAssistant, config: dict):
        self.hass = hass
        self.config = config
        self._active_devices = {}   # address -> {"handler": ..., "task": ...}
        self._cancel_callbacks = []
        self._stopping = False

    async def start(self):
        """Register BLE advertisement callbacks for all device handlers."""
        for handler_class in DEVICE_HANDLERS:
            # Register a callback for each handler's BLE name pattern
            cancel = async_register_callback(
                self.hass,
                self._on_ble_advertisement,
                BluetoothCallbackMatcher(
                    connectable=True,
                ),
                BluetoothChange.ADVERTISEMENT,
            )
            self._cancel_callbacks.append(cancel)

        # Subscribe to MQTT command topics
        # Uses wildcard: librecoach/ble/+/+/set
        await self.hass.components.mqtt.async_subscribe(
            "librecoach/ble/+/+/set",
            self._on_mqtt_command,
            qos=1,
        )

    async def stop(self):
        """Cancel all poll loops and callbacks."""
        self._stopping = True
        for cancel in self._cancel_callbacks:
            cancel()
        for address, entry in self._active_devices.items():
            entry["task"].cancel()
            try:
                await entry["task"]
            except asyncio.CancelledError:
                pass

    def _on_ble_advertisement(
        self,
        service_info: BluetoothServiceInfoBleak,
        change: BluetoothChange,
    ) -> None:
        """Called when HA sees a BLE advertisement."""
        name = service_info.name or ""
        address = service_info.address.lower()

        if address in self._active_devices:
            return  # Already tracking

        # Find matching handler
        for handler_class in DEVICE_HANDLERS:
            if handler_class.match_name(name):
                _LOGGER.info(
                    "Discovered %s device: %s (%s)",
                    handler_class.device_type(), address, name,
                )
                handler = handler_class(address, self.config)
                task = self.hass.async_create_task(
                    self._poll_loop(handler, address)
                )
                self._active_devices[address] = {
                    "handler": handler,
                    "task": task,
                }
                return

    async def _poll_loop(self, handler, address: str):
        """Poll a device at regular intervals, publish state to MQTT."""
        device_type = handler.device_type()
        poll_interval = int(self.config.get("ble_scan_interval", 30))
        failure_count = 0

        while not self._stopping:
            try:
                # Get BLE device from HA (picks best adapter/proxy automatically)
                ble_device = async_ble_device_from_address(
                    self.hass, address, connectable=True
                )
                if not ble_device:
                    raise Exception(f"BLE device {address} not available")

                # Connect via Bleak (routed through best proxy)
                client = await establish_connection(
                    BleakClientWithServiceCache,
                    ble_device,
                    address,
                    timeout=20.0,
                )

                try:
                    parsed = await handler.poll(client)
                finally:
                    await client.disconnect()

                if not parsed:
                    raise Exception("No status response")

                # Publish each zone state to MQTT
                zones = parsed.get("zones", {})
                for zone_num, zone_state in zones.items():
                    zone_state["zone"] = zone_num
                    topic = TOPIC_STATE.format(
                        device_type=device_type, address=address
                    )
                    await self.hass.components.mqtt.async_publish(
                        topic, json.dumps(zone_state), qos=1, retain=False
                    )

                # Mark online
                failure_count = 0
                await self.hass.components.mqtt.async_publish(
                    TOPIC_AVAILABLE.format(
                        device_type=device_type, address=address
                    ),
                    "online", qos=1, retain=True,
                )
                await self.hass.components.mqtt.async_publish(
                    TOPIC_BRIDGE.format(
                        device_type=device_type, address=address
                    ),
                    "connected", qos=1, retain=True,
                )

            except Exception as exc:
                failure_count += 1
                _LOGGER.warning(
                    "%s poll failed for %s (count %d): %s",
                    device_type, address, failure_count, exc,
                )
                handler._authenticated = False  # Force re-auth on reconnect

                if failure_count >= 10:
                    await self.hass.components.mqtt.async_publish(
                        TOPIC_AVAILABLE.format(
                            device_type=device_type, address=address
                        ),
                        "offline", qos=1, retain=True,
                    )
                    await self.hass.components.mqtt.async_publish(
                        TOPIC_BRIDGE.format(
                            device_type=device_type, address=address
                        ),
                        "disconnected", qos=1, retain=True,
                    )

            await asyncio.sleep(poll_interval)

    async def _on_mqtt_command(self, msg):
        """Handle inbound MQTT commands on librecoach/ble/+/+/set."""
        # Parse topic: librecoach/ble/{device_type}/{address}/set
        parts = msg.topic.split("/")
        if len(parts) < 5:
            return
        address = parts[3].lower()

        entry = self._active_devices.get(address)
        if not entry:
            _LOGGER.warning("Command for unknown device: %s", address)
            return

        handler = entry["handler"]

        try:
            command = json.loads(msg.payload)
        except (json.JSONDecodeError, TypeError):
            _LOGGER.warning("Invalid command payload: %s", msg.payload)
            return

        try:
            ble_device = async_ble_device_from_address(
                self.hass, address, connectable=True
            )
            if not ble_device:
                _LOGGER.warning("BLE device %s not available for command", address)
                return

            client = await establish_connection(
                BleakClientWithServiceCache,
                ble_device,
                address,
                timeout=20.0,
            )
            try:
                await handler.handle_command(client, command)
            finally:
                await client.disconnect()

        except Exception as exc:
            _LOGGER.warning("Command failed for %s: %s", address, exc)
```

---

### 6. `librecoach_ble/__init__.py` — Integration entry point

```python
"""LibreCoach BLE Bridge — generic Bluetooth-to-MQTT bridge for RV devices."""
import json
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, CONFIG_PATH
from .bridge import BleBridgeManager

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up LibreCoach BLE from configuration.yaml."""
    # Read config written by the add-on
    try:
        conf = json.loads(Path(CONFIG_PATH).read_text())
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        _LOGGER.warning("LibreCoach BLE config not found or invalid: %s", exc)
        _LOGGER.warning("Ensure the LibreCoach add-on is installed and MicroAir is enabled")
        return True  # Don't fail HA startup

    if not conf.get("microair_enabled"):
        _LOGGER.info("LibreCoach BLE: MicroAir disabled in add-on config")
        return True

    manager = BleBridgeManager(hass, conf)
    hass.data[DOMAIN] = manager

    # Start after HA is fully running (Bluetooth + MQTT ready)
    async def _start_bridge(event=None):
        await manager.start()
        _LOGGER.info("LibreCoach BLE bridge started")

    hass.bus.async_listen_once("homeassistant_started", _start_bridge)

    return True

async def async_unload(hass: HomeAssistant) -> bool:
    """Unload the integration."""
    manager = hass.data.get(DOMAIN)
    if manager:
        await manager.stop()
    return True
```

**Key design decisions:**
- Waits for `homeassistant_started` event before starting — ensures Bluetooth
  and MQTT integrations are fully loaded
- Reads config from JSON file written by the add-on (no config flow needed)
- Returns `True` even on config errors — never prevents HA from starting

---

### 7. `librecoach_ble/manifest.json`

```json
{
    "domain": "librecoach_ble",
    "name": "LibreCoach BLE Bridge",
    "codeowners": ["@Backroads4Me"],
    "dependencies": ["bluetooth", "mqtt"],
    "documentation": "https://librecoach.com",
    "integration_type": "hub",
    "iot_class": "local_polling",
    "bluetooth": [
        {
            "local_name": "EasyTouch*",
            "connectable": true
        }
    ],
    "requirements": [],
    "version": "1.0.0"
}
```

**Notes:**
- `dependencies` must include `"bluetooth"` (not just `bluetooth_adapters`) because
  `bridge.py` imports directly from `homeassistant.components.bluetooth`
- `bluetooth` matcher tells HA to wake us when it sees EasyTouch devices
- `requirements: []` — Bleak etc. already installed by HA Core's bluetooth
- Add future BLE matchers to the `bluetooth` array as new device types are added
  (e.g. `{"local_name": "OneControl*", "connectable": true}`)

---

## Modified Existing Files

### 8. `config.yaml` — Add config:rw mapping

Add `config:rw` to the `map:` section:

```yaml
map:
  - share:rw
  - config:rw
```

This allows the add-on to write to `/config/custom_components/` and
`/config/.librecoach-ble-config.json`.

Also add `ble_scan_interval` as a new user-facing option:

```yaml
options:
  ble_scan_interval: 30        # ← ADD (seconds between BLE polls)

schema:
  ble_scan_interval: "int(10,300)?"   # ← ADD
```

Existing `microair_enabled`, `microair_password`, and `microair_email` remain unchanged.

---

### 9. `Dockerfile` — Bundle integration, remove dbus-next

**Change a)** Remove `dbus-next` from pip install:
```dockerfile
RUN pip install --no-cache-dir --break-system-packages \
    python-can \
    paho-mqtt \
    pyserial \
    bitstruct
```
(dbus-next was only used by the MicroAir bridge. can_bridge uses python-can/socketcan.)

**Change b)** Add COPY for bundled integration:
```dockerfile
# Copy bundled HA integration (installed to /config/custom_components/ at runtime)
COPY librecoach_ble /opt/librecoach_ble
```

Place this near the existing `COPY vehicle_bridge /opt/vehicle_bridge` line.

**Change c)** Add the new directory to the CRLF stripping find command:
```dockerfile
RUN find /etc/s6-overlay /etc/cont-init.d /opt/vehicle_bridge /opt/librecoach-project \
    /opt/librecoach_ble \
    -type f -exec sed -i 's/\r$//' {} + 2>/dev/null || true
```

---

### 10. `run.sh` — Add Phase 1.5

Insert between the end of Phase 1 (after `bashio::log.info "   MQTT integration
is configured"` block, around line 461) and before Phase 2 (Node-RED).

```bash
# ========================
# Phase 1.5: LibreCoach BLE Integration
# ========================
MICROAIR_ENABLED=$(bashio::config 'microair_enabled')

if [ "$MICROAIR_ENABLED" = "true" ]; then
    bashio::log.info "Phase 1.5: LibreCoach BLE Integration"

    INTEGRATION_SRC="/opt/librecoach_ble"
    INTEGRATION_DST="/config/custom_components/librecoach_ble"

    # Write config file for the integration to read at runtime
    # NOTE: No mqtt_* fields needed — the integration uses hass.components.mqtt
    # which piggybacks on HA's already-configured MQTT connection.
    MICROAIR_PASSWORD=$(bashio::config 'microair_password')
    MICROAIR_EMAIL=$(bashio::config 'microair_email')
    BLE_SCAN_INTERVAL=$(bashio::config 'ble_scan_interval')

    jq -n \
        --argjson enabled true \
        --arg password "$MICROAIR_PASSWORD" \
        --arg email "$MICROAIR_EMAIL" \
        --argjson scan_interval "${BLE_SCAN_INTERVAL:-30}" \
        '{
            microair_enabled: $enabled,
            microair_password: $password,
            microair_email: $email,
            ble_scan_interval: $scan_interval
        }' > /config/.librecoach-ble-config.json

    # Install/update integration files
    NEEDS_HA_RESTART=false

    if [ -d "$INTEGRATION_DST" ]; then
        INSTALLED_VER=$(jq -r '.version // "0"' "$INTEGRATION_DST/manifest.json" 2>/dev/null || echo "0")
        BUNDLED_VER=$(jq -r '.version // "0"' "$INTEGRATION_SRC/manifest.json" 2>/dev/null || echo "0")

        if [ "$INSTALLED_VER" != "$BUNDLED_VER" ]; then
            bashio::log.info "   Updating librecoach_ble ($INSTALLED_VER → $BUNDLED_VER)..."
            rm -rf "$INTEGRATION_DST"
            cp -r "$INTEGRATION_SRC" "$INTEGRATION_DST"
            NEEDS_HA_RESTART=true
        else
            bashio::log.info "   librecoach_ble is up to date (v$INSTALLED_VER)"
        fi
    else
        bashio::log.info "   Installing librecoach_ble integration..."
        mkdir -p /config/custom_components
        cp -r "$INTEGRATION_SRC" "$INTEGRATION_DST"
        NEEDS_HA_RESTART=true
    fi

    # Add to configuration.yaml if not present
    if ! grep -q "librecoach_ble:" /config/configuration.yaml 2>/dev/null; then
        bashio::log.info "   Adding librecoach_ble to configuration.yaml..."
        echo -e "\nlibrecoach_ble:" >> /config/configuration.yaml
        NEEDS_HA_RESTART=true
    fi

    if [ "$NEEDS_HA_RESTART" = "true" ]; then
        bashio::log.info "   Restarting Home Assistant Core to load integration..."
        api_call POST "/core/restart" >/dev/null 2>&1

        # Wait for HA to come back (up to 3 minutes)
        bashio::log.info "   Waiting for Home Assistant to restart..."
        retries=90
        while [ $retries -gt 0 ]; do
            if api_call GET "/core/api/" 2>/dev/null | grep -q "API running"; then
                bashio::log.info "   Home Assistant is back online"
                break
            fi
            sleep 2
            ((retries--))
        done

        if [ $retries -eq 0 ]; then
            bashio::log.warning "   ⚠️  HA restart taking longer than expected"
            bashio::log.warning "   BLE integration will load after HA finishes"
        fi
    fi

    bashio::log.info "   LibreCoach BLE integration ready"
else
    bashio::log.info "Phase 1.5: MicroAir disabled, skipping BLE integration"

    # Clean up if previously installed but now disabled
    if [ -d "/config/custom_components/librecoach_ble" ]; then
        bashio::log.info "   Removing librecoach_ble integration..."
        rm -rf "/config/custom_components/librecoach_ble"
        sed -i '/^librecoach_ble:/d' /config/configuration.yaml 2>/dev/null
        rm -f /config/.librecoach-ble-config.json
    fi
fi
```

**Note:** The config JSON intentionally omits `mqtt_*` fields. The integration
uses `hass.components.mqtt` which reuses HA's already-configured MQTT connection —
no duplicate credentials or connections needed.

---

### 11. `vehicle_bridge/main.py` — Remove MicroAir bridge

Remove:
```python
from microair_bridge import MicroAirBridge
```

Change:
```python
modules = [
    CanBridge(config, mqtt),
    MicroAirBridge(config, mqtt),     # ← REMOVE this line
]
```
To:
```python
modules = [
    CanBridge(config, mqtt),
    # MicroAir BLE now handled by librecoach_ble HA integration
]
```

### 12. `vehicle_bridge/microair_bridge.py` — DELETE

Tell user to delete this file manually. All MicroAir BLE is now handled by the
librecoach_ble HA integration.

---

## How to Add a Future Device Type

Example: adding OneControl BLE support.

1. Create `librecoach_ble/devices/onecontrol.py`:
   ```python
   from .base import BleDeviceHandler

   class OneControlHandler(BleDeviceHandler):
       @staticmethod
       def device_type() -> str:
           return "onecontrol"

       @staticmethod
       def match_name(name: str) -> bool:
           return name.startswith("OneControl")

       async def poll(self, client) -> dict | None:
           # OneControl-specific BLE protocol
           ...

       async def handle_command(self, client, command: dict) -> bool:
           # OneControl-specific command handling
           ...

       def parse_status(self, raw: dict) -> dict:
           # OneControl-specific parsing
           ...
   ```

2. Register it in `librecoach_ble/devices/__init__.py`:
   ```python
   from .microair import MicroAirHandler
   from .onecontrol import OneControlHandler

   DEVICE_HANDLERS = [
       MicroAirHandler,
       OneControlHandler,
   ]
   ```

3. Add BLE matcher to `manifest.json`:
   ```json
   "bluetooth": [
       {"local_name": "EasyTouch*", "connectable": true},
       {"local_name": "OneControl*", "connectable": true}
   ]
   ```

4. Add any new config options to the add-on's `config.yaml` and update
   run.sh to pass them into `.librecoach-ble-config.json`.

That's it. No changes to `bridge.py`, `__init__.py`, or any other file.

---

## Implementation Order

1. `librecoach_ble/const.py` — simple, no dependencies
2. `librecoach_ble/devices/base.py` — abstract class, no dependencies
3. `librecoach_ble/devices/microair.py` — copy parser from stable, add BLE methods
4. `librecoach_ble/devices/__init__.py` — one-line registry
5. `librecoach_ble/bridge.py` — the core orchestrator
6. `librecoach_ble/__init__.py` — integration entry point
7. `librecoach_ble/manifest.json` — integration manifest
8. Modify `config.yaml` — add `config:rw`
9. Modify `Dockerfile` — bundle integration, remove dbus-next
10. Modify `run.sh` — add Phase 1.5
11. Modify `vehicle_bridge/main.py` — remove MicroAir import
12. Delete `vehicle_bridge/microair_bridge.py` (manual)

---

## Testing Checklist

- [ ] Add-on builds successfully (docker build)
- [ ] MicroAir DISABLED: no integration installed, no errors
- [ ] MicroAir ENABLED: integration appears in `/config/custom_components/librecoach_ble/`
- [ ] `configuration.yaml` has `librecoach_ble:` entry after first run
- [ ] HA logs show "LibreCoach BLE bridge started" after restart
- [ ] EasyTouch device discovered via Bluetooth advertisement
- [ ] Status published to `librecoach/ble/microair/{address}/state`
- [ ] Zone data includes `zone` key in each published state
- [ ] Commands accepted on `librecoach/ble/microair/{address}/set`
- [ ] Availability topics published (online/offline)
- [ ] If ZWA-2 proxy is available, connection routes through it (check HA BT logs)
- [ ] CAN bridge still works independently
- [ ] Node-RED flows still receive MicroAir MQTT data on same topics
- [ ] Disabling MicroAir and restarting removes integration cleanly
- [ ] Re-enabling after disable re-installs correctly
- [ ] Second add-on restart does NOT trigger HA restart (version check works)
- [ ] Integration survives HA restart without add-on restart (reads config from file)

---

## Clarifications (Q&A)

**Q: `ble_scan_interval` is read by `bridge.py` but not passed into the config JSON.**
A: Add `ble_scan_interval` as a user-facing option in `config.yaml` (default 30,
range 10-300). Pass it into `.librecoach-ble-config.json` via the `jq` command in
run.sh Phase 1.5. Updated above.

**Q: Should `mqtt_*` fields be in the config JSON?**
A: No. Remove them. The integration uses `hass.components.mqtt` which piggybacks on
HA's already-configured MQTT connection. The config JSON only needs fields the
integration can't get from HA itself: `microair_enabled`, `microair_password`,
`microair_email`, and `ble_scan_interval`. Updated above.

**Q: Should `manifest.json` dependencies include `"bluetooth"`?**
A: Yes. `bridge.py` imports directly from `homeassistant.components.bluetooth`
(`async_ble_device_from_address`, `async_register_callback`, etc.). The correct
dependencies are `["bluetooth", "mqtt"]`, not `["bluetooth_adapters", "mqtt"]`.
Updated above.

**Q: Can we drop zone config fetching (MAV, FA, SPL, MA)?**
A: No. Zone configs tell you how many zones the device has and their min/max
temperature limits. Without them the integration doesn't know which zones to poll
or what valid setpoint ranges are. Add a `_fetch_zone_config()` method to
`MicroAirHandler` that runs on first successful connection, caches the results,
and is referenced by subsequent `poll()` and `handle_command()` calls. These
values don't change at runtime so fetch once and reuse. Updated above.
