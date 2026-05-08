#!/usr/bin/env python3
"""
Script de diagnóstico SIMPLE para Windows — AULA F75 Max
Copia este archivo a tu PC Windows y ejecútalo con Codex.

Este es el script SIMPLIFICADO que solo prueba la conexión y slot 1.
"""

import subprocess
import json
import urllib.request
import sys
import traceback

# CONFIGURACIÓN
BRIDGE_URL = "http://192.168.1.15:8765"

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
    print("AULA F75 Max — Windows Diagnostic Script (SIMPLE)")
    print(f"Enviando resultados a: {BRIDGE_URL}")
    print("=" * 60)

    # Paso 1: Verificar conexión con Mac
    print("\n[1/3] Verificando conexión con Mac...")
    try:
        req = urllib.request.Request(BRIDGE_URL, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            health = json.loads(resp.read().decode("utf-8"))
            print(f"✅ Mac responde: {health}")
            send_to_mac("connection_test", {"status": "ok", "mac_response": health})
    except Exception as e:
        print(f"❌ No puedo conectar con Mac: {e}")
        print("Verifica que ambas PCs están en la misma red.")
        print(f"IP actual del bridge: {BRIDGE_URL}")
        send_to_mac("connection_test", {"status": "failed", "error": str(e)})
        return 1

    # Paso 2: Enumerar dispositivos HID
    print("\n[2/3] Enumerando dispositivos HID...")
    hid_result = run_command("python -m aula_hacky.windows_hid")
    print(hid_result["stdout"])
    if hid_result["stderr"]:
        print(f"Errores: {hid_result['stderr']}")
    send_to_mac("hid_enumeration", hid_result)

    # Paso 3: Probar upload a slot 1 (solo uno, más rápido)
    print("\n[3/3] Probando upload a slot 1...")
    slot1 = run_command("python -m aula_hacky.windows_tft_upload --test-pattern --slot 1 --debug")
    print(slot1["stdout"][-1000:] if len(slot1["stdout"]) > 1000 else slot1["stdout"])
    if slot1["stderr"]:
        print(f"Errores: {slot1['stderr']}")
    send_to_mac("upload_slot_1", slot1)

    print("\n" + "=" * 60)
    print("✅ Diagnóstico completo. Todos los resultados enviados a Mac.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
