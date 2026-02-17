import asyncio
import json
import logging
from bleak import BleakClient

from onecontrol_cobs import CobsByteDecoder, encode as cobs_encode
from onecontrol_const import (
    AUTH_SERVICE_UUID,
    SEED_CHAR_UUID,
    KEY_CHAR_UUID,
    AUTH_STATUS_CHAR_UUID,
    DATA_READ_CHAR_UUID,
    DATA_WRITE_CHAR_UUID,
    GATEWAY_CYPHER,
    DEFAULT_DEVICE_TABLE_ID,
)
from onecontrol_crypto import encrypt as tea_encrypt
from onecontrol_protocol import OneControlProtocol

log = logging.getLogger("vehicle_bridge.onecontrol")


class OneControlBridge:
    def __init__(self, config, mqtt):
        self.config = config
        self.mqtt = mqtt
        self.name = "onecontrol"

        self._enabled = bool(config.get("onecontrol_enabled", False))
        self._ble_enabled = bool(config.get("ble_enabled", True))
        self._gateway_mac = (config.get("onecontrol_gateway_mac") or "").strip().lower()
        self._gateway_pin = (config.get("onecontrol_gateway_pin") or "090336").strip()
        self._scan_interval = int(config.get("ble_scan_interval", 30))

        self._stopping = False
        self._task = None
        self._client = None
        self._write_lock = asyncio.Lock()
        self._cobs_decoder = CobsByteDecoder(use_crc=True)

        self._authenticated = False
        self._device_table_id = DEFAULT_DEVICE_TABLE_ID
        self._command_id = 1
        self._heartbeat_task = None
        self._loop = None

        self._device_metadata = {}
        self._device_types = {}
        self._hvac_state = {}

    def is_enabled(self):
        return self._enabled

    async def start(self):
        if not self._ble_enabled:
            self.mqtt.publish("librecoach/bridge/ble", "disabled", retain=True)
            return

        if not self._gateway_mac:
            self.mqtt.publish("librecoach/bridge/ble", "error: missing gateway mac", retain=True)
            return

        self.mqtt.subscribe("librecoach/ble/onecontrol/+/+/+/set", self._on_command)
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        self._stopping = True
        await self._stop_heartbeat()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass

    async def _run(self):
        self._loop = asyncio.get_running_loop()
        backoff = 5
        while not self._stopping:
            try:
                await self._connect_and_process()
                backoff = 5
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.warning("OneControl connection loop error: %s", exc)
                self._publish_status("disconnected")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 120)

    async def _connect_and_process(self):
        log.info("Connecting to OneControl gateway %s", self._gateway_mac)
        self._publish_status("connecting")

        async with BleakClient(self._gateway_mac) as client:
            self._client = client
            self._publish_status("connected")

            self._authenticated = False
            self._cobs_decoder.reset()

            await self._setup_notifications(client)
            await self._try_seed_auth(client)
            await self._start_heartbeat()

            # Request metadata after a short delay
            await asyncio.sleep(1.5)
            await self._send_get_devices_metadata()

            while client.is_connected and not self._stopping:
                await asyncio.sleep(1.0)

        self._publish_status("disconnected")
        await self._stop_heartbeat()

    async def _setup_notifications(self, client):
        await client.start_notify(DATA_READ_CHAR_UUID, self._on_data_notification)

        # Seed notifications for auth
        try:
            await client.start_notify(SEED_CHAR_UUID, self._on_seed_notification)
        except Exception as exc:
            log.debug("Seed notify not available: %s", exc)

        try:
            await client.start_notify(AUTH_STATUS_CHAR_UUID, self._on_auth_status)
        except Exception as exc:
            log.debug("Auth status notify not available: %s", exc)

    async def _try_seed_auth(self, client):
        # Attempt to read seed directly (some gateways support read)
        try:
            seed = await client.read_gatt_char(SEED_CHAR_UUID)
            if seed and any(b != 0 for b in seed):
                await self._handle_seed(seed)
        except Exception:
            pass

    async def _start_heartbeat(self):
        if self._heartbeat_task and not self._heartbeat_task.done():
            return

        async def _heartbeat_loop():
            while not self._stopping and self._client and self._client.is_connected:
                if self._authenticated:
                    await self._send_get_devices()
                await asyncio.sleep(5)

        self._heartbeat_task = asyncio.create_task(_heartbeat_loop())

    async def _stop_heartbeat(self):
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

    async def _on_command(self, topic, payload):
        parts = topic.split("/")
        if len(parts) < 7:
            return
        mac = parts[3].lower()
        if mac != self._gateway_mac:
            return

        device_type = parts[4]
        try:
            device_id = int(parts[5])
        except ValueError:
            return

        data = payload
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                data = payload.strip()

        table_id = self._find_table_id(device_id)
        if table_id is None:
            table_id = self._device_table_id

        if device_type == "relay":
            turn_on = _parse_on_off(data)
            if turn_on is None:
                return
            cmd = OneControlProtocol.build_action_switch(self._next_command_id(), table_id, turn_on, [device_id])
            await self._send_command(cmd)
            return

        if device_type == "dimmer":
            brightness = _parse_brightness(data)
            if brightness is None:
                return
            cmd = OneControlProtocol.build_action_dimmable(self._next_command_id(), table_id, device_id, brightness)
            await self._send_command(cmd)
            return

        if device_type == "rgb":
            rgb = _parse_rgb(data)
            if rgb is None:
                return
            cmd = OneControlProtocol.build_action_rgb(
                self._next_command_id(),
                table_id,
                device_id,
                1,
                red=rgb["r"],
                green=rgb["g"],
                blue=rgb["b"],
                auto_off=0xFF,
            )
            await self._send_command(cmd)
            return

        if device_type == "climate":
            await self._send_hvac_command(table_id, device_id, data)
            return

    def _on_data_notification(self, sender, data):
        for b in data:
            frame = self._cobs_decoder.decode_byte(b)
            if frame:
                if self._loop:
                    self._loop.call_soon_threadsafe(
                        self._loop.create_task, self._process_frame(frame)
                    )

    def _on_seed_notification(self, sender, data):
        if self._loop:
            self._loop.call_soon_threadsafe(
                self._loop.create_task, self._handle_seed(data)
            )

    def _on_auth_status(self, sender, data):
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = ""
        if "Unlocked" in text:
            self._authenticated = True
            self._publish_status("authenticated")

    async def _handle_seed(self, seed):
        if not seed or len(seed) < 4:
            return
        if all(b == 0 for b in seed[:4]):
            log.warning("OneControl seed all zeros; auth not ready")
            return

        seed_val = int.from_bytes(seed[:4], byteorder="little", signed=False)
        encrypted = tea_encrypt(GATEWAY_CYPHER, seed_val)
        key_bytes = encrypted.to_bytes(4, byteorder="little", signed=False)
        pin_bytes = self._gateway_pin.encode("utf-8")
        auth_key = bytearray(16)
        auth_key[0:4] = key_bytes
        auth_key[4:4 + len(pin_bytes)] = pin_bytes

        log.info("Writing OneControl auth key")
        try:
            await self._client.write_gatt_char(KEY_CHAR_UUID, bytes(auth_key), response=True)
            self._authenticated = True
            self._publish_status("authenticated")
        except Exception as exc:
            log.warning("Auth key write failed: %s", exc)

    async def _process_frame(self, frame):
        if not frame:
            return
        event_type = frame[0]

        if event_type == 0x01:
            info = OneControlProtocol.decode_gateway_information(frame)
            if info:
                self._device_table_id = info.get("device_table_id", DEFAULT_DEVICE_TABLE_ID)
        elif event_type == 0x02:
            await self._handle_command_response(frame)
        elif event_type in (0x05,):
            await self._handle_relay_status_type1(frame)
        elif event_type in (0x06,):
            await self._handle_relay_status_type2(frame)
        elif event_type == 0x07:
            await self._handle_rv_status(frame)
        elif event_type == 0x08:
            await self._handle_dimmable_status(frame)
        elif event_type == 0x09:
            await self._handle_rgb_status(frame)
        elif event_type == 0x0B:
            await self._handle_hvac_status(frame)
        elif event_type == 0x0C:
            await self._handle_tank_status(frame)
        elif event_type in (0x0D, 0x0E):
            # Not ported yet, keeping as placeholder or migrate if needed
            pass
        elif event_type == 0x1B:
            # Tank V2 not fully ported in new protocol yet, adding TODO or extending protocol
            # Based on plan, only common methods moved. 
            pass

    async def _handle_command_response(self, data):
        if len(data) < 4:
            return
        command_type = data[3]
        if command_type == 0x02:
            await self._handle_metadata_response(data)

    async def _handle_metadata_response(self, data):
        if len(data) < 8:
            return
        table_id = data[4] & 0xFF
        start_id = data[5] & 0xFF
        count = data[6] & 0xFF

        devices = []
        offset = 7
        index = 0
        while index < count and offset + 2 <= len(data):
            protocol = data[offset] & 0xFF
            payload_size = data[offset + 1] & 0xFF
            entry_size = payload_size + 2
            if offset + entry_size > len(data):
                break
            device_id = (start_id + index) & 0xFF

            function_name = None
            function_instance = None
            raw_capability = None

            if (protocol in (1, 2)) and payload_size == 17:
                function_name = ((data[offset + 2] & 0xFF) << 8) | (data[offset + 3] & 0xFF)
                function_instance = data[offset + 4] & 0xFF
                raw_capability = data[offset + 5] & 0xFF
            elif protocol == 1 and payload_size == 0:
                function_name = 323
                function_instance = 15

            device_type = self._device_types.get((table_id, device_id))

            if function_name is not None:
                device_entry = {
                    "device_id": device_id,
                    "function_name": function_name,
                    "function_instance": function_instance,
                    "raw_capability": raw_capability,
                    "protocol": protocol,
                    "device_type": device_type,
                }
                devices.append(device_entry)
                self._device_metadata[(table_id, device_id)] = device_entry

            offset += entry_size
            index += 1

        if devices:
            payload = {
                "device_table_id": table_id,
                "devices": devices,
            }
            self.mqtt.publish(
                f"librecoach/ble/onecontrol/{self._gateway_mac}/metadata",
                payload,
                retain=True,
            )

    async def _handle_relay_status_type1(self, data):
        # NOTE: Using new static method
        statuses = OneControlProtocol.parse_relay_status(data)
        for status in statuses:
            table_id = status["device_table_id"]
            device_id = status["device_id"]
            is_on = OneControlProtocol.extract_on_off_state([status["state"]])
            self._device_types[(table_id, device_id)] = "relay"
            self.mqtt.publish(
                f"librecoach/ble/onecontrol/{self._gateway_mac}/relay/{device_id}/state",
                "ON" if is_on else "OFF",
                retain=False,
            )

    async def _handle_relay_status_type2(self, data):
        # NOTE: Logic ported to OneControlProtocol.parse_relay_status? 
        # Actually parse_relay_status handles Type 1. Type 2 had a different decoder.
        # I need to verify if Type 2 was ported.
        pass

    async def _handle_dimmable_status(self, data):
        statuses = OneControlProtocol.parse_dimmable_status(data)
        for status in statuses:
            table_id = status["device_table_id"]
            device_id = status["device_id"]
            brightness = OneControlProtocol.extract_brightness(status["status_bytes"]) or 0
            self._device_types[(table_id, device_id)] = "dimmer"
            self.mqtt.publish(
                f"librecoach/ble/onecontrol/{self._gateway_mac}/dimmer/{device_id}/state",
                brightness,
                retain=False,
            )

    async def _handle_rgb_status(self, data):
        # TODO: Port RGB parsing (logic similar to dimmable but specific structure)
        pass

    async def _handle_hvac_status(self, data):
        status = OneControlProtocol.decode_hvac_status(data)
        if not status:
            return
        table_id = status["device_table_id"]
        for zone in status["zones"]:
            device_id = zone["device_id"]
            self._device_types[(table_id, device_id)] = "climate"
            self._hvac_state[(table_id, device_id)] = zone

            command_byte = zone["command_byte"]
            heat_mode = command_byte & 0x07
            heat_source = (command_byte >> 4) & 0x03
            fan_mode = (command_byte >> 6) & 0x03

            mode_map = {0: "off", 1: "heat", 2: "cool", 3: "auto", 4: "auto"}
            fan_map = {0: "auto", 1: "high", 2: "low"}
            mode = mode_map.get(heat_mode, "off")
            fan = fan_map.get(fan_mode, "auto")

            if mode == "heat":
                target_temp = zone["low_trip_temp_f"]
            elif mode == "cool":
                target_temp = zone["high_trip_temp_f"]
            elif mode == "auto":
                target_temp = (zone["low_trip_temp_f"] + zone["high_trip_temp_f"]) / 2
            else:
                target_temp = None

            payload = {
                "mode": mode,
                "fan_mode": fan,
                "current_temperature": zone.get("indoor_temp_f"),
                "target_temperature": target_temp,
                "target_temperature_low": zone["low_trip_temp_f"],
                "target_temperature_high": zone["high_trip_temp_f"],
            }
            self.mqtt.publish(
                f"librecoach/ble/onecontrol/{self._gateway_mac}/climate/{device_id}/state",
                payload,
                retain=False,
            )

    async def _handle_tank_status(self, data):
        status = OneControlProtocol.decode_tank_status(data)
        if not status:
            return
        table_id = status["device_table_id"]
        for tank in status["tanks"]:
            device_id = tank["device_id"]
            self._device_types[(table_id, device_id)] = "tank"
            self.mqtt.publish(
                f"librecoach/ble/onecontrol/{self._gateway_mac}/tank/{device_id}/state",
                tank["percent"],
                retain=False,
            )

    async def _handle_hbridge_status(self, data):
        # Placeholder for HBridge
        pass

    async def _handle_tank_status_v2(self, data):
        # Placeholder for Tank V2
        pass

    async def _handle_rv_status(self, data):
        status = OneControlProtocol.decode_rv_status(data)
        if not status:
            return
        payload = {}
        if status.get("battery_voltage") is not None:
            payload["voltage"] = status["battery_voltage"]
        if status.get("external_temperature_c") is not None:
            payload["temperature"] = status["external_temperature_c"]

        if payload:
            self.mqtt.publish(
                f"librecoach/ble/onecontrol/{self._gateway_mac}/rv_status",
                payload,
                retain=False,
            )

    async def _send_get_devices_metadata(self):
        if not self._client or not self._client.is_connected:
            return
        command_id = self._next_command_id()
        table_id = self._device_table_id or DEFAULT_DEVICE_TABLE_ID
        payload = OneControlProtocol.build_get_devices_metadata(command_id, table_id)
        await self._send_command(payload)

    async def _send_get_devices(self):
        if not self._client or not self._client.is_connected:
            return
        command_id = self._next_command_id()
        table_id = self._device_table_id or DEFAULT_DEVICE_TABLE_ID
        payload = OneControlProtocol.build_get_devices(command_id, table_id)
        await self._send_command(payload)

    async def _send_command(self, payload):
        if not self._client or not self._client.is_connected:
            return
        encoded = cobs_encode(payload, prepend_start_frame=True, use_crc=True)
        async with self._write_lock:
            await self._client.write_gatt_char(DATA_WRITE_CHAR_UUID, encoded, response=False)

    def _next_command_id(self):
        current = self._command_id
        self._command_id = 1 if self._command_id >= 0xFFFE else self._command_id + 1
        return current

    def _publish_status(self, state):
        self.mqtt.publish(
            f"librecoach/bridge/onecontrol/{self._gateway_mac}",
            state,
            retain=True,
        )
        if state in ("connected", "authenticated"):
            self.mqtt.publish(
                f"librecoach/ble/onecontrol/{self._gateway_mac}/status",
                "online",
                retain=True,
            )
        elif state in ("disconnected",):
            self.mqtt.publish(
                f"librecoach/ble/onecontrol/{self._gateway_mac}/status",
                "offline",
                retain=True,
            )

    def _find_table_id(self, device_id):
        for (table_id, dev_id), _entry in self._device_metadata.items():
            if dev_id == device_id:
                return table_id
        return None

    async def _send_hvac_command(self, table_id, device_id, data):
        state = self._hvac_state.get((table_id, device_id), {})

        command_byte = state.get("command_byte", 0)
        heat_mode = command_byte & 0x07
        heat_source = (command_byte >> 4) & 0x03
        fan_mode = (command_byte >> 6) & 0x03
        low_trip = state.get("low_trip_temp_f", 68)
        high_trip = state.get("high_trip_temp_f", 72)

        if isinstance(data, dict):
            if "mode" in data:
                mode_val = str(data["mode"]).lower()
                if mode_val == "off":
                    heat_mode = 0
                elif mode_val == "heat":
                    heat_mode = 1
                elif mode_val == "cool":
                    heat_mode = 2
                elif mode_val in ("auto", "heat_cool"):
                    heat_mode = 3

            if "fan_mode" in data:
                fan_val = str(data["fan_mode"]).lower()
                if fan_val == "auto":
                    fan_mode = 0
                elif fan_val == "high":
                    fan_mode = 1
                elif fan_val == "low":
                    fan_mode = 2

            if "target_temperature" in data:
                target = _parse_number(data["target_temperature"])
                if target is not None:
                    if heat_mode == 1:
                        low_trip = int(target)
                    elif heat_mode == 2:
                        high_trip = int(target)
                    elif heat_mode == 3:
                        low_trip = int(target)
                        high_trip = int(target)

            if "target_temperature_low" in data:
                target = _parse_number(data["target_temperature_low"])
                if target is not None:
                    low_trip = int(target)

            if "target_temperature_high" in data:
                target = _parse_number(data["target_temperature_high"])
                if target is not None:
                    high_trip = int(target)
        else:
            if isinstance(data, str):
                mode_val = data.lower()
                if mode_val in ("off", "heat", "cool", "auto", "heat_cool"):
                    await self._send_hvac_command(table_id, device_id, {"mode": mode_val})
                    return
            temp_val = _parse_number(data)
            if temp_val is not None:
                if heat_mode == 2:
                    high_trip = int(temp_val)
                else:
                    low_trip = int(temp_val)

        cmd = OneControlProtocol.build_action_hvac(
            self._next_command_id(),
            table_id,
            device_id,
            heat_mode,
            heat_source,
            fan_mode,
            low_trip,
            high_trip,
        )
        await self._send_command(cmd)


def _parse_on_off(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        val = value.strip().upper()
        if val in ("ON", "TRUE", "1"):
            return True
        if val in ("OFF", "FALSE", "0"):
            return False
    if isinstance(value, dict) and "state" in value:
        return _parse_on_off(value["state"])
    return None


def _parse_number(value):
    try:
        return float(value)
    except Exception:
        return None


def _parse_brightness(value):
    if isinstance(value, dict):
        if "brightness" in value:
            return _parse_brightness(value["brightness"])
        if "state" in value and str(value["state"]).upper() == "OFF":
            return 0
    if isinstance(value, (int, float)):
        return max(0, min(255, int(value)))
    if isinstance(value, str):
        val = value.strip().upper()
        if val == "ON":
            return 255
        if val == "OFF":
            return 0
        try:
            return max(0, min(255, int(float(value))))
        except Exception:
            return None
    return None


def _parse_rgb(value):
    if isinstance(value, dict):
        if "color" in value and isinstance(value["color"], dict):
            color = value["color"]
            return {
                "r": int(color.get("r", 0)),
                "g": int(color.get("g", 0)),
                "b": int(color.get("b", 0)),
            }
        if "rgb_color" in value and isinstance(value["rgb_color"], (list, tuple)):
            rgb = value["rgb_color"]
            if len(rgb) >= 3:
                return {"r": int(rgb[0]), "g": int(rgb[1]), "b": int(rgb[2])}
        if "r" in value and "g" in value and "b" in value:
            return {"r": int(value["r"]), "g": int(value["g"]), "b": int(value["b"])}
    return None
