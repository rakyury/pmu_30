"""
Unit Tests: Digital Input State Logic

Critical tests for verifying:
1. Switch Active Low: physical LOW voltage = logical ON
2. Switch Active High: physical HIGH voltage = logical ON
3. Initial state after config load
4. Debounce behavior

These tests verify the core logic without requiring a running emulator.
"""

import pytest
import struct


class TestTelemetryParsing:
    """Test telemetry parsing for digital inputs."""

    def test_digital_inputs_all_on(self):
        """Test parsing telemetry with all digital inputs ON."""
        # All 20 inputs ON = bitmask 0x000FFFFF
        bitmask = 0x000FFFFF
        digital_inputs = [(bitmask >> i) & 1 for i in range(20)]

        assert len(digital_inputs) == 20
        assert all(state == 1 for state in digital_inputs)

    def test_digital_inputs_all_off(self):
        """Test parsing telemetry with all digital inputs OFF."""
        bitmask = 0x00000000
        digital_inputs = [(bitmask >> i) & 1 for i in range(20)]

        assert len(digital_inputs) == 20
        assert all(state == 0 for state in digital_inputs)

    def test_digital_inputs_mixed(self):
        """Test parsing telemetry with mixed states."""
        # Inputs 0, 2, 4 ON (bits 0, 2, 4 set) = 0b10101 = 21
        bitmask = 0b10101
        digital_inputs = [(bitmask >> i) & 1 for i in range(20)]

        assert digital_inputs[0] == 1
        assert digital_inputs[1] == 0
        assert digital_inputs[2] == 1
        assert digital_inputs[3] == 0
        assert digital_inputs[4] == 1
        assert digital_inputs[5] == 0


class TestSwitchTypeLogic:
    """Test switch type voltage to state conversion logic.

    Mirrors the firmware logic in pmu_adc.c
    """

    THRESHOLD_HIGH_MV = 2500  # 2.5V
    THRESHOLD_LOW_MV = 1250   # 1.25V (threshold / 2)
    ADC_VREF_MV = 3300        # 3.3V reference
    ADC_RESOLUTION = 1024     # 10-bit

    def voltage_from_adc(self, adc_value: int) -> int:
        """Convert ADC value to millivolts."""
        return (adc_value * self.ADC_VREF_MV) // self.ADC_RESOLUTION

    def process_switch_active_low(self, voltage_mv: int, current_state: int) -> int:
        """
        Active LOW switch logic:
        - When switch CLOSED (pressed): voltage is LOW (grounded) → output 1
        - When switch OPEN (released): voltage is HIGH (pulled up) → output 0
        """
        new_state = current_state

        if voltage_mv < self.THRESHOLD_LOW_MV:
            new_state = 1  # LOW voltage = pressed (active)
        elif voltage_mv > self.THRESHOLD_HIGH_MV:
            new_state = 0  # HIGH voltage = released (inactive)
        # else: keep current state (hysteresis zone)

        return new_state

    def process_switch_active_high(self, voltage_mv: int, current_state: int) -> int:
        """
        Active HIGH switch logic:
        - When voltage HIGH: output 1 (active)
        - When voltage LOW: output 0 (inactive)
        """
        new_state = current_state

        if voltage_mv > self.THRESHOLD_HIGH_MV:
            new_state = 1  # HIGH voltage = pressed
        elif voltage_mv < self.THRESHOLD_LOW_MV:
            new_state = 0  # LOW voltage = released
        # else: keep current state (hysteresis zone)

        return new_state

    # =========================================================================
    # Switch Active Low Tests
    # =========================================================================

    def test_active_low_0v_should_be_on(self):
        """Active Low: 0V input should result in ON state (1)."""
        voltage_mv = 0  # 0V - switch is closed/grounded
        new_state = self.process_switch_active_low(voltage_mv, current_state=0)
        assert new_state == 1, f"Active Low @ 0V should be ON, got {new_state}"

    def test_active_low_5v_should_be_off(self):
        """Active Low: 5V input should result in OFF state (0)."""
        voltage_mv = 5000  # 5V - switch is open, pulled up
        new_state = self.process_switch_active_low(voltage_mv, current_state=1)
        assert new_state == 0, f"Active Low @ 5V should be OFF, got {new_state}"

    def test_active_low_3v3_should_be_off(self):
        """Active Low: 3.3V input should result in OFF state (0)."""
        voltage_mv = 3300  # 3.3V - above high threshold
        new_state = self.process_switch_active_low(voltage_mv, current_state=1)
        assert new_state == 0, f"Active Low @ 3.3V should be OFF, got {new_state}"

    def test_active_low_hysteresis_keeps_on(self):
        """Active Low: Voltage in hysteresis zone keeps ON state."""
        voltage_mv = 2000  # Between thresholds
        new_state = self.process_switch_active_low(voltage_mv, current_state=1)
        assert new_state == 1, "Hysteresis should keep current state (ON)"

    def test_active_low_hysteresis_keeps_off(self):
        """Active Low: Voltage in hysteresis zone keeps OFF state."""
        voltage_mv = 2000  # Between thresholds
        new_state = self.process_switch_active_low(voltage_mv, current_state=0)
        assert new_state == 0, "Hysteresis should keep current state (OFF)"

    # =========================================================================
    # Switch Active High Tests
    # =========================================================================

    def test_active_high_5v_should_be_on(self):
        """Active High: 5V input should result in ON state (1)."""
        voltage_mv = 5000  # 5V - switch is pressed
        new_state = self.process_switch_active_high(voltage_mv, current_state=0)
        assert new_state == 1, f"Active High @ 5V should be ON, got {new_state}"

    def test_active_high_3v3_should_be_on(self):
        """Active High: 3.3V input should result in ON state (1)."""
        voltage_mv = 3300  # 3.3V - above high threshold
        new_state = self.process_switch_active_high(voltage_mv, current_state=0)
        assert new_state == 1, f"Active High @ 3.3V should be ON, got {new_state}"

    def test_active_high_0v_should_be_off(self):
        """Active High: 0V input should result in OFF state (0)."""
        voltage_mv = 0  # 0V - switch is released
        new_state = self.process_switch_active_high(voltage_mv, current_state=1)
        assert new_state == 0, f"Active High @ 0V should be OFF, got {new_state}"

    def test_active_high_hysteresis_keeps_on(self):
        """Active High: Voltage in hysteresis zone keeps ON state."""
        voltage_mv = 2000  # Between thresholds
        new_state = self.process_switch_active_high(voltage_mv, current_state=1)
        assert new_state == 1, "Hysteresis should keep current state (ON)"


class TestEmulatorStateMapping:
    """Test emulator state to voltage mapping.

    The emulator maps logical states to ADC voltages based on input type:
    - Active Low: ON=0V (switch to ground), OFF=5V (pull-up)
    - Active High: ON=5V (powered), OFF=0V (grounded)
    """

    def test_active_low_logical_on_to_voltage(self):
        """Active Low + Logical ON → Should set 0V (switch grounded)."""
        is_active_high = False
        debounced_state = True  # Logical ON

        if debounced_state:
            if is_active_high:
                raw_value = 1023  # 5V
            else:
                raw_value = 0     # 0V
        else:
            if is_active_high:
                raw_value = 0     # 0V
            else:
                raw_value = 1023  # 5V

        assert raw_value == 0, "Active Low + ON should set 0V"

    def test_active_low_logical_off_to_voltage(self):
        """Active Low + Logical OFF → Should set 5V (pull-up)."""
        is_active_high = False
        debounced_state = False  # Logical OFF

        if debounced_state:
            if is_active_high:
                raw_value = 1023
            else:
                raw_value = 0
        else:
            if is_active_high:
                raw_value = 0
            else:
                raw_value = 1023

        assert raw_value == 1023, "Active Low + OFF should set 5V"

    def test_active_high_logical_on_to_voltage(self):
        """Active High + Logical ON → Should set 5V."""
        is_active_high = True
        debounced_state = True  # Logical ON

        if debounced_state:
            if is_active_high:
                raw_value = 1023  # 5V
            else:
                raw_value = 0
        else:
            if is_active_high:
                raw_value = 0
            else:
                raw_value = 1023

        assert raw_value == 1023, "Active High + ON should set 5V"

    def test_active_high_logical_off_to_voltage(self):
        """Active High + Logical OFF → Should set 0V."""
        is_active_high = True
        debounced_state = False  # Logical OFF

        if debounced_state:
            if is_active_high:
                raw_value = 1023
            else:
                raw_value = 0
        else:
            if is_active_high:
                raw_value = 0
            else:
                raw_value = 1023

        assert raw_value == 0, "Active High + OFF should set 0V"


class TestFullFlowLogic:
    """Test the complete flow: emulator state → ADC → telemetry."""

    THRESHOLD_HIGH_MV = 2500
    THRESHOLD_LOW_MV = 1250
    ADC_VREF_MV = 3300
    ADC_RESOLUTION = 1024

    def emulator_state_to_voltage(self, debounced_state: bool, is_active_high: bool) -> int:
        """Convert emulator logical state to voltage (mV)."""
        if debounced_state:  # Logical ON
            if is_active_high:
                return 5000  # 5V
            else:
                return 0     # 0V (grounded)
        else:  # Logical OFF
            if is_active_high:
                return 0     # 0V
            else:
                return 5000  # 5V (pull-up)

    def adc_process(self, voltage_mv: int, is_active_high: bool) -> int:
        """Process ADC voltage to digital state."""
        if is_active_high:
            if voltage_mv > self.THRESHOLD_HIGH_MV:
                return 1
            elif voltage_mv < self.THRESHOLD_LOW_MV:
                return 0
        else:  # Active low
            if voltage_mv < self.THRESHOLD_LOW_MV:
                return 1
            elif voltage_mv > self.THRESHOLD_HIGH_MV:
                return 0
        return 0  # Default

    def test_active_low_default_on_flow(self):
        """
        CRITICAL: Active Low input with default ON state.

        Emulator starts with debounced_state=True (ON).
        For active_low: ON means switch is pressed/grounded.
        Expected: digital_state = 1 (ON)
        """
        is_active_high = False
        debounced_state = True  # Emulator default: ON

        # Step 1: Emulator maps state to voltage
        voltage_mv = self.emulator_state_to_voltage(debounced_state, is_active_high)
        assert voltage_mv == 0, f"Active Low + ON should be 0V, got {voltage_mv}mV"

        # Step 2: ADC processes voltage to state
        digital_state = self.adc_process(voltage_mv, is_active_high)
        assert digital_state == 1, f"0V on Active Low should be ON (1), got {digital_state}"

        # Step 3: Telemetry sends this state
        # UI should show ON
        assert digital_state == 1, "UI should show ON"

    def test_active_high_default_on_flow(self):
        """
        CRITICAL: Active High input with default ON state.

        Emulator starts with debounced_state=True (ON).
        For active_high: ON means switch is pressed = HIGH voltage.
        Expected: digital_state = 1 (ON)
        """
        is_active_high = True
        debounced_state = True  # Emulator default: ON

        # Step 1: Emulator maps state to voltage
        voltage_mv = self.emulator_state_to_voltage(debounced_state, is_active_high)
        assert voltage_mv == 5000, f"Active High + ON should be 5V, got {voltage_mv}mV"

        # Step 2: ADC processes voltage to state
        digital_state = self.adc_process(voltage_mv, is_active_high)
        assert digital_state == 1, f"5V on Active High should be ON (1), got {digital_state}"

    def test_active_low_toggle_off(self):
        """Test toggling active low input to OFF."""
        is_active_high = False
        debounced_state = False  # Toggled to OFF

        voltage_mv = self.emulator_state_to_voltage(debounced_state, is_active_high)
        assert voltage_mv == 5000, "Active Low + OFF should be 5V (pull-up)"

        digital_state = self.adc_process(voltage_mv, is_active_high)
        assert digital_state == 0, "5V on Active Low should be OFF (0)"

    def test_active_high_toggle_off(self):
        """Test toggling active high input to OFF."""
        is_active_high = True
        debounced_state = False  # Toggled to OFF

        voltage_mv = self.emulator_state_to_voltage(debounced_state, is_active_high)
        assert voltage_mv == 0, "Active High + OFF should be 0V"

        digital_state = self.adc_process(voltage_mv, is_active_high)
        assert digital_state == 0, "0V on Active High should be OFF (0)"


class TestDebounceLogic:
    """Test debounce behavior."""

    def test_debounce_counter_increments(self):
        """Debounce counter should increment when state changes."""
        debounce_ms = 50
        debounce_counter = 0
        current_state = 0
        new_state = 1  # Changed

        # Simulate debounce updates
        for _ in range(debounce_ms):
            if new_state != current_state:
                debounce_counter += 1

        assert debounce_counter == debounce_ms

    def test_state_changes_after_debounce(self):
        """State should change after debounce period."""
        debounce_ms = 50
        debounce_counter = 0
        digital_state = 0
        new_state = 1

        # Simulate debounce updates
        for _ in range(debounce_ms):
            if new_state != digital_state:
                debounce_counter += 1
                if debounce_counter >= debounce_ms:
                    digital_state = new_state
                    debounce_counter = 0

        assert digital_state == 1, "State should be 1 after debounce"

    def test_debounce_resets_on_same_state(self):
        """Debounce counter resets when state matches."""
        debounce_counter = 25
        current_state = 1
        new_state = 1  # Same state

        if new_state == current_state:
            debounce_counter = 0

        assert debounce_counter == 0


class TestConfigLoadingBehavior:
    """Test behavior when config is loaded/not loaded."""

    def test_no_config_digital_state_stays_zero(self):
        """
        Without config, digital_state should remain 0.

        This is the BUG scenario: if input_configs[i] == NULL,
        PMU_ADC_Update() doesn't process the input, so digital_state
        stays at 0 (initialized value).
        """
        input_configs = [None] * 20  # No configs loaded
        digital_states = [0] * 20    # Initialized to 0

        # Simulate PMU_ADC_Update() without configs
        for i in range(20):
            if input_configs[i] is not None:
                # Would process here
                pass
            # else: no processing, state stays 0

        # All states should still be 0
        assert all(s == 0 for s in digital_states)

    def test_with_config_state_should_update(self):
        """
        With config loaded, digital_state should update after debounce.

        This test simulates what SHOULD happen after config is written.
        """
        # Simulate config loaded for input 0
        config_loaded = [True] + [False] * 19
        digital_states = [0] * 20
        voltages = [0] * 20  # All at 0V (active low ON)

        THRESHOLD_LOW = 1250

        # Simulate PMU_ADC_Update() with config
        for i in range(20):
            if config_loaded[i]:
                # Active low processing
                if voltages[i] < THRESHOLD_LOW:
                    digital_states[i] = 1  # Would be set after debounce

        # Input 0 should be ON
        assert digital_states[0] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
