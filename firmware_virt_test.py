"""Test virtual channel telemetry with correct config format."""
import serial
import struct
import time
import json

def calc_crc_ccitt(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

def build_frame(cmd, payload=b''):
    length = len(payload)
    crc_data = struct.pack('<H', length) + bytes([cmd]) + payload
    crc = calc_crc_ccitt(crc_data)
    return bytes([0xAA]) + crc_data + struct.pack('<H', crc)

def parse_virtual_channels(payload):
    for offset in [8, 14, 20, 26, 32, 38]:
        if len(payload) >= offset:
            try:
                test_count = struct.unpack_from('<H', payload, len(payload)-offset)[0]
                expected_size = 2 + test_count * 6
                if 0 < test_count < 20 and expected_size == offset:
                    idx = len(payload) - offset + 2
                    channels = {}
                    for i in range(test_count):
                        if idx + 6 <= len(payload):
                            ch_id = struct.unpack_from('<H', payload, idx)[0]
                            ch_val = struct.unpack_from('<i', payload, idx + 2)[0]
                            channels[ch_id] = ch_val
                            idx += 6
                    return test_count, channels
            except:
                pass
    return 0, {}

# Correct config format for timer
config = {
    "version": "3.0",
    "device": {"name": "VirtTest"},
    "channels": [
        {
            "channel_type": "digital_input",
            "channel_id": 50,
            "channel_name": "Button",
            "input_pin": 0,
            "subtype": "switch_active_high"
        },
        {
            "channel_type": "timer",
            "channel_id": 300,
            "channel_name": "Timer5s",
            "start_channel": 50,
            "start_edge": "rising",
            "mode": "count_down",
            "limit_seconds": 5
        }
    ]
}

print("Opening COM11...")
ser = serial.Serial('COM11', 115200, timeout=2)
time.sleep(0.5)
ser.reset_input_buffer()

print("Loading config...")
config_json = json.dumps(config).encode('utf-8')
frame = build_frame(0x22, config_json)  # LOAD_CONFIG
ser.write(frame)
time.sleep(0.5)

data = ser.read(ser.in_waiting or 1024)
for pos in range(len(data) - 5):
    if data[pos] == 0xAA:
        cmd = data[pos+3] if pos+3 < len(data) else 0
        if cmd == 0x21:
            print("[OK] Config loaded")
            break
        elif cmd == 0x22:
            print("[ERROR] Config rejected")

# Start telemetry
frame = build_frame(0x30, struct.pack('<H', 5))
ser.write(frame)
time.sleep(0.3)

print("\nChecking virtual channels in telemetry...")
print("=" * 70)

for i in range(15):
    time.sleep(0.25)
    data = ser.read(ser.in_waiting or 1024)

    pos = 0
    while pos < len(data) - 10:
        if data[pos] == 0xAA:
            length = struct.unpack_from('<H', data, pos+1)[0]
            cmd = data[pos+3]
            if cmd == 0x32 and length > 50:
                payload = data[pos+4:pos+4+length]

                timestamp = struct.unpack_from('<I', payload, 4)[0]
                din = payload[78] if len(payload) > 78 else 0
                
                virt_count, virt = parse_virtual_channels(payload)
                
                btn = "BTN" if (din & 1) else "---"
                virt_str = ", ".join([f"Ch{k}={v}" for k, v in virt.items()]) if virt else "none"
                
                print(f"[{i:2d}] t={timestamp:6d}ms DIN={din:02X} {btn} | Virt({virt_count}): {virt_str}")
                pos = len(data)
                break
            pos += 1
        else:
            pos += 1

frame = build_frame(0x31)
ser.write(frame)
ser.close()
print("\nDone!")
