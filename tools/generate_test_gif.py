"""Generate a simple test GIF for AULA F75 Max screen upload.

Usage:
    python tools/generate_test_gif.py output.gif [--frames 5]

Requires Pillow.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

def generate_test_gif(output_path: Path, frame_count: int = 5) -> None:
    try:
        from PIL import Image
    except ImportError:
        print("Error: Pillow is required. Install with: pip install Pillow")
        sys.exit(1)

    size = 128
    frames: list[Image.Image] = []
    
    colors = [
        (255, 0, 0),    # Red
        (0, 255, 0),    # Green
        (0, 0, 255),    # Blue
        (255, 255, 0),  # Yellow
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Cyan
        (255, 255, 255),# White
        (0, 0, 0),      # Black
    ]
    
    for i in range(frame_count):
        img = Image.new("RGB", (size, size), colors[i % len(colors)])
        frames.append(img)
    
    # Save as GIF with 200ms delay (delay=100 in 2ms units ~ 200ms)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=200,  # ms per frame
        loop=0,
    )
    print(f"Generated {frame_count}-frame test GIF: {output_path}")
    print(f"Each frame is {size}x{size}, RGB. Total size: {output_path.stat().st_size} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate test GIF for AULA F75 Max")
    parser.add_argument("output", help="output GIF path")
    parser.add_argument("--frames", type=int, default=5, help="number of frames (1-255)")
    args = parser.parse_args()
    
    if args.frames < 1 or args.frames > 255:
        parser.error("--frames must be 1..255")
    
    generate_test_gif(Path(args.output), args.frames)
