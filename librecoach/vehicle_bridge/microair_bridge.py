import asyncio
import json
import logging
import time

from dbus_next.aio import MessageBus
from dbus_next.constants import BusType
from dbus_next import Variant

log = logging.getLogger("vehicle_bridge.microair")

UUIDS = {
    "service": "000000ff-0000-1000-8000-00805f9b34fb",
    "passwordCmd": "0000dd01-0000-1000-8000-00805f9b34fb",
    "jsonCmd": "0000ee01-0000-1000-8000-00805f9b34fb",
    "jsonReturn": "0000ff01-0000-1000-8000-00805f9b34fb",
}

MODE_NUM_TO_MODE = {
    0: "off",
    1: "fan_only",
    2: "cool",
    3: "heat",
    4: "heat",
    5: "heat",
    6: "dry",
    7: "heat",
    8: "auto",
    9: "auto",
    10: "auto",
    11: "auto",
    12: "heat",
}

HEAT_TYPE_REVERSE = {
    5: "Heat Pump",
    4: "Furnace",
    3: "Gas Furnace",
    7: "Heat Strip",
    12: "Electric Heat",
}

FAN_MODE_MAP = {
    0: "off",
    1: "low",
    2: "high",
    3: "medium",
    128: "auto",
}


async def _get_bus():
    """Connect to the system D-Bus."""
    return await MessageBus(bus_type=BusType.SYSTEM).connect()


async def _get_interface(bus, path, iface_name):
    """Introspect a BlueZ object and return a specific interface proxy."""
    introspection = await bus.introspect("org.bluez", path)
    proxy = bus.get_proxy_object("org.bluez", path, introspection)
    return proxy.get_interface(iface_name)


class MicroAirBridge:
    def __init__(self, config, mqtt):
        self.config = config
        self.mqtt = mqtt
        self.name = "microair"
        self._stopping = False

        self._enabled = bool(config.get("microair_enabled", False))
        self._ble_enabled = bool(config.get("ble_enabled", True))
        self._password = (config.get("microair_password") or "").strip()
        self._email = (config.get("microair_email") or "").strip()
        self._scan_interval = int(config.get("ble_scan_interval", 30))

        self._devices = {}
        self._scan_task = None

    def is_enabled(self):
        return self._enabled

    async def start(self):
        if not self._ble_enabled:
            self.mqtt.publish("librecoach/bridge/ble", "disabled", retain=True)
            return

        self.mqtt.publish("librecoach/bridge/ble", "scanning", retain=True)
        self.mqtt.subscribe("librecoach/ble/microair/+/set", self._on_command)
        self._scan_task = asyncio.create_task(self._scan_loop())

    async def stop(self):
        self._stopping = True
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        for device in list(self._devices.values()):
            await device.stop()

    async def _scan_loop(self):
        while not self._stopping:
            bus = None
            try:
                bus = await _get_bus()

                # Get adapter interface
                adapter = await _get_interface(bus, "/org/bluez/hci0", "org.bluez.Adapter1")

                # Set discovery filter for BLE with MicroAir service UUID
                await adapter.call_set_discovery_filter({
                    "Transport": Variant("s", "le"),
                    "UUIDs": Variant("as", [UUIDS["service"]]),
                })

                await adapter.call_start_discovery()
                await asyncio.sleep(10.0)

                try:
                    await adapter.call_stop_discovery()
                except Exception:
                    pass

                # Enumerate discovered devices via ObjectManager
                obj_manager = await _get_interface(bus, "/", "org.freedesktop.DBus.ObjectManager")
                objects = await obj_manager.call_get_managed_objects()

                for path, interfaces in objects.items():
                    if "org.bluez.Device1" not in interfaces:
                        continue
                    props = interfaces["org.bluez.Device1"]
                    name = props.get("Name", Variant("s", "")).value
                    if not name.startswith("EasyTouch"):
                        continue
                    address = props.get("Address", Variant("s", "")).value.lower()
                    if address not in self._devices:
                        log.info("Discovered MicroAir device: %s (%s)", address, name)
                        microair = _MicroAirDevice(
                            address=address,
                            device_path=path,
                            name=name,
                            password=self._password,
                            email=self._email,
                            mqtt=self.mqtt,
                        )
                        self._devices[address] = microair
                        microair.start(self._scan_interval)

            except Exception as exc:
                log.warning("BLE scan error: %s", exc)
                self.mqtt.publish("librecoach/bridge/ble", f"error: {exc}", retain=True)
            finally:
                if bus:
                    bus.disconnect()

            await asyncio.sleep(self._scan_interval)

    async def _on_command(self, topic, payload):
        parts = topic.split("/")
        if len(parts) < 5:
            return
        mac = parts[3].lower()
        device = self._devices.get(mac)
        if not device:
            log.warning("MicroAir command for unknown device: %s", mac)
            return

        try:
            data = json.loads(payload) if isinstance(payload, str) else payload
        except json.JSONDecodeError:
            log.warning("Invalid MicroAir command payload: %s", payload)
            return

        if not isinstance(data, dict):
            log.warning("MicroAir command payload must be JSON object")
            return

        await device.send_command(data)


class _MicroAirDevice:
    def __init__(self, address, device_path, name, password, email, mqtt):
        self.address = address
        self.device_path = device_path
        self.name = name
        self.password = password
        self.email = email
        self.mqtt = mqtt

        self._stopping = False
        self._lock = asyncio.Lock()
        self._poll_task = None
        self._zone_configs = {}

    def start(self, interval):
        if self._poll_task and not self._poll_task.done():
            return
        self._poll_task = asyncio.create_task(self._poll_loop(interval))

    async def stop(self):
        self._stopping = True
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

    async def _poll_loop(self, interval):
        while not self._stopping:
            await self._poll_once()
            await asyncio.sleep(interval)

    async def _poll_once(self):
        try:
            status = await self._request_json(
                {
                    "Type": "Get Status",
                    "Zone": 0,
                    "EM": self.email,
                    "TM": int(time.time()),
                }
            )
            if not status:
                self.mqtt.publish(
                    f"librecoach/ble/microair/{self.address}/available",
                    "offline",
                    retain=True,
                )
                return

            parsed = _parse_status(status)
            zones = parsed.get("available_zones", [])
            for zone in zones:
                zone_state = parsed.get("zones", {}).get(zone, {})
                zone_state["zone"] = zone
                self.mqtt.publish(
                    f"librecoach/ble/microair/{self.address}/state",
                    zone_state,
                    retain=False,
                )

            self.mqtt.publish(
                f"librecoach/ble/microair/{self.address}/available",
                "online",
                retain=True,
            )
            self.mqtt.publish(
                f"librecoach/bridge/microair/{self.address}",
                "polling",
                retain=True,
            )

            if zones and not self._zone_configs:
                await self._fetch_zone_configs(zones)
                if self._zone_configs:
                    self.mqtt.publish(
                        f"librecoach/ble/microair/{self.address}/config",
                        {"zone_configs": self._zone_configs},
                        retain=True,
                    )
        except Exception as exc:
            log.warning("MicroAir poll failed for %s: %s", self.address, exc)
            self.mqtt.publish(
                f"librecoach/ble/microair/{self.address}/available",
                "offline",
                retain=True,
            )
            self.mqtt.publish(
                f"librecoach/bridge/microair/{self.address}",
                "disconnected",
                retain=True,
            )

    async def send_command(self, command):
        try:
            await self._write_json(command)
        except Exception as exc:
            log.warning("MicroAir command failed for %s: %s", self.address, exc)

    async def _fetch_zone_configs(self, zones):
        for zone in zones:
            response = await self._request_json({"Type": "Get Config", "Zone": zone})
            if not response:
                continue
            if response.get("Type") != "Response" or response.get("RT") != "Config":
                continue
            cfg_str = response.get("CFG", "{}")
            cfg_data = json.loads(cfg_str) if isinstance(cfg_str, str) else cfg_str
            self._zone_configs[zone] = {
                "MAV": cfg_data.get("MAV", 0),
                "FA": cfg_data.get("FA", [0] * 16),
                "SPL": cfg_data.get("SPL", [60, 85, 50, 85]),
                "MA": cfg_data.get("MA", [0] * 16),
            }

    async def _connect_and_resolve(self, bus):
        """Connect to device and wait for GATT services to resolve."""
        device_iface = await _get_interface(bus, self.device_path, "org.bluez.Device1")
        props_iface = await _get_interface(
            bus, self.device_path, "org.freedesktop.DBus.Properties"
        )

        await device_iface.call_connect()

        # Wait for ServicesResolved
        for _ in range(30):
            resolved = await props_iface.call_get(
                "org.bluez.Device1", "ServicesResolved"
            )
            if resolved.value:
                break
            await asyncio.sleep(0.5)
        else:
            raise TimeoutError("GATT services did not resolve within 15s")

        return device_iface

    async def _find_characteristic(self, bus, uuid):
        """Find a GATT characteristic by UUID under the device path."""
        obj_manager = await _get_interface(bus, "/", "org.freedesktop.DBus.ObjectManager")
        objects = await obj_manager.call_get_managed_objects()

        for path, interfaces in objects.items():
            if not path.startswith(self.device_path + "/"):
                continue
            if "org.bluez.GattCharacteristic1" not in interfaces:
                continue
            props = interfaces["org.bluez.GattCharacteristic1"]
            char_uuid = props.get("UUID", Variant("s", "")).value
            if char_uuid.lower() == uuid.lower():
                return path
        return None

    async def _write_characteristic(self, bus, char_path, data):
        """Write bytes to a GATT characteristic."""
        char_iface = await _get_interface(bus, char_path, "org.bluez.GattCharacteristic1")
        await char_iface.call_write_value(list(data), {})

    async def _read_characteristic(self, bus, char_path):
        """Read bytes from a GATT characteristic."""
        char_iface = await _get_interface(bus, char_path, "org.bluez.GattCharacteristic1")
        result = await char_iface.call_read_value({})
        return bytes(result)

    async def _request_json(self, command):
        async with self._lock:
            bus = None
            try:
                bus = await _get_bus()
                await self._connect_and_resolve(bus)

                if self.password:
                    pw_path = await self._find_characteristic(bus, UUIDS["passwordCmd"])
                    if pw_path:
                        await self._write_characteristic(
                            bus, pw_path, self.password.encode("utf-8")
                        )
                        await asyncio.sleep(0.2)

                cmd_path = await self._find_characteristic(bus, UUIDS["jsonCmd"])
                ret_path = await self._find_characteristic(bus, UUIDS["jsonReturn"])

                if not cmd_path or not ret_path:
                    log.debug("MicroAir GATT characteristics not found")
                    return None

                await self._write_characteristic(
                    bus, cmd_path, json.dumps(command).encode("utf-8")
                )
                await asyncio.sleep(1.0)
                payload = await self._read_characteristic(bus, ret_path)
                if not payload:
                    return None
                return json.loads(payload.decode("utf-8"))
            except (OSError, asyncio.TimeoutError, json.JSONDecodeError, TimeoutError) as exc:
                log.debug("MicroAir request failed: %s", exc)
                return None
            except Exception as exc:
                log.debug("MicroAir request failed: %s", exc)
                return None
            finally:
                if bus:
                    try:
                        device_iface = await _get_interface(
                            bus, self.device_path, "org.bluez.Device1"
                        )
                        await device_iface.call_disconnect()
                    except Exception:
                        pass
                    bus.disconnect()

    async def _write_json(self, command):
        async with self._lock:
            bus = None
            try:
                bus = await _get_bus()
                await self._connect_and_resolve(bus)

                if self.password:
                    pw_path = await self._find_characteristic(bus, UUIDS["passwordCmd"])
                    if pw_path:
                        await self._write_characteristic(
                            bus, pw_path, self.password.encode("utf-8")
                        )
                        await asyncio.sleep(0.2)

                cmd_path = await self._find_characteristic(bus, UUIDS["jsonCmd"])
                if not cmd_path:
                    log.debug("MicroAir jsonCmd characteristic not found")
                    return

                await self._write_characteristic(
                    bus, cmd_path, json.dumps(command).encode("utf-8")
                )
            finally:
                if bus:
                    try:
                        device_iface = await _get_interface(
                            bus, self.device_path, "org.bluez.Device1"
                        )
                        await device_iface.call_disconnect()
                    except Exception:
                        pass
                    bus.disconnect()


def _parse_status(status):
    if not isinstance(status, dict):
        return {"available_zones": [0], "zones": {0: {}}}

    if "Z_sts" not in status:
        return {"available_zones": [0], "zones": {0: {}}}

    param = status.get("PRM", [])
    zone_data = {}
    available_zones = []

    for zone_key, info in status["Z_sts"].items():
        try:
            zone_num = int(zone_key)
        except (ValueError, TypeError):
            continue

        try:
            zone_status = {
                "autoHeat_sp": info[0],
                "autoCool_sp": info[1],
                "cool_sp": info[2],
                "heat_sp": info[3],
                "dry_sp": info[4],
                "rh_sp": info[5],
                "fan_mode_num": info[6],
                "cool_fan_mode_num": info[7],
                "heat_fan_mode_num": info[8],
                "auto_fan_mode_num": info[9],
                "dry_fan_mode_num": info[9],
                "mode_num": info[10],
                "furnace_fan_mode_num": info[11],
                "facePlateTemperature": info[12],
                "outdoorTemperature": info[13],
                "active_state_num": info[15],
            }
        except (IndexError, TypeError):
            continue

        if len(param) > 1:
            flags_register = param[1]
            system_power_on = (flags_register & 8) > 0
            zone_status["off"] = not system_power_on
            zone_status["on"] = system_power_on

        mode_num = zone_status.get("mode_num")
        zone_status["mode"] = MODE_NUM_TO_MODE.get(mode_num, "off")

        active_state = zone_status.get("active_state_num", 0)
        if active_state & 2:
            current_mode = "cool"
        elif active_state & 4:
            current_mode = "heat"
        elif active_state & 1:
            if zone_status["mode"] == "fan_only":
                current_mode = "fan_only"
            else:
                current_mode = "dry"
        elif active_state & 32:
            current_mode = "off"
        else:
            current_mode = "off"
        zone_status["current_mode"] = current_mode

        if mode_num in HEAT_TYPE_REVERSE:
            zone_status["heat_source"] = HEAT_TYPE_REVERSE[mode_num]

        fan_num = _select_fan_mode(zone_status)
        zone_status["fan_mode_num"] = fan_num
        zone_status["fan_mode"] = FAN_MODE_MAP.get(fan_num, "off")

        zone_data[zone_num] = zone_status
        available_zones.append(zone_num)

    if not available_zones:
        return {"available_zones": [0], "zones": {0: {}}}

    return {
        "available_zones": sorted(available_zones),
        "zones": zone_data,
    }


def _select_fan_mode(zone_status):
    mode = zone_status.get("mode")
    if mode == "cool":
        return zone_status.get("cool_fan_mode_num", 0)
    if mode == "heat":
        return zone_status.get("heat_fan_mode_num", zone_status.get("furnace_fan_mode_num", 0))
    if mode == "auto":
        return zone_status.get("auto_fan_mode_num", 0)
    if mode == "dry":
        return zone_status.get("dry_fan_mode_num", 0)
    if mode == "fan_only":
        return zone_status.get("fan_mode_num", 0)
    return 0
