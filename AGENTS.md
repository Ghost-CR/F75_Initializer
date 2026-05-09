# Agent Memory: Aula F75 Max Reverse Engineering

This file is local project memory for AI agents. Read it before changing code or documentation.

## Goal

Build toward a native macOS software stack for the AULA F75 Max keyboard that can eventually control all available features: RTC/TFT initialization, Mac adaptation, RGB, macros, remapping, profiles, and TFT image/GIF management.

The current repository is not a full keyboard control app. It is a proof and implementation of the proprietary HID RTC/display initialization path for Linux and the macOS 2.4 GHz dongle.

Phase 1 is complete: protocol builders and validators are centralized in the platform-neutral `aula_hacky/protocol_core.py` module. Linux and tests import that module directly; `aula_hacky/protocol.py` remains a compatibility re-export.

Phase 2 is complete for dongle session-init: `aula_hacky/hid_macos.py` can enumerate and open the dongle vendor interface `05ac:024f`, usage page `0xff60`, usage `0x61`, outside the sandbox. The working macOS report semantics are output report, report ID `0`, raw 32-byte payload, callback read. The observed macOS reply is `02000040300000450c0a801001ffff000000000000000000000000000000005c`, which differs from the Linux capture but is valid by prefix/checksum.

Phase 3 is implemented for the macOS 2.4 GHz dongle in `aula_hacky/macos_rtc_sync.py`. It sends the known `session-init`, `session-query`, and `rtc-set` transactions over 32-byte output reports. By default, it accepts the known firmware-dependent `session-init` and `session-query` replies by prefix/checksum and requires the exact reply for `rtc-set`. Use `--allow-prefix-replies` only while investigating a changed RTC ACK.

Local hardware verification on 2026-05-07: `python3 -m aula_hacky.macos_rtc_sync --time now --timeout 1 --debug` completed against `ioreg:10002336c`, with `session-init` prefix match, `session-query` prefix match, and `rtc-set` exact ACK `0c1000000000000000000000000000000000000000000000000000000000001c`.

Phase 4 is implemented and hardware-verified for macOS USB-C in `aula_hacky/macos_cable_rtc_sync.py`. It sends the existing 64-byte cable transaction sequence through feature reports on `0c45:800a`. The observed macOS cable interface is `usage_page=0xff13`, `usage=0x0001`, `in=64`, `out=64`, `feature=64`. Use raw 64-byte feature payloads by default; the report-ID-prefixed form shifted the packet and returned `000418ff...`. Use the declared feature report length for `GET_REPORT`; asking macOS for 65 bytes failed with `0xe0005000`.

Local USB-C hardware verification on 2026-05-07: `python3 -m aula_hacky.macos_cable_rtc_sync --time now --timeout 1 --debug --usage-page ff13 --usage 0001 --no-prefix-report-id` completed with exact matches for `cable-session-init`, `cable-session-prepare`, `cable-rtc-set`, and `cable-session-finalize`. The CLI now defaults to that raw 64-byte behavior, so `--no-prefix-report-id` is no longer needed.

## Current Truth

Repository path:

```text
/Users/garymurdock/Projects/F75_Initializer
```

Known paths:

- Dongle: `05ac:024f`, interface `3`, 32-byte HID interrupt reports.
- Cable: `0c45:800a`, interface `3`, 64-byte HID feature reports.
- Bluetooth LE on macOS: appears as a standard Apple HID keyboard/media/pointer device. It is useful for typing and OS-level remapping, but it has not exposed the full configuration protocol.

Local macOS observation showed the 2.4 GHz dongle exposes vendor HID channels, including usage pages matching 32-byte and 64-byte vendor reports. This aligns with the existing Linux captures.

## Implemented Protocol

Implemented in `aula_hacky/protocol_core.py`:

- Dongle session init.
- Dongle session query.
- Dongle RTC set.
- Cable session init.
- Cable session prepare.
- Cable RTC set.
- Cable session finalize.
- 32-byte packet checksum.
- Reply validation.

Implemented in `aula_hacky/macos_rtc_sync.py`:

- macOS dry-run for the dongle RTC sequence.
- macOS RTC sync over the dongle vendor interface.
- Reply matching that prefers exact ACKs and handles the observed session-init firmware variant.

Implemented in `aula_hacky/macos_cable_rtc_sync.py`:

- macOS dry-run for the USB-C cable RTC sequence.
- macOS cable RTC sync using `IOHIDDeviceSetReport` / `IOHIDDeviceGetReport` feature reports.
- Feature report normalization for both raw 64-byte replies and report-ID-prefixed 65-byte replies.

Implemented in `aula_hacky/screen_upload.py`:

- TFT test-pattern stream builder.
- Optional Pillow-based image/GIF stream builder.
- 128x128 RGB565 little-endian frame encoding.
- USB-C screen upload over `ff13` feature reports and `ff68` 4096-byte output reports.
- Optional chunk ACK wait; `--no-chunk-ack` is currently the verified Terminal/Python path.

Implemented in `aula_hacky/windows_hid.py`:

- Windows HID enumeration via SetupAPI (ctypes, zero dependencies).
- Windows feature report I/O (`HidD_SetFeature`, `HidD_GetFeature`).
- Windows output report I/O (`WriteFile`).

Implemented in `aula_hacky/windows_tft_upload.py`:

- Windows TFT upload using native HID APIs.
- Same atomic transaction safety as macOS (`tft_service.py`).

Dongle checksum:

```text
sum(packet[0:31]) & 0xff
```

Dongle RTC command shape:

```text
0c 10 00 00 01 5a YY MM DD HH mm SS 00 05 00 00 00 aa 55 ... checksum
```

Cable RTC command shape:

```text
00 01 5a YY MM DD HH mm SS 00 05 ... aa 55
```

## Missing Protocol

Do not claim these write commands are implemented:

- RGB effects.
- Per-key RGB.
- RGB brightness/speed/direction.
- Internal macros.
- Internal key remapping.
- Profile save/load.
- TFT static image upload UI.
- TFT GIF upload UI.
- Firmware update.

These require additional captures from the official Windows software using USBPcap/Wireshark.

Phase 5 capture/decode tooling is implemented. Public-source audit is also in progress: `docs/protocol_sources.md` records reviewed protocol facts from `RoseWaveStudio/Aula-F75-Max-OSX` and `not-nullptr/openajazz`. RGB packet builders have been ported into `aula_hacky/protocol_core.py`; the macOS USB-C screen uploader is ported in `aula_hacky/screen_upload.py`; macros, remapping, and profiles are not ported yet. Use `aula_hacky/capture_analysis.py` to extract USBPcap HID traffic to JSONL and diff controlled captures when captures become available.

Screen uploader hardware note: `python3 -m aula_hacky.screen_upload --test-pattern --timeout 1 --debug --chunk-delay 0.04` opened control `ff13`, pipe `ff68`, sent metadata for 9 chunks, all chunks, and exit successfully. The keyboard does not send per-chunk ACKs over either the `ff13` control channel or the `ff68` bulk channel. The only replies are feature-report ACKs for the control commands (`0418` → `04180001...`, `0472` → `04720101...`). Therefore `--no-chunk-ack` is the correct protocol behavior, not a workaround, and it is now the default.

### TFT Transaction Atomicity Incident (2026-05-07)

A probe script sent only 3 of 9 expected chunks followed by the `exit` command (`0402`). The keyboard firmware entered a "loading 33%" state and blocked all other features (RGB, RTC, etc.). Recovery required disconnecting and reconnecting the USB-C cable.

Root cause: the TFT upload protocol is a **stateful transaction**. Once the metadata command declares a chunk count, the firmware expects exactly that many chunks before `exit`. Sending `exit` early tells the firmware the stream is complete, but the internal framebuffer is only partially filled, so it waits forever for data that never arrives.

Design rules derived from this incident:

1. **Never send `exit` on an incomplete stream.** If an error occurs mid-upload, abort without sending `0402`.
2. **Validate the full stream before starting.** The `chunk_count` in metadata must match the actual number of chunks that will be sent.
3. **Treat the firmware as single-threaded.** During a TFT transaction, no other commands (RGB, RTC, profiles) will be processed.
4. **Document recovery clearly.** If a transaction aborts mid-stream, the user must disconnect and reconnect the USB-C cable.

Implemented safeguard: `aula_hacky/tft_service.py` (`TFTService`) wraps the upload in an atomic sequence. It only sends `exit` after all chunks are confirmed written. If any step fails, it raises `TFTTransactionError` and skips `exit`, leaving the keyboard in a recoverable state (cable reconnect).

### TFT Resolution Discovery (2026-05-07)

The retail box lists a 320x240 TFT, but hardware testing confirmed the firmware uses **128x128 RGB565 little-endian** for screen uploads. Uploading 128x128 streams works; 320x240 produced a small corrupted texture in the top-left corner because the firmware interpreted the smaller stream as partial frame data.

Frame format:

```text
offset 0      frame count
offset 1..N   frame delays (delay units are ~2 ms; RoseWaveStudio uses round(seconds * 500))
offset 256    frame 0 RGB565 pixels, 128 * 128 * 2 bytes
offset ...    additional frames, same size
padding       zero padding to 4096-byte chunk boundary
```

One frame = 33,024 payload bytes = 9 chunks of 4096.

The keyboard has two independent screen memories:
- **Boot animation** (shown at power-on)
- **Slot 1+** (shown when rotating the dial)

The metadata command byte 2 (`slot`) selects the target slot (0–255). The official software defaults to slot 1 for the dial-accessible screen. F75Probe exposes `--screen-slot` for any slot in that range; AulaF75Bar hardcodes slot 1 even for its "Upload boot animation" feature, suggesting the true boot animation is firmware-burned and not user-writable.

RoseWaveStudio audit confirmed the `04 28` command (`{0x04, 0x28, 0, 0, 0, 0, 0, 0, 0x01}`) is **only** used during `SyncScreenTime`, not during screen uploads. The upload sequence is strictly `04 18` → `04 72 SS LL HH` → chunks → `04 02`.

### Windows HID Interface Audit (2026-05-07)

Static reverse engineering from official Windows driver `DeviceDriver.exe` (Beta 1.0.0.5) confirms the following HID interfaces on USB-C (`0c45:800a`):

```text
MI_03 (control):  usage_page=0xFF13 usage=0x0001  feature=65  input=65  output=65
MI_02 (data):     usage_page=0xFF68 usage=0x0061  output=4097 input=65  feature=0
```

Key findings:
- **Output report size 4097** = 1 byte report ID + 4096 bytes payload. This matches our `SCREEN_CHUNK_BYTES=4096` exactly.
- **Feature report size 65** = 1 byte report ID + 64 bytes payload. This matches our 64-byte control commands (`04 18`, `04 72`, `04 02`).
- `gif_headlength="256"` in `layouts/rgb-keyboard.xml` confirms our 256-byte stream header.
- `GetImageRGB565Data` symbol confirms the app converts frames to RGB565 before upload.
- The official app decomposes GIFs into individual PNG frames (observed 251 frames → 251 PNGs in AppData), then converts to RGB565 for HID transfer.
- SQLite `t_ledframe_data.delay_time=10` suggests delay units of ~2ms (10 units ≈ 20ms per frame).

Transfer model:
```text
Control: HidD_SetFeature / HidD_GetFeature on MI_03, 65-byte reports
Data:    WriteFile on MI_02, 4097-byte output reports (8 reports per 128x128 frame)
Frame:   32768 bytes RGB565 LE
Header:  256 bytes (frame_count + delay table + padding)
```

Implemented Windows transport: `aula_hacky/windows_hid.py` (ctypes, zero dependencies).
Implemented Windows uploader: `aula_hacky/windows_tft_upload.py`.

### Windows HID Enumeration Workaround (2026-05-08)

**Issue:** `windows_hid.py` auto-enumeration via ctypes/SetupAPI may return empty results even when the AULA F75 Max is connected and visible in Device Manager.

**Verified workaround:** Use manual HID InstanceId paths with `--control-path` and `--pipe-path`:

```cmd
python -m aula_hacky.windows_tft_upload --test-pattern --slot 1 --debug ^
  --control-path "HID\VID_0C45&PID_800A&MI_03\8&5E1A8CD&0&0000" ^
  --pipe-path "HID\VID_0C45&PID_800A&MI_02\8&1DA53512&0&0000"
```

**Verified result:** Upload completes successfully (`begin → metadata → 9 chunks → exit`).

**Discovery:** PowerShell `Get-PnpDevice` correctly enumerates HID InstanceIds, but the ctypes SetupAPI approach does not always open the device handles. The `windows_tft_upload.py` now supports `normalize_hid_path()` to accept either full device paths or Windows InstanceIds.

**Commits:** `887421c` (manual path support), `2053713` (diagnostic script update).

### macOS Upload Blocker — PARTIALLY RESOLVED (2026-05-08)

**Root cause:** macOS was sending HID reports **without** the report_id prefix byte, while Windows sends them **with** the report_id prefix.

| Report Type | Windows (working) | macOS (broken) |
|-------------|-------------------|----------------|
| Feature (control) | 65 bytes (0x00 + 64 payload) | 64 bytes (no prefix) |
| Output (chunks) | 4097 bytes (0x00 + 4096 payload) | 4096 bytes (no prefix) |

**Discovery method:** Byte-by-byte comparison using `tools/capture_windows.py` vs `tools/capture_macos.py`. Windows capture showed 64-byte payloads with `report_id=0` but `HidD_SetFeature` automatically prepends the report_id byte on the wire. macOS `IOHIDDeviceSetReport` with `prefix_report_id=False` sent raw 64/4096 bytes without the prefix.

**Fix:** Changed `hid_macos.py` `write()` default to `prefix_report_id=True`, and `tft_service.py` `_send_control()` to use `prefix_report_id=True`. Now macOS sends 65-byte feature reports and 4097-byte output reports, matching Windows behavior.

**Hardware test result (2026-05-08):** Upload command completes without errors (`begin → metadata → 9 chunks → exit`), but the dial screen does **not** change to show the uploaded pattern. It continues showing the GIF that was uploaded from the official Windows software.

**Hypothesis:** The dial may be displaying a different slot than the one we're uploading to (slots 0, 1, 2, 3 tested). Or there may be an additional "activate slot" command needed.

**Commits:** `43ab7e7` (macOS report_id fix), `36149be` (capture tools).

## Safety Rules

- Do not send invented packets to the keyboard.
- Do not fuzz the device.
- Do not add write paths for macros or remapping until packets are captured or ported from audited public code and documented.
- RGB builders are documented, but a UI should wait until a narrow CLI has exercised them on hardware.
- Keep protocol builders separate from transport code.
- Keep platform-specific HID transport separate from protocol logic.
- Do not implement or recommend a macOS kernel extension.
- Prefer a native SwiftUI macOS app with IOKit/HID transport.
- Use dry-run/logging modes for new command classes before real writes.
- Restrict device access to known VID/PID/interface or usage-page combinations.

## Security Notes

Static inspection found no obvious malware/injection behavior:

- No network client imports.
- No third-party dependencies in `uv.lock`.
- No `eval`, `exec`, `pickle`, or dynamic code loading.
- `subprocess.run` is limited to `tshark` capture decoding.
- `systemd` automation is optional and Linux-only.

Operational risks remain:

- Linux may require `sudo` or a udev rule for HID access.
- The timer writes to `/run/aula-hacky-poll-state.json`.
- The wrapper logs to `/tmp/aula-hacky-poll.log`.
- HID writes intentionally modify keyboard state.

## Development Direction

Recommended macOS architecture:

```text
SwiftUI App
├─ DeviceManager
├─ MacHIDTransport
├─ ProtocolCore
├─ RTCService
├─ ProfileEngine
├─ RGBService
├─ MacroService
└─ TFTService
```

Implementation order:

1. Preserve and document existing Linux RTC behavior.
2. Port protocol builders into a platform-neutral module.
3. Build macOS HID enumeration/open/read/write for the dongle.
4. Implement RTC sync on macOS. Done for the 2.4 GHz dongle.
5. Add cable feature report support. Done and verified on connected macOS USB-C hardware.
6. Capture Windows traffic for one advanced feature at a time.
7. Implement verified advanced commands only after tests reproduce captured packets.

Phase 5 workflow:

1. Capture one Windows software action to `.pcapng`.
2. Extract with `python3 -m aula_hacky.capture_analysis extract ... --output ...jsonl`.
3. Diff controlled captures with `python3 -m aula_hacky.capture_analysis diff left.jsonl right.jsonl`.
4. Document stable headers, variable bytes, report direction, report size, report ID behavior, and ACK behavior.
5. Add protocol builders only after the exact packet is understood and tested.

## Capture Guidance

Use Windows + USBPcap + Wireshark with the official AULA F75 Max software.

Capture one change at a time:

- RGB brightness: 10%, 20%, 30%.
- RGB colors: red, green, blue, white.
- RGB effects: static, breathing, wave.
- Macro: one key sequence, then sequence with delay.
- Remap: one source key to one target key.
- TFT: one small image, then one short GIF.
- Profile save/load: one minimal profile change.

Keep capture filenames explicit:

```text
rgb_brightness_10.pcapng
rgb_brightness_20.pcapng
rgb_color_red.pcapng
macro_simple_ab.pcapng
tft_static_logo.pcapng
```

## Tests

Current verification command:

```bash
python3 -m unittest discover -s tests -v
```

Expected:

```text
Ran 33 tests
OK
```

When adding protocol builders, add tests that reproduce exact captured packet bytes.

## Pending Tasks (Next Session)

### High Priority

1. **TFT Slot/Dial Investigation**
   - macOS uploads complete without error but dial screen does not change
   - Windows uploads currently failing with `HidD_SetFeature failed: 0` (keyboard may be in blocked state)
   - Need to determine: which slot is the dial currently displaying? (probably not 0-3)
   - Need to determine: is there an "activate slot" command? (RoseWaveStudio `04 28` command only used in SyncScreenTime)
   - Need to determine: does the dial have fixed positions (0, 1, 2, 3) or continuous scroll?
   - File: `docs/captures/WINDOWS_SLOT_DIAL_REPORT.md` has Codex initial findings
   - File: `tools/CODEX_QUESTIONS.md` has full investigation questions

2. **Keyboard Recovery**
   - Windows uploads failing — likely keyboard firmware in blocked state
   - Try: disconnect USB-C cable, wait 10s, reconnect
   - Try: power cycle keyboard (if battery powered)
   - Once recovered, verify Windows uploads work again with manual paths

### Medium Priority

3. **macOS Upload Verification**
   - Once slot/dial behavior is understood, test macOS upload to correct slot
   - Verify test pattern or GIF appears on dial screen
   - If successful, port `anim_upload.py` to use configurable frame count and delay

4. **Windows Capture Tools**
   - `tools/capture_windows.py` exists and works (when keyboard is responsive)
   - Use it to capture official software traffic for slot switching, dial rotation
   - Compare bytes with `tools/compare_buffers.py`

### Low Priority

5. **RGB/Protocol Phase 5**
   - RGB packet builders already in `protocol_core.py` (from public reverse engineering)
   - Need hardware-verified captures before implementing UI
   - Wait until TFT protocol is stable

## Current Status Summary

| Feature | macOS | Windows | Linux |
|---------|-------|---------|-------|
| RTC Dongle | ✅ Verified | — | ✅ Verified |
| RTC Cable | ✅ Verified | — | ✅ Verified |
| TFT Upload (command) | ✅ Works | ✅ Works* | — |
| TFT Upload (visible) | ❌ No | ❌ No** | — |
| RGB | Not started | Not started | Not started |
| Macros/Remap | Not started | Not started | Not started |

*Windows requires manual `--control-path` and `--pipe-path` flags.
**Both platforms complete HID commands but dial still shows GIF from official software. Root cause: unknown slot behavior or missing activate command.

## Files Modified This Session

- `aula_hacky/hid_macos.py` — `write()` defaults to `prefix_report_id=True`
- `aula_hacky/tft_service.py` — `_send_control()` uses `prefix_report_id=True`
- `aula_hacky/windows_hid.py` — PowerShell fallback enumeration + manual path support
- `aula_hacky/windows_tft_upload.py` — `--control-path` and `--pipe-path` CLI args
- `tools/byte_logger.py` — JSONL buffer logger (new)
- `tools/capture_windows.py` — Windows buffer capture (new)
- `tools/capture_macos.py` — macOS buffer capture (new)
- `tools/compare_buffers.py` — Cross-platform diff (new)
- `tools/windows_diagnostic.py` — Automated slot testing + bridge client
- `tools/test_connectivity.py` — Network diagnostics
- `tools/debug_hid_windows.py` — PowerShell HID enumeration debug
- `tools/CODEX_QUESTIONS.md` — Questions for Windows investigation
- `docs/captures/WINDOWS_SLOT_DIAL_REPORT.md` — Codex findings
- `docs/WINDOWS_UPLOAD.md` — Windows step-by-step guide
- `AGENTS.md` — This file
