from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from can_routing import (
    TOPIC_DIAGNOSTICS,
    TOPIC_DIAGNOSTICS_TIMESTAMPED,
    TOPIC_RAW,
    TOPIC_TIMESTAMPED,
    format_timestamped_frame,
    timestamped_topic_for_can_id,
    topic_for_can_id,
)


def test_rvc_dm_rv_uses_diagnostics_topic():
    assert topic_for_can_id(0x19FECA21) == TOPIC_DIAGNOSTICS


def test_j1939_dm1_remains_on_raw_topic():
    assert topic_for_can_id(0x18FECA21) == TOPIC_RAW


def test_unrelated_rvc_traffic_remains_on_raw_topic():
    assert topic_for_can_id(0x19FEDB21) == TOPIC_RAW


def test_timestamped_topics_preserve_diagnostic_separation():
    assert timestamped_topic_for_can_id(0x19FECA21) == TOPIC_DIAGNOSTICS_TIMESTAMPED
    assert timestamped_topic_for_can_id(0x18FECA21) == TOPIC_TIMESTAMPED


def test_timestamped_frame_is_candump_compatible():
    class Message:
        arbitration_id = 0x19FEDB21
        is_extended_id = True
        timestamp = 1704067200.125
        data = bytes.fromhex("0102030405060708")

    assert format_timestamped_frame(Message(), "can0") == (
        "(1704067200.125000) can0 19FEDB21#0102030405060708"
    )
