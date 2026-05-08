# Windows Slot/Dial Investigation Report

## 2026-05-08 02:23 (America/Denver)

### Scope executed on Windows
- Pulled latest `master` before tests.
- Ran slot sweep `0..4` using `windows_tft_upload --test-pattern --debug`.
- Ran `tools/capture_windows.py` for byte-level evidence.

### Commands run
```powershell
python -m aula_hacky.windows_tft_upload --test-pattern --slot 0 --debug --control-path "HID\VID_0C45&PID_800A&MI_03\8&5E1A8CD&0&0000" --pipe-path "HID\VID_0C45&PID_800A&MI_02\8&1DA53512&0&0000"
python -m aula_hacky.windows_tft_upload --test-pattern --slot 1 --debug --control-path "HID\VID_0C45&PID_800A&MI_03\8&5E1A8CD&0&0000" --pipe-path "HID\VID_0C45&PID_800A&MI_02\8&1DA53512&0&0000"
python -m aula_hacky.windows_tft_upload --test-pattern --slot 2 --debug --control-path "HID\VID_0C45&PID_800A&MI_03\8&5E1A8CD&0&0000" --pipe-path "HID\VID_0C45&PID_800A&MI_02\8&1DA53512&0&0000"
python -m aula_hacky.windows_tft_upload --test-pattern --slot 3 --debug --control-path "HID\VID_0C45&PID_800A&MI_03\8&5E1A8CD&0&0000" --pipe-path "HID\VID_0C45&PID_800A&MI_02\8&1DA53512&0&0000"
python -m aula_hacky.windows_tft_upload --test-pattern --slot 4 --debug --control-path "HID\VID_0C45&PID_800A&MI_03\8&5E1A8CD&0&0000" --pipe-path "HID\VID_0C45&PID_800A&MI_02\8&1DA53512&0&0000"
python tools/capture_windows.py
```

### Results
- Slot sweep failed identically for slots `0,1,2,3,4`.
- Failure point in all runs: first `begin` control command.
- Error string: `HidD_SetFeature failed: 0`.
- `capture_windows.py` also failed at the same first `begin` feature set.

### Evidence files
- `logs/slot_sweep_20260508_022246.txt`
- `logs/windows_20260508_022301.jsonl`

### Current inference
- This run did not reach metadata/chunk transfer phase.
- No slot activation behavior could be observed from this run because control command failed before upload session started.
- Likely gating factor is device/session state, permissions, or handle/report mode mismatch at runtime.

### Pending manual observations in official Windows app
- Slot UI exists? (dropdown/tabs/list and max visible slot count)
- Dial behavior: fixed positions vs continuous scroll.
- Whether turning dial emits USB traffic while app open.
- Whether "upload" implicitly activates slot or requires separate activation.

### Next recommended capture sequence
1. Open official Windows software and keep device connected/awake.
2. Start USB/HID capture.
3. Perform: select slot in UI -> upload -> set active/default (if present) -> rotate dial.
4. Export capture and compare command bytes against repo scripts.

