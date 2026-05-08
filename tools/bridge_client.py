"""Client for sending messages from Windows agent to Mac bridge server.

Usage:
    python tools/bridge_client.py --url http://<mac-ip>:8765 --file results.txt
    python tools/bridge_client.py --url http://<mac-ip>:8765 --message "Hello from Windows"
    
Or from Python:
    from bridge_client import send_message
    send_message("http://<mac-ip>:8765", type="test_result", payload={...})
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path


def send_message(url: str, message_type: str = "message", payload: dict | str = None, sender: str = "CODEX_WINDOWS") -> dict:
    """Send a message to the bridge server."""
    if payload is None:
        payload = {}
    
    data = {
        "from": sender,
        "type": message_type,
        "payload": payload if isinstance(payload, dict) else {"text": str(payload)}
    }
    
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Send messages to Mac bridge server")
    parser.add_argument("--url", required=True, help="Bridge server URL (e.g., http://192.168.1.100:8765)")
    parser.add_argument("--type", default="message", help="Message type")
    parser.add_argument("--file", help="File to send as payload")
    parser.add_argument("--message", help="Simple text message")
    parser.add_argument("--sender", default="CODEX_WINDOWS", help="Sender identifier")
    args = parser.parse_args()
    
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: File not found: {path}")
            return 1
        payload = {
            "filename": path.name,
            "content": path.read_text(encoding="utf-8")
        }
    elif args.message:
        payload = {"text": args.message}
    else:
        payload = {}
    
    try:
        result = send_message(args.url, args.type, payload, args.sender)
        print("Message sent successfully.")
        print(f"Response: {result}")
        return 0
    except Exception as e:
        print(f"Error sending message: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
