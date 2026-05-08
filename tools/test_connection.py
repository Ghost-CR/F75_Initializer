#!/usr/bin/env python3
"""
Script de PRUEBA ultra-simple para Windows.
Solo envía un mensaje "hola" al servidor bridge en Mac.
No requiere módulos del proyecto.
"""

import json
import urllib.request

BRIDGE_URL = "http://192.168.1.15:8765"

def main():
    print("=" * 50)
    print("PRUEBA DE CONEXIÓN - Windows a Mac")
    print(f"Destino: {BRIDGE_URL}")
    print("=" * 50)
    
    # 1. Verificar conexión con GET
    print("\n[1/2] Probando GET...")
    try:
        req = urllib.request.Request(BRIDGE_URL, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            health = json.loads(resp.read().decode("utf-8"))
            print(f"✅ Mac responde: {health}")
    except Exception as e:
        print(f"❌ Error en GET: {e}")
        return 1
    
    # 2. Enviar mensaje de prueba con POST
    print("\n[2/2] Enviando mensaje de prueba...")
    try:
        data = {
            "from": "CODEX_WINDOWS",
            "type": "hello_test",
            "payload": {
                "message": "¡Hola desde Windows!",
                "status": "ok",
                "python_version": "funcionando"
            }
        }
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            BRIDGE_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(f"✅ Mensaje enviado. Respuesta: {result}")
    except Exception as e:
        print(f"❌ Error en POST: {e}")
        return 1
    
    print("\n" + "=" * 50)
    print("✅ Prueba completada. Revisa tu Mac.")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
