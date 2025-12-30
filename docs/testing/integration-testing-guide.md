# Integration Testing Guide

**Version:** 1.0
**Date:** December 2024

---

## 1. Overview

Integration tests verify that PMU-30 components work correctly together.

### Test Levels

1. **Module Integration**: Multiple firmware modules
2. **Hardware-in-Loop**: Firmware with actual hardware
3. **System Integration**: Complete system with peripherals

---

## 2. Test Environment

### Hardware Setup

```
+----------------+          +----------------+
|   Test PC      |   USB    |    PMU-30      |
|  (Python)      |----------|    (DUT)       |
+----------------+          +-------+--------+
                                    |
                            +-------+--------+
                            |   Load Board   |
                            | (Resistive)    |
                            +----------------+
```

### Software Requirements

- Python 3.8+
- pytest
- pyserial
- python-can

---

## 3. Test Framework

### Base Test Class

```python
# test_base.py

import pytest
import serial
import time

class PMUTestBase:
    """Base class for PMU integration tests"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Connect to PMU before each test"""
        self.pmu = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
        self.send_command('RESET')
        time.sleep(0.5)
        yield
        self.pmu.close()

    def send_command(self, cmd):
        """Send command and get response"""
        self.pmu.write(f'{cmd}\n'.encode())
        return self.pmu.readline().decode().strip()

    def get_channel(self, channel_id):
        """Read channel value"""
        response = self.send_command(f'CH {channel_id}')
        return int(response.split('=')[1])

    def set_channel(self, channel_id, value):
        """Write channel value"""
        self.send_command(f'CH {channel_id} {value}')

    def wait_stable(self, timeout=1.0):
        """Wait for system to stabilize"""
        time.sleep(timeout)
```

---

## 4. Channel Integration Tests

### Input to Output Flow

```python
# test_channel_flow.py

class TestChannelFlow(PMUTestBase):

    def test_adc_to_output_direct(self):
        """Test ADC input directly controls output"""
        # Configure logic function: CH0 > 500 -> CH100 ON
        self.send_command('FUNC 0 GREATER 0 500 100')

        # Set ADC below threshold
        self.simulate_adc(0, 400)
        self.wait_stable()
        assert self.get_channel(100) == 0

        # Set ADC above threshold
        self.simulate_adc(0, 600)
        self.wait_stable()
        assert self.get_channel(100) == 1

    def test_can_to_output(self):
        """Test CAN signal controls output"""
        # Configure CAN RX: ID 0x360, bit 0-15 -> CH200
        self.send_command('CAN RX 0x360 0 16 200')

        # Configure logic: CH200 > 3000 -> CH101 ON
        self.send_command('FUNC 0 GREATER 200 3000 101')

        # Send CAN message with RPM = 2000
        self.send_can(0x360, [0xD0, 0x07, 0, 0, 0, 0, 0, 0])
        self.wait_stable()
        assert self.get_channel(101) == 0

        # Send CAN message with RPM = 4000
        self.send_can(0x360, [0xA0, 0x0F, 0, 0, 0, 0, 0, 0])
        self.wait_stable()
        assert self.get_channel(101) == 1

    def test_chain_functions(self):
        """Test chained logic functions"""
        # Function 0: Scale ADC (CH0 * 10 -> CH200)
        self.send_command('FUNC 0 SCALE 0 10 0 200')

        # Function 1: Compare (CH200 > 5000 -> CH210)
        self.send_command('FUNC 1 GREATER 200 5000 210')

        # Function 2: AND (CH210 AND CH20 -> CH100)
        self.send_command('FUNC 2 AND 210 20 100')

        # Set ADC to 600 (scaled = 6000, > 5000)
        self.simulate_adc(0, 600)
        self.set_channel(20, 0)  # Switch OFF
        self.wait_stable()
        assert self.get_channel(100) == 0  # AND fails

        self.set_channel(20, 1)  # Switch ON
        self.wait_stable()
        assert self.get_channel(100) == 1  # AND passes
```

---

## 5. CAN Integration Tests

### Message Reception

```python
# test_can_integration.py

import can

class TestCANIntegration(PMUTestBase):

    @pytest.fixture(autouse=True)
    def setup_can(self):
        self.can_bus = can.interface.Bus(
            channel='can0',
            bustype='socketcan',
            bitrate=500000
        )
        yield
        self.can_bus.shutdown()

    def test_can_rx_signal_parsing(self):
        """Test CAN signal parsing"""
        # Configure: ID 0x360, start 0, len 16, factor 1, offset 0 -> CH200
        self.send_command('CAN RX 0x360 0 16 1 0 200')

        # Send message
        msg = can.Message(arbitration_id=0x360, data=[0xE8, 0x03, 0, 0, 0, 0, 0, 0])
        self.can_bus.send(msg)

        self.wait_stable(0.1)
        assert self.get_channel(200) == 1000  # 0x03E8 = 1000

    def test_can_rx_timeout(self):
        """Test CAN timeout detection"""
        # Configure with 100ms timeout
        self.send_command('CAN RX 0x360 0 16 1 0 200 100')

        # Send message
        msg = can.Message(arbitration_id=0x360, data=[0xE8, 0x03, 0, 0, 0, 0, 0, 0])
        self.can_bus.send(msg)
        self.wait_stable(0.05)
        assert not self.is_channel_timeout(200)

        # Wait for timeout
        time.sleep(0.15)
        assert self.is_channel_timeout(200)

    def test_can_tx_periodic(self):
        """Test periodic CAN transmission"""
        # Configure TX: ID 0x600, 100ms, CH100 at byte 0
        self.send_command('CAN TX 0x600 100 100 0')

        # Set output value
        self.set_channel(100, 255)

        # Receive messages
        messages = []
        start = time.time()
        while time.time() - start < 0.5:
            msg = self.can_bus.recv(timeout=0.1)
            if msg and msg.arbitration_id == 0x600:
                messages.append(msg)

        # Should have ~5 messages in 500ms
        assert len(messages) >= 4
        assert len(messages) <= 6
        assert messages[0].data[0] == 255
```

---

## 6. Protection Integration Tests

```python
# test_protection.py

class TestProtection(PMUTestBase):

    def test_overcurrent_protection(self):
        """Test output shuts down on overcurrent"""
        # Configure output with 10A limit
        self.send_command('OUT 100 LIMIT 10000')
        self.set_channel(100, 1000)  # Full ON

        # Simulate overcurrent
        self.simulate_load_current(100, 12000)  # 12A
        self.wait_stable(0.1)

        # Output should be faulted
        assert self.is_channel_fault(100)
        assert self.get_channel(100) == 0

    def test_overcurrent_retry(self):
        """Test automatic retry after fault clear"""
        # Configure 3 retries, 1s delay
        self.send_command('OUT 100 RETRY 3 1000')
        self.set_channel(100, 1000)

        # Trigger overcurrent
        self.simulate_load_current(100, 15000)
        self.wait_stable(0.1)
        assert self.is_channel_fault(100)

        # Clear overcurrent, wait for retry
        self.simulate_load_current(100, 5000)
        time.sleep(1.1)

        # Should have retried and succeeded
        assert not self.is_channel_fault(100)
        assert self.get_channel(100) == 1000

    def test_thermal_derating(self):
        """Test output derated on high temperature"""
        # Set output to 100%
        self.set_channel(100, 1000)

        # Simulate board temp rise
        self.simulate_board_temp(80)  # 80°C
        self.wait_stable()

        # Should be derated
        actual = self.get_actual_output(100)
        assert actual < 1000

        # Higher temp, more derating
        self.simulate_board_temp(95)
        self.wait_stable()
        actual2 = self.get_actual_output(100)
        assert actual2 < actual
```

---

## 7. Logic Function Integration

```python
# test_logic_integration.py

class TestLogicIntegration(PMUTestBase):

    def test_pid_controller(self):
        """Test PID temperature control"""
        # Configure PID: CH0 (temp), setpoint 850, output CH100
        self.send_command('FUNC 0 PID 0 850 100 80 20 10')

        # Simulate temperature below setpoint
        self.simulate_adc(0, 750)  # 75°C
        self.wait_stable(0.5)
        output1 = self.get_channel(100)
        assert output1 > 500  # Should be high

        # Temperature at setpoint
        self.simulate_adc(0, 850)
        self.wait_stable(2.0)  # Allow PID to settle
        output2 = self.get_channel(100)
        assert 400 < output2 < 600  # Should be around 50%

        # Temperature above setpoint
        self.simulate_adc(0, 950)
        self.wait_stable(0.5)
        output3 = self.get_channel(100)
        assert output3 < output2  # Should decrease

    def test_hysteresis(self):
        """Test hysteresis function"""
        # Configure: ON at 85, OFF at 80
        self.send_command('FUNC 0 HYSTERESIS 0 850 800 100')

        # Below both thresholds - OFF
        self.simulate_adc(0, 750)
        self.wait_stable()
        assert self.get_channel(100) == 0

        # Cross ON threshold
        self.simulate_adc(0, 860)
        self.wait_stable()
        assert self.get_channel(100) == 1

        # Between thresholds - stays ON
        self.simulate_adc(0, 820)
        self.wait_stable()
        assert self.get_channel(100) == 1

        # Below OFF threshold
        self.simulate_adc(0, 790)
        self.wait_stable()
        assert self.get_channel(100) == 0

    def test_timer_functions(self):
        """Test delay on/off functions"""
        # Configure delay-on: 500ms
        self.send_command('FUNC 0 DELAY_ON 20 100 500')

        # Input goes high
        self.set_channel(20, 1)
        self.wait_stable(0.2)
        assert self.get_channel(100) == 0  # Not yet

        time.sleep(0.4)
        assert self.get_channel(100) == 1  # Now ON

        # Input goes low - immediate off
        self.set_channel(20, 0)
        self.wait_stable(0.1)
        assert self.get_channel(100) == 0
```

---

## 8. Performance Tests

```python
# test_performance.py

class TestPerformance(PMUTestBase):

    def test_logic_execution_time(self):
        """Verify logic functions execute within 2ms"""
        # Configure all 64 functions
        for i in range(64):
            self.send_command(f'FUNC {i} ADD {i*2} {i*2+1} {i+200}')

        # Measure execution time
        times = []
        for _ in range(100):
            start = time.time()
            self.send_command('EXEC')
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        assert avg_time < 1.5  # Average < 1.5ms
        assert max_time < 2.0  # Max < 2ms

    def test_adc_sample_rate(self):
        """Verify ADC samples at 1kHz"""
        # Enable ADC timestamp logging
        self.send_command('LOG ADC ON')

        time.sleep(1.0)

        # Get log
        log = self.send_command('LOG ADC GET')
        samples = log.count('ADC')

        assert 990 < samples < 1010  # 1000 +/- 1%
```

---

## 9. Running Tests

### Command Line

```bash
# Run all integration tests
pytest test/ -v

# Run specific test file
pytest test/test_channel_flow.py -v

# Run with hardware
pytest test/ -v --hardware

# Generate report
pytest test/ --html=report.html
```

### CI/CD Integration

```yaml
# .github/workflows/integration.yml
integration_test:
  runs-on: self-hosted
  steps:
    - uses: actions/checkout@v2
    - name: Run Integration Tests
      run: |
        pytest test/ -v --hardware --junitxml=results.xml
    - name: Upload Results
      uses: actions/upload-artifact@v2
      with:
        name: test-results
        path: results.xml
```

---

## See Also

- [Emulator Guide](emulator-guide.md) - Desktop testing without hardware
- [Unit Testing Guide](unit-testing-guide.md)
- [Test Cases](test-cases.md)
- [Troubleshooting Guide](../operations/troubleshooting-guide.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024
