"""
Byte logger for HID buffer comparison between Windows and macOS.
Captures exact bytes sent to the keyboard for forensic analysis.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import BinaryIO


class ByteLogger:
    """Logs HID report bytes to a file for later comparison."""
    
    def __init__(self, output_dir: str = "logs", platform: str = "unknown"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.platform = platform
        self.sequence = 0
        self.log_file = self.output_dir / f"{platform}_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
    
    def log(self, direction: str, report_type: str, report_id: int, payload: bytes, label: str = ""):
        """Log a buffer."""
        self.sequence += 1
        entry = {
            "seq": self.sequence,
            "timestamp": time.time(),
            "platform": self.platform,
            "direction": direction,
            "report_type": report_type,
            "report_id": report_id,
            "payload_hex": payload.hex(),
            "payload_length": len(payload),
            "label": label,
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def log_feature_set(self, report_id: int, payload: bytes, label: str = ""):
        self.log("out", "feature", report_id, payload, label)
    
    def log_feature_get(self, report_id: int, payload: bytes, label: str = ""):
        self.log("in", "feature", report_id, payload, label)
    
    def log_output(self, report_id: int, payload: bytes, label: str = ""):
        self.log("out", "output", report_id, payload, label)
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
