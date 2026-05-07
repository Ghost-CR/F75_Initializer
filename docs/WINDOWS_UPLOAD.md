# Windows TFT Upload Guide

## Objective
Run the AULA F75 Max screen uploader directly on Windows using the official USB stack.

## Prerequisites

- Windows 10/11
- Python 3.11+ installed on Windows
- The keyboard connected via **USB-C cable**
- (Optional) Pillow if you want to upload custom GIFs

## Step 1: Copy project to Windows

Copy the entire `F75_Initializer` folder to your Windows machine (USB drive, cloud, etc.).

## Step 2: Install Pillow (optional)

If you want to upload GIFs instead of test patterns:

```cmd
cd F75_Initializer
python -m pip install Pillow
```

## Step 3: Generate a test GIF (optional)

```cmd
python tools\generate_test_gif.py test.gif --frames 5
```

This creates a 5-frame, 128x128 GIF with solid color frames.

## Step 4: Enumerate HID devices

```cmd
python -m aula_hacky.windows_hid
```

You should see:

```text
AULA F75 Max: \\?\hid#vid_0c45&pid_800a&mi_03#...
  usage_page=0xFF13 usage=0x0001
  input=65 output=65 feature=65
AULA F75 Max: \\?\hid#vid_0c45&pid_800a&mi_02#...
  usage_page=0xFF68 usage=0x0061
  input=65 output=4097 feature=0
```

If you don't see these, the keyboard may not be connected via USB-C, or the driver isn't loaded.

## Step 5: Upload test pattern to slot 1

```cmd
python -m aula_hacky.windows_tft_upload --test-pattern --slot 1 --debug
```

Watch the output. You should see:
- `begin` command sent
- `metadata` command sent
- chunk progress 1/9, 2/9, etc.
- `exit` command sent
- "Upload completed" message

## Step 6: Test different slots

If slot 1 doesn't work (keyboard doesn't show the pattern), try slot 0:

```cmd
python -m aula_hacky.windows_tft_upload --test-pattern --slot 0 --debug
```

Try slots 0, 1, 2, 3, etc. The firmware may have remapped the dial to a different slot.

## Step 7: Upload the official GIF

If you have the official `0.gif` (128x128) or the generated `test.gif`:

```cmd
python -m aula_hacky.screen_upload --image test.gif --slot 1 --debug
```

**Note:** `screen_upload.py` currently uses macOS IOKit. For Windows, use `windows_tft_upload.py` for test patterns, or we need to port `screen_upload.py` to use `windows_hid.py`.

## If Upload Fails

1. **Disconnect and reconnect the USB-C cable** between attempts. The firmware can lock up after failed transactions.
2. **Try the official software first** to confirm the keyboard accepts uploads at all.
3. **Capture the official software traffic** using API Monitor or Frida (see below).

## API-Level Capture (Advanced)

If our uploader fails but the official software works, we need to see exactly what buffers the official software sends.

### Option A: API Monitor (GUI)
1. Download [API Monitor](http://www.rohitab.com/apimonitor) on Windows.
2. Launch API Monitor as Administrator.
3. Start monitoring `DeviceDriver.exe`.
4. Filter API calls: `hid.dll!HidD_SetFeature`, `hid.dll!HidD_GetFeature`, `kernel32!WriteFile`.
5. Click "Upload to keyboard" in the official software.
6. Export the captured buffers.

### Option B: Frida Script (Command Line)
1. Install Frida on Windows: `pip install frida-tools`
2. Run the hook script:
   ```cmd
   python tools\frida_hid_hook.py
   ```
   (Script not yet created — ask Kimi if needed.)

## Expected Buffer Sizes

| Call | Size | Purpose |
|------|------|---------|
| `HidD_SetFeature` | 65 bytes | Control commands (begin, metadata, exit) |
| `WriteFile` | 4097 bytes | Image data chunks (1 report ID + 4096 RGB565) |

## Recovery from "Loading" State

If the keyboard shows "loading" or a corrupted texture:
1. Unplug USB-C cable.
2. Wait 5 seconds.
3. Plug USB-C cable back in.
4. Try upload again.

**Do not send `04 02` (exit) on incomplete streams.** That causes the "loading" state.
