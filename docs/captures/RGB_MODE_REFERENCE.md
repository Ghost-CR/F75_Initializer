# RGB Mode Discovery (2026-05-08)

**Note:** These modes are already accessible via the keyboard's physical dial on any OS.
This file is kept for reference but is NOT a development priority.

## Command Sequence

```
04 18 → begin
04 13 → select RGB data
MM ff 00 00 00 00 00 00 BR SP DI 00 00 00 aa 55 ... → payload
04 02 → exit/apply
04 f0 → finish
04 f5 → commit/status (polls repeatedly)
```

## Discovered Modes

| Hex | Count | Likely Name (from official software) |
|-----|-------|--------------------------------------|
| 00  | 1x    | LED Off |
| 01  | 1x    | Static |
| 02  | 1x    | SingleOn |
| 03  | 1x    | SingleOff |
| 04  | 1x    | Glittering |
| 05  | 1x    | Falling |
| 06  | 1x    | Colorful |
| 07  | 1x    | Breath |
| 08  | 1x    | Spectrum |
| 09  | 1x    | Outward |
| 0a  | 1x    | Scrolling |
| 0b  | 1x    | Rolling |
| 0c  | 1x    | Rotating |
| 0d  | 1x    | Explode |
| 0e  | 1x    | Launch |
| 0f  | 1x    | Ripples |
| 10  | 1x    | Flowing |
| 11  | 1x    | Pulsating |
| 12  | 1x    | Tilt |
| 13  | 1x    | Shuttle |

## Payload Format

```
Offset 0:   MM     = mode (0x00-0x13)
Offset 1:   0xff   = fixed?
Offset 2-7: 00...  = padding
Offset 8:   BR     = brightness (0x01-0x05)
Offset 9:   SP     = speed (0x00-0x05)
Offset 10:  DI     = direction (0x00-0x03)
Offset 11-15: 00.. = padding
Offset 16-17: aa55 = marker
```

## Source

Capture: `docs/captures/rgb_mode_off_static_breathing_wave_rainbow.pcapng`
Date: 2026-05-08
