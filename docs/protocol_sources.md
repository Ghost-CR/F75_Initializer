# Public Protocol Sources

This project can continue without new Windows captures by auditing public reverse-engineering work and porting only the byte-level commands that are independently understandable and testable.

## Sources Reviewed

### RoseWaveStudio/Aula-F75-Max-OSX

Local path:

```text
/Users/garymurdock/Projects/Aula-F75-Max-OSX
```

Latest reviewed commit:

```text
68f15a4 Update README.md
```

License: MIT.

Relevant files:

- `Sources/F75Probe/main.m`
- `Sources/AulaF75Bar/main.m`

Useful facts:

- 2.4 GHz dongle: `05ac:024f`, RGB/battery/performance path.
- USB-C: `0c45:800a`, screen upload path.
- Screen control endpoint: `usage_page=0xff13`.
- Screen bulk endpoint: `usage_page=0xff68`, 4096-byte output reports.
- RGB dongle endpoint: `usage_page=0xff60`, 32-byte output reports.

### not-nullptr/openajazz

Local path:

```text
/Users/garymurdock/Projects/openajazz
```

Latest reviewed commit:

```text
800e8fb fix: AX820 effects
```

Relevant files:

- `crates/jazztastic/src/keyboards/f75_max/mod.rs`
- `crates/jazztastic/src/reports/rgb/*.rs`
- `crates/jazztastic/src/reports/time.rs`

Useful facts:

- F75 Max is listed with `VID:PID 0c45:800a`, usage page `0xff13`.
- RGB and time sync share the `0418 -> pre -> payload -> 0402` guard pattern.
- F75 RGB field positions agree with the public macOS app for mode/color/brightness/speed/direction.

## Ported Protocol Facts

### Wireless RGB, 2.4 GHz Dongle

Transport:

```text
vid=0x05ac pid=0x024f usage_page=0xff60 usage=0x0061
IOHID output report, report ID 0, raw 32-byte payload
```

Packet checksum:

```text
sum(packet[0:31]) & 0xff
```

RGB LED mode packet:

```text
05 10 00 MM BB GG RR 00 00 00 00 CC BR SP DI 00 00 aa 55 ... checksum
```

Fields:

- `MM`: mode, `0..31`; `0` means LED off.
- `BB GG RR`: fixed color from a `0xRRGGBB` integer, stored little-endian by color channel.
- `CC`: colorful flag.
- `BR`: brightness, `0..5`; UI should normally expose `1..5`.
- `SP`: speed, `0..5`; UI should normally expose `1..5`.
- `DI`: direction. RoseWaveStudio exposes `0=Right`, `1=Down`, `2=Left`, `3=Up`.
- marker: `aa55` at offsets 17 and 18.

Companion packets:

- Legacy RGB mode report: `05 01 00 (mode + 0x1f) ... aa 55 ... checksum`.
- Commit report: `0f 00 ... checksum`.

The Python builders are:

- `build_wireless_rgb_mode_packet`
- `build_wireless_rgb_commit_packet`
- `build_wireless_rgb_led_mode_packet`

### Cable RGB, USB-C

Transport:

```text
vid=0x0c45 pid=0x800a usage_page=0xff13 usage=0x0001
IOHID feature report, report ID 0, raw 64-byte payload on macOS
```

Sequence:

```text
0418...                      begin
041300000000000001...        select RGB data
MM BB GG RR 00000000 CC BR SP DI 0000 aa55...  payload
0402...                      apply/end
04f0...                      finish
```

The Python builder is `build_cable_rgb_transaction_sequence`.

### Screen Image/GIF Upload

Transport:

```text
control: vid=0x0c45 pid=0x800a usage_page=0xff13, feature reports, 64 bytes
bulk:    vid=0x0c45 pid=0x800a usage_page=0xff68, output reports, 4096 bytes
```

High-level sequence:

```text
0418...                        begin
0472010000000000 LL HH...      metadata, chunk count little-endian at offsets 8..9
4096-byte chunks on ff68        padded stream chunks
0402...                        exit
```

Stream format:

```text
offset 0      frame count
offset 1..N   frame delays
offset 256    frame 0 RGB565 pixels, 128 * 128 * 2 bytes
then          additional frames, same size
padding       zero padding to 4096-byte chunk boundary
```

The TFT firmware uses **128x128 RGB565 little-endian**. The box lists 320x240, but that appears to be incorrect or refers to the physical panel rather than the upload buffer size. Uploading 320x240 data to the 128x128 buffer produces a partial corrupted texture.

The keyboard has two independent screen memories:
- **Boot animation** (shown at power-on)
- **Slot 1+** (shown when rotating the dial)

The metadata command byte 2 selects the target slot. The official software defaults to slot 1 for the dial-accessible screen.

GIF delay units are about 2 ms; RoseWaveStudio computes `round(seconds * 500)` and clamps to `1..255`.

Pixel format in the app path is RGB565 little-endian:

```text
rgb565 = ((r & 0xf8) << 8) | ((g & 0xfc) << 3) | (b >> 3)
stream byte 0 = rgb565 & 0xff
stream byte 1 = rgb565 >> 8
```

Screen upload is ported in `aula_hacky/screen_upload.py`.

Verified command path:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m aula_hacky.screen_upload --test-pattern --chunk-delay 0.04
```

The command opened `ff13` and `ff68`, sent `0418`, metadata for 9 chunks, all 9 chunks, and `0402` successfully. The keyboard does not send per-chunk ACKs over either the `ff13` control channel or the `ff68` bulk channel. The only replies are feature-report ACKs for the control commands (`0418` → `04180001...`, `0472` → `04720101...`). Therefore `--no-chunk-ack` is the correct protocol behavior, not a workaround, and it is now the default.

Image/GIF raster conversion is implemented through optional Pillow support. Transport and test-pattern upload do not require Pillow.

## What Is Still Not Ported

- Macros.
- Internal remapping.
- Profile save/load.
- Screen ACK callback delivery in Python/Terminal.
- Battery query API.
- Performance/game mode API.

These should be ported only after the source commands are reduced to exact packet builders and covered by tests.
