#!/usr/bin/env python3
"""
Diagnóstico de conectividad ultra-simple para Windows.
Prueba paso a paso la conexión con el servidor bridge en Mac.
"""

import json
import socket
import urllib.request

BRIDGE_URL = "http://192.168.1.15:8765"

def test_connectivity():
    print("=" * 60)
    print("DIAGNÓSTICO DE CONECTIVIDAD - Windows a Mac")
    print(f"Destino: {BRIDGE_URL}")
    print("=" * 60)
    
    # Paso 1: Resolver DNS/IP
    print("\n[1/4] Resolviendo IP...")
    try:
        hostname = BRIDGE_URL.replace("http://", "").split(":")[0]
        ip = socket.gethostbyname(hostname)
        print(f"✅ IP resuelta: {ip}")
    except Exception as e:
        print(f"❌ Error resolviendo IP: {e}")
        return False
    
    # Paso 2: Probar conexión TCP
    print("\n[2/4] Probando conexión TCP...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, 8765))
        if result == 0:
            print(f"✅ Conexión TCP exitosa a {ip}:8765")
            sock.close()
        else:
            print(f"❌ Conexión TCP falló con código: {result}")
            print("   Posibles causas:")
            print("   - Firewall en Mac bloqueando puerto 8765")
            print("   - Firewall en Windows bloqueando conexiones salientes")
            print("   - Mac y Windows en redes diferentes")
            return False
    except Exception as e:
        print(f"❌ Error en conexión TCP: {e}")
        return False
    
    # Paso 3: HTTP GET
    print("\n[3/4] Probando HTTP GET...")
    try:
        req = urllib.request.Request(BRIDGE_URL, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"✅ GET exitoso: {data}")
    except Exception as e:
        print(f"❌ Error en GET: {e}")
        return False
    
    # Paso 4: HTTP POST
    print("\n[4/4] Probando HTTP POST...")
    try:
        data = {
            "from": "CODEX_WINDOWS",
            "type": "connectivity_test",
            "payload": {"status": "ok", "message": "Conexión funcionando"}
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
            print(f"✅ POST exitoso: {result}")
    except Exception as e:
        print(f"❌ Error en POST: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ TODAS LAS PRUEBAS PASARON - La conexión funciona")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_connectivity()
    exit(0 if success else 1)
