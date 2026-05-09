import frida
import sys
import time
from datetime import datetime

LOG_FILE = r"C:\Projects\F75_Initializer\frida_hid_log.txt"

def on_message(message, data):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        if message["type"] == "send":
            payload = message["payload"]
            ts = datetime.now().isoformat()
            f.write(f"[{ts}] {payload}\n")
            f.flush()
            print(payload)

code = """
var loggedHandles = {};

function logBuffer(name, ptr, len) {
    if (len < 1 || len > 8192) return;
    var buf = Memory.readByteArray(ptr, len);
    var hex = [];
    var bytes = new Uint8Array(buf);
    for (var i = 0; i < bytes.length; i++) {
        hex.push(("0" + bytes[i].toString(16)).slice(-2));
    }
    send(name + " len=" + len + " " + hex.join(" "));
}

// Hook CreateFileW to track HID device opens
var pCreateFileW = Module.findExportByName("kernel32.dll", "CreateFileW");
Interceptor.attach(pCreateFileW, {
    onLeave: function(retval) {
        var handle = this.returnValue;
        if (handle.toInt32() !== -1) {
            send("CreateFileW opened handle=" + handle);
        }
    }
});

// Hook DeviceIoControl
var pDeviceIoControl = Module.findExportByName("kernel32.dll", "DeviceIoControl");
Interceptor.attach(pDeviceIoControl, {
    onEnter: function(args) {
        this.hDevice = args[0];
        this.dwIoControlCode = args[1].toInt32();
        this.lpInBuffer = args[2];
        this.nInBufferSize = args[3].toInt32();
        this.lpOutBuffer = args[4];
        this.nOutBufferSize = args[5].toInt32();
    },
    onLeave: function(retval) {
        if (this.nInBufferSize > 0) {
            logBuffer("DeviceIoControl IN code=0x" + this.dwIoControlCode.toString(16) + " handle=" + this.hDevice, this.lpInBuffer, this.nInBufferSize);
        }
        if (this.nOutBufferSize > 0 && this.lpOutBuffer) {
            logBuffer("DeviceIoControl OUT code=0x" + this.dwIoControlCode.toString(16) + " handle=" + this.hDevice, this.lpOutBuffer, this.nOutBufferSize);
        }
    }
});

// Hook HidD_SetFeature
var pHidD_SetFeature = Module.findExportByName("hid.dll", "HidD_SetFeature");
if (pHidD_SetFeature) {
    Interceptor.attach(pHidD_SetFeature, {
        onEnter: function(args) {
            var len = args[2].toInt32();
            if (len > 0) {
                logBuffer("HidD_SetFeature handle=" + args[0], args[1], len);
            }
        }
    });
}

// Hook HidD_GetFeature
var pHidD_GetFeature = Module.findExportByName("hid.dll", "HidD_GetFeature");
if (pHidD_GetFeature) {
    Interceptor.attach(pHidD_GetFeature, {
        onEnter: function(args) {
            this.h = args[0];
            this.buf = args[1];
            this.len = args[2].toInt32();
        },
        onLeave: function(retval) {
            if (this.len > 0) {
                logBuffer("HidD_GetFeature handle=" + this.h, this.buf, this.len);
            }
        }
    });
}

// Hook HidD_SetOutputReport
var pHidD_SetOutputReport = Module.findExportByName("hid.dll", "HidD_SetOutputReport");
if (pHidD_SetOutputReport) {
    Interceptor.attach(pHidD_SetOutputReport, {
        onEnter: function(args) {
            var len = args[2].toInt32();
            if (len > 0) {
                logBuffer("HidD_SetOutputReport handle=" + args[0], args[1], len);
            }
        }
    });
}

// Hook WriteFile (all sizes)
var pWriteFile = Module.findExportByName("kernel32.dll", "WriteFile");
Interceptor.attach(pWriteFile, {
    onEnter: function(args) {
        var len = args[2].toInt32();
        if (len > 0) {
            logBuffer("WriteFile handle=" + args[0], args[1], len);
        }
    }
});

// Hook ReadFile (all sizes)
var pReadFile = Module.findExportByName("kernel32.dll", "ReadFile");
Interceptor.attach(pReadFile, {
    onEnter: function(args) {
        this.h = args[0];
        this.buf = args[1];
        this.len = args[2].toInt32();
    },
    onLeave: function(retval) {
        if (this.len > 0) {
            logBuffer("ReadFile handle=" + this.h, this.buf, this.len);
        }
    }
});

send("HOOKS READY. Waiting for HID traffic...");
"""

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")

print("[*] Finding DeviceDriver.exe...")
device = frida.get_local_device()
pid = None
for proc in device.enumerate_processes():
    if proc.name.lower() == "devicedriver.exe":
        pid = proc.pid
        break

if pid is None:
    print("[!] DeviceDriver.exe is not running.")
    print("[!] Please open the official AULA software first.")
    sys.exit(1)

print(f"[*] Attaching to DeviceDriver.exe (PID {pid})...")
session = device.attach(pid)
script = session.create_script(code)
script.on("message", on_message)
script.load()

print("[*] Hooks active. Now do this EXACTLY:")
print("    1. Click 'Upload to keyboard' in the software")
print("    2. Wait for it to finish (progress bar / 'Success')")
print("    3. Then press Ctrl+C here to stop capture")
print("[*] Waiting for traffic...\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass

print("\n[*] Detaching...")
session.detach()
print("[*] Done. Check frida_hid_log.txt")
