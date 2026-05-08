#!/usr/bin/env python3
"""Windows diagnostic for AULA F75 Max with manual HID paths."""

import ctypes
import json
import subprocess
import urllib.request

BRIDGE_URL = "http://192.168.1.15:8765"
CONTROL_PATH = r"HID\VID_0C45&PID_800A&MI_03\8&5E1A8CD&0&0000"
PIPE_PATH = r"HID\VID_0C45&PID_800A&MI_02\8&1DA53512&0&0000"


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def send_to_mac(message_type: str, payload):
    data = {"from": "CODEX_WINDOWS", "type": message_type, "payload": payload}
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        BRIDGE_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"[WARN] Error enviando a Mac: {exc}")
        return {"error": str(exc)}


def run_command(cmd: str, timeout: int = 60):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True,
        )
        return {
            "command": cmd,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "command": cmd,
            "stdout": "",
            "stderr": f"Timeout after {timeout}s",
            "returncode": -1,
        }
    except Exception as exc:
        return {
            "command": cmd,
            "stdout": "",
            "stderr": str(exc),
            "returncode": -1,
        }


def run_slot(slot: int):
    cmd = (
        f'python -m aula_hacky.windows_tft_upload --test-pattern --slot {slot} --debug '
        f'--control-path "{CONTROL_PATH}" --pipe-path "{PIPE_PATH}"'
    )
    return run_command(cmd, timeout=120)


def main() -> int:
    print("=" * 60)
    print("AULA F75 Max - Windows Diagnostic Script")
    print(f"Bridge: {BRIDGE_URL}")
    print(f"Control path: {CONTROL_PATH}")
    print(f"Pipe path: {PIPE_PATH}")
    print("=" * 60)

    admin = is_admin()
    print(f"[ADMIN] {admin}")
    send_to_mac("admin_check", {"is_admin": admin})

    print("\n[1/6] Verificando conexion con Mac...")
    try:
        req = urllib.request.Request(BRIDGE_URL, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            health = json.loads(resp.read().decode("utf-8"))
            print(f"[OK] Mac responde: {health}")
    except Exception as exc:
        print(f"[ERROR] No puedo conectar con Mac: {exc}")
        return 1

    print("\n[2/6] Enumerando HID via PowerShell fallback...")
    hid_result = run_command("python -m aula_hacky.windows_hid_ps", timeout=60)
    print(hid_result["stdout"])
    if hid_result["stderr"]:
        print(f"Errores: {hid_result['stderr']}")
    send_to_mac("hid_enumeration", hid_result)

    for idx, slot in enumerate([0, 1, 2, 3], start=3):
        print(f"\n[{idx}/6] Probando upload slot {slot}...")
        res = run_slot(slot)
        out = res["stdout"]
        print(out[-1000:] if len(out) > 1000 else out)
        if res["stderr"]:
            print(f"Errores: {res['stderr']}")
        send_to_mac(f"upload_slot_{slot}", res)

    print("\n" + "=" * 60)
    print("[OK] Diagnostico completo. Resultados enviados a Mac.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
