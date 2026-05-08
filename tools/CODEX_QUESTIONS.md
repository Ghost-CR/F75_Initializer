# Preguntas para investigar en Windows - AULA F75 Max Slot/Dial System

## Contexto
El teclado acepta uploads desde macOS (comando exitoso) pero el dial sigue mostrando el GIF oficial subido desde Windows. Necesitamos entender cómo funciona el sistema de slots y cómo cambiar el slot activo del dial.

## Preguntas para explorar en el software oficial Windows

### 1. Sistema de Slots
- ¿En el software oficial hay opciones de "slot" o "pantalla" múltiples?
- ¿Puedes subir diferentes imágenes/GIFs a diferentes "pantallas" o "slots"?
- ¿Hay un dropdown, pestañas, o lista donde seleccionar slot 0, 1, 2, 3?
- ¿Cuántos slots máximo permite el software? (Nosotros sabemos 0-255, pero ¿cuántos usa el software?)

### 2. Funcionamiento del Dial
- ¿Girar el dial físico cambia entre diferentes imágenes/animaciones?
- ¿Cuántas "posiciones" tiene el dial? (ej. 3 posiciones = 3 slots)
- ¿Cada posición del dial muestra un slot diferente?
- ¿El dial funciona como un "switch" entre slots o como un "scroll" continuo?

### 3. Activación/Selección de Slots
- ¿Hay un comando para "activar" o "seleccionar" un slot?
- ¿Hay botones como "Set as default", "Activate", "Switch to this screen"?
- ¿Hay opciones de "Boot animation" vs "Dial screen" vs "Screensaver"?
- ¿Subir una imagen la hace automáticamente visible en el dial, o hay que activarla?

### 4. Captura de tráfico
- Si giras el dial mientras el software está abierto, ¿envía algún comando USB?
- Si cambias de slot en el software, ¿envía un comando de selección?
- Capturar con: `python tools\capture_windows.py` mientras giras el dial

### 5. Estado actual
- ¿A qué slot subiste el GIF que ahora se ve en el dial?
- ¿Puedes subir otro GIF a un slot diferente y ver si el dial cambia?

## Hipótesis
El firmware tiene múltiples slots (0-255) pero el dial solo muestra uno a la vez. Posiblemente:
- El dial tiene posiciones fijas (0, 1, 2) que mapean a slots
- O hay un slot "activo" que se selecciona vía software
- O el dial simplemente itera entre slots que tienen contenido

## Comandos para probar
```cmd
# Ver qué slots están ocupados
for ($slot = 0; $slot -lt 5; $slot++) {
    Write-Host "Testing slot $slot..."
    python -m aula_hacky.windows_tft_upload --test-pattern --slot $slot --debug --control-path "HID\VID_0C45&PID_800A&MI_03\8&5E1A8CD&0&0000" --pipe-path "HID\VID_0C45&PID_800A&MI_02\8&1DA53512&0&0000"
    Start-Sleep -Seconds 2
}
```

## Información a reportar
- Número de posiciones del dial
- Si girar el dial envía comandos USB
- Si el software tiene UI para seleccionar slot activo
- Qué slot muestra el dial actualmente
