"""CAN-to-MQTT topic routing."""

TOPIC_RAW = "can/raw"
TOPIC_DIAGNOSTICS = "can/diagnostics"
TOPIC_TIMESTAMPED = "can/timestamped"
TOPIC_DIAGNOSTICS_TIMESTAMPED = "can/diagnostics-timestamped"

# RV-C DM_RV is data page 1. SAE J1939 DM1 has the same FECA PGN bytes on
# data page 0 and uses a different payload layout.
RV_C_DIAGNOSTIC_PGNS = {(1, 0xFE, 0xCA)}
FILTERED_PGNS = {
    (0xFF, 0xB8),  # 1FFB8 DIGITAL_INPUT_STATUS
    (0xFF, 0xFF),  # 1FFFF DATE_TIME_STATUS
}


def should_publish_can_id(arbitration_id):
    """Return whether an inbound CAN frame belongs on MQTT."""
    pdu_format = (arbitration_id >> 16) & 0xFF
    pdu_specific = (arbitration_id >> 8) & 0xFF
    return (pdu_format, pdu_specific) not in FILTERED_PGNS


def topic_for_can_id(arbitration_id):
    """Return the MQTT topic for a 29-bit CAN identifier."""
    data_page = (arbitration_id >> 24) & 0x01
    pdu_format = (arbitration_id >> 16) & 0xFF
    pdu_specific = (arbitration_id >> 8) & 0xFF
    if (data_page, pdu_format, pdu_specific) in RV_C_DIAGNOSTIC_PGNS:
        return TOPIC_DIAGNOSTICS
    return TOPIC_RAW


def timestamped_topic_for_can_id(arbitration_id):
    """Return the timestamp-preserving companion topic for a CAN identifier."""
    if topic_for_can_id(arbitration_id) == TOPIC_DIAGNOSTICS:
        return TOPIC_DIAGNOSTICS_TIMESTAMPED
    return TOPIC_TIMESTAMPED


def format_timestamped_frame(message, interface):
    """Format python-can input as a candump -L compatible source record."""
    can_id = (
        f"{message.arbitration_id:08X}"
        if message.is_extended_id
        else f"{message.arbitration_id:03X}"
    )
    return (
        f"({message.timestamp:.6f}) {interface} "
        f"{can_id}#{message.data.hex().upper()}"
    )
