#!/usr/bin/env python3
"""
Windows HID enumeration v2 - Uses PowerShell to get device paths reliably.
This version queries WMI/PowerShell for device paths and then opens them with CreateFileW.
"""

from __future__ import annotations

import ctypes
import json
import subprocess
from ctypes import wintypes

# Windows constants
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3

# HID API
hid_dll = ctypes.windll.hid
HidD_GetAttributes = hid_dll.HidD_GetAttributes
HidD_GetPreparsedData = hid_dll.HidD_GetPreparsedData
HidP_GetCaps = hid_dll.HidP_GetCaps
HidD_FreePreparsedData = hid_dll.HidD_FreePreparsedData
HidD_SetFeature = hid_dll.HidD_SetFeature
HidD_GetFeature = hid_dll.HidD_GetFeature

kernel32 = ctypes.windll.kernel32
CreateFileW = kernel32.CreateFileW
CloseHandle = kernel32.CloseHandle
WriteFile = kernel32.WriteFile


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


def get_device_paths_from_wmi(vid: int, pid: int) -> list[str]:
    """Use PowerShell/WMI to get HID device paths for a specific VID/PID."""
    ps_cmd = f"""
$vid = "{vid:04X}"
$pid = "{pid:04X}"
Get-PnpDevice -Class HIDClass | Where-Object {{ 
    $_.InstanceId -match "VID_$vid" -and $_.InstanceId -match "PID_$pid"
}} | ForEach-Object {{
    $instanceId = $_.InstanceId
    # Get the device path from registry or WMI
    Write-Output $instanceId
}}
"""
    result = subprocess.run(
        ["powershell", "-Command", ps_cmd],
        capture_output=True, text=True, timeout=30
    )
    
    paths = []
    for line in result.stdout.strip().split('\n'):
        line = line.strip()
        if line and 'VID_' in line:
            # Convert InstanceId to device path format
            # HID\VID_0C45&PID_800A&MI_03\8&5E1A8CD&0&0000
            # becomes: \\?\hid#vid_0c45&pid_800a&mi_03#8&5e1a8cd&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}
            parts = line.split('\\')
            if len(parts) >= 2:
                device_id = parts[0].lower().replace('\\', '#')
                instance = parts[1].lower()
                path = f"\\\\?\\hid#{device_id}#{instance}#{{4d1e55b2-f16f-11cf-88cb-001111000030}}"
                paths.append(path)
    
    return paths


def enumerate_hid_devices_ps():
    """Enumerate HID devices using PowerShell."""
    ps_cmd = """
$devices = @()
Get-PnpDevice -Class HIDClass | Where-Object { 
    $_.InstanceId -match 'HID\\\\VID_' 
} | ForEach-Object {
    $instanceId = $_.InstanceId
    $friendlyName = $_.FriendlyName
    $status = $_.Status
    
    # Extract VID and PID
    if ($instanceId -match 'VID_([0-9A-F]{4})') {
        $vid = [convert]::ToInt32($matches[1], 16)
    } else { $vid = 0 }
    
    if ($instanceId -match 'PID_([0-9A-F]{4})') {
        $pid = [convert]::ToInt32($matches[1], 16)
    } else { $pid = 0 }
    
    # Extract MI (interface) if present
    if ($instanceId -match 'MI_(\d{2})') {
        $mi = $matches[1]
    } else { $mi = "00" }
    
    $devices += [PSCustomObject]@{
        InstanceId = $instanceId
        FriendlyName = $friendlyName
        Status = $status
        VID = $vid
        PID = $pid
        MI = $mi
    }
}

$devices | ConvertTo-Json -Compress
"""
    result = subprocess.run(
        ["powershell", "-Command", ps_cmd],
        capture_output=True, text=True, timeout=30
    )
    
    try:
        devices = json.loads(result.stdout)
        if not isinstance(devices, list):
            devices = [devices]
        return devices
    except json.JSONDecodeError:
        return []


def open_hid_device(path: str) -> wintypes.HANDLE:
    """Open HID device with read/write access."""
    handle = CreateFileW(
        path,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        0,
        None,
    )
    if handle == -1 or handle == ctypes.c_void_p(-1).value:
        err = ctypes.get_last_error()
        raise OSError(f"Cannot open HID device {path}: error {err}")
    return handle


def get_device_caps(handle) -> dict:
    """Get HID device capabilities."""
    attrs = HIDD_ATTRIBUTES()
    attrs.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
    
    if not HidD_GetAttributes(handle, ctypes.byref(attrs)):
        return None
    
    preparsed = ctypes.c_void_p()
    if not HidD_GetPreparsedData(handle, ctypes.byref(preparsed)):
        return None
    
    caps = HIDP_CAPS()
    result = HidP_GetCaps(preparsed, ctypes.byref(caps))
    HidD_FreePreparsedData(preparsed)
    
    if result != 0:  # HIDP_STATUS_SUCCESS = 0
        return None
    
    return {
        "vid": attrs.VendorID,
        "pid": attrs.ProductID,
        "usage_page": caps.UsagePage,
        "usage": caps.Usage,
        "input_report_bytes": caps.InputReportByteLength,
        "output_report_bytes": caps.OutputReportByteLength,
        "feature_report_bytes": caps.FeatureReportByteLength,
    }


def find_aula_devices():
    """Find all AULA F75 Max HID devices."""
    devices = enumerate_hid_devices_ps()
    aula_devices = []
    
    for dev in devices:
        if dev.get("VID") == 0x0C45 and dev.get("PID") == 0x800A:
            # Try to convert instance ID to device path and open
            instance_id = dev.get("InstanceId", "")
            parts = instance_id.split('\\')
            if len(parts) >= 2:
                device_id = parts[0].lower().replace('\\', '#')
                instance = parts[1].lower()
                path = f"\\\\?\\hid#{device_id}#{instance}#{{4d1e55b2-f16f-11cf-88cb-001111000030}}"
                
                try:
                    handle = open_hid_device(path)
                    caps = get_device_caps(handle)
                    CloseHandle(handle)
                    
                    if caps:
                        aula_devices.append({
                            "path": path,
                            **caps,
                            "instance_id": instance_id,
                            "mi": dev.get("MI", "00"),
                            "status": dev.get("Status", "Unknown"),
                        })
                except OSError:
                    # Can't open this device
                    pass
    
    return aula_devices


def hid_set_feature(handle, report_id: int, data: bytes) -> None:
    """Send HID feature report with report ID prepended."""
    buf = bytes([report_id]) + data
    buf_size = len(buf)
    c_buf = ctypes.create_string_buffer(buf, buf_size)
    ok = HidD_SetFeature(handle, c_buf, buf_size)
    if not ok:
        err = ctypes.get_last_error()
        raise OSError(f"HidD_SetFeature failed: {err}")


def hid_get_feature(handle, report_id: int, length: int) -> bytes:
    """Read HID feature report."""
    buf = ctypes.create_string_buffer(length)
    buf.raw = bytes([report_id]) + bytes(length - 1)
    ok = HidD_GetFeature(handle, buf, length)
    if not ok:
        err = ctypes.get_last_error()
        raise OSError(f"HidD_GetFeature failed: {err}")
    return bytes(buf.raw)


def hid_write_output(handle, report_id: int, data: bytes) -> None:
    """Send HID output report via WriteFile."""
    buf = bytes([report_id]) + data
    buf_size = len(buf)
    c_buf = ctypes.create_string_buffer(buf, buf_size)
    written = wintypes.DWORD()
    ok = WriteFile(handle, c_buf, buf_size, ctypes.byref(written), None)
    if not ok:
        err = ctypes.get_last_error()
        raise OSError(f"WriteFile failed: {err}")
    if written.value != buf_size:
        raise OSError(f"WriteFile short write: {written.value}/{buf_size}")


if __name__ == "__main__":
    print("Windows HID enumeration v2 (PowerShell-based):")
    devices = find_aula_devices()
    
    if not devices:
        print("  No AULA F75 Max devices found.")
    else:
        for dev in devices:
            print(f"  AULA MI_{dev['mi']}: {dev['path']}")
            print(f"    usage_page=0x{dev['usage_page']:04X} usage=0x{dev['usage']:04X}")
            print(f"    input={dev['input_report_bytes']} output={dev['output_report_bytes']} feature={dev['feature_report_bytes']}")
            print(f"    status={dev['status']}")
