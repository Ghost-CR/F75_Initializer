# AULA F75 Max — Protocol Reference

Complete HID protocol reference for USB-C cable connection (`0c45:800a`).

## HID Interfaces

| Interface | Usage Page | Usage | Feature | Input | Output | Purpose |
|-----------|-----------|-------|---------|-------|--------|---------|
| MI_03 | 0xFF13 | 0x0001 | 65B | 65B | 65B | Control commands |
| MI_02 | 0xFF68 | 0x0061 | 0B | 65B | 4097B | Data transfer (TFT chunks) |

**Windows:** `HidD_SetFeature` / `HidD_GetFeature` on MI_03, `WriteFile` on MI_02.
**macOS:** `IOHIDDeviceSetReport` / `IOHIDDeviceGetReport` on MI_03, `IOHIDDeviceSetReport` on MI_02.

All feature reports are 65 bytes on wire (1-byte report ID `0x00` + 64-byte payload).

---

## 1. RTC Time Sync

**Purpose:** Set keyboard real-time clock.

**Sequence:**
```
[MI_03] SET_FEATURE  04 18 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ...  (begin)
[MI_03] GET_FEATURE  → 04 18 00 01 00 00 00 00 ...                          (ack)
[MI_03] SET_FEATURE  04 28 00 00 00 00 00 00 01 00 00 00 00 00 00 00 ...  (prepare)
[MI_03] GET_FEATURE  → 04 28 00 01 00 00 00 00 01 00 ...                    (ack)
[MI_03] SET_FEATURE  00 01 5a YY MM DD HH mm SS 00 05 ... aa 55 ...        (rtc data)
[MI_03] GET_FEATURE  → echo of sent bytes                                   (ack)
[MI_03] SET_FEATURE  04 02 00 00 00 00 00 00 00 00 ...                     (apply)
[MI_03] GET_FEATURE  → 04 02 00 01 00 00 ...                                (ack)
```

**RTC Data Format (offset 0 of payload):**
```
00 01 5a YY MM DD HH mm SS 00 05 00 00 00 aa 55 [zeros...]
```
- `YY` = year - 2000
- Time is local (no timezone encoding)

**Delay between steps:** 36-40ms

**Scripts:** `protocol_core.py` → `build_cable_transaction_sequence()`, `macos_cable_rtc_sync.py`

---

## 2. TFT Screen Upload (GIF / Static)

**Purpose:** Upload image or GIF animation to keyboard TFT screen.

**Sequence:**
```
[MI_03] SET_FEATURE  04 18 00 00 00 00 00 00 00 00 00 00 00 00 ...  (begin)
[MI_03] GET_FEATURE  → 04 18 00 01 00 00 00 00 ...                     (ack)
[MI_03] SET_FEATURE  04 72 SS LL HH 00 00 00 00 00 00 00 00 ...        (metadata)
[MI_03] GET_FEATURE  → 04 72 01 SS 00 00 ...                           (ack)
[MI_02] WRITE_FILE   [4096-byte chunk 1]                                (data)
[MI_02] READ_FILE    → 00 01 5a 02 ...                                 (chunk ack)
[MI_02] WRITE_FILE   [4096-byte chunk 2]
...repeat for all chunks...
[MI_03] SET_FEATURE  04 02 00 00 00 00 00 00 00 00 ...                 (exit)
[MI_03] GET_FEATURE  → 04 02 00 01 00 00 ...                           (ack)
```

**Metadata command (`04 72`):**
```
04 72 SS LL HH 00 00 ...
```
- `SS` = slot number (0-255). Official software uses slot 1.
- `LL HH` = chunk count (little-endian). One 128×128 frame = 9 chunks.

**Frame Format (inside chunk stream):**
```
Offset 0:     frame_count (1 byte)
Offset 1..N:  delay table (1 byte per frame, units ≈ 2ms)
              round(seconds * 500) = delay value
Offset 256:   frame 0 RGB565 little-endian pixels (128×128×2 = 32768 bytes)
Offset 256+N: additional frames, same size
Padding:      zeros to 4096-byte boundary
```

**Chunk size:** 4096 bytes. TFT resolution: 128×128 pixels.

**Critical rules:**
1. Never send `04 02` (exit) on incomplete stream — corrupts firmware state.
2. Chunk count in metadata MUST match actual chunks sent.
3. Recovery from corrupted state: disconnect/reconnect USB-C cable.
4. Chunk delay: ~65ms between chunks (matches official software).

**Scripts:** `windows_tft_upload.py`, `tft_protocol.py`, `screen_upload.py` (macOS)

---

## 3. RGB Color Control

**Purpose:** Set per-key RGB color or lighting effect mode.

**Sequence:**
```
[MI_03] SET_FEATURE  04 19 00 00 00 00 00 00 00 00 00 00 ...      (begin)
[MI_03] GET_FEATURE  → 04 19 00 01 00 00 ...                       (ack)
[MI_03] SET_FEATURE  04 15 00 00 00 00 00 00 SS 00 00 00 ...      (prepare, SS=slot)
[MI_03] GET_FEATURE  → 04 15 00 01 00 00 ... SS ...                 (ack)
[MI_03] SET_FEATURE  04 13 00 00 00 00 00 00 01 00 00 00 ...      (select RGB)
[MI_03] GET_FEATURE  → 04 13 00 01 ...                              (ack)
[MI_03] SET_FEATURE  MM RR GG BB 00 00 00 00 CC BR SP DI 00 00 00 aa 55 ... (payload)
[MI_03] GET_FEATURE  → echo of MM ...                               (ack)
[MI_03] SET_FEATURE  04 02 00 00 00 00 00 00 ...                   (apply)
[MI_03] GET_FEATURE  → 04 02 00 01 00 00 ...                        (ack)
[MI_03] SET_FEATURE  04 f0 00 00 00 00 00 00 ...                   (finish)
[MI_03] GET_FEATURE  → 04 f0 00 01 00 00 ...                        (ack)
```

**RGB Payload Format:**
```
Offset 0:  MM     = mode (0x00=off, 0x01=static, 0x07=breath, etc.)
Offset 1:  RR     = RED   (0x00-0xFF)
Offset 2:  GG     = GREEN (0x00-0xFF)
Offset 3:  BB     = BLUE  (0x00-0xFF)
Offset 4-7: 00    = padding
Offset 8:  CC     = colorful flag (0x00=manual, 0x01=colorful mode)
Offset 9:  BR     = brightness (0x00-0x05)
Offset 10: SP     = speed (0x00-0x05)
Offset 11: DI     = direction (0x00-0x03)
Offset 12-13: 00  = padding
Offset 14-15: aa55 = end marker
```

**Color byte order:** RR GG BB (not BB GG RR as some public sources claim — verified on hardware)

**20 RGB modes discovered** (see `docs/captures/RGB_MODE_REFERENCE.md`).

**Delay:** ~40ms between steps.

**Scripts:** `windows_rgb_test.py`, `protocol_core.py` → `build_cable_rgb_transaction_sequence()`

---

## 4. Macros

**Purpose:** Record and store key sequences in keyboard firmware.

**Sequence:**
```
[MI_03] SET_FEATURE  04 19 00 00 00 00 00 00 00 00 ...           (begin)
[MI_03] GET_FEATURE  → 04 19 00 01 00 00 ...                       (ack)
[MI_03] SET_FEATURE  04 15 00 00 00 00 00 00 SS 00 00 00 ...     (prepare, SS=slot)
[MI_03] GET_FEATURE  → 04 15 00 01 00 00 00 00 SS ...              (ack)
[MI_03] SET_FEATURE  [macro key data 64 bytes]                     (data)
[MI_03] GET_FEATURE  → device echo                                  (ack)
[MI_03] SET_FEATURE  04 02 00 00 00 00 00 00 ...                  (apply)
[MI_03] GET_FEATURE  → 04 02 00 01 XX XX ...                       (ack)
```

**Macro Key Data Format (8 bytes per keystroke):**
```
[KEYCODE] [TYPE] 0a 00 00 50 00 00
```

| Byte | Value | Meaning |
|------|-------|---------|
| 0 | Keycode | USB HID keycode (0x04=A, 0x05=B, 0x06=C, 0x07=D...) |
| 1 | Type | `0xB0` = key down, `0x30` = key up |
| 2-7 | Fixed | `0a 00 00 50 00 00` |

**Example: Macro "C, D"** (4 actions):
```
06 b0 0a 00 00 50 00 00    ← C down
06 30 0a 00 00 50 00 00    ← C up
07 b0 0a 00 00 50 00 00    ← D down
07 30 0a 00 00 50 00 00    ← D up
```

**Delay:** ~40ms between steps.

**Verified captures:** 
- `macro_simple_ab.pcapng` — A,B macro
- `macro_simple_cd.pcapng` — C,D macro

**Scripts:** `windows_macro_test.py`

---

## 5. Key Remapping

**Purpose:** Remap physical keys to different functions (Caps Lock → Ctrl, etc.)

### 5a. Caps Lock → Ctrl (checkbox)

**Sequence:**
```
[MI_03] SET_FEATURE  04 18 00 00 00 00 00 00 ...         (begin)
[MI_03] GET_FEATURE  → 04 18 00 01 ...                     (ack)
[MI_03] SET_FEATURE  04 11 00 00 00 00 00 00 09 ...      (keymap prepare)
[MI_03] GET_FEATURE  → 04 11 00 01 00 00 00 00 09 ...      (ack)
[MI_03] SET_FEATURE  02 01 00 00 00 00 ...                (remap data: ON)
[MI_03] GET_FEATURE  → 02 01 00 00 ...                     (echo)
[MI_03] SET_FEATURE  04 02 00 00 00 00 ...                (apply)
[MI_03] GET_FEATURE  → 04 02 00 01 ...                     (ack)
[MI_03] SET_FEATURE  04 f0 00 00 00 00 ...                (finish)
[MI_03] GET_FEATURE  → 04 f0 00 01 ...                     (ack)
```

**Remap Data Format:**
```
02 [FLAG] [KEYCODE] [00]
```

| Flag | Meaning |
|------|---------|
| `01` | Caps Lock → Ctrl ON |
| `00` | Caps Lock → Ctrl OFF |

**Scripts:** `windows_remap_test.py`

### 5b. Key-to-Key Remap (custom)

Format uses internal keyboard matrix codes (different from USB HID). Caps Lock → Ctrl is fully verified. Full matrix mapping requires additional per-key capture.

---

## Common Command Reference

| Command | Name | Used By |
|---------|------|---------|
| `04 18` | Begin session | RTC, Remap |
| `04 19` | Begin session (alt) | RGB, Macro |
| `04 28` | Prepare | RTC |
| `04 15` | Prepare (with slot) | RGB, Macro |
| `04 13` | Select RGB | RGB |
| `04 11` | Keymap prepare | Remap |
| `04 72` | Metadata (TFT) | TFT |
| `04 02` | Apply / Exit | All protocols |
| `04 f0` | Finish | RGB, Remap |

---

## USB HID Keycodes

```
A=04 B=05 C=06 D=07 E=08 F=09 G=0a H=0b I=0c J=0d
K=0e L=0f M=10 N=11 O=12 P=13 Q=14 R=15 S=16 T=17
U=18 V=19 W=1a X=1b Y=1c Z=1d
1=1e 2=1f 3=20 4=21 5=22 6=23 7=24 8=25 9=26 0=27
ENTER=28 ESC=29 BACKSPACE=2a TAB=2b SPACE=2c
CAPSLOCK=39
LEFT_CTRL=e0 LEFT_SHIFT=e1 LEFT_ALT=e2 LEFT_META=e3
RIGHT_CTRL=e4 RIGHT_SHIFT=e5 RIGHT_ALT=e6 RIGHT_META=e7
F1=3a F2=3b F3=3c F4=3d F5=3e F6=3f F7=40 F8=41 F9=42 F10=43 F11=44 F12=45
```

---

## macOS Migration Notes

All protocol builders are in `protocol_core.py` (platform-neutral). macOS transport is in `hid_macos.py` (IOKit-based).

To add a feature on macOS, follow this pattern:
```python
from aula_hacky.hid_macos import HIDDevice
from aula_hacky.protocol_core import CABLE_SESSION_INIT_OUT, CABLE_PACKET_SIZE

dev = HIDDevice(vid=0x0C45, pid=0x800A, usage_page=0xFF13, usage=0x0001)
dev.open()
dev.set_report(payload)   # sends feature report
reply = dev.get_report()  # reads feature report
```

Existing macOS scripts (working):
- `macos_rtc_sync.py` — RTC time sync (dongle)
- `macos_cable_rtc_sync.py` — RTC time sync (cable)
- `screen_upload.py` — TFT screen upload

To create (in priority order):
1. `macos_rgb_test.py` — RGB color control
2. `macos_macro_test.py` — Macro recording
3. `macos_remap_test.py` — Key remapping

---

## Captures Directory

| File | Content |
|------|---------|
| `macro_simple_ab.pcapng` | Macro A,B protocol reference |
| `macro_simple_cd.pcapng` | Macro C,D for diff analysis |
| `remap_caps_to_ctrl.pcapng` | Caps Lock → Ctrl full protocol |
| `remap_key_to_key_3.pcapng` | Key-to-key remap (Q→L physical press) |
| `rgb_color_red_green_blue_white.pcapng` | RGB color protocol |
| `rgb_mode_off_static_breathing_wave_rainbow.pcapng` | RGB mode sweep |
| `official_guts_upload.pcapng` | Official software GIF upload reference |
| `RGB_MODE_REFERENCE.md` | 20 RGB modes documented |
