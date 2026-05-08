#!/usr/bin/env python3
"""
Script de debug HID para Windows - usa PowerShell como fallback.
"""

import subprocess
import json
import urllib.request

BRIDGE_URL = "http://192.168.1.15:8765"

def send_to_mac(message_type, payload):
    data = {
        "from": "CODEX_WINDOWS",
        "type": message_type,
        "payload": payload
    }
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        BRIDGE_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error enviando: {e}")
        return {"error": str(e)}


def main():
    print("=" * 60)
    print("DEBUG HID - Windows")
    print("=" * 60)
    
    # Método 1: Nuestro script de Python
    print("\n[1/2] Intentando con script Python...")
    py_result = subprocess.run(
        ["python", "-m", "aula_hacky.windows_hid"],
        capture_output=True, text=True, timeout=10
    )
    print(py_result.stdout)
    if py_result.stderr:
        print(f"Errores: {py_result.stderr}")
    
    # Método 2: PowerShell (más confiable)
    print("\n[2/2] Intentando con PowerShell...")
    ps_cmd = """
Get-PnpDevice -Class HIDClass | Where-Object { 
    $_.InstanceId -match 'HID\\\\VID_0C45' -or 
    $_.InstanceId -match 'HID\\\\VID_05AC'
} | Select-Object Name, InstanceId, Status | Format-List
"""
    ps_result = subprocess.run(
        ["powershell", "-Command", ps_cmd],
        capture_output=True, text=True, timeout=15
    )
    print(ps_result.stdout)
    if ps_result.stderr:
        print(f"Errores PS: {ps_result.stderr}")
    
    # Enviar todo a Mac
    send_to_mac("hid_debug", {
        "python_stdout": py_result.stdout,
        "python_stderr": py_result.stderr,
        "powershell_stdout": ps_result.stdout,
        "powershell_stderr": ps_result.stderr,
    })
    
    print("\n" + "=" * 60)
    print("Debug enviado a Mac.")
    print("=" * 60)


if __name__ == "__main__":
    raise SystemExit(main())
