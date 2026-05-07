# Aula F75 Max Reverse Engineering

Tooling and documentation for the proprietary HID protocol used by the AULA F75 Max keyboard. The current code initializes the keyboard RTC/date-time so the TFT screen leaves the default AULA logo animation and enters its normal mode. The project goal is broader: build a native macOS control app that can eventually configure every available keyboard feature.

Current implementation status:

- Linux CLI works through `hidraw`.
- Platform-neutral protocol builders live in `aula_hacky/protocol_core.py`.
- macOS HID enumeration/open support for the 2.4 GHz dongle lives in `aula_hacky/hid_macos.py`.
- Dongle RTC path is implemented with 32-byte HID interrupt reports.
- Cable RTC path is implemented with 64-byte HID feature reports.
- macOS app and macOS HID transport are not implemented yet.
- RGB, macros, internal key remapping, profiles, and TFT/GIF upload protocols are not fully decoded yet.

## Known Hardware And Protocols

Observed locally on macOS and confirmed by the capture-based Linux implementation:

| Path | VID:PID | Interface | Transport | Report shape | Status |
| --- | --- | ---: | --- | --- | --- |
| 2.4 GHz dongle | `05ac:024f` | `3` | USB HID interrupt | 32-byte input/output reports | RTC sync implemented |
| USB-C cable | `0c45:800a` | `3` | USB HID feature reports | 64-byte `SET_REPORT` / `GET_REPORT` | RTC sync implemented |
| Bluetooth LE | `05ac:024f` as Apple HID keyboard on macOS | N/A | BLE HID | Standard keyboard/media/pointer usages | Useful for typing/remaps, not yet for full config |

The dongle path uses three transactions:

```text
session-init  -> 0200000000000000000000000000000000000000000000000000000000000002
session-query -> 2001000000000000000000000000000000000000000000000000000000000021
rtc-set       -> 0c100000015aYYMMDDHHmmSS0005000000aa55000000000000000000000000CC
```

For 32-byte dongle packets, byte 31 is the checksum:

```text
sum(packet[0:31]) & 0xff
```

The RTC payload fields are raw binary:

```text
YY = year - 2000
MM = month
DD = day
HH = hour
mm = minute
SS = second
```

The cable path uses four 64-byte feature reports:

```text
0418...        cable session init
0428...        cable session prepare
00015aYY...    RTC payload
0402...        cable session finalize
```

The cable RTC payload ends with `aa55`. See `aula_hacky/protocol_core.py` for exact builders and expected replies.

## Project Goal

The long-term target is a native macOS application, tentatively "Aula Control for macOS", that can configure the AULA F75 Max without the Windows-only vendor software.

Target capabilities:

- Detect the keyboard over Bluetooth, 2.4 GHz dongle, and USB-C.
- Initialize/sync RTC so the TFT display enters normal mode.
- Configure Mac layout behavior and profiles.
- Configure RGB effects, per-key color, brightness, speed, and direction.
- Configure macros and internal key mappings.
- Upload and manage TFT screen assets such as images/GIFs if the protocol permits it.
- Save/restore keyboard profiles where firmware support exists.

The current repository only proves and implements the RTC/display initialization path. Advanced controls require additional protocol captures from the official Windows software.

## Repository Files

- `aula_hacky/protocol_core.py`: platform-neutral protocol constants, checksum, packet builders, validators.
- `aula_hacky/protocol.py`: compatibility re-export for older imports.
- `aula_hacky/hidraw_linux.py`: Linux `hidraw` enumeration and I/O.
- `aula_hacky/hid_macos.py`: macOS IOKit/HID enumeration and transport primitives.
- `aula_hacky/macos_cli.py`: macOS HID inspection and transport probe CLI.
- `aula_hacky/macos_probe_matrix.py`: macOS IOKit report semantics probe matrix.
- `aula_hacky/cli.py`: RTC setter CLI.
- `aula_hacky/timer_sync.py`: polling-friendly sync entrypoint for Linux/systemd.
- `aula_hacky/decode_capture.py`: `tshark`-based helper for packet capture decoding.
- `tests/test_protocol.py`: tests proving packet builders match observed captures.
- `keyboard5.pcapng`: dongle capture used for 32-byte interrupt reports.
- `keyboard6.pcapng`: wired capture used for 64-byte feature reports.
- `keyboard7.pcapng`: additional capture for future protocol analysis.
- `deploy/systemd/`: optional Linux timer automation.
- `AGENTS.md`: local memory and guidance for AI agents working on this project.

## Linux Usage

Create the environment and run commands with `uv`. This project is configured for offline-safe `uv run python -m ...` usage, so it does not need to download packaging backends from PyPI just to run locally.

List matching `hidraw` devices:

```bash
uv run python -m aula_hacky.cli --list
```

Set the keyboard clock to the current local time with autodiscovery:

```bash
sudo uv run python -m aula_hacky.cli --time now
```

Set a specific local time:

```bash
sudo uv run python -m aula_hacky.cli --device /dev/hidrawX --time 2026-03-20T10:07:53
```

Dry-run and print packets without touching the device:

```bash
uv run python -m aula_hacky.cli --time 2026-03-20T10:07:53 --dry-run
```

Decode observed endpoint-5 packets from a capture:

```bash
uv run python -m aula_hacky.decode_capture /path/to/keyboard5.pcapng
```

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

## macOS Implementation Plan

Use SwiftUI for the app and IOKit/HID APIs for device access. Do not use kernel extensions.

Recommended architecture:

```text
Aula Control for macOS
├─ SwiftUI app
├─ HID device manager
├─ macOS HID transport
├─ protocol core
├─ profile engine
├─ RGB/macro/TFT modules
└─ local configuration storage
```

Implementation phases:

  1. Port protocol builders from `aula_hacky/protocol.py` into a platform-neutral protocol module.
  2. Implement a macOS HID transport that can open the dongle vendor interface `05ac:024f` and send/receive 32-byte reports.
  3. Implement RTC sync on macOS using the known dongle sequence.
  4. Implement USB-C cable support using 64-byte feature reports for `0c45:800a`.
  5. Capture and decode Windows software traffic for RGB, macros, remapping, and TFT/GIF operations.
  6. Add UI modules only after the corresponding protocol commands are verified.

## Capturing Missing Protocols

Use a Windows machine or a Windows VM with real USB passthrough:

1. Install the official AULA F75 Max software.
2. Install Wireshark with USBPcap.
3. Connect the keyboard through USB-C or the 2.4 GHz dongle.
4. Start a USBPcap capture.
5. Change exactly one setting in the vendor software.
6. Stop and save the capture as `.pcapng`.
7. Repeat with small controlled changes.

Recommended capture matrix:

| Feature | Capture examples |
| --- | --- |
| RGB brightness | 10%, 20%, 30% |
| RGB color | red, green, blue, white |
| RGB effect | static, breathing, wave |
| Per-key RGB | same key, different colors |
| Macro | one simple key sequence, then with delay |
| Remap | one source key to one target key |
| TFT | small static image, then short GIF |
| Profile save/load | one setting change followed by save |

Compare packet bodies between captures and add only verified commands to `protocol_core.py`. Do not fuzz random payloads against the keyboard.

## Security Review

No obvious injection or malware behavior was found in the current repository during local static inspection.

Observed facts:

- `uv.lock` contains only the local project, no third-party packages.
- No code imports `requests`, `urllib`, sockets, or other network libraries.
- No code uses `eval`, `exec`, `pickle`, or dynamic code loading.
- `subprocess.run` is used only in `decode_capture.py` to invoke `tshark` with fixed argument structure.
- Linux `systemd` files are optional and only run the local timer sync command.

Operational risks:

- Linux access may require `sudo` or a udev rule to open HID devices.
- The timer writes state to `/run/aula-hacky-poll-state.json`.
- The wrapper writes logs to `/tmp/aula-hacky-poll.log`.
- HID writes can alter device state, so new commands must come from verified captures.

macOS safety rules:

- Do not implement a kernel extension.
- Restrict device access to known VID/PID/usage-page combinations.
- Add dry-run/logging mode before writing new command classes.
- Do not send RGB, macro, or TFT commands until they are captured and documented.

## macOS HID Probe

List AULA dongle HID interfaces:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m aula_hacky.macos_cli --list
```

Expected dongle vendor interface for the 32-byte path:

```text
vid=0x05ac pid=0x024f usage_page=0xff60 usage=0x0061 in=32 out=32 USB 2.4G Dongle
```

Open the target interface:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m aula_hacky.macos_cli --open-probe
```

In sandboxed environments this may fail with `0xe00002e2`; outside the sandbox it has been verified to open successfully.

Run the report semantics matrix:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m aula_hacky.macos_probe_matrix --timeout 0.25 --stop-on-match
```

Resolved matrix result:

```text
usage_page=0xff60
report_size=32
seize=0
write=output
report_id=0
shape=raw
read=callback
```

The macOS dongle reply can differ from the Linux capture while still being a valid session-init response by prefix and checksum. Observed macOS response:

```text
02000040300000450c0a801001ffff000000000000000000000000000000005c
```

## Timer Automation On Linux

The repository includes a polling-based `systemd` setup that checks every 5 seconds whether the supported cable or dongle interface is present, then runs RTC sync. This is Linux-only and should not be used for macOS.

Before installing, replace the example repository path with the actual checkout path.

```bash
repo_root=/absolute/path/to/your/aula-hacky
cd "$repo_root"
sed "s#__AULA_HACKY_REPO_ROOT__#$repo_root#g" deploy/systemd/aula-hacky-poll.sh | sudo tee /usr/local/bin/aula-hacky-poll.sh >/dev/null
sudo chmod 0755 /usr/local/bin/aula-hacky-poll.sh
sudo install -m 0644 deploy/systemd/aula-hacky-poll.service /etc/systemd/system/aula-hacky-poll.service
sudo install -m 0644 deploy/systemd/aula-hacky-poll.timer /etc/systemd/system/aula-hacky-poll.timer
sudo systemctl daemon-reload
sudo systemctl enable --now aula-hacky-poll.timer
```

The timer uses autodiscovery and prefers:

- cable `0c45:800a`, interface `3`
- dongle `05ac:024f`, interface `3`

State is stored in:

```text
/run/aula-hacky-poll-state.json
```

Logs are written to:

```text
/tmp/aula-hacky-poll.log
```

## Validation

Current protocol tests:

```bash
python3 -m unittest discover -s tests -v
```

Expected result:

```text
Ran 9 tests
OK
```

Use `tshark` for deeper capture analysis when available. It is not required for the existing tests.
