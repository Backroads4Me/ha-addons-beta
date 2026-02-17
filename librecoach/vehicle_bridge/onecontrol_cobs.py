FRAME_CHAR = 0x00
MAX_DATA_BYTES = 63
FRAME_BYTE_COUNT_LSB = 64
MAX_COMPRESSED_FRAME_BYTES = 192


class Crc8:
    RESET_VALUE = 0x55
    TABLE = [
        0, 94, 188, 226, 97, 63, 221, 131, 194, 156,
        126, 32, 163, 253, 31, 65, 157, 195, 33, 127,
        252, 162, 64, 30, 95, 1, 227, 189, 62, 96,
        130, 220, 35, 125, 159, 193, 66, 28, 254, 160,
        225, 191, 93, 3, 128, 222, 60, 98, 190, 224,
        2, 92, 223, 129, 99, 61, 124, 34, 192, 158,
        29, 67, 161, 255, 70, 24, 250, 164, 39, 121,
        155, 197, 132, 218, 56, 102, 229, 187, 89, 7,
        219, 133, 103, 57, 186, 228, 6, 88, 25, 71,
        165, 251, 120, 38, 196, 154, 101, 59, 217, 135,
        4, 90, 184, 230, 167, 249, 27, 69, 198, 152,
        122, 36, 248, 166, 68, 26, 153, 199, 37, 123,
        58, 100, 134, 216, 91, 5, 231, 185, 140, 210,
        48, 110, 237, 179, 81, 15, 78, 16, 242, 172,
        47, 113, 147, 205, 17, 79, 173, 243, 112, 46,
        204, 146, 211, 141, 111, 49, 178, 236, 14, 80,
        175, 241, 19, 77, 206, 144, 114, 44, 109, 51,
        209, 143, 12, 82, 176, 238, 50, 108, 142, 208,
        83, 13, 239, 177, 240, 174, 76, 18, 145, 207,
        45, 115, 202, 148, 118, 40, 171, 245, 23, 73,
        8, 86, 180, 234, 105, 55, 213, 139, 87, 9,
        235, 181, 54, 104, 138, 212, 151, 201, 41, 119,
        244, 170, 72, 22, 233, 183, 85, 11, 136, 214,
        52, 106, 43, 117, 151, 201, 74, 20, 246, 168,
        116, 42, 200, 150, 21, 75, 169, 247, 182, 232,
        10, 84, 215, 137, 107, 53
    ]

    def __init__(self):
        self._value = self.RESET_VALUE

    @property
    def value(self):
        return self._value & 0xFF

    def reset(self):
        self._value = self.RESET_VALUE

    def update(self, byte_val):
        self._value = self.TABLE[(self._value ^ (byte_val & 0xFF)) & 0xFF] & 0xFF

    @classmethod
    def calculate(cls, data, offset=0, count=None):
        if count is None:
            count = len(data) - offset
        crc = cls.RESET_VALUE
        for i in range(offset, offset + count):
            crc = cls.TABLE[(crc ^ (data[i] & 0xFF)) & 0xFF] & 0xFF
        return crc


class CobsByteDecoder:
    def __init__(self, use_crc=True):
        self.use_crc = use_crc
        self.code_byte = 0
        self.output = bytearray(382)
        self.dest_index = 0
        self.min_payload = 1 if use_crc else 0

    def decode_byte(self, byte_val):
        if byte_val == FRAME_CHAR:
            if self.code_byte != 0:
                self.reset()
                return None
            if self.dest_index <= self.min_payload:
                self.reset()
                return None
            if self.use_crc:
                received_crc = self.output[self.dest_index - 1]
                self.dest_index -= 1
                calculated = Crc8.calculate(self.output, 0, self.dest_index)
                if calculated != received_crc:
                    self.reset()
                    return None
            result = bytes(self.output[: self.dest_index])
            self.reset()
            return result

        if self.code_byte <= 0:
            self.code_byte = byte_val & 0xFF
        else:
            self.code_byte -= 1
            self.output[self.dest_index] = byte_val
            self.dest_index += 1

        if (self.code_byte & MAX_DATA_BYTES) == 0:
            while self.code_byte > 0:
                self.output[self.dest_index] = FRAME_CHAR
                self.dest_index += 1
                self.code_byte -= FRAME_BYTE_COUNT_LSB

        return None

    def reset(self):
        self.code_byte = 0
        self.dest_index = 0

    def has_partial_data(self):
        return self.code_byte > 0 or self.dest_index > 0


def decode(data, use_crc=True):
    if not data:
        return None
    output = []
    code_byte = 0
    min_payload = 1 if use_crc else 0

    for byte_val in data:
        if byte_val == FRAME_CHAR:
            if code_byte != 0:
                return None
            if len(output) <= min_payload:
                return None
            if use_crc:
                received = output.pop()
                calculated = Crc8.calculate(output)
                if received != calculated:
                    return None
            return bytes(output)
        if code_byte == 0:
            code_byte = byte_val & 0xFF
        else:
            code_byte -= 1
            output.append(byte_val)
        if (code_byte & MAX_DATA_BYTES) == 0:
            while code_byte > 0:
                output.append(FRAME_CHAR)
                code_byte -= FRAME_BYTE_COUNT_LSB

    return None


def encode(data, prepend_start_frame=True, use_crc=True):
    output = bytearray(382)
    output_index = 0

    if prepend_start_frame:
        output[output_index] = FRAME_CHAR
        output_index += 1

    if not data:
        return bytes(output[:output_index])

    source_count = len(data)
    total_count = source_count + 1 if use_crc else source_count
    crc = Crc8()
    src_index = 0

    while src_index < total_count:
        code_index = output_index
        code = 0
        output[output_index] = 0xFF
        output_index += 1

        while src_index < total_count:
            if src_index < source_count:
                byte_val = data[src_index]
                if byte_val == FRAME_CHAR:
                    break
                crc.update(byte_val)
            else:
                byte_val = crc.value
                if byte_val == FRAME_CHAR:
                    break
            src_index += 1
            output[output_index] = byte_val
            output_index += 1
            code += 1
            if code >= MAX_DATA_BYTES:
                break

        while src_index < total_count:
            byte_val = data[src_index] if src_index < source_count else crc.value
            if byte_val != FRAME_CHAR:
                break
            crc.update(FRAME_CHAR)
            src_index += 1
            code += FRAME_BYTE_COUNT_LSB
            if code >= MAX_COMPRESSED_FRAME_BYTES:
                break

        output[code_index] = code & 0xFF

    output[output_index] = FRAME_CHAR
    output_index += 1

    return bytes(output[:output_index])
