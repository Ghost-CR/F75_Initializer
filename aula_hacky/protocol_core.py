from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

PACKET_SIZE = 32
CABLE_PACKET_SIZE = 64

SESSION_INIT_OUT = bytes.fromhex(
    "0200000000000000000000000000000000000000000000000000000000000002"
)
SESSION_INIT_IN = bytes.fromhex(
    "02000040300000450c0a800801ffff0000000000000000000000000000000054"
)
SESSION_QUERY_OUT = bytes.fromhex(
    "2001000000000000000000000000000000000000000000000000000000000021"
)
SESSION_QUERY_IN = bytes.fromhex(
    "2001006400000000000000000000000000000000000000000000000000000085"
)
RTC_SET_ACK = bytes.fromhex(
    "0c1000000000000000000000000000000000000000000000000000000000001c"
)
CABLE_SESSION_INIT_OUT = bytes.fromhex(
    "04180000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
)
CABLE_SESSION_INIT_IN = bytes.fromhex(
    "04180001000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
)
CABLE_SESSION_PREPARE_OUT = bytes.fromhex(
    "04280000000000000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
)
CABLE_SESSION_PREPARE_IN = bytes.fromhex(
    "04280001000000000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
)
CABLE_RTC_SET_IN_EXAMPLE = bytes.fromhex(
    "00015a1a03140b0a120005000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000aa55"
)
CABLE_SESSION_FINALIZE_OUT = bytes.fromhex(
    "04020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
)
CABLE_SESSION_FINALIZE_IN = bytes.fromhex(
    "04020001000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
)


@dataclass(frozen=True)
class Transaction:
    name: str
    outgoing: bytes
    expected_reply_prefix: bytes
    expected_reply: bytes | None = None
    read_delay_seconds: float = 0.0
    post_delay_seconds: float = 0.0


def checksum(payload: bytes) -> int:
    if len(payload) != PACKET_SIZE - 1:
        raise ValueError(f"checksum expects {PACKET_SIZE - 1} bytes, got {len(payload)}")
    return sum(payload) & 0xFF


def finalize_packet(body: bytes) -> bytes:
    if len(body) != PACKET_SIZE - 1:
        raise ValueError(f"packet body must be {PACKET_SIZE - 1} bytes, got {len(body)}")
    return body + bytes([checksum(body)])


def build_rtc_set_packet(when: datetime) -> bytes:
    year = when.year - 2000
    if not 0 <= year <= 255:
        raise ValueError(f"year {when.year} cannot be encoded as year_since_2000")

    body = bytes(
        [
            0x0C,
            0x10,
            0x00,
            0x00,
            0x01,
            0x5A,
            year,
            when.month,
            when.day,
            when.hour,
            when.minute,
            when.second,
            0x00,
            0x05,
            0x00,
            0x00,
            0x00,
            0xAA,
            0x55,
        ]
        + [0x00] * 12
    )
    return finalize_packet(body)


def decode_rtc_set_packet(packet: bytes) -> dict[str, int]:
    validate_packet(packet)
    if packet[:6] != bytes([0x0C, 0x10, 0x00, 0x00, 0x01, 0x5A]):
        raise ValueError("packet does not look like an RTC set command")

    return {
        "year": 2000 + packet[6],
        "month": packet[7],
        "day": packet[8],
        "hour": packet[9],
        "minute": packet[10],
        "second": packet[11],
    }


def validate_packet(packet: bytes) -> None:
    if len(packet) != PACKET_SIZE:
        raise ValueError(f"packet must be {PACKET_SIZE} bytes, got {len(packet)}")
    if checksum(packet[:-1]) != packet[-1]:
        raise ValueError(
            f"invalid checksum: expected 0x{checksum(packet[:-1]):02x}, got 0x{packet[-1]:02x}"
        )


def validate_reply(reply: bytes, expected_prefix: bytes, exact: bytes | None = None) -> None:
    validate_packet(reply)
    if not reply.startswith(expected_prefix):
        raise ValueError(
            f"reply prefix mismatch: expected {expected_prefix.hex()}, got {reply.hex()}"
        )
    if exact is not None and reply != exact:
        raise ValueError(f"reply mismatch: expected {exact.hex()}, got {reply.hex()}")


def is_valid_reply(reply: bytes, expected_prefix: bytes, exact: bytes | None = None) -> bool:
    try:
        validate_reply(reply, expected_prefix, exact=exact)
    except ValueError:
        return False
    return True


def validate_cable_reply(reply: bytes, expected_prefix: bytes, exact: bytes | None = None) -> None:
    if len(reply) != CABLE_PACKET_SIZE:
        raise ValueError(f"cable reply must be {CABLE_PACKET_SIZE} bytes, got {len(reply)}")
    if not reply.startswith(expected_prefix):
        raise ValueError(
            f"cable reply prefix mismatch: expected {expected_prefix.hex()}, got {reply.hex()}"
        )
    if exact is not None and reply != exact:
        raise ValueError(f"cable reply mismatch: expected {exact.hex()}, got {reply.hex()}")


def is_valid_cable_reply(reply: bytes, expected_prefix: bytes, exact: bytes | None = None) -> bool:
    try:
        validate_cable_reply(reply, expected_prefix, exact=exact)
    except ValueError:
        return False
    return True


def iter_candidate_packets(raw_report: bytes) -> list[bytes]:
    candidates: list[bytes] = []
    seen: set[bytes] = set()

    def add(candidate: bytes) -> None:
        if candidate in seen:
            return
        seen.add(candidate)
        candidates.append(candidate)

    if len(raw_report) >= PACKET_SIZE:
        add(raw_report[:PACKET_SIZE])
        add(raw_report[-PACKET_SIZE:])

        for offset in range(0, len(raw_report) - PACKET_SIZE + 1):
            window = raw_report[offset : offset + PACKET_SIZE]
            try:
                validate_packet(window)
            except ValueError:
                continue
            add(window)

    return candidates


def build_transaction_sequence(when: datetime) -> list[Transaction]:
    return [
        Transaction(
            name="session-init",
            outgoing=SESSION_INIT_OUT,
            expected_reply_prefix=SESSION_INIT_OUT[:3],
            expected_reply=SESSION_INIT_IN,
        ),
        Transaction(
            name="session-query",
            outgoing=SESSION_QUERY_OUT,
            expected_reply_prefix=SESSION_QUERY_OUT[:3],
            expected_reply=SESSION_QUERY_IN,
        ),
        Transaction(
            name="rtc-set",
            outgoing=build_rtc_set_packet(when),
            expected_reply_prefix=bytes([0x0C, 0x10, 0x00, 0x00]),
            expected_reply=RTC_SET_ACK,
        ),
    ]


def build_cable_rtc_set_packet(when: datetime) -> bytes:
    year = when.year - 2000
    if not 0 <= year <= 255:
        raise ValueError(f"year {when.year} cannot be encoded as year_since_2000")

    body = bytearray(CABLE_PACKET_SIZE)
    body[0] = 0x00
    body[1] = 0x01
    body[2] = 0x5A
    body[3] = year
    body[4] = when.month
    body[5] = when.day
    body[6] = when.hour
    body[7] = when.minute
    body[8] = when.second
    body[9] = 0x00
    body[10] = 0x05
    body[-2] = 0xAA
    body[-1] = 0x55
    return bytes(body)


def build_cable_transaction_sequence(when: datetime) -> list[Transaction]:
    return [
        Transaction(
            name="cable-session-init",
            outgoing=CABLE_SESSION_INIT_OUT,
            expected_reply_prefix=bytes([0x04, 0x18]),
            expected_reply=CABLE_SESSION_INIT_IN,
            read_delay_seconds=0.036,
            post_delay_seconds=0.036,
        ),
        Transaction(
            name="cable-session-prepare",
            outgoing=CABLE_SESSION_PREPARE_OUT,
            expected_reply_prefix=bytes([0x04, 0x28]),
            expected_reply=CABLE_SESSION_PREPARE_IN,
            read_delay_seconds=0.036,
            post_delay_seconds=0.036,
        ),
        Transaction(
            name="cable-rtc-set",
            outgoing=build_cable_rtc_set_packet(when),
            expected_reply_prefix=bytes([0x00, 0x01, 0x5A]),
            expected_reply=build_cable_rtc_set_packet(when),
            read_delay_seconds=0.036,
            post_delay_seconds=0.036,
        ),
        Transaction(
            name="cable-session-finalize",
            outgoing=CABLE_SESSION_FINALIZE_OUT,
            expected_reply_prefix=bytes([0x04, 0x02]),
            expected_reply=CABLE_SESSION_FINALIZE_IN,
            read_delay_seconds=0.036,
        ),
    ]


def build_wireless_rgb_mode_packet(mode: int) -> bytes:
    if not 0 <= mode <= 31:
        raise ValueError(f"RGB mode must be in 0..31, got {mode}")

    body = bytearray(PACKET_SIZE - 1)
    body[0] = 0x05
    body[1] = 0x01
    body[2] = 0x00
    body[3] = mode + 0x1F
    body[17] = 0xAA
    body[18] = 0x55
    return finalize_packet(bytes(body))


def build_wireless_rgb_commit_packet() -> bytes:
    body = bytearray(PACKET_SIZE - 1)
    body[0] = 0x0F
    return finalize_packet(bytes(body))


def build_wireless_rgb_led_mode_packet(
    mode: int,
    brightness: int,
    speed: int,
    direction: int,
    colorful: int,
    color: int,
) -> bytes:
    if not 0 <= mode <= 31:
        raise ValueError(f"RGB mode must be in 0..31, got {mode}")
    if not 0 <= brightness <= 5:
        raise ValueError(f"RGB brightness must be in 0..5, got {brightness}")
    if not 0 <= speed <= 5:
        raise ValueError(f"RGB speed must be in 0..5, got {speed}")
    if not 0 <= direction <= 255:
        raise ValueError(f"RGB direction must be in 0..255, got {direction}")
    if not 0 <= colorful <= 255:
        raise ValueError(f"RGB colorful flag must be in 0..255, got {colorful}")
    if not 0 <= color <= 0xFFFFFF:
        raise ValueError(f"RGB color must be in 0..0xffffff, got 0x{color:x}")

    body = bytearray(PACKET_SIZE - 1)
    body[0] = 0x05
    body[1] = 0x10
    body[2] = 0x00
    body[3] = mode
    if mode != 0:
        body[4] = color & 0xFF
        body[5] = (color >> 8) & 0xFF
        body[6] = (color >> 16) & 0xFF
        body[11] = colorful
        body[12] = brightness
        body[13] = speed
        body[14] = direction
    body[17] = 0xAA
    body[18] = 0x55
    return finalize_packet(bytes(body))


def build_cable_rgb_transaction_sequence(
    mode: int,
    brightness: int,
    speed: int,
    direction: int,
    colorful: int,
    color: int,
) -> list[Transaction]:
    if not 0 <= mode <= 31:
        raise ValueError(f"RGB mode must be in 0..31, got {mode}")
    if not 0 <= brightness <= 5:
        raise ValueError(f"RGB brightness must be in 0..5, got {brightness}")
    if not 0 <= speed <= 5:
        raise ValueError(f"RGB speed must be in 0..5, got {speed}")
    if not 0 <= direction <= 255:
        raise ValueError(f"RGB direction must be in 0..255, got {direction}")
    if not 0 <= colorful <= 255:
        raise ValueError(f"RGB colorful flag must be in 0..255, got {colorful}")
    if not 0 <= color <= 0xFFFFFF:
        raise ValueError(f"RGB color must be in 0..0xffffff, got 0x{color:x}")

    select = bytearray(CABLE_PACKET_SIZE)
    select[0] = 0x04
    select[1] = 0x13
    select[8] = 0x01

    payload = bytearray(CABLE_PACKET_SIZE)
    payload[0] = mode
    if mode != 0:
        payload[1] = color & 0xFF
        payload[2] = (color >> 8) & 0xFF
        payload[3] = (color >> 16) & 0xFF
        payload[8] = colorful
        payload[9] = brightness
        payload[10] = speed
        payload[11] = direction
    payload[14] = 0xAA
    payload[15] = 0x55

    finish = bytearray(CABLE_PACKET_SIZE)
    finish[0] = 0x04
    finish[1] = 0xF0

    return [
        Transaction(
            name="cable-rgb-begin",
            outgoing=CABLE_SESSION_INIT_OUT,
            expected_reply_prefix=bytes([0x04, 0x18]),
            expected_reply=CABLE_SESSION_INIT_IN,
            read_delay_seconds=0.04,
            post_delay_seconds=0.04,
        ),
        Transaction(
            name="cable-rgb-select",
            outgoing=bytes(select),
            expected_reply_prefix=bytes([0x04, 0x13]),
            expected_reply=None,
            read_delay_seconds=0.04,
            post_delay_seconds=0.04,
        ),
        Transaction(
            name="cable-rgb-payload",
            outgoing=bytes(payload),
            expected_reply_prefix=bytes([mode]),
            expected_reply=None,
            read_delay_seconds=0.04,
            post_delay_seconds=0.04,
        ),
        Transaction(
            name="cable-rgb-apply",
            outgoing=CABLE_SESSION_FINALIZE_OUT,
            expected_reply_prefix=bytes([0x04, 0x02]),
            expected_reply=CABLE_SESSION_FINALIZE_IN,
            read_delay_seconds=0.04,
            post_delay_seconds=0.04,
        ),
        Transaction(
            name="cable-rgb-finish",
            outgoing=bytes(finish),
            expected_reply_prefix=bytes([0x04, 0xF0]),
            expected_reply=None,
            read_delay_seconds=0.04,
        ),
    ]


def parse_time_argument(value: str, now: datetime | None = None) -> datetime:
    if value == "now":
        return now or datetime.now().astimezone()

    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        return parsed.astimezone().replace(tzinfo=None)
    return parsed


__all__ = [
    "CABLE_PACKET_SIZE",
    "CABLE_RTC_SET_IN_EXAMPLE",
    "CABLE_SESSION_FINALIZE_IN",
    "CABLE_SESSION_FINALIZE_OUT",
    "CABLE_SESSION_INIT_IN",
    "CABLE_SESSION_INIT_OUT",
    "CABLE_SESSION_PREPARE_IN",
    "CABLE_SESSION_PREPARE_OUT",
    "PACKET_SIZE",
    "RTC_SET_ACK",
    "SESSION_INIT_IN",
    "SESSION_INIT_OUT",
    "SESSION_QUERY_IN",
    "SESSION_QUERY_OUT",
    "Transaction",
    "build_cable_rtc_set_packet",
    "build_cable_rgb_transaction_sequence",
    "build_cable_transaction_sequence",
    "build_rtc_set_packet",
    "build_transaction_sequence",
    "build_wireless_rgb_commit_packet",
    "build_wireless_rgb_led_mode_packet",
    "build_wireless_rgb_mode_packet",
    "checksum",
    "decode_rtc_set_packet",
    "finalize_packet",
    "is_valid_cable_reply",
    "is_valid_reply",
    "iter_candidate_packets",
    "parse_time_argument",
    "validate_cable_reply",
    "validate_packet",
    "validate_reply",
]
