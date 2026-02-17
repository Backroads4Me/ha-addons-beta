from onecontrol_const import (
    TEA_DELTA,
    TEA_CONSTANT_1,
    TEA_CONSTANT_2,
    TEA_CONSTANT_3,
    TEA_CONSTANT_4,
    TEA_ROUNDS,
)


def _uint32(value):
    return value & 0xFFFFFFFF


def encrypt(cypher, seed):
    delta = TEA_DELTA
    c = cypher & 0xFFFFFFFF
    s = seed & 0xFFFFFFFF

    for _ in range(TEA_ROUNDS):
        s = _uint32(s + (((c << 4) + TEA_CONSTANT_1) ^ (c + delta) ^ ((c >> 5) + TEA_CONSTANT_2)))
        c = _uint32(c + (((s << 4) + TEA_CONSTANT_3) ^ (s + delta) ^ ((s >> 5) + TEA_CONSTANT_4)))
        delta = _uint32(delta + TEA_DELTA)

    return s


def decrypt(cypher, encrypted):
    delta = _uint32(TEA_DELTA * TEA_ROUNDS)
    c = cypher & 0xFFFFFFFF
    s = encrypted & 0xFFFFFFFF

    for _ in range(TEA_ROUNDS):
        c = _uint32(c - (((s << 4) + TEA_CONSTANT_3) ^ (s + delta) ^ ((s >> 5) + TEA_CONSTANT_4)))
        s = _uint32(s - (((c << 4) + TEA_CONSTANT_1) ^ (c + delta) ^ ((c >> 5) + TEA_CONSTANT_2)))
        delta = _uint32(delta - TEA_DELTA)

    return s


def decrypt_byte_array(data, key):
    if len(data) % 8 != 0:
        return None
    if len(key) != 8:
        return None

    result = bytearray(len(data))
    key_long = _bytes_to_long(key, 0)

    for i in range(0, len(data), 8):
        block = _bytes_to_long(data, i)
        decrypted = decrypt(key_long, block)
        _long_to_bytes(decrypted, result, i)

    return bytes(result)


def _bytes_to_long(data, offset):
    return (
        (data[offset] & 0xFF)
        | ((data[offset + 1] & 0xFF) << 8)
        | ((data[offset + 2] & 0xFF) << 16)
        | ((data[offset + 3] & 0xFF) << 24)
        | ((data[offset + 4] & 0xFF) << 32)
        | ((data[offset + 5] & 0xFF) << 40)
        | ((data[offset + 6] & 0xFF) << 48)
        | ((data[offset + 7] & 0xFF) << 56)
    )


def _long_to_bytes(value, out, offset):
    out[offset] = value & 0xFF
    out[offset + 1] = (value >> 8) & 0xFF
    out[offset + 2] = (value >> 16) & 0xFF
    out[offset + 3] = (value >> 24) & 0xFF
    out[offset + 4] = (value >> 32) & 0xFF
    out[offset + 5] = (value >> 40) & 0xFF
    out[offset + 6] = (value >> 48) & 0xFF
    out[offset + 7] = (value >> 56) & 0xFF
