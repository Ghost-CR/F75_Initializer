#!/usr/bin/env python3
"""Simple HTTP bridge server for cross-agent communication.

This server accepts JSON POST requests and prints them to stdout,
allowing a Windows agent (Codex) to send data to this Mac agent.

Usage:
    python3 tools/bridge_server.py [--port 8765]
"""

from __future__ import annotations

import argparse
import json
import socket
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer


class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default logging
        pass

    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "agent": "NET_RED_AMIGO"}).encode())

    def do_POST(self):
        """Receive messages from other agents."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body.decode("utf-8"))
            timestamp = datetime.now().isoformat()
            sender = data.get("from", "unknown")
            message_type = data.get("type", "message")
            payload = data.get("payload", {})

            # Print formatted message
            print(f"\n{'='*60}")
            print(f"[{timestamp}] Message from {sender}")
            print(f"Type: {message_type}")
            print(f"{'='*60}")
            if isinstance(payload, dict):
                for key, value in payload.items():
                    print(f"  {key}: {value}")
            else:
                print(f"  {payload}")
            print(f"{'='*60}\n")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "received",
                "timestamp": timestamp,
                "agent": "NET_RED_AMIGO"
            }).encode())

        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def get_ip():
    """Get the primary local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(description="Agent bridge server for cross-machine communication")
    parser.add_argument("--port", type=int, default=8765, help="port to listen on")
    parser.add_argument("--bind", default="0.0.0.0", help="address to bind to")
    args = parser.parse_args()

    ip = get_ip()
    server = HTTPServer((args.bind, args.port), BridgeHandler)

    print(f"🌉 Bridge server running!")
    print(f"   Local URL: http://{ip}:{args.port}")
    print(f"   Health check: curl http://{ip}:{args.port}")
    print(f"   Send message: POST http://{ip}:{args.port}")
    print(f"")
    print(f"   Press Ctrl+C to stop")
    print(f"   Waiting for messages from Windows agent...")
    print(f"")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
        server.shutdown()


if __name__ == "__main__":
    main()
