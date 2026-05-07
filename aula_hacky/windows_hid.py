from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

# Windows HID API via ctypes — no external dependencies.

create_file = ctypes.windll.kernel32.CreateFileW
close_handle = ctypes.windll.kernel32.CloseHandle
write_file = ctypes.windll.kernel32.WriteFile
read_file = ctypes.windll.kernel32.ReadFile

hid_dll = ctypes.windll.hid

HidD_GetAttributes = hid_dll.HidD_GetAttributes
HidD_GetPreparsedData = hid_dll.HidD_GetPreparsedData
HidP_GetCaps = hid_dll.HidP_GetCaps
HidD_FreePreparsedData = hid_dll.HidD_FreePreparsedData
HidD_SetFeature = hid_dll.HidD_SetFeature
HidD_GetFeature = hid_dll.HidD_GetFeature
HidD_SetOutputReport = hid_dll.HidD_SetOutputReport

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3


class HIDD_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Size", wintypes.ULONG),
        ("VendorID", wintypes.USHORT),
        ("ProductID", wintypes.USHORT),
        ("VersionNumber", wintypes.USHORT),
    ]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", wintypes.USHORT),
        ("UsagePage", wintypes.USHORT),
        ("InputReportByteLength", wintypes.USHORT),
        ("OutputReportByteLength", wintypes.USHORT),
        ("FeatureReportByteLength", wintypes.USHORT),
        ("Reserved", wintypes.USHORT * 17),
        ("NumberLinkCollectionNodes", wintypes.USHORT),
        ("NumberInputButtonCaps", wintypes.USHORT),
        ("NumberInputValueCaps", wintypes.USHORT),
        ("NumberInputDataIndices", wintypes.USHORT),
        ("NumberOutputButtonCaps", wintypes.USHORT),
        ("NumberOutputValueCaps", wintypes.USHORT),
        ("NumberOutputDataIndices", wintypes.USHORT),
        ("NumberFeatureButtonCaps", wintypes.USHORT),
        ("NumberFeatureValueCaps", wintypes.USHORT),
        ("NumberFeatureDataIndices", wintypes.USHORT),
    ]


def enumerate_hid_devices():
    """Yield (path, vid, pid, usage_page, usage, caps) for all HID devices."""
    from ctypes import wintypes

    setupapi = ctypes.windll.setupapi
    cfgmgr32 = ctypes.windll.cfgmgr32

    # {4D1E55B2-F16F-11CF-88CB-001111000030}
    hid_guid = (ctypes.c_byte * 16)(
        0xB2, 0x55, 0x1E, 0x4D, 0x6F, 0xF1, 0xCF, 0x11, 0x88, 0xCB,
        0x00, 0x11, 0x11, 0x00, 0x00, 0x30
    )

    DIGCF_PRESENT = 0x00000002
    DIGCF_DEVICEINTERFACE = 0x00000010

    h_info = setupapi.SetupDiGetClassDevsW(
        ctypes.byref(hid_guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    )
    if h_info == ctypes.c_void_p(-1).value:
        return

    try:
        # SP_DEVICE_INTERFACE_DATA: DWORD cbSize + GUID + DWORD Flags + ULONG_PTR Reserved
        _spdid_size = 32 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28

        index = 0
        while True:
            iface_data = ctypes.create_string_buffer(_spdid_size)
            ctypes.cast(iface_data, ctypes.POINTER(wintypes.DWORD))[0] = _spdid_size

            ok = setupapi.SetupDiEnumDeviceInterfaces(
                h_info, None, ctypes.byref(hid_guid), index, ctypes.byref(iface_data)
            )
            if not ok:
                break

            req_size = wintypes.DWORD()
            setupapi.SetupDiGetDeviceInterfaceDetailW(
                h_info, ctypes.byref(iface_data), None, 0, ctypes.byref(req_size), None
            )

            # SP_DEVICE_INTERFACE_DETAIL_DATA_W: DWORD cbSize + WCHAR DevicePath[ANYSIZE_ARRAY]
            # cbSize is 6 on both 32-bit and 64-bit (4 + 2 for first WCHAR)
            detail_size = req_size.value
            buf = ctypes.create_string_buffer(detail_size)
            ctypes.cast(buf, ctypes.POINTER(wintypes.DWORD))[0] = 6

            ok = setupapi.SetupDiGetDeviceInterfaceDetailW(
                h_info, ctypes.byref(iface_data), buf, detail_size, None, None
            )
            if ok:
                # WCHAR path starts at offset 4 (cbSize DWORD)
                path = ctypes.wstring_at(ctypes.addressof(buf) + 4)
                handle = create_file(
                    path,
                    0,
                    FILE_SHARE_READ | FILE_SHARE_WRITE,
                    None,
                    OPEN_EXISTING,
                    0,
                    None,
                )
                if handle != -1:
                    attrs = HIDD_ATTRIBUTES()
                    attrs.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
                    if HidD_GetAttributes(handle, ctypes.byref(attrs)):
                        preparsed = ctypes.c_void_p()
                        if HidD_GetPreparsedData(handle, ctypes.byref(preparsed)):
                            caps = HIDP_CAPS()
                            if HidP_GetCaps(preparsed, ctypes.byref(caps)) == 0:
                                yield {
                                    "path": path,
                                    "vid": attrs.VendorID,
                                    "pid": attrs.ProductID,
                                    "usage_page": caps.UsagePage,
                                    "usage": caps.Usage,
                                    "input_report_bytes": caps.InputReportByteLength,
                                    "output_report_bytes": caps.OutputReportByteLength,
                                    "feature_report_bytes": caps.FeatureReportByteLength,
                                }
                            HidD_FreePreparsedData(preparsed)
                    close_handle(handle)
            index += 1
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(h_info)


def open_hid_device(path: str) -> wintypes.HANDLE:
    handle = create_file(
        path,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        0,
        None,
    )
    if handle == -1:
        err = ctypes.get_last_error()
        raise OSError(f"Cannot open HID device {path}: error {err}")
    return handle


def hid_set_feature(handle, report_id: int, data: bytes) -> None:
    """Send HID feature report. Windows expects report_id prepended."""
    buf = bytes([report_id]) + data
    buf_size = len(buf)
    c_buf = ctypes.create_string_buffer(buf, buf_size)
    ok = HidD_SetFeature(handle, c_buf, buf_size)
    if not ok:
        err = ctypes.get_last_error()
        raise OSError(f"HidD_SetFeature failed: {err}")


def hid_get_feature(handle, report_id: int, length: int) -> bytes:
    """Read HID feature report. Windows expects report_id prepended."""
    buf = ctypes.create_string_buffer(length)
    buf.raw = bytes([report_id]) + bytes(length - 1)
    ok = HidD_GetFeature(handle, buf, length)
    if not ok:
        err = ctypes.get_last_error()
        raise OSError(f"HidD_GetFeature failed: {err}")
    return bytes(buf.raw)


def hid_write_output(handle, report_id: int, data: bytes) -> None:
    """Send HID output report via WriteFile. Windows expects report_id prepended."""
    buf = bytes([report_id]) + data
    buf_size = len(buf)
    c_buf = ctypes.create_string_buffer(buf, buf_size)
    written = wintypes.DWORD()
    ok = write_file(handle, c_buf, buf_size, ctypes.byref(written), None)
    if not ok:
        err = ctypes.get_last_error()
        raise OSError(f"WriteFile failed: {err}")
    if written.value != buf_size:
        raise OSError(f"WriteFile short write: {written.value}/{buf_size}")


if __name__ == "__main__":
    print("Windows HID enumeration:")
    for dev in enumerate_hid_devices():
        if dev["vid"] == 0x0C45 and dev["pid"] == 0x800A:
            print(f"  AULA F75 Max: {dev['path']}")
            print(f"    usage_page=0x{dev['usage_page']:04X} usage=0x{dev['usage']:04X}")
            print(f"    input={dev['input_report_bytes']} output={dev['output_report_bytes']} feature={dev['feature_report_bytes']}")
        elif dev["usage_page"] in (0xFF13, 0xFF68):
            print(f"  Vendor HID: {dev['path']}")
            print(f"    vid=0x{dev['vid']:04X} pid=0x{dev['pid']:04X}")
            print(f"    usage_page=0x{dev['usage_page']:04X} usage=0x{dev['usage']:04X}")
