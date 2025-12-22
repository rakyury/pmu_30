# Security Guide

**Version:** 1.0
**Date:** December 2024

---

## 1. Security Overview

PMU-30 implements multiple security layers to protect against unauthorized access and ensure safe operation.

---

## 2. Communication Security

### WiFi Security

| Feature | Implementation |
|---------|----------------|
| Protocol | WPA2-Personal |
| Encryption | AES-256 |
| Default SSID | PMU-30-XXXX (last 4 of serial) |
| Default Password | pmu30admin |

**Best Practices:**
1. Change default password immediately
2. Use strong password (12+ characters)
3. Disable WiFi when not needed
4. Use hidden SSID in production

### Bluetooth Security

| Feature | Implementation |
|---------|----------------|
| Protocol | BLE 5.0 |
| Pairing | Secure Simple Pairing |
| Bonding | Required |
| Encryption | AES-128 |

### USB Security

- Authenticated configuration upload
- CRC verification
- Firmware signature check

---

## 3. Configuration Protection

### Access Levels

| Level | Access | Authentication |
|-------|--------|----------------|
| View | Read-only | None |
| User | Basic settings | PIN (4-digit) |
| Admin | Full access | Password |
| Factory | Calibration | Factory key |

### Setting Access Level

```json
{
  "security": {
    "access_level": "admin",
    "pin": "1234",
    "password_hash": "sha256:...",
    "lockout_attempts": 5,
    "lockout_duration_min": 15
  }
}
```

### Protected Settings

| Setting | Minimum Level |
|---------|---------------|
| Output names | User |
| Current limits | Admin |
| Protection thresholds | Admin |
| CAN configuration | Admin |
| Firmware update | Admin |
| Factory calibration | Factory |

---

## 4. Firmware Security

### Secure Boot

1. Bootloader verifies firmware signature
2. Only signed firmware accepted
3. Rollback protection enabled

### Firmware Signing

```bash
# Sign firmware
pmu-sign --key private.pem --input firmware.bin --output firmware.signed

# Verify signature
pmu-verify --key public.pem --input firmware.signed
```

### Update Process

1. Upload signed firmware
2. Verify signature
3. Verify CRC
4. Write to flash
5. Verify written data
6. Reboot to new firmware

---

## 5. CAN Bus Security

### Message Authentication

Optional CAN message authentication:

```json
{
  "can_security": {
    "authentication": true,
    "key": "0x0102030405060708",
    "protected_ids": ["0x7E0", "0x7E1"]
  }
}
```

### Protective Measures

1. **ID filtering**: Reject unknown message IDs
2. **Rate limiting**: Detect flood attacks
3. **Timeout detection**: Identify missing messages
4. **Sequence numbers**: Detect replay attacks

---

## 6. Physical Security

### Enclosure

- Tamper-evident seals
- No external debug ports
- Protected USB port

### Debug Interface

- JTAG disabled in production
- SWD protected by readout protection
- Debug requires factory unlock

---

## 7. Safe Failure Modes

### Fault Responses

| Condition | Response |
|-----------|----------|
| Authentication failure | Lock access, log event |
| Invalid configuration | Reject, use previous |
| Firmware corruption | Boot recovery image |
| Crash detected | Safe shutdown |
| Watchdog timeout | System reset |

### Safe State

All outputs disabled, H-bridges in coast mode, error logged.

---

## 8. Audit Logging

### Logged Events

| Event | Severity |
|-------|----------|
| Login success | Info |
| Login failure | Warning |
| Configuration change | Info |
| Firmware update | Info |
| Security lockout | Warning |
| Fault detected | Error |
| Safe shutdown | Critical |

### Log Format

```json
{
  "timestamp": "2024-12-15T10:30:00Z",
  "event": "CONFIG_CHANGE",
  "severity": "INFO",
  "user": "admin",
  "details": "Output 5 current limit changed from 15A to 20A"
}
```

### Log Retention

- 1000 events in RAM
- 10000 events in flash
- Oldest overwritten when full

---

## 9. Security Checklist

### Initial Setup

- [ ] Change default WiFi password
- [ ] Set admin password
- [ ] Configure access levels
- [ ] Disable unused interfaces
- [ ] Enable audit logging

### Regular Maintenance

- [ ] Review audit logs
- [ ] Update firmware
- [ ] Rotate passwords
- [ ] Check for security updates

### Before Deployment

- [ ] Lock configuration
- [ ] Verify firmware signature
- [ ] Test authentication
- [ ] Document access credentials

---

## 10. Vulnerability Reporting

Report security vulnerabilities to R2 m-sport security team.

**Do NOT:**
- Disclose publicly before fix
- Exploit vulnerabilities
- Share exploit code

---

## See Also

- [Configuration Reference](../operations/configuration-reference.md)
- [Deployment Guide](../operations/deployment-guide.md)
- [Troubleshooting](../operations/troubleshooting-guide.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024
