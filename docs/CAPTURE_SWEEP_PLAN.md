# Plan de Barrido Completo — AULA F75 Max Reverse Engineering

## Estado Actual (2026-05-08)

| Función | Builders Python | Verificado Hardware | Requiere Captura |
|---------|----------------|---------------------|------------------|
| RTC (dongle/cable) | ✅ Completo | ✅ macOS/Windows/Linux | ❌ No |
| TFT upload (estático/GIF) | ✅ Completo | ✅ Windows verificado | ❌ No |
| **RGB** | ✅ `protocol_core.py` | ❌ No | ✅ **Sí** |
| **Macros** | ❌ No existe | ❌ No | ✅ **Sí** |
| **Key Remapping** | ❌ No existe | ❌ No | ✅ **Sí** |
| **Profiles** | ❌ No existe | ❌ No | ✅ **Sí** |
| **Battery/Performance** | ❌ No existe | ❌ No | ✅ **Sí** |
| **Dial/Slot behavior** | ❌ No existe | ❌ No | ✅ **Sí** |

## Fase 1: RGB (Prioridad Alta — Builders ya portados)

### Objetivo
Verificar que `build_wireless_rgb_led_mode_packet()` y `build_cable_rgb_transaction_sequence()` generan bytes correctos.

### Sesión 1.1: RGB Mode
1. Abrir USBPcap + Wireshark
2. En software oficial: RGB → **Off** → espera 3s → **Static** → espera 3s → **Breathing** → espera 3s → **Wave** → espera 3s → **Rainbow** → espera 3s
3. Guardar: `rgb_mode_off_static_breathing_wave_rainbow.pcapng`

### Sesión 1.2: RGB Color
1. Captura limpia
2. Cambiar color: **Rojo puro (FF0000)** → espera 3s → **Verde (00FF00)** → espera 3s → **Azul (0000FF)** → espera 3s → **Blanco (FFFFFF)**
3. Guardar: `rgb_color_red_green_blue_white.pcapng`

### Sesión 1.3: RGB Brightness + Speed + Direction
1. Captura limpia
2. Brillo: **10%** → **50%** → **100%** (3s entre cada)
3. Velocidad: **Lento** → **Medio** → **Rápido**
4. Dirección: **Right** → **Down** → **Left** → **Up**
5. Guardar: `rgb_brightness_speed_direction.pcapng`

**Tiempo:** ~15 minutos

## Fase 2: Macros (Prioridad Media)

### Objetivo
Descubrir protocolo de secuencias de teclas programables.

### Sesión 2.1: Macro Simple
1. Captura limpia
2. Sección **Macro / Macro Manager**
3. Crear macro: **A** (sin delay) → **B** (sin delay)
4. Guardar en slot M1
5. Guardar: `macro_simple_ab.pcapng`

### Sesión 2.2: Macro con Delay
1. Captura limpia
2. Crear macro: **A** → espera 500ms → **B**
3. Guardar: `macro_delay_ab.pcapng`

### Observaciones necesarias
- ¿Cuántos slots de macro hay?
- ¿Se puede asignar macro a tecla específica?
- ¿Hay opción "repeat" o "loop"?

## Fase 3: Key Remapping (Prioridad Media)

### Objetivo
Descubrir cómo se reprograman las teclas.

### Sesión 3.1: Remap Simple
1. Captura limpia
2. **Key Mapping / Remap**
3. Mapear **Caps Lock** → **Ctrl**
4. Aplicar/Guardar
5. Guardar: `remap_caps_to_ctrl.pcapng`

### Sesión 3.2: Remap Multiple
1. Captura limpia
2. Mapear **F1** → **Mute**, **F2** → **Volume Down**
3. Aplicar/Guardar
4. Guardar: `remap_multiple.pcapng`

### Observaciones necesarias
- ¿Lista de "acciones disponibles" (media keys, macros, combos)?
- ¿Se puede desactivar una tecla?
- ¿Hay "layers" o "fn" remapping?

## Fase 4: Profiles (Prioridad Media)

### Objetivo
Descubrir guardado/carga de configuraciones completas.

### Sesión 4.1: Save Profile
1. Captura limpia
2. Sección **Profile**
3. Guardar perfil actual en **Slot 2**
4. Guardar: `profile_save_slot2.pcapng`

### Sesión 4.2: Load Profile
1. Cambiar algo (ej. RGB a rojo)
2. Captura limpia
3. Cargar perfil de **Slot 2**
4. Guardar: `profile_load_slot2.pcapng`

### Observaciones necesarias
- ¿Cuántos slots de perfil?
- ¿Incluyen RGB + Macros + Remap + TFT?

## Fase 5: Battery / Performance (Prioridad Baja)

### Objetivo
Consulta de batería y cambio de modo rendimiento.

### Sesión 5.1: Battery Query
1. Captura limpia
2. **Device Info / Battery / Status**
3. Si hay "Refresh" o "Query", hacer clic
4. Guardar: `battery_query.pcapng`

### Sesión 5.2: Performance Mode
1. Captura limpia
2. **Performance / Game Mode / Response Time**
3. Cambiar: **Normal** → **Game Mode** → **Battery Saving**
4. Guardar: `performance_mode.pcapng`

## Fase 6: Dial / Slot Behavior (Prioridad Alta — Bloqueante para TFT)

### Objetivo
Entender funcionamiento del dial físico y slots.

### Sesión 6.1: Dial Rotation
1. Captura limpia
2. Mantener software abierto
3. **Girar dial físicamente** una posición → espera 2s → otra → espera 2s → otra
4. Guardar: `dial_rotation.pcapng`

### Sesión 6.2: Slot Selection in UI
1. Captura limpia
2. En sección de pantalla/TFT, seleccionar diferentes slots (0, 1, 2, 3)
3. Guardar: `slot_selection_ui.pcapng`

## Calendario Sugerido

| Orden | Fase | Funciones | Tiempo | Prioridad |
|-------|------|-----------|--------|-----------|
| 1 | Fase 1 | RGB | 15 min | 🔴 Alta |
| 2 | Fase 6 | Dial/Slots | 10 min | 🔴 Alta |
| 3 | Fase 2 | Macros | 15 min | 🟡 Media |
| 4 | Fase 3 | Key Remap | 15 min | 🟡 Media |
| 5 | Fase 4 | Profiles | 10 min | 🟡 Media |
| 6 | Fase 5 | Battery/Perf | 10 min | 🟢 Baja |

**Total:** ~75 minutos

## Metodología de Captura

Para cada sesión:
1. **Abrir** USBPcap + Wireshark
2. **Iniciar** captura
3. **Esperar** 2-3 segundos antes de la primera acción
4. **Esperar** 2-3 segundos entre cada cambio
5. **Detener** captura
6. **Guardar** con nombre explícito

## Archivos Esperados

```
docs/captures/
├── rgb_mode_off_static_breathing_wave_rainbow.pcapng
├── rgb_color_red_green_blue_white.pcapng
├── rgb_brightness_speed_direction.pcapng
├── macro_simple_ab.pcapng
├── macro_delay_ab.pcapng
├── remap_caps_to_ctrl.pcapng
├── remap_multiple.pcapng
├── profile_save_slot2.pcapng
├── profile_load_slot2.pcapng
├── battery_query.pcapng
├── performance_mode.pcapng
├── dial_rotation.pcapng
└── slot_selection_ui.pcapng
```

## Post-Captura

1. Copiar archivos a macOS
2. Extraer con:
   ```bash
   python3 -m aula_hacky.capture_analysis extract CAPTURE.pcapng --output CAPTURE.jsonl
   ```
3. Comparar capturas controladas con `capture_analysis diff`
4. Documentar bytes exactos en `protocol_sources.md`
5. Implementar builders en `protocol_core.py`
6. Verificar en hardware real

## Notas Importantes

- **Capturar una función a la vez** para poder hacer diff claro
- **Matar DeviceDriver.exe** antes de usar scripts propios
- **Reconectar USB-C** si el firmware entra en estado "loading"
- El dial puede enviar tráfico USB en tiempo real — mantener captura abierta mientras se gira
