# Capture Workflow For Advanced AULA F75 Max Protocols

This phase captures and decodes the Windows-only vendor software traffic for features that are not implemented yet: RGB, macros, remapping, profiles, and TFT image/GIF operations.

Do not add write commands for these features until a command is reproduced from at least one controlled capture and covered by tests.

## Capture Setup

Use Windows with the official AULA F75 Max software, Wireshark, and USBPcap.

Preferred connection for first captures:

```text
USB-C cable
VID:PID 0c45:800a
macOS equivalent interface: usage_page=0xff13 usage=0x0001 feature=64
```

Capture rules:

- Start from a known keyboard profile.
- Change exactly one setting per capture.
- Stop capture immediately after the vendor software finishes the operation.
- Save raw `.pcapng` files; do not edit them.
- Keep filenames stable and descriptive.
- Do not fuzz or invent packets.

## File Layout

Store captures under this directory:

```text
docs/captures/raw/
docs/captures/extracted/
docs/captures/notes/
```

Recommended naming:

```text
rgb_brightness_10.pcapng
rgb_brightness_20.pcapng
rgb_brightness_30.pcapng
rgb_color_red.pcapng
rgb_color_green.pcapng
rgb_color_blue.pcapng
rgb_effect_static.pcapng
rgb_effect_breathing.pcapng
macro_simple_ab.pcapng
macro_with_delay_ab.pcapng
remap_caps_to_escape.pcapng
remap_restore_caps.pcapng
tft_static_small_image.pcapng
tft_gif_two_frame.pcapng
profile_save_slot_1.pcapng
profile_load_slot_1.pcapng
```

## Capture Matrix

| Area | Capture | Exact operation |
| --- | --- | --- |
| RGB brightness | `rgb_brightness_10/20/30` | Set same effect/color, change only brightness. |
| RGB color | `rgb_color_red/green/blue/white` | Static mode, same brightness, change only color. |
| RGB effect | `rgb_effect_static/breathing/wave` | Same brightness/color, change only effect. |
| Per-key RGB | `rgb_perkey_a_red/green/blue` | Same key, change only color. |
| Macro | `macro_simple_ab` | Assign macro `A`, `B` with no delay to one known key. |
| Macro delay | `macro_with_delay_ab` | Same macro with one known delay between `A` and `B`. |
| Remap | `remap_caps_to_escape` | Remap one source key to one target key. |
| Remap restore | `remap_restore_caps` | Restore the same key to default. |
| TFT static | `tft_static_small_image` | Upload one tiny known PNG/JPG. |
| TFT GIF | `tft_gif_two_frame` | Upload one tiny two-frame GIF. |
| Profile | `profile_save/load_slot_1` | Save and load one slot after one small change. |

## Extract Reports

Convert each `.pcapng` to JSONL:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m aula_hacky.capture_analysis extract \
  docs/captures/raw/rgb_brightness_10.pcapng \
  --vid 0c45 --pid 800a \
  --output docs/captures/extracted/rgb_brightness_10.jsonl
```

If VID/PID filters are missing from the capture, use bus/device filters from Wireshark:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m aula_hacky.capture_analysis extract \
  docs/captures/raw/rgb_brightness_10.pcapng \
  --bus 1 --device 7 \
  --output docs/captures/extracted/rgb_brightness_10.jsonl
```

Inspect annotated output without writing JSONL:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m aula_hacky.capture_analysis extract \
  docs/captures/raw/rgb_brightness_10.pcapng \
  --vid 0c45 --pid 800a
```

## Compare Captures

Diff two controlled captures:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m aula_hacky.capture_analysis diff \
  docs/captures/extracted/rgb_brightness_10.jsonl \
  docs/captures/extracted/rgb_brightness_20.jsonl
```

The output is JSON lines with changed byte offsets. Useful command candidates are usually reports where:

- The same frame index has the same report length.
- Only one or a few bytes change.
- The changed byte tracks the UI value.
- Adjacent captures differ predictably.

## Acceptance Criteria Before Implementing A Command

A decoded command is ready for implementation only when:

- The report direction is known.
- The transport is known: interrupt, output report, or feature report.
- Report size and report ID behavior are known.
- Static header bytes are documented.
- Variable bytes are mapped to UI values.
- Reply/ACK behavior is documented.
- At least one unit test reproduces the exact captured packet.
- The command is added to `protocol_core.py` before any macOS UI calls it.

## Current Status

Implemented and verified:

- RTC sync over 2.4 GHz dongle.
- RTC sync over USB-C cable.

Not decoded yet:

- RGB effects.
- Per-key RGB.
- Macros.
- Remapping.
- Profiles.
- TFT static image upload.
- TFT GIF upload.
