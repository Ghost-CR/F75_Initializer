# Instrucciones de Captura en Vivo — GIF Upload

## ANTES de tocar nada en el software

### Paso 0: Verificar detección
1. ¿El software oficial muestra el teclado como conectado? (¿Hay un indicador de "Connected"?)
2. ¿Por qué conexión está? (USB-C, 2.4G, o Bluetooth?)
3. ¿La pantalla del teclado sigue mostrando la textura corrupta?

### Paso 1: Navegar a la sección de pantalla
4. Busca en el software una pestaña/sección llamada:
   - "Screen"
   - "TFT"
   - "Display"  
   - "LCD"
   - "Animation"
   - "Boot Animation"
   - "Screen Saver"

5. Haz clic en esa sección. ¿Qué opciones ves? Lista TODO lo que aparezca:
   - Botones
   - Dropdowns/menús
   - Preview de la pantalla actual
   - Lista de imágenes/animaciones guardadas

### Paso 2: Preparar archivo GIF de prueba
6. Necesitas un GIF pequeño para subir. Usa este o crea uno:
   - **128×128 píxeles**
   - **Máximo 32 frames** (cuanto menos, mejor para analizar)
   - Colores simples (ej. un cuadrado rojo que parpadea)
   
   Si no tienes uno, descarga cualquier GIF de 128×128 o redimensiona uno.

### Paso 3: Capturar el tráfico USB del GIF upload
7. Abre **Wireshark**.
8. Selecciona la interfaz **USBPcap** donde está el teclado (si no sabes cuál, abre USBPcapCMD.exe y mira la lista).
9. **Inicia la captura** (botón azul de shark fin).
10. En el software oficial AULA, busca **"Upload GIF"**, **"Import Animation"**, o similar.
11. Selecciona tu GIF de prueba.
12. Si te pregunta opciones (slot, frames, delay), anota qué opciones te da y qué seleccionaste.
13. **Haz clic en Upload/Apply/OK.**
14. Espera hasta que el software diga "Success", "Complete", o la barra de progreso termine.
15. **Detén la captura** en Wireshark.
16. Guarda el archivo: `File → Save As` → nombre: `upload_gif_128x128.pcapng`

### Paso 4: Verificar resultado
17. ¿La pantalla del teclado cambió a mostrar el GIF?
18. ¿El dial funciona para cambiar entre imágenes?
19. ¿Ves la imagen corrupta anterior o el nuevo GIF?

### Paso 5: Capturar "Delete/Clear" (si existe)
20. En la misma sección de pantalla, busca opciones como:
    - "Delete"
    - "Remove"
    - "Clear"
    - "Reset"
    - "Factory Reset"
    - "Default"
21. Si existe, inicia otra captura en Wireshark.
22. Haz clic en esa opción.
23. Detén la captura y guarda como `tft_delete_or_clear.pcapng`.

## Información que necesito que me escribas

Copia y pega esto y rellena:

```
CONEXIÓN: [USB-C / 2.4G / Bluetooth]
TECLADO DETECTADO: [Sí / No]
PANTALLA ACTUAL: [Textura corrupta / Animación de boot / Negro / Otra]

SECCIÓN DE PANTALLA ENCONTRADA: [nombre exacto]
OPCIONES VISTAS EN LA SECCIÓN:
- [botón 1]
- [botón 2]
- [dropdown 1: opciones que muestra]
- [etc.]

SUBIR GIF:
- ¿Botón encontrado? [Sí / No, se llama ___]
- ¿Pide seleccionar archivo? [Sí / No]
- ¿Opciones de configuración? [cuántos frames, delay, slot, etc.]
- ¿Resultado del upload? [Éxito / Error / No cambió nada]

BORRAR/RESET:
- ¿Opción encontrada? [Sí, se llama ___ / No]
- ¿Funcionó? [Sí / No]

OTRAS OBSERVACIONES:
- [cualquier cosa rara o interesante]
```
