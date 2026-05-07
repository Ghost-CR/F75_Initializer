# Tarea para Codex (Windows) — AULA F75 Max Diagnostic

## Contexto
El usuario está diagnosticando por qué un teclado AULA F75 Max no acepta uploads de pantalla TFT. El teclado muestra una textura corrupta en el dial. El usuario tiene acceso a Windows con el software oficial instalado.

## Tu objetivo
Ejecutar un script Python que pruebe múltiples estrategias de upload en el teclado AULA F75 Max conectado por USB-C.

## Prerrequisitos
- Python 3.11+ instalado en Windows
- Teclado AULA F75 Max conectado por USB-C cable
- (Opcional) Pillow instalado: `python -m pip install Pillow`

## Archivos necesarios
Copia la carpeta `F75_Initializer` completa desde la Mac al PC Windows.

## Comandos a ejecutar

### Paso 1: Enumerar dispositivos HID
```cmd
cd F75_Initializer
python -m aula_hacky.windows_hid
```

**Esperado:** Debe mostrar al menos dos interfaces del teclado:
```text
AULA F75 Max: \\?\hid#vid_0c45...
  usage_page=0xFF13 usage=0x0001
  input=65 output=65 feature=65
AULA F75 Max: \\?\hid#vid_0c45...
  usage_page=0xFF68 usage=0x0061
  input=65 output=4097 feature=0
```

Si NO aparecen, verifica:
- ¿El teclado está conectado por USB-C?
- ¿El software oficial lo detecta?
- ¿Hay algún error de permisos? (Ejecutar CMD como Administrador)

### Paso 2: Probar upload a múltiples slots
Ejecuta estos comandos uno por uno. Después de cada intento:
- OBSERVA si la pantalla del teclado cambia
- Anota el resultado

```cmd
python -m aula_hacky.windows_tft_upload --test-pattern --slot 0 --debug
```

Espera 5 segundos, luego:
```cmd
python -m aula_hacky.windows_tft_upload --test-pattern --slot 1 --debug
```

Espera 5 segundos, luego:
```cmd
python -m aula_hacky.windows_tft_upload --test-pattern --slot 2 --debug
```

Espera 5 segundos, luego:
```cmd
python -m aula_hacky.windows_tft_upload --test-pattern --slot 3 --debug
```

### Paso 3: Si ningún slot funciona
Prueba con chunk_delay más largo (el firmware puede necesitar más tiempo):
```cmd
python -m aula_hacky.windows_tft_upload --test-pattern --slot 1 --debug --chunk-delay 0.1
```

### Paso 4: Generar GIF de prueba (opcional)
Si tienes Pillow instalado:
```cmd
python tools\generate_test_gif.py test_5frames.gif --frames 5
```

## Qué reportar

Copia y pega esto rellenando los resultados:

```
=== RESULTADOS ===

Dispositivos HID encontrados:
[Pega aquí la salida del paso 1]

Slot 0:
- ¿Funcionó? [Sí / No]
- ¿Pantalla cambió? [Sí / No / No reaccionó]
- Últimas líneas de output: [pega aquí]

Slot 1:
- ¿Funcionó? [Sí / No]
- ¿Pantalla cambió? [Sí / No / No reaccionó]
- Últimas líneas de output: [pega aquí]

Slot 2:
- ¿Funcionó? [Sí / No]
- ¿Pantalla cambió? [Sí / No / No reaccionó]
- Últimas líneas de output: [pega aquí]

Slot 3:
- ¿Funcionó? [Sí / No]
- ¿Pantalla cambió? [Sí / No / No reaccionó]
- Últimas líneas de output: [pega aquí]

Observaciones adicionales:
- [¿Viste algún error específico?]
- [¿El software oficial detecta el teclado?]
- [¿Puedes subir GIFs desde el software oficial?]
```

## Notas de seguridad
- No modifiques el firmware del teclado.
- Si algo falla, desconecta y reconecta el cable USB-C.
- No envíes comandos inventados al teclado.
- Usa solo los scripts proporcionados.

## Si todo falla
Si ningún slot funciona, necesitamos capturar el tráfico del software oficial. Pregunta al usuario si quiere usar API Monitor o Frida para capturar los buffers exactos que envía el software oficial Windows.
