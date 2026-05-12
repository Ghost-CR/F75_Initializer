# Agent Memory: Aula F75 Max Reverse Engineering

## Goal

Build a native macOS control stack for the AULA F75 Max keyboard controlling all available features via HID protocols.

## Current Status (2026-05-12)

| Protocol | Windows | macOS | Script |
|----------|---------|-------|--------|
| RTC sync | ✅ | ✅ | `protocol_core.py`, `macos_cable_rtc_sync.py` |
| TFT GIF upload | ✅ | ✅ | `windows_tft_upload.py`, `screen_upload.py` |
| RGB color | ✅ | ❌ | `windows_rgb_test.py` |
| Macros | ✅ | ❌ | `windows_macro_test.py` |
| Remap (Caps→Ctrl) | ✅ | ❌ | `windows_remap_test.py` |
| Remap (key-to-key) | 🔶 | ❌ | Need matrix mapping |
| Profiles | ❌ | ❌ | Not started |

🔶 = Caps Lock → Ctrl works. Arbitrary key-to-key needs internal matrix mapping.

## Architecture

```
aula_hacky/
├── protocol_core.py      # Platform-neutral protocol builders
├── windows_hid.py        # Windows HID transport (ctypes/SetupAPI)
├── hid_macos.py          # macOS HID transport (IOKit)
├── hidraw_linux.py       # Linux HID transport
├── windows_tft_upload.py # TFT upload (Windows)
├── windows_rgb_test.py   # RGB color control (Windows)
├── windows_macro_test.py # Macro recording (Windows)
├── windows_remap_test.py # Key remapping (Windows)
├── screen_upload.py      # TFT upload (macOS)
├── macos_cable_rtc_sync.py  # RTC sync cable (macOS)
├── macos_rtc_sync.py     # RTC sync dongle (macOS)
├── tft_protocol.py       # TFT frame builder
├── tft_service.py        # TFT atomic transaction wrapper
└── capture_analysis.py   # USBPcap extraction utilities
```

## HID Interfaces (Cable: 0c45:800a)

| Interface | Usage Page | Usage | Transport | Purpose |
|-----------|-----------|-------|-----------|---------|
| MI_03 | 0xFF13 | 0x0001 | Feature 65B | Control commands |
| MI_02 | 0xFF68 | 0x0061 | Output 4097B / Input 65B | Data chunks |

## Protocols

All protocols documented in `PROTOCOL_REFERENCE.md`. Summary:

1. **RTC**: `0418` begin → `0428` prepare → `00015a YY MM DD...` → `0402` apply
2. **TFT**: `0418` begin → `0472 slot chunk_count` → MI_02 chunks → `0402` exit. 128×128 RGB565 LE.
3. **RGB**: `0419` begin → `0415` prepare → `0413` select → `MM RR GG BB...aa55` → `0402` → `04f0`
4. **Macro**: `0419` begin → `0415` prepare → `KK TT 0a0000500000` × N → `0402`. `TT` = `b0`(down)/`30`(up).
5. **Remap**: `0418` begin → `0411` prepare → `02 [flag] [key] 00` → `0402` → `04f0`

## macOS Migration

Transport layer done (`hid_macos.py`). Protocol builders are shared (`protocol_core.py`).

To do (in priority):
1. `macos_rgb_test.py` — port `windows_rgb_test.py`
2. `macos_macro_test.py` — port `windows_macro_test.py`
3. `macos_remap_test.py` — port `windows_remap_test.py`

Pattern: replace `windows_hid` imports with `hid_macos`, same protocol calls.

## Safety Rules

- Kill `DeviceDriver.exe` before using custom scripts (locks HID)
- Never send incomplete TFT streams (corrupts firmware)
- Do not send invented packets — use only captured/verified bytes
- Recovery from TFT corruption: disconnect/reconnect USB-C cable

## Files

- `PROTOCOL_REFERENCE.md` — Complete protocol specification
- `docs/protocol_sources.md` — Public source audit
- `docs/captures/` — Verified capture files
- `docs/captures/RGB_MODE_REFERENCE.md` — 20 RGB modes

## Commands

```bash
# Windows
python -m aula_hacky.windows_rgb_test --red 255 --debug
python -m aula_hacky.windows_macro_test H E L L O --slot 2 --debug
python -m aula_hacky.windows_remap_test --caps-to-ctrl on

# macOS
python3 -m aula_hacky.macos_cable_rtc_sync --time now --debug
python3 -m aula_hacky.screen_upload --test-pattern --debug
```
