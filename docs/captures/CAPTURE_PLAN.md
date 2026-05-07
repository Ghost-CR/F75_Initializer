# Plan de Captura USBPcap — AULA F75 Max

## Objetivo
Capturar el tráfico HID entre el software oficial Windows y el teclado para:
1. Recuperar el teclado del estado TFT corrupto.
2. Decodificar los protocolos de RGB, macros, remapping, profiles y TFT.

## Setup

### Requisitos
- Windows 10/11
- [USBPcap](https://github.com/desowin/usbpcap) instalado
- [Wireshark](https://www.wireshark.org/) instalado
- Software oficial AULA F75 Max instalado (`DeviceDriver.exe`)

### Paso 0: Identificar el bus USB
1. Conecta el teclado por **USB-C cable** (prioridad) y también por **dongle 2.4 GHz** (si puedes).
2. Abre USBPcapCMD.exe (viene con USBPcap).
3. Identifica el bus donde aparece el teclado. Suele ser algo como `\\.\USBPcap1`.
4. Anota el nombre exacto del bus.

## Captura 1: Recuperación TFT (PRIORIDAD MÁXIMA)

**Contexto:** El teclado muestra una textura corrupta en el dial y no acepta uploads de pantalla desde macOS. Necesitamos ver cómo el software oficial Windows la recupera.

### Instrucciones
1. Abre Wireshark.
2. Selecciona la interfaz USBPcap correspondiente al teclado.
3. **Inicia la captura** (botón azul).
4. Abre el software oficial AULA F75 Max.
5. Navega a la sección de **pantalla / TFT / screen**.
6. Si hay una opción de **"Delete", "Clear", "Reset", "Factory Reset"** de la pantalla — úsala.
7. Si no hay opción de borrado, sube la imagen oficial `0.gif` (128×128) como **nueva animación de boot** o **nueva pantalla**.
8. Si te da opción de elegir **slot** (0, 1, 2, etc.), prueba slot 0 y slot 1.
9. **Detén la captura** después de que el software diga "Success" o similar.
10. Guarda el archivo como `tft_recovery_upload.pcapng`.

### Qué documentar
- ¿El software muestra opciones de slot? ¿Cuáles?
- ¿Hay una opción de "delete" o "clear"?
- ¿La pantalla del teclado cambia inmediatamente después del upload?
- ¿El dial del teclado funciona para cambiar entre imágenes?

## Captura 2: RGB — Brightness

**Objetivo:** Entender el protocolo de control RGB.

1. Inicia captura limpia en Wireshark.
2. En el software oficial, ve a la sección **RGB / Lighting**.
3. Cambia el **brillo** de 10% → 20% → 30%.
4. Detén la captura.
5. Guarda como `rgb_brightness_10_20_30.pcapng`.

## Captura 3: RGB — Color

1. Inicia captura limpia.
2. Cambia el color a **rojo puro** → **verde puro** → **azul puro** → **blanco**.
3. Detén la captura.
4. Guarda como `rgb_color_red_green_blue_white.pcapng`.

## Captura 4: RGB — Effect

1. Inicia captura limpia.
2. Cambia el efecto a **static** → **breathing** → **wave**.
3. Detén la captura.
4. Guarda como `rgb_effect_static_breathing_wave.pcapng`.

## Captura 5: Macro Simple

1. Inicia captura limpia.
2. Ve a la sección **Macro**.
3. Crea un macro simple: pulsa **A** luego **B** (sin delay).
4. Guarda el macro en un perfil.
5. Detén la captura.
6. Guarda como `macro_ab.pcapng`.

## Captura 6: Remap Simple

1. Inicia captura limpia.
2. Ve a la sección **Key Mapping / Remap**.
3. Mapea una sola tecla (ej. **Caps Lock** → **Ctrl**).
4. Guarda/Aplica el remap.
5. Detén la captura.
6. Guarda como `remap_caps_to_ctrl.pcapng`.

## Captura 7: Profile Save/Load

1. Inicia captura limpia.
2. Ve a la sección **Profile**.
3. Guarda el perfil actual en un **slot nuevo** (ej. slot 2).
4. Cambia algo pequeño (ej. color RGB a rojo).
5. Guarda de nuevo en el mismo slot.
6. Detén la captura.
7. Guarda como `profile_save_slot2.pcapng`.

## Formato de Archivos

Nombrar archivos explícitamente:

```
tft_recovery_upload.pcapng
rgb_brightness_10_20_30.pcapng
rgb_color_red_green_blue_white.pcapng
rgb_effect_static_breathing_wave.pcapng
macro_ab.pcapng
remap_caps_to_ctrl.pcapng
profile_save_slot2.pcapng
```

## Después de las Capturas

1. Copia los archivos `.pcapng` a macOS (AirDrop, USB, cloud).
2. Colócalos en `/Users/garymurdock/Projects/F75_Initializer/docs/captures/`.
3. Ejecuta el decoder:
   ```bash
   python3 -m aula_hacky.capture_analysis extract docs/captures/tft_recovery_upload.pcapng --output docs/captures/tft_recovery_upload.jsonl
   ```
4. Comparte el archivo JSONL para análisis.

## Notas Importantes

- **Captura uno a la vez:** Cada `.pcapng` debe contener **solo un cambio** para poder hacer diff.
- **Espera entre cambios:** Déjale al software 2-3 segundos entre cada acción para que el tráfico se separe claramente.
- **USB-C primero:** Captura USB-C (64-byte feature reports) antes que dongle (32-byte interrupt reports).
- **Dongle también:** Si puedes, repite la captura de TFT recovery con el dongle para comparar protocolos.
