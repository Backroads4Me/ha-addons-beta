import struct

class OneControlProtocol:
    """
    Handles protocol-specific logic for OneControl/MyRVLink.
    Consolidates command building, event decoding, and status parsing.
    """

    # --- Commands ---

    @staticmethod
    def _le_u16(value):
        return struct.pack("<H", value & 0xFFFF)

    @staticmethod
    def build_get_devices(command_id, device_table_id, start_device_id=0x00, max_device_count=0xFF):
        return OneControlProtocol._le_u16(command_id) + bytes([0x01, device_table_id, start_device_id, max_device_count])

    @staticmethod
    def build_get_devices_metadata(command_id, device_table_id, start_device_id=0x00, max_device_count=0xFF):
        return OneControlProtocol._le_u16(command_id) + bytes([0x02, device_table_id, start_device_id, max_device_count])

    @staticmethod
    def build_action_switch(command_id, device_table_id, switch_state, device_ids):
        if not device_ids:
            raise ValueError("At least one device ID required")
        state_byte = 0x01 if switch_state else 0x00
        payload = bytes(device_ids)
        return OneControlProtocol._le_u16(command_id) + bytes([0x40, device_table_id, state_byte]) + payload

    @staticmethod
    def build_action_dimmable(command_id, device_table_id, device_id, brightness, mode=-1):
        b = max(0, min(255, int(brightness)))
        if mode >= 0:
            mode_byte = max(0, min(127, int(mode)))
        else:
            mode_byte = 0x00 if b == 0 else 0x01

        header = OneControlProtocol._le_u16(command_id) + bytes([0x43, device_table_id, device_id])
        if mode_byte in (0x00, 0x7F):
            payload = bytes([mode_byte])
        else:
            payload = bytes([mode_byte, b, 0x00])
        return header + payload

    @staticmethod
    def build_action_rgb(command_id, device_table_id, device_id, mode, red=0, green=0, blue=0, auto_off=0xFF, blink_on_interval=207, blink_off_interval=207, transition_interval_ms=750):
        header = OneControlProtocol._le_u16(command_id) + bytes([0x44, device_table_id, device_id])
        mode = int(mode)
        
        # Mode definitions: 0/127=Simple, 1=Solid, 2=Blink, 3=Fade
        if mode in (0, 127):
            payload = bytes([mode])
        elif mode == 1:
            payload = bytes([
                mode,
                max(0, min(255, int(red))),
                max(0, min(255, int(green))),
                max(0, min(255, int(blue))),
                max(0, min(255, int(auto_off))),
            ])
        elif mode == 2:
            payload = bytes([
                mode,
                max(0, min(255, int(red))),
                max(0, min(255, int(green))),
                max(0, min(255, int(blue))),
                max(0, min(255, int(auto_off))),
                max(0, min(255, int(blink_on_interval))),
                max(0, min(255, int(blink_off_interval))),
            ])
        else:
            payload = bytes([
                mode,
                max(0, min(255, int(auto_off))),
                (transition_interval_ms >> 8) & 0xFF,
                transition_interval_ms & 0xFF,
            ])
        return header + payload

    @staticmethod
    def build_action_hvac(command_id, device_table_id, device_id, heat_mode, heat_source, fan_mode, low_trip_temp_f, high_trip_temp_f):
        command_byte = (heat_mode & 0x07) | ((heat_source & 0x03) << 4) | ((fan_mode & 0x03) << 6)
        return OneControlProtocol._le_u16(command_id) + bytes([
            0x45, device_table_id, device_id,
            command_byte,
            max(0, min(255, int(low_trip_temp_f))),
            max(0, min(255, int(high_trip_temp_f))),
        ])

    @staticmethod
    def build_action_generator(command_id, device_table_id, device_id, turn_on):
        return OneControlProtocol._le_u16(command_id) + bytes([0x42, device_table_id, device_id, 0x01 if turn_on else 0x00])

    # --- Events ---

    @staticmethod
    def decode_gateway_information(data):
        if len(data) < 13:
            return None
        # Use struct unpacking for cleaner syntax
        # < = little endian, B = unsigned char (1 byte), I = unsigned int (4 bytes)
        # Format: (skip 1), B, B, B, B, I, I
        try:
            _, proto_ver, options, dev_count, table_id, table_crc, meta_crc = struct.unpack("<BBBBBII", data[0:13])
            return {
                "protocol_version": proto_ver,
                "options": options,
                "device_count": dev_count,
                "device_table_id": table_id,
                "device_table_crc": table_crc,
                "device_metadata_table_crc": meta_crc,
            }
        except struct.error:
            return None

    @staticmethod
    def decode_rv_status(data):
        if len(data) < 6:
            return None
        
        voltage_raw = (data[1] << 8) | data[2]
        temp_raw = (data[3] << 8) | data[4]
        features = data[5]

        voltage = None if voltage_raw == 0xFFFF else voltage_raw / 256.0
        
        temperature = None
        if temp_raw != 0x7FFF:
            # Handle signed 16-bit temperature
            signed = temp_raw - 0x10000 if temp_raw & 0x8000 else temp_raw
            temperature = signed / 256.0

        return {
            "battery_voltage": voltage,
            "external_temperature_c": temperature,
            "voltage_available": (features & 0x01) != 0,
            "temperature_available": (features & 0x02) != 0,
        }

    @staticmethod
    def decode_tank_status(data):
        if len(data) < 3 or data[0] != 0x0C:
            return None
        
        table_id = data[1]
        tanks = []
        for i in range(2, len(data) - 1, 2):
            tanks.append({
                "device_id": data[i],
                "percent": data[i+1]
            })
        
        return {"device_table_id": table_id, "tanks": tanks}

    @staticmethod
    def decode_hvac_status(data):
        if len(data) < 13 or data[0] != 0x0B:
            return None
            
        table_id = data[1]
        zones = []
        bytes_per_zone = 11
        invalid_sentinels = {0x8000, 0x2FF0}

        def decode_temp(raw):
            if raw in invalid_sentinels:
                return None
            signed = raw - 0x10000 if raw & 0x8000 else raw
            return signed / 256.0
            
        for i in range(2, len(data) - bytes_per_zone + 1, bytes_per_zone):
            chunk = data[i : i + bytes_per_zone]
            # device_id(0), command(1), low(2), high(3), status(4), indoor(5-6), outdoor(7-8), dtc(9-10)
            
            indoor_raw = (chunk[5] << 8) | chunk[6]
            outdoor_raw = (chunk[7] << 8) | chunk[8]
            dtc = (chunk[9] << 8) | chunk[10]
            
            zones.append({
                "device_id": chunk[0],
                "command_byte": chunk[1],
                "low_trip_temp_f": chunk[2],
                "high_trip_temp_f": chunk[3],
                "zone_status": chunk[4],
                "indoor_temp_f": decode_temp(indoor_raw),
                "outdoor_temp_f": decode_temp(outdoor_raw),
                "dtc": dtc,
            })
            
        return {"device_table_id": table_id, "zones": zones}

    # --- Status Parsers (formerly device_status_parser.py) ---

    @staticmethod
    def parse_relay_status(data):
        if len(data) < 2:
            return []
        
        table_id = data[1]
        statuses = []
        # Pairs of (device_id, state)
        for i in range(2, len(data) - 1, 2):
            statuses.append({
                "device_table_id": table_id,
                "device_id": data[i],
                "state": data[i+1]
            })
        return statuses

    @staticmethod
    def parse_dimmable_status(data):
        if len(data) < 2:
            return []
        
        table_id = data[1]
        statuses = []
        # Chunks of 9: device_id(1) + status_bytes(8)
        chunk_size = 9
        
        for i in range(2, len(data) - chunk_size + 1, chunk_size):
            statuses.append({
                "device_table_id": table_id,
                "device_id": data[i],
                "status_bytes": bytes(data[i+1 : i+chunk_size])
            })
        return statuses
        
    @staticmethod
    def extract_brightness(status_bytes):
        return status_bytes[3] if len(status_bytes) >= 4 else None

    @staticmethod
    def extract_on_off_state(status_bytes):
        return (status_bytes[0] > 0) if len(status_bytes) >= 1 else None

    # --- V2 CAN-over-BLE Message Parsing ---
    # Handles Packed (0x01), 11-bit (0x02), and 29-bit (0x03) CAN frames
    # received through the BLE data characteristic.

    @staticmethod
    def parse_v2_message(raw_message):
        """Parse a V2 CAN-over-BLE message into CAN frame(s)."""
        if not raw_message:
            return []
        message_type = raw_message[0]
        if message_type == 1:
            return OneControlProtocol._parse_packed_message(raw_message)
        if message_type == 2:
            return OneControlProtocol._parse_eleven_bit_message(raw_message)
        if message_type == 3:
            return OneControlProtocol._parse_twenty_nine_bit_message(raw_message)
        return []

    @staticmethod
    def _parse_packed_message(raw_message):
        if len(raw_message) < 19:
            return []
        device_address = raw_message[1]
        network_status = raw_message[2]
        ids_can_version = raw_message[3]
        device_mac = raw_message[4:10]
        product_id = raw_message[10:12]
        product_instance = raw_message[12]
        device_type = raw_message[13]
        function_name = raw_message[14:16]
        device_instance = raw_message[16]
        device_capabilities = raw_message[17]
        data_length = raw_message[18]
        status_data = raw_message[19:19 + data_length] if len(raw_message) >= 19 + data_length else b""

        messages = []
        msg1 = bytearray(12)
        msg1[0] = 11
        msg1[1] = 8
        msg1[2] = 0
        msg1[3] = device_address
        msg1[4] = network_status
        msg1[5] = ids_can_version
        msg1[6:12] = device_mac
        messages.append(bytes(msg1))

        msg2 = bytearray(12)
        msg2[0] = 11
        msg2[1] = 8
        msg2[2] = 2
        msg2[3] = device_address
        msg2[4:6] = product_id
        msg2[6] = product_instance
        msg2[7] = device_type
        msg2[8:10] = function_name
        msg2[10] = device_instance
        msg2[11] = device_capabilities
        messages.append(bytes(msg2))

        if data_length > 0:
            msg3 = bytearray(4 + data_length)
            msg3[0] = 3 + data_length
            msg3[1] = data_length
            msg3[2] = 3
            msg3[3] = device_address
            msg3[4:] = status_data
            messages.append(bytes(msg3))
        return messages

    @staticmethod
    def _parse_eleven_bit_message(raw_message):
        if len(raw_message) < 6:
            return []
        message_type = raw_message[3]
        device_address = raw_message[4]
        data_length = raw_message[5]
        if len(raw_message) < 6 + data_length:
            return []
        msg = bytearray(4 + data_length)
        msg[0] = 3 + data_length
        msg[1] = data_length
        msg[2] = message_type
        msg[3] = device_address
        msg[4:] = raw_message[6:6 + data_length]
        return [bytes(msg)]

    @staticmethod
    def _parse_twenty_nine_bit_message(raw_message):
        if len(raw_message) < 6:
            return []
        data_length = raw_message[5]
        if len(raw_message) < 6 + data_length:
            return []
        msg = bytearray(6 + data_length)
        msg[0] = 5 + data_length
        msg[1] = data_length
        msg[2:6] = raw_message[1:5]
        msg[6:] = raw_message[6:6 + data_length]
        return [bytes(msg)]

    @staticmethod
    def extract_myrvlink_event_data(can_message):
        """Extract event data from a parsed CAN message."""
        if len(can_message) < 2:
            return None
        return bytes(can_message[2:])

