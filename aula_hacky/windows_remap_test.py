from __future__ import annotations

import argparse
import time

from aula_hacky.windows_hid import (
    enumerate_hid_devices,
    hid_get_feature,
    hid_set_feature,
    open_hid_device,
    close_handle,
)

WIRED_VID = 0x0C45
WIRED_PID = 0x800A
CONTROL_USAGE_PAGE = 0xFF13
CONTROL_USAGE = 0x0001
CABLE_PACKET_SIZE = 64

# Key remap types
REMAP_CAPS_TO_CTRL = 0x01
REMAP_CAPS_TO_ALT = 0x02  # speculative
REMAP_CAPS_OFF = 0x00

# USB HID keycodes (for direct key-to-key remapping)
KEYCODES = {
    "A": 0x04, "B": 0x05, "C": 0x06, "D": 0x07, "E": 0x08, "F": 0x09,
    "G": 0x0a, "H": 0x0b, "I": 0x0c, "J": 0x0d, "K": 0x0e, "L": 0x0f,
    "M": 0x10, "N": 0x11, "O": 0x12, "P": 0x13, "Q": 0x14, "R": 0x15,
    "S": 0x16, "T": 0x17, "U": 0x18, "V": 0x19, "W": 0x1a, "X": 0x1b,
    "Y": 0x1c, "Z": 0x1d,
    "1": 0x1e, "2": 0x1f, "3": 0x20, "4": 0x21, "5": 0x22,
    "6": 0x23, "7": 0x24, "8": 0x25, "9": 0x26, "0": 0x27,
    "ENTER": 0x28, "ESC": 0x29, "BACKSPACE": 0x2a, "TAB": 0x2b,
    "SPACE": 0x2c, "CAPSLOCK": 0x39,
    "LEFT_CTRL": 0xe0, "LEFT_SHIFT": 0xe1, "LEFT_ALT": 0xe2,
    "LEFT_META": 0xe3, "RIGHT_CTRL": 0xe4, "RIGHT_SHIFT": 0xe5,
    "RIGHT_ALT": 0xe6, "RIGHT_META": 0xe7,
}


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
    packet[1] = 0x18
    return bytes(packet)


def build_keymap_prepare():
    packet = bytearray(CABLE_PACKET_SIZE)
    packet[0] = 0x04
    packet[1] = 0x11
    packet[8] = 0x09
    return bytes(packet)


def build_apply():
    packet = bytearray(CABLE_PACKET_SIZE)
    packet[0] = 0x04
    packet[1] = 0x02
    return bytes(packet)


def build_finish():
    packet = bytearray(CABLE_PACKET_SIZE)
    packet[0] = 0x04
    packet[1] = 0xF0
    return bytes(packet)


def build_remap_data_capslock(enabled: int):
    data = bytearray(CABLE_PACKET_SIZE)
    data[0] = 0x02
    data[1] = enabled
    return bytes(data)


def send_capslock_remap(enabled: bool, debug: bool = False,
                         control_path: str | None = None):
    if control_path:
        from aula_hacky.windows_tft_upload import normalize_hid_path
        ctl_path = normalize_hid_path(control_path)
        feature_size = 65
    else:
        ctl_path, feature_size = find_device(CONTROL_USAGE_PAGE, CONTROL_USAGE)

    ctl_handle = open_hid_device(ctl_path)
    val = REMAP_CAPS_TO_CTRL if enabled else REMAP_CAPS_OFF

    if debug:
        print(f"Device: {ctl_path}")
        print()

    try:
        # 1. Begin
        begin = build_begin()
        if debug:
            print(f"[1] begin set: {begin[:8].hex()}")
        hid_set_feature(ctl_handle, 0, begin)
        time.sleep(0.05)

        resp = hid_get_feature(ctl_handle, 0, feature_size)
        if debug:
            print(f"[1] begin get: {resp[:8].hex()}")
        time.sleep(0.04)

        # 2. Keymap prepare
        prepare = build_keymap_prepare()
        if debug:
            print(f"[2] keymap prepare set: {prepare[:8].hex()}")
        hid_set_feature(ctl_handle, 0, prepare)
        time.sleep(0.05)

        resp = hid_get_feature(ctl_handle, 0, feature_size)
        if debug:
            print(f"[2] keymap prepare get: {resp[:8].hex()}")
        time.sleep(0.04)

        # 3. Send remap data
        remap_data = build_remap_data_capslock(val)
        if debug:
            print(f"[3] remap data set: {remap_data[:8].hex()}")
        hid_set_feature(ctl_handle, 0, remap_data)
        time.sleep(0.05)

        resp = hid_get_feature(ctl_handle, 0, feature_size)
        if debug:
            print(f"[3] remap data get: {resp[:8].hex()}")
        time.sleep(0.04)

        # 4. Apply
        apply_pkt = build_apply()
        if debug:
            print(f"[4] apply set: {apply_pkt[:8].hex()}")
        hid_set_feature(ctl_handle, 0, apply_pkt)
        time.sleep(0.05)

        resp = hid_get_feature(ctl_handle, 0, feature_size)
        if debug:
            print(f"[4] apply get: {resp[:8].hex()}")
        time.sleep(0.04)

        # 5. Finish
        finish = build_finish()
        if debug:
            print(f"[5] finish set: {finish[:8].hex()}")
        hid_set_feature(ctl_handle, 0, finish)
        time.sleep(0.05)

        resp = hid_get_feature(ctl_handle, 0, feature_size)
        if debug:
            print(f"[5] finish get: {resp[:8].hex()}")

        state = "ON" if enabled else "OFF"
        print(f"Caps Lock -> Ctrl: {state}")

    finally:
        close_handle(ctl_handle)


def main():
    parser = argparse.ArgumentParser(description="Remap keys on AULA F75 Max")
    parser.add_argument("--caps-to-ctrl", choices=["on", "off"],
                        help="Toggle Caps Lock -> Ctrl mapping")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--control-path", help="MI_03 HID path")
    args = parser.parse_args()

    if args.caps_to_ctrl:
        send_capslock_remap(
            enabled=(args.caps_to_ctrl == "on"),
            debug=args.debug,
            control_path=args.control_path,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
