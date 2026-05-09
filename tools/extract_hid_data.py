"""Extract and analyze HID output reports from official software capture."""
import subprocess
import re

LOG_FILE = r"C:\Projects\F75_Initializer\official_hid_log.txt"

# Use tshark to extract HID data with direction
cmd = [
    r"C:\Program Files\Wireshark\tshark.exe",
    "-r", r"C:\Projects\F75_Initializer\official_upload_capture.pcapng",
    "-Y", "usb.idVendor==0x0c45 && usbhid.data",
    "-T", "fields",
    "-e", "frame.number",
    "-e", "usb.src",
    "-e", "usb.dst",
    "-e", "usb.endpoint_address.number",
    "-e", "usb.endpoint_address.direction",
    "-e", "usbhid.data",
]

result = subprocess.run(cmd, capture_output=True, text=True)
lines = result.stdout.strip().split('\n')

print(f"Total HID lines: {len(lines)}")

# Separate host->device vs device->host
host_to_dev = []
dev_to_host = []

for line in lines:
    parts = line.split('\t')
    if len(parts) != 6:
        continue
    frame, src, dst, ep_num, ep_dir, data_hex = parts
    
    # Determine direction
    if "host" in src.lower():
        host_to_dev.append((int(frame), int(ep_num), data_hex))
    else:
        dev_to_host.append((int(frame), int(ep_num), data_hex))

print(f"Host->Device: {len(host_to_dev)}")
print(f"Device->Host: {len(dev_to_host)}")

# Show first 20 host->device packets
print("\n=== First 20 Host->Device HID reports ===")
for i, (frame, ep, data) in enumerate(host_to_dev[:20]):
    print(f"  frame={frame} ep={ep} len={len(data)//2} data={data[:64]}...")

# Show unique starting bytes for host->device
prefixes = {}
for frame, ep, data in host_to_dev:
    prefix = data[:16] if len(data) >= 16 else data
    if prefix not in prefixes:
        prefixes[prefix] = 0
    prefixes[prefix] += 1

print("\n=== Unique host->device prefixes (first 8 bytes) ===")
for prefix, count in sorted(prefixes.items(), key=lambda x: -x[1])[:20]:
    print(f"  {prefix}: {count} times")

# Save all host->device data for analysis
with open(r"C:\Projects\F75_Initializer\host_to_dev_hid.bin", "wb") as f:
    for frame, ep, data in host_to_dev:
        f.write(bytes.fromhex(data))
print(f"\nSaved {len(host_to_dev)} host->device reports to host_to_dev_hid.bin")

# Save all device->host data
with open(r"C:\Projects\F75_Initializer\dev_to_host_hid.bin", "wb") as f:
    for frame, ep, data in dev_to_host:
        f.write(bytes.fromhex(data))
print(f"Saved {len(dev_to_host)} device->host reports to dev_to_host_hid.bin")
