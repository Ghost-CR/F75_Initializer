from __future__ import annotations

import argparse
import time

from aula_hacky.windows_hid import (
    enumerate_hid_devices,
    hid_get_feature,
    hid_set_feature,
    hid_write_output,
    open_hid_device,
    close_handle,
)

WIRED_VID = 0x0C45
WIRED_PID = 0x800A
CONTROL_USAGE_PAGE = 0xFF13
CONTROL_USAGE = 0x0001
DATA_USAGE_PAGE = 0xFF68  # MI_02 for output reports
DATA_USAGE = 0x0061
CABLE_PACKET_SIZE = 64

# USB HID keycodes
KEYCODES = {
    "A": 0x04, "B": 0x05, "C": 0x06, "D": 0x07, "E": 0x08, "F": 0x09,
    "G": 0x0a, "H": 0x0b, "I": 0x0c, "J": 0x0d, "K": 0x0e, "L": 0x0f,
    "M": 0x10, "N": 0x11, "O": 0x12, "P": 0x13, "Q": 0x14, "R": 0x15,
    "S": 0x16, "T": 0x17, "U": 0x18, "V": 0x19, "W": 0x1a, "X": 0x1b,
    "Y": 0x1c, "Z": 0x1d,
    "1": 0x1e, "2": 0x1f, "3": 0x20, "4": 0x21, "5": 0x22,
    "6": 0x23, "7": 0x24, "8": 0x25, "9": 0x26, "0": 0x27,
    "ENTER": 0x28, "ESC": 0x29, "BACKSPACE": 0x2a, "TAB": 0x2b,
    "SPACE": 0x2c, "MINUS": 0x2d, "EQUAL": 0x2e, "LEFTBRACE": 0x2f,
    "RIGHTBRACE": 0x30, "BACKSLASH": 0x31, "SEMICOLON": 0x33,
    "QUOTE": 0x34, "TILDE": 0x35, "COMMA": 0x36, "DOT": 0x37,
    "SLASH": 0x38, "CAPSLOCK": 0x39,
    "F1": 0x3a, "F2": 0x3b, "F3": 0x3c, "F4": 0x3d, "F5": 0x3e,
    "F6": 0x3f, "F7": 0x40, "F8": 0x41, "F9": 0x42, "F10": 0x43,
    "F11": 0x44, "F12": 0x45,
    "LEFT_CTRL": 0xe0, "LEFT_SHIFT": 0xe1, "LEFT_ALT": 0xe2,
    "LEFT_META": 0xe3, "RIGHT_CTRL": 0xe4, "RIGHT_SHIFT": 0xe5,
    "RIGHT_ALT": 0xe6, "RIGHT_META": 0xe7,
}

KEY_DOWN = 0xB0
KEY_UP = 0x30


def find_device(usage_page: int, usage: int):
    for dev in enumerate_hid_devices():
        if (dev["vid"] == WIRED_VID and dev["pid"] == WIRED_PID
                and dev["usage_page"] == usage_page
                and dev["usage"] == usage):
            return dev["path"], dev["feature_report_bytes"]
    raise RuntimeError(f"No device found with usage_page=0x{usage_page:04X} usage=0x{usage:04X}")


def build_begin():
    packet = bytearray(CABLE_PACKET_SIZE)
    packet[0] = 0x04
    packet[1] = 0x19
    return bytes(packet)


def build_prepare(slot: int):
    packet = bytearray(CABLE_PACKET_SIZE)
    packet[0] = 0x04
    packet[1] = 0x15
    packet[8] = slot
    return bytes(packet)


def build_apply():
    packet = bytearray(CABLE_PACKET_SIZE)
    packet[0] = 0x04
    packet[1] = 0x02
    return bytes(packet)


def build_macro_data(keys: list[str]) -> bytes:
    data = bytearray()
    for key in keys:
        if key.upper() not in KEYCODES:
            raise ValueError(f"Unknown key: {key}")
        kc = KEYCODES[key.upper()]
        data.append(kc)
        data.append(KEY_DOWN)
        data.extend([0x0A, 0x00, 0x00, 0x50, 0x00, 0x00])
        data.append(kc)
        data.append(KEY_UP)
        data.extend([0x0A, 0x00, 0x00, 0x50, 0x00, 0x00])
    return bytes(data)


def send_macro(keys: list[str], slot: int = 2, debug: bool = False,
               control_path: str | None = None, pipe_path: str | None = None):
    if control_path:
        from aula_hacky.windows_tft_upload import normalize_hid_path
        ctl_path = normalize_hid_path(control_path)
        feature_size = 65
    else:
        ctl_path, feature_size = find_device(CONTROL_USAGE_PAGE, CONTROL_USAGE)

    ctl_handle = open_hid_device(ctl_path)

    pipe_handle = None
    if pipe_path:
        dta_path = normalize_hid_path(pipe_path)
        pipe_handle = open_hid_device(dta_path)

    if debug:
        print(f"Control: {ctl_path}")
        if pipe_handle:
            print(f"Data: {pipe_path}")
        print(f"Keys: {keys} -> slot {slot}")
        print()

    try:
        # 1. Begin
        begin = build_begin()
        if debug:
            print(f"[1] begin set: {begin.hex()}")
        hid_set_feature(ctl_handle, 0, begin)
        time.sleep(0.05)

        resp = hid_get_feature(ctl_handle, 0, feature_size)
        if debug:
            print(f"[1] begin get: {resp[:16].hex()}")
        time.sleep(0.04)

        # 2. Prepare
        prepare = build_prepare(slot)
        if debug:
            print(f"[2] prepare set: {prepare.hex()}")
        hid_set_feature(ctl_handle, 0, prepare)
        time.sleep(0.05)

        resp = hid_get_feature(ctl_handle, 0, feature_size)
        if debug:
            print(f"[2] prepare get: {resp[:16].hex()}")
        time.sleep(0.04)

        # 3. Send macro key data
        key_data = build_macro_data(keys)
        if debug:
            print(f"[3] macro data ({len(key_data)} bytes): {key_data.hex()}")

        if pipe_handle:
            pad = bytearray(4096)
            pad[:len(key_data)] = key_data
            if debug:
                print(f"[3] sending via MI_02 pipe (4096 bytes)")
            hid_write_output(pipe_handle, 0, bytes(pad))
        else:
            data_packet = bytearray(CABLE_PACKET_SIZE)
            data_packet[:len(key_data)] = key_data
            if debug:
                print(f"[3] sending via MI_03 feature (64 bytes)")
            hid_set_feature(ctl_handle, 0, bytes(data_packet))
        time.sleep(0.04)

        # 4. Apply
        apply_pkt = build_apply()
        if debug:
            print(f"[4] apply set: {apply_pkt.hex()}")
        hid_set_feature(ctl_handle, 0, apply_pkt)
        time.sleep(0.05)

        resp = hid_get_feature(ctl_handle, 0, feature_size)
        if debug:
            print(f"[4] apply get: {resp[:16].hex()}")
        time.sleep(0.04)

        print(f"Macro sent: {' + '.join(keys)} -> slot {slot}")

    finally:
        close_handle(ctl_handle)
        if pipe_handle:
            close_handle(pipe_handle)


def main():
    parser = argparse.ArgumentParser(description="Send macro to AULA F75 Max")
    parser.add_argument("keys", nargs="+", help="Key sequence (e.g. A B C)")
    parser.add_argument("--slot", type=int, default=2, help="Macro slot (default 2)")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--control-path", help="MI_03 HID path")
    parser.add_argument("--pipe-path", help="MI_02 HID path (for data)")
    args = parser.parse_args()

    send_macro(
        keys=args.keys,
        slot=args.slot,
        debug=args.debug,
        control_path=args.control_path,
        pipe_path=args.pipe_path,
    )


if __name__ == "__main__":
    main()
