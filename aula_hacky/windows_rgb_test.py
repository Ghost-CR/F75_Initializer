from __future__ import annotations

import argparse
import time

from aula_hacky.protocol_core import (
    CABLE_PACKET_SIZE,
    CABLE_SESSION_INIT_IN,
    CABLE_SESSION_INIT_OUT,
    CABLE_SESSION_FINALIZE_IN,
    CABLE_SESSION_FINALIZE_OUT,
)
from aula_hacky.windows_hid import (
    enumerate_hid_devices,
    hid_get_feature,
    hid_set_feature,
    open_hid_device,
    close_handle,
)

WIRED_VID = 0x0C45
WIRED_PID = 0x800A
RGB_USAGE_PAGE = 0xFF13
RGB_USAGE = 0x0001


def find_control_device():
    for dev in enumerate_hid_devices():
        if (dev["vid"] == WIRED_VID and dev["pid"] == WIRED_PID
                and dev["usage_page"] == RGB_USAGE_PAGE
                and dev["usage"] == RGB_USAGE):
            return dev["path"], dev["feature_report_bytes"]
    raise RuntimeError("No MI_03 control device found. Is the keyboard connected via USB-C?")


def build_rgb_select():
    select = bytearray(CABLE_PACKET_SIZE)
    select[0] = 0x04
    select[1] = 0x13
    select[8] = 0x01
    return bytes(select)


def build_rgb_payload(mode: int, red: int, green: int, blue: int,
                      brightness: int = 5, speed: int = 3, direction: int = 0,
                      colorful: int = 0) -> bytes:
    payload = bytearray(CABLE_PACKET_SIZE)
    payload[0] = mode
    if mode != 0:
        payload[1] = red & 0xFF
        payload[2] = green & 0xFF
        payload[3] = blue & 0xFF
        payload[8] = colorful
        payload[9] = brightness
        payload[10] = speed
        payload[11] = direction
    payload[14] = 0xAA
    payload[15] = 0x55
    return bytes(payload)


def build_rgb_finish():
    finish = bytearray(CABLE_PACKET_SIZE)
    finish[0] = 0x04
    finish[1] = 0xF0
    return bytes(finish)


def hex_bytes(data: bytes) -> str:
    return data[:32].hex() + ("..." if len(data) > 32 else "")


def send_color(red: int, green: int, blue: int, mode: int = 1,
               brightness: int = 5, speed: int = 3, direction: int = 0,
               debug: bool = False, control_path: str | None = None,
               no_apply: bool = False):
    if control_path:
        from aula_hacky.windows_tft_upload import normalize_hid_path
        path = normalize_hid_path(control_path)
        feature_size = 65
    else:
        path, feature_size = find_control_device()

    handle = open_hid_device(path)
    if debug:
        print(f"Device: {path}")
        print(f"Feature report size: {feature_size}")
        print()

    try:
        # 1. Begin
        if debug:
            print(f"begin set: {hex_bytes(CABLE_SESSION_INIT_OUT)}")
        hid_set_feature(handle, 0, CABLE_SESSION_INIT_OUT)
        time.sleep(0.05)

        resp = hid_get_feature(handle, 0, feature_size)
        if debug:
            print(f"begin get: {hex_bytes(resp)}")
        time.sleep(0.04)

        # 2. Select RGB
        select = build_rgb_select()
        if debug:
            print(f"select set: {hex_bytes(select)}")
        hid_set_feature(handle, 0, select)
        time.sleep(0.05)

        resp = hid_get_feature(handle, 0, feature_size)
        if debug:
            print(f"select get: {hex_bytes(resp)}")
        time.sleep(0.04)

        # 3. Payload
        payload = build_rgb_payload(mode, red, green, blue,
                                     brightness, speed, direction, colorful=0)
        if debug:
            print(f"payload set: {hex_bytes(payload)}")
        hid_set_feature(handle, 0, payload)
        time.sleep(0.05)

        resp = hid_get_feature(handle, 0, feature_size)
        if debug:
            print(f"payload get: {hex_bytes(resp)}")
        time.sleep(0.04)

        if no_apply:
            if debug:
                print("Skipping apply (--no-apply)")
            return

        # 4. Apply
        if debug:
            print(f"apply set: {hex_bytes(CABLE_SESSION_FINALIZE_OUT)}")
        hid_set_feature(handle, 0, CABLE_SESSION_FINALIZE_OUT)
        time.sleep(0.05)

        resp = hid_get_feature(handle, 0, feature_size)
        if debug:
            print(f"apply get: {hex_bytes(resp)}")
        time.sleep(0.04)

        # 5. Finish
        finish = build_rgb_finish()
        if debug:
            print(f"finish set: {hex_bytes(finish)}")
        hid_set_feature(handle, 0, finish)
        time.sleep(0.05)

        print(f"RGB set: R={red} G={green} B={blue} mode={mode}")

    finally:
        close_handle(handle)


def main():
    parser = argparse.ArgumentParser(description="Set AULA F75 Max RGB color")
    parser.add_argument("--red", type=int, default=255, help="Red (0-255)")
    parser.add_argument("--green", type=int, default=0, help="Green (0-255)")
    parser.add_argument("--blue", type=int, default=0, help="Blue (0-255)")
    parser.add_argument("--mode", type=int, default=1, help="RGB mode (default 1=Static)")
    parser.add_argument("--brightness", type=int, default=5, help="Brightness (0-5)")
    parser.add_argument("--speed", type=int, default=3, help="Speed (0-5)")
    parser.add_argument("--direction", type=int, default=0, help="Direction (0-3)")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--no-apply", action="store_true", help="Send begin+select+payload only (no apply)")
    parser.add_argument(
        "--control-path",
        help="full HID path for MI_03",
    )
    args = parser.parse_args()

    if not 0 <= args.red <= 255:
        parser.error("--red must be 0-255")
    if not 0 <= args.green <= 255:
        parser.error("--green must be 0-255")
    if not 0 <= args.blue <= 255:
        parser.error("--blue must be 0-255")

    send_color(
        red=args.red, green=args.green, blue=args.blue,
        mode=args.mode, brightness=args.brightness,
        speed=args.speed, direction=args.direction,
        debug=args.debug, control_path=args.control_path,
        no_apply=args.no_apply,
    )


if __name__ == "__main__":
    main()
