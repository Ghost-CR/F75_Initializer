"""Parse USBPcap pcapng files to extract HID data - broad search."""
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
    irp_id = struct.unpack('<Q', raw[2:10])[0]
    status = struct.unpack('<I', raw[10:14])[0]
    function = struct.unpack('<H', raw[14:16])[0]
    info = struct.unpack('<H', raw[16:18])[0]
    bus = struct.unpack('<H', raw[18:20])[0]
    device = struct.unpack('<H', raw[20:22])[0]
    endpoint = raw[22]
    transfer = raw[23]
    data_len = struct.unpack('<I', raw[24:28])[0]
    payload_start = header_len
    payload = raw[payload_start:payload_start + data_len] if len(raw) >= payload_start + data_len else raw[payload_start:]
    return {
        'header_len': header_len, 'bus': bus, 'device': device,
        'endpoint': endpoint, 'transfer': transfer, 'data_len': data_len,
        'payload': payload, 'raw': raw
    }

markers = {
    '04 18': bytes([0x04, 0x18]),
    '04 72': bytes([0x04, 0x72]),
    '04 02': bytes([0x04, 0x02]),
    '04 28': bytes([0x04, 0x28]),
    '04 F0': bytes([0x04, 0xF0]),
    '04 13': bytes([0x04, 0x13]),
}

for fname in ['keyboard5.pcapng', 'keyboard6.pcapng', 'keyboard7.pcapng']:
    print(f"\n=== {fname} ===")
    try:
        pkts = parse_pcapng(fname)
    except Exception as e:
        print(f"Error: {e}")
        continue
    print(f"Total packets: {len(pkts)}")
    
    # Show first few packet structures
    print("\nFirst 5 packet structures:")
    for i in range(min(5, len(pkts))):
        p = parse_usbpcap(pkts[i])
        if p:
            print(f"  pkt={i}: header_len={p['header_len']} bus={p['bus']} dev={p['device']} ep={p['endpoint']:02X} transfer={p['transfer']} data_len={p['data_len']} payload_len={len(p['payload'])}")
            print(f"    payload[:32]: {p['payload'][:32].hex()}")
    
    # Search for any marker anywhere in any payload
    found_total = 0
    found_by_marker = {k: 0 for k in markers}
    for i, raw in enumerate(pkts):
        p = parse_usbpcap(raw)
        if not p or len(p['payload']) < 2:
            continue
        payload = p['payload']
        for name, marker in markers.items():
            if marker in payload:
                found_by_marker[name] += 1
                if found_total < 10:
                    idx = payload.find(marker)
                    print(f"\n  MATCH pkt={i} ep={p['endpoint']:02X} marker={name} at offset={idx}")
                    print(f"    context[{max(0,idx-8)}:{idx+24}]: {payload[max(0,idx-8):idx+24].hex()}")
                found_total += 1
    
    print(f"\nTotal matches: {found_total}")
    for name, count in found_by_marker.items():
        if count > 0:
            print(f"  {name}: {count}")
