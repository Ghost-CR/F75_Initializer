# AULA F75 Max — HID Protocol Reverse Engineering

Reverse-engineered HID protocols for the AULA F75 Max keyboard. Builds toward a native macOS control app.

## Status

| Protocol | Windows | macOS | 
|----------|---------|-------|
| RTC time sync | ✅ | ✅ |
| TFT GIF upload | ✅ | ✅ |
| RGB color control | ✅ | — |
| Macro recording | ✅ | — |
| Remap Caps→Ctrl | ✅ | — |

Full protocol spec: **[PROTOCOL_REFERENCE.md](PROTOCOL_REFERENCE.md)**

## Hardware

| Path | VID:PID | Interface | Reports |
|------|---------|-----------|---------|
| USB-C cable | `0c45:800a` | MI_03 (0xFF13) | Feature 65B |
| USB-C cable | `0c45:800a` | MI_02 (0xFF68) | Output 4097B / Input 65B |
| 2.4 GHz dongle | `05ac:024f` | IF 3 | Interrupt 32B |

## Quick Start (Windows)

```powershell
# Kill official driver first (locks HID)
Stop-Process -Name DeviceDriver -Force

# RGB: set color
python -m aula_hacky.windows_rgb_test --red 255 --green 0 --blue 0

# Macro: record key sequence
python -m aula_hacky.windows_macro_test H E L L O --slot 2

# Remap: Caps Lock as Ctrl
python -m aula_hacky.windows_remap_test --caps-to-ctrl on

# TFT: upload GIF
python -m aula_hacky.windows_tft_upload --gif guts.gif --slot 1
```

## Quick Start (macOS)

```bash
# RTC sync via USB-C
python3 -m aula_hacky.macos_cable_rtc_sync --time now

# TFT upload test pattern
python3 -m aula_hacky.screen_upload --test-pattern
```

## Architecture

```
aula_hacky/
├── protocol_core.py         # Platform-neutral protocol builders
├── windows_hid.py           # Windows HID transport (ctypes)
├── hid_macos.py             # macOS HID transport (IOKit)
├── hidraw_linux.py          # Linux HID transport
├── windows_tft_upload.py    # TFT upload
├── windows_rgb_test.py      # RGB control
├── windows_macro_test.py    # Macro recording
├── windows_remap_test.py    # Key remapping
├── screen_upload.py         # macOS TFT upload
├── macos_cable_rtc_sync.py  # macOS RTC sync
└── tft_protocol.py          # TFT frame builder
```

## Documentation

- `PROTOCOL_REFERENCE.md` — Complete protocol specification
- `AGENTS.md` — Development memory for AI agents
- `docs/protocol_sources.md` — Public source audit
- `docs/captures/` — Verified USB captures

## Safety

- Kill `DeviceDriver.exe` before custom scripts
- Never interrupt TFT upload mid-stream
- Recovery: disconnect/reconnect USB-C cable
