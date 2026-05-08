# Instrucciones para ejecutar diagnóstico en PowerShell como Administrador

## Paso 1: Abrir PowerShell como Administrador

**Método A - Menú Inicio:**
1. Presiona tecla **Windows**
2. Escribe **"PowerShell"**
3. **Click derecho** en "Windows PowerShell" 
4. Selecciona **"Ejecutar como administrador"**
5. Click **"Sí"** en el diálogo de Control de Cuentas de Usuario (UAC)

**Método B - Atajo de teclado:**
1. Presiona **Win + X**
2. Selecciona **"Windows PowerShell (administrador)"** o **"Terminal (administrador)"**
3. Click **"Sí"** en el UAC

**Método C - Desde CMD:**
```cmd
powershell -Command "Start-Process powershell -Verb runAs"
```

## Paso 2: Navegar al proyecto

En la ventana de PowerShell (con título que dice "Administrador"):

```powershell
cd "C:\Users\Gary Mueras Martínez\OneDrive\Escritorio\F75_Initializer"
```

## Paso 3: Actualizar desde GitHub

```powershell
git pull origin master
```

## Paso 4: Ejecutar diagnóstico HID

```powershell
python tools\debug_hid_windows.py
```

Esto usará PowerShell nativo para buscar dispositivos HID, lo cual es más confiable que nuestro script ctypes.

## Paso 5: Si encuentra el teclado, ejecutar upload de prueba

```powershell
python tools\windows_diagnostic.py
```

## Verificación de permisos

Para confirmar que PowerShell tiene permisos de admin, ejecuta:

```powershell
[Security.Principal.WindowsIdentity]::GetCurrent().Groups -match 'S-1-5-32-544'
```

Si devuelve un valor (no vacío), tienes permisos de administrador.

## Si Codex está integrado en VS Code

Si estás usando Codex dentro de VS Code:

1. **Cierra VS Code completamente**
2. Busca "Visual Studio Code" en el menú inicio
3. **Click derecho** → **"Ejecutar como administrador"**
4. Abre la terminal integrada (Ctrl + `)
5. Ejecuta los comandos arriba

## Solución de problemas

**Si git no funciona en PowerShell:**
```powershell
# Verificar que git está en PATH
git --version

# Si no funciona, usa la ruta completa:
& "C:\Program Files\Git\bin\git.exe" pull origin master
```

**Si python no funciona:**
```powershell
# Verificar versión
python --version

# Si no funciona, prueba py:
py tools\debug_hid_windows.py
```

**Si sigue sin detectar dispositivos:**
1. Verifica que el teclado esté conectado por USB-C físico
2. Desconecta y reconecta el cable USB-C
3. Espera 5 segundos
4. Ejecuta el diagnóstico de nuevo
