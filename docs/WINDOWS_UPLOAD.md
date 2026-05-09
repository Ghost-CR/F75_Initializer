# Windows TFT Upload Guide

## Objective
Run the AULA F75 Max screen uploader directly on Windows using the official USB stack.

## Prerequisites

- Windows 10/11
- Python 3.11+ installed on Windows
- The keyboard connected via **USB-C cable**
- Pillow (`python -m pip install Pillow`) for GIF uploads
- **Kill DeviceDriver.exe** before running our uploader (it locks the HID interfaces)

```powershell
Stop-Process -Name "DeviceDriver" -Force
```

## HID Interfaces

The keyboard exposes two vendor HID interfaces when connected via USB-C:

| Interface | Usage Page | Usage | Purpose | Report Sizes |
|-----------|-----------|-------|---------|--------------|
| MI_03 | `0xFF13` | `0x0001` | **Control** — commands & responses | in=65, out=65, feature=65 |
| MI_02 | `0xFF68` | `0x0061` | **Data pipe** — image chunks | in=65, out=4097, feature=0 |

Enumerate them:

```cmd
python -m aula_hacky.windows_hid
```

## Reverse-Engineered Protocol (Verified)

Based on full USBPcap capture of the official software (`DeviceDriver.exe`).

### Control Commands (MI_03 via `HidD_SetFeature` / `HidD_GetFeature`)

All control commands are **64-byte feature reports** (prepended with report_id=0 on Windows, total 65 bytes).

| Command | Bytes | Purpose |
|---------|-------|---------|
| `04 18` | `build_control_command(bytes([0x04, 0x18]))` | **Begin** — signals start of upload |
| `04 72 <slot> <...> <chunk_count>` | `build_metadata_command(chunk_count, slot)` | **Metadata** — tells firmware how many chunks to expect |
| `04 02` | `build_control_command(bytes([0x04, 0x02]))` | **Exit** — signals end of upload |

**Critical discovery:** the official software sends each control command with `HidD_SetFeature`, then **immediately reads back the response** with `HidD_GetFeature`. The response contains the command echoed back plus status bytes.

### Data Transfer (MI_02 via `WriteFile` / `ReadFile`)

Image data is sent as **4097-byte output reports** (1 byte report_id + 4096 bytes payload) via `WriteFile` on MI_02.

After **every chunk**, the official software reads a **65-byte input report** via `ReadFile` from MI_02. The response is always:

```
00 01 5a 02 00 00 00 00 ...
```

This is an **ACK** from the firmware confirming chunk receipt.

### Upload Sequence

1. **Begin:** `HidD_SetFeature(MI_03, 04 18...)` → sleep 50ms → `HidD_GetFeature(MI_03)` → sleep 100ms
2. **Metadata:** `HidD_SetFeature(MI_03, 04 72...)` → sleep 50ms → `HidD_GetFeature(MI_03)` → sleep 100ms
3. **For each chunk:**
   - `WriteFile(MI_02, 4097 bytes)` → sleep ~65ms
   - `ReadFile(MI_02, 65 bytes)` ← ACK `00 01 5a 02...`
4. **Exit:** `HidD_SetFeature(MI_03, 04 02...)`

### Chunk Delay

The official software uses approximately **65-70ms between chunks**. Too fast and the firmware drops data; too slow and upload takes unnecessarily long.

## GIF Animation — Black Buffer Frame

The AULA F75 firmware has an **initial loop glitch**: without a buffer frame, it locks onto the first frame and the animation never plays.

**Solution:** prepend a single **black frame** with minimal delay (~2ms) before the actual GIF frames. This absorbs the firmware's initial loop glitch.

```python
from aula_hacky.tft_protocol import prepend_black_buffer
stream = prepend_black_buffer(stream)
```

## Image Format

- Resolution: **128×128**
- Format: **RGB565 little-endian**
- Header: 256 bytes (frame_count + per-frame delays)
- Payload: padded to multiple of **4096 bytes**

## Quick Start

### Upload test pattern

```cmd
python -m aula_hacky.windows_tft_upload --test-pattern --slot 1 --debug
```

### Upload a GIF

```cmd
python -m aula_hacky.windows_tft_upload --image guts.gif --slot 1 --debug
```

### Upload with custom options

```cmd
python -m aula_hacky.windows_tft_upload --image my.gif --slot 1 --max-frames 50 --chunk-delay 0.15
```

## Troubleshooting

### "Upload failed: Cannot open HID device"
- **Kill DeviceDriver.exe**: `Stop-Process -Name "DeviceDriver" -Force`
- Reconnect USB-C cable

### TFT shows "loading" or corrupted texture
1. Unplug USB-C cable
2. Wait 5 seconds
3. Plug back in
4. **Do not send `04 02` (exit) on incomplete streams** — that causes the "loading" state

### Animation doesn't play (static image)
- Make sure you're using a **true animated GIF** (not a static image saved as .gif)
- The black buffer frame must be prepended (`prepend_black_buffer`)
- Some firmware versions may require a specific dial mode to enable animation

## Capture & Analysis

To capture official software traffic for further reverse engineering:

```powershell
# List USBPcap devices
& "C:\Program Files\Wireshark\dumpcap.exe" -D

# Capture (run this, then click Upload in official software)
& "C:\Program Files\Wireshark\tshark.exe" -i "\\.\USBPcap1" -w capture.pcapng
```

Analyze with:

```cmd
tshark -r capture.pcapng -Y "usb.transfer_type == 0x01" -T fields -e frame.number -e usb.endpoint_address.direction -e usb.endpoint_address.number -e usb.data_len
```

## Files

- `aula_hacky/windows_hid.py` — ctypes wrapper for Windows HID API
- `aula_hacky/windows_tft_upload.py` — main upload script
- `aula_hacky/tft_protocol.py` — protocol builders (frames, chunks, commands)
