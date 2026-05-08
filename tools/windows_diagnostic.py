#!/usr/bin/env python3
"""
Script de diagnóstico para Windows — AULA F75 Max TFT Upload Test
Copia este archivo a tu PC Windows y ejecútalo con Codex.

Envía resultados automáticamente al bridge server en Mac.
"""

import subprocess
import json
import urllib.request
import sys
import ctypes

# CONFIGURACIÓN — Cambia esto si la IP de tu Mac es diferente
BRIDGE_URL = "http://192.168.1.15:8765"


def is_admin():
    """Verifica si el script se ejecuta como Administrador en Windows."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def send_to_mac(message_type, payload):
    """Envía un mensaje al servidor bridge en Mac."""
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
        print(f"⚠️  Error enviando a Mac: {e}")
        return {"error": str(e)}


def run_command(cmd, timeout=30):
    """Ejecuta un comando y devuelve stdout/stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Timeout after {timeout}s",
            "returncode": -1
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": -1
        }


def main():
    print("=" * 60)
    print("AULA F75 Max — Windows Diagnostic Script")
    print(f"Enviando resultados a: {BRIDGE_URL}")
    print("=" * 60)

    # Verificar privilegios de administrador
    if not is_admin():
        print("\n⚠️  ADVERTENCIA: Este script NO se ejecuta como Administrador.")
        print("    En Windows, la enumeración HID requiere privilegios elevados.")
        print("    Cierra esta ventana y ejecuta CMD/PowerShell como Administrador.")
        print("    Click derecho → 'Ejecutar como administrador'")
        send_to_mac("admin_warning", {"is_admin": False})
    else:
        print("\n✅ Ejecutando como Administrador.")
        send_to_mac("admin_check", {"is_admin": True})

    # Paso 1: Verificar conexión con Mac
    print("\n[1/6] Verificando conexión con Mac...")
    try:
        req = urllib.request.Request(BRIDGE_URL, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            health = json.loads(resp.read().decode("utf-8"))
            print(f"✅ Mac responde: {health}")
    except Exception as e:
        print(f"❌ No puedo conectar con Mac: {e}")
        print("Verifica que ambas PCs están en la misma red.")
        print(f"IP actual del bridge: {BRIDGE_URL}")
        return 1

    # Paso 2: Enumerar dispositivos HID
    print("\n[2/6] Enumerando dispositivos HID...")
    hid_result = run_command("python -m aula_hacky.windows_hid")
    print(hid_result["stdout"])
    if hid_result["stderr"]:
        print(f"Errores: {hid_result['stderr']}")
    send_to_mac("hid_enumeration", hid_result)

    # Paso 3: Probar upload a slot 0
    print("\n[3/6] Probando upload a slot 0...")
    slot0 = run_command("python -m aula_hacky.windows_tft_upload --test-pattern --slot 0 --debug")
    print(slot0["stdout"][-500:] if len(slot0["stdout"]) > 500 else slot0["stdout"])
    send_to_mac("upload_slot_0", slot0)

    # Paso 4: Probar upload a slot 1
    print("\n[4/6] Probando upload a slot 1...")
    slot1 = run_command("python -m aula_hacky.windows_tft_upload --test-pattern --slot 1 --debug")
    print(slot1["stdout"][-500:] if len(slot1["stdout"]) > 500 else slot1["stdout"])
    send_to_mac("upload_slot_1", slot1)

    # Paso 5: Probar upload a slot 2
    print("\n[5/6] Probando upload a slot 2...")
    slot2 = run_command("python -m aula_hacky.windows_tft_upload --test-pattern --slot 2 --debug")
    print(slot2["stdout"][-500:] if len(slot2["stdout"]) > 500 else slot2["stdout"])
    send_to_mac("upload_slot_2", slot2)

    # Paso 6: Probar upload a slot 3
    print("\n[6/6] Probando upload a slot 3...")
    slot3 = run_command("python -m aula_hacky.windows_tft_upload --test-pattern --slot 3 --debug")
    print(slot3["stdout"][-500:] if len(slot3["stdout"]) > 500 else slot3["stdout"])
    send_to_mac("upload_slot_3", slot3)

    print("\n" + "=" * 60)
    print("✅ Diagnóstico completo. Todos los resultados enviados a Mac.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
