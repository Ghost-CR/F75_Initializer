from __future__ import annotations

import ctypes
import subprocess
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
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


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


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", ctypes.c_void_p),
    ]


HID_INTERFACE_GUID = "{4d1e55b2-f16f-11cf-88cb-001111000030}"


def _probe_hid_path(path: str):
    handle = create_file(
        path,
        0,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        0,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        return None
    try:
        attrs = HIDD_ATTRIBUTES()
        attrs.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
        if not HidD_GetAttributes(handle, ctypes.byref(attrs)):
            return None

        preparsed = ctypes.c_void_p()
        if not HidD_GetPreparsedData(handle, ctypes.byref(preparsed)):
            return None
        try:
            caps = HIDP_CAPS()
            status = HidP_GetCaps(preparsed, ctypes.byref(caps))
            if status & 0x80000000:  # NTSTATUS failure (severity bit set)
                return None
            return {
                "path": path,
                "vid": attrs.VendorID,
                "pid": attrs.ProductID,
                "usage_page": caps.UsagePage,
                "usage": caps.Usage,
                "input_report_bytes": caps.InputReportByteLength,
                "output_report_bytes": caps.OutputReportByteLength,
                "feature_report_bytes": caps.FeatureReportByteLength,
            }
        finally:
            HidD_FreePreparsedData(preparsed)
    finally:
        close_handle(handle)


def _enumerate_hid_devices_powershell_fallback():
    cmd = (
        r"Get-PnpDevice -Class HIDClass | "
        r"Where-Object { $_.InstanceId -match '^HID\\VID_[0-9A-Fa-f]{4}&PID_[0-9A-Fa-f]{4}' } | "
        r"Select-Object -ExpandProperty InstanceId"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        return

    seen = set()
    for line in result.stdout.splitlines():
        inst = line.strip()
        if not inst:
            continue
        path = r"\\?\\" + inst.lower().replace("\\", "#") + "#" + HID_INTERFACE_GUID
        if path in seen:
            continue
        seen.add(path)
        dev = _probe_hid_path(path)
        if dev is not None:
            yield dev


def enumerate_hid_devices():
    """Yield (path, vid, pid, usage_page, usage, caps) for all HID devices."""
    setupapi = ctypes.windll.setupapi

    HidD_GetHidGuid = hid_dll.HidD_GetHidGuid
    HidD_GetHidGuid.argtypes = [ctypes.POINTER(GUID)]
    HidD_GetHidGuid.restype = None
    hid_guid = GUID()
    HidD_GetHidGuid(ctypes.byref(hid_guid))

    SetupDiGetClassDevsW = setupapi.SetupDiGetClassDevsW
    SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD]
    SetupDiGetClassDevsW.restype = ctypes.c_void_p
    SetupDiEnumDeviceInterfaces = setupapi.SetupDiEnumDeviceInterfaces
    SetupDiEnumDeviceInterfaces.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID), wintypes.DWORD, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)]
    SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
    SetupDiGetDeviceInterfaceDetailW = setupapi.SetupDiGetDeviceInterfaceDetailW
    SetupDiGetDeviceInterfaceDetailW.argtypes = [ctypes.c_void_p, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA), ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
    SetupDiDestroyDeviceInfoList = setupapi.SetupDiDestroyDeviceInfoList
    SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]
    SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL

    DIGCF_PRESENT = 0x00000002
    DIGCF_DEVICEINTERFACE = 0x00000010

    h_info = SetupDiGetClassDevsW(
        ctypes.byref(hid_guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    )
    if h_info == INVALID_HANDLE_VALUE:
        return

    yielded = False
    try:
        index = 0
        while True:
            iface_data = SP_DEVICE_INTERFACE_DATA()
            iface_data.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)

            ok = SetupDiEnumDeviceInterfaces(
                h_info, None, ctypes.byref(hid_guid), index, ctypes.byref(iface_data)
            )
            if not ok:
                break

            req_size = wintypes.DWORD()
            SetupDiGetDeviceInterfaceDetailW(
                h_info, ctypes.byref(iface_data), None, 0, ctypes.byref(req_size), None
            )

            detail_size = req_size.value
            if detail_size == 0:
                index += 1
                continue

            buf = ctypes.create_string_buffer(detail_size)
            cb_size = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            ctypes.cast(buf, ctypes.POINTER(wintypes.DWORD))[0] = cb_size

            ok = SetupDiGetDeviceInterfaceDetailW(
                h_info, ctypes.byref(iface_data), buf, detail_size, None, None
            )
            if ok:
                # DevicePath follows cbSize; on x64, align to 8-byte offset.
                path_offset = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 4
                path = ctypes.wstring_at(ctypes.addressof(buf) + path_offset)
                dev = _probe_hid_path(path)
                if dev is not None:
                    yielded = True
                    yield dev
            index += 1
    finally:
        SetupDiDestroyDeviceInfoList(h_info)

    # Some Windows environments fail SetupAPI interface detail enumeration
    # while PnP still reports HID instance IDs. Probe those paths directly.
    if not yielded:
        yield from _enumerate_hid_devices_powershell_fallback()


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
    if handle == INVALID_HANDLE_VALUE:
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


def hid_set_output_report(handle, report_id: int, data: bytes) -> None:
    """Send HID output report via HidD_SetOutputReport. Windows expects report_id prepended."""
    buf = bytes([report_id]) + data
    buf_size = len(buf)
    c_buf = ctypes.create_string_buffer(buf, buf_size)
    ok = HidD_SetOutputReport(handle, c_buf, buf_size)
    if not ok:
        err = ctypes.get_last_error()
        raise OSError(f"HidD_SetOutputReport failed: {err}")


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


def hid_read_input(handle, report_id: int, length: int) -> bytes:
    """Read HID input report via ReadFile. Windows expects report_id prepended."""
    buf = ctypes.create_string_buffer(length)
    buf.raw = bytes([report_id]) + bytes(length - 1)
    read = wintypes.DWORD()
    ok = read_file(handle, buf, length, ctypes.byref(read), None)
    if not ok:
        err = ctypes.get_last_error()
        if err == 0x00000121:  # ERROR_SEM_TIMEOUT
            raise TimeoutError(f"ReadFile timed out")
        raise OSError(f"ReadFile failed: {err}")
    return bytes(buf.raw[:read.value])


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
