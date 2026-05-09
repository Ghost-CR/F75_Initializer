"""Extract HID output reports from pcapng capture."""
import struct
import sys

def parse_pcapng(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    pos = 0
    packets = []
    while pos < len(data):
        if pos + 8 > len(data):
            break
        block_type, block_len = struct.unpack('<II', data[pos:pos+8])
        if block_type == 0x00000006:  # EPB
            if pos + 32 <= len(data):
                iface_id, ts_hi, ts_lo, cap_len, orig_len = struct.unpack('<IIIII', data[pos+8:pos+28])
                pkt_start = pos + 32
                pkt_data = data[pkt_start:pkt_start + cap_len]
                packets.append(pkt_data)
        pos += block_len
        if block_len == 0:
            break
    return packets

def parse_usbpcap(raw):
    if len(raw) < 28:
        return None
    header_len = struct.unpack('<H', raw[0:2])[0]
    bus = struct.unpack('<H', raw[18:20])[0]
    device = struct.unpack('<H', raw[20:22])[0]
    endpoint = raw[22]
    transfer = raw[23]
    data_len = struct.unpack('<I', raw[24:28])[0]
    payload_start = header_len
    payload = raw[payload_start:payload_start + data_len] if len(raw) >= payload_start + data_len else raw[payload_start:]
    return {
        'bus': bus, 'device': device, 'endpoint': endpoint,
        'transfer': transfer, 'data_len': data_len, 'payload': payload
    }

# Parse the capture
pkts = parse_pcapng('official_upload_capture.pcapng')
print(f"Total packets: {len(pkts)}")

# Extract HID output reports (host -> device, endpoint OUT or control with data)
# transfer type: 1 = Interrupt, 2 = Control, 3 = Bulk
# endpoint bit 7 = direction (0 = OUT, 1 = IN)
reports = []
for i, raw in enumerate(pkts):
    p = parse_usbpcap(raw)
    if not p or len(p['payload']) < 2:
        continue
    
    # Only host-to-device
    ep_dir = (p['endpoint'] >> 7) & 1
    if ep_dir != 0:  # Skip IN packets
        continue
    
    payload = p['payload']
    
    # Look for HID reports starting with known report IDs
    # The official software uses report_id=0x01 for many things
    if payload[0] == 0x01 and len(payload) >= 65:
        reports.append({
            'frame': i,
            'device': p['device'],
            'endpoint': p['endpoint'],
            'data': payload[:65]
        })
    elif payload[0] == 0x00 and len(payload) >= 65:
        reports.append({
            'frame': i,
            'device': p['device'],
            'endpoint': p['endpoint'],
            'data': payload[:65]
        })

print(f"Extracted {len(reports)} HID output reports")

# Show first 20 unique report patterns
seen = {}
for r in reports[:200]:
    key = r['data'][:8].hex()
    if key not in seen:
        seen[key] = {'count': 0, 'first_frame': r['frame'], 'sample': r['data']}
    seen[key]['count'] += 1

print("\nUnique report patterns (first 8 bytes):")
for key, info in sorted(seen.items(), key=lambda x: x[1]['first_frame'])[:30]:
    print(f"  frame={info['first_frame']} count={info['count']:3d} prefix={key} sample={info['sample'][:16].hex()}")

# Save all reports for analysis
with open('official_upload_reports.bin', 'wb') as f:
    for r in reports:
        f.write(r['data'])
print(f"\nSaved {len(reports)*65} bytes to official_upload_reports.bin")
