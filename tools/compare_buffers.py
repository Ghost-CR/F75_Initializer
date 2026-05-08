#!/usr/bin/env python3
"""
Compare Windows vs macOS buffer logs to find differences.
Usage: python tools/compare_buffers.py logs/windows_*.jsonl logs/macos_*.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_log(path: Path) -> list[dict]:
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def compare_entries(win_entries: list[dict], mac_entries: list[dict]):
    print("=" * 70)
    print("BUFFER COMPARISON: Windows vs macOS")
    print("=" * 70)
    
    # Match by sequence and label
    win_by_label = {e["label"]: e for e in win_entries}
    mac_by_label = {e["label"]: e for e in mac_entries}
    
    all_labels = sorted(set(win_by_label.keys()) | set(mac_by_label.keys()))
    
    differences = 0
    
    for label in all_labels:
        win = win_by_label.get(label)
        mac = mac_by_label.get(label)
        
        print(f"\n--- {label} ---")
        
        if win and not mac:
            print(f"  ❌ Only in Windows")
            continue
        if mac and not win:
            print(f"  ❌ Only in macOS")
            continue
        
        win_hex = win["payload_hex"]
        mac_hex = mac["payload_hex"]
        win_len = win["payload_length"]
        mac_len = mac["payload_length"]
        
        print(f"  Windows: {win_len} bytes")
        print(f"  macOS:   {mac_len} bytes")
        
        if win_len != mac_len:
            print(f"  ⚠️  LENGTH DIFFERENCE: {win_len} vs {mac_len}")
            differences += 1
        
        if win_hex != mac_hex:
            print(f"  ❌ PAYLOAD DIFFERENCE")
            differences += 1
            
            # Show first difference
            win_bytes = bytes.fromhex(win_hex)
            mac_bytes = bytes.fromhex(mac_hex)
            min_len = min(len(win_bytes), len(mac_bytes))
            
            for i in range(min_len):
                if win_bytes[i] != mac_bytes[i]:
                    print(f"     First diff at byte {i}: Windows=0x{win_bytes[i]:02X}, macOS=0x{mac_bytes[i]:02X}")
                    # Show context
                    start = max(0, i - 8)
                    end = min(min_len, i + 8)
                    print(f"     Context:")
                    print(f"       Windows: {win_bytes[start:end].hex()}")
                    print(f"       macOS:   {mac_bytes[start:end].hex()}")
                    break
        else:
            print(f"  ✅ IDENTICAL")
    
    print(f"\n{'=' * 70}")
    if differences == 0:
        print("✅ ALL BUFFERS IDENTICAL")
        print("The issue is NOT in the payload bytes.")
        print("Possible causes: timing, report ID handling, or USB stack differences.")
    else:
        print(f"❌ {differences} differences found")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Compare Windows vs macOS HID buffers")
    parser.add_argument("windows_log", help="Windows log file (.jsonl)")
    parser.add_argument("macos_log", help="macOS log file (.jsonl)")
    args = parser.parse_args()
    
    win_entries = load_log(Path(args.windows_log))
    mac_entries = load_log(Path(args.macos_log))
    
    print(f"Windows entries: {len(win_entries)}")
    print(f"macOS entries: {len(mac_entries)}")
    
    compare_entries(win_entries, mac_entries)


if __name__ == "__main__":
    main()
