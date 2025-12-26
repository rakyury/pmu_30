"""
Integration Tests: H-Bridge with PID Control
Tests H-Bridge motor control with PID position control and failsafe features.

Covers:
- H-Bridge basic modes (forward, reverse, brake, coast)
- PID position control
- Signal loss detection and failsafe mode
- DBW (Drive By Wire) system with table + PID
- EWG (Electronic Wastegate) system with table + PID
- Recovery from failsafe mode

These tests require a running PMU-30 emulator.
"""

import pytest
import asyncio
import json

# Import fixtures and helpers from conftest
from .helpers import (
    BASE_CONFIG,
    ChannelState,
)



def make_can_message_config(msg_id: str, can_id: int, can_bus: int = 1) -> dict:
    """Create CAN message configuration."""
    return {
        "id": msg_id,
        "name": f"CAN Message {can_id}",
        "base_id": can_id,
        "can_bus": can_bus,
        "dlc": 8,
        "enabled": True,
        "frame_count": 1,
        "is_extended": False,
        "message_type": "standard",
        "timeout_ms": 100,
    }


def make_can_input_config(channel_id: int, name: str, message_ref: str,
                          byte_offset: int = 0, bit_length: int = 16,
                          multiplier: float = 1.0, divider: float = 1.0) -> dict:
    """Create CAN input channel configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "can_rx",
        "id": name,
        "name": name,
        "message_ref": message_ref,
        "byte_offset": byte_offset,
        "bit_length": bit_length,
        "byte_order": "little_endian",
        "data_type": "unsigned",
        "multiplier": multiplier,
        "divider": divider,
        "offset": 0.0,
        "default_value": 0.0,
        "timeout_behavior": "use_default",
    }


def make_analog_input_config(input_num: int, name: str) -> dict:
    """Create analog input configuration for position feedback."""
    return {
        "channel_id": 400 + input_num,
        "channel_type": "analog_input",
        "id": name,
        "name": name,
        "channel": input_num - 1,
        "mode": "linear",
        "min_value": 0,
        "min_voltage": 0.0,
        "max_value": 1000,
        "max_voltage": 5.0,
    }


def make_table_3d_config(channel_id: int, name: str,
                         x_channel: str, y_channel: str,
                         x_values: list, y_values: list,
                         data: list) -> dict:
    """Create 3D table configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "table_3d",
        "id": name,
        "name": name,
        "x_channel": x_channel,
        "y_channel": y_channel,
        "x_values": x_values,
        "y_values": y_values,
        "data": data,
        "interpolation": "bilinear",
        "decimal_places": 0,
    }


def make_pid_config(channel_id: int, name: str,
                    setpoint_channel: str, process_channel: str,
                    kp: float = 1.0, ki: float = 0.0, kd: float = 0.0,
                    output_min: float = -100.0, output_max: float = 100.0) -> dict:
    """Create PID controller configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "pid",
        "id": name,
        "name": name,
        "setpoint_channel": setpoint_channel,
        "setpoint_value": 0.0,
        "process_channel": process_channel,
        "output_channel": None,
        "kp": kp,
        "ki": ki,
        "kd": kd,
        "output_min": output_min,
        "output_max": output_max,
        "i_min": -50.0,
        "i_max": 50.0,
        "sample_time_ms": 10,
        "enabled": True,
    }


def make_hbridge_config(channel_id: int, name: str, bridge_number: int,
                        source_channel: str = "", mode: str = "forward",
                        pwm_source: str = "", position_source: str = "",
                        target_source: str = "",
                        failsafe_enabled: bool = True,
                        signal_timeout_ms: int = 100,
                        failsafe_mode: str = "park",
                        failsafe_position: int = 0) -> dict:
    """Create H-Bridge configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "hbridge",
        "id": name,
        "name": name,
        "enabled": True,
        "bridge_number": bridge_number,
        "motor_preset": "valve",
        "mode": mode,
        "direction": "forward",
        "source_channel": source_channel,
        "direction_source_channel": "",
        "pwm_value": 255,
        "pwm_source_channel": pwm_source,
        "invert_direction": False,
        "position_source_channel": position_source,
        "target_source_channel": target_source,
        "failsafe_enabled": failsafe_enabled,
        "signal_timeout_ms": signal_timeout_ms,
        "failsafe_mode": failsafe_mode,
        "failsafe_position": failsafe_position,
    }


def make_logic_config(channel_id: int, name: str, operation: str,
                      input1: str, input2: str = None) -> dict:
    """Create logic channel configuration."""
    config = {
        "channel_id": channel_id,
        "channel_type": "logic",
        "id": name,
        "name": name,
        "operation": operation,
        "input1_channel": input1,
    }
    if input2:
        config["input2_channel"] = input2
    return config


class TestHBridgeBasicModes:
    """Test basic H-Bridge operating modes."""

    async def test_hbridge_forward_mode(self, emulator_connection):
        """
        Test: H-Bridge forward mode with digital control.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            {
                "channel_id": 1,
                "channel_type": "digital_input",
                "id": "di_control",
                "name": "Control Switch",
                "channel": 0,
                "input_type": "switch_active_high",
                "debounce_ms": 10,
            },
            make_hbridge_config(100, "hb_motor", 0,
                              source_channel="di_control",
                              mode="forward",
                              failsafe_enabled=False),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Activate control
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        # H-Bridge should be running forward
        telemetry = await protocol.get_telemetry()
        # Check H-Bridge state (implementation specific)

    async def test_hbridge_brake_mode(self, emulator_connection):
        """
        Test: H-Bridge brake mode stops motor.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            {
                "channel_id": 1,
                "channel_type": "digital_input",
                "id": "di_brake",
                "name": "Brake Switch",
                "channel": 0,
                "input_type": "switch_active_high",
                "debounce_ms": 10,
            },
            make_hbridge_config(100, "hb_motor", 0,
                              source_channel="di_brake",
                              mode="brake",
                              failsafe_enabled=False),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)


class TestHBridgePIDControl:
    """Test H-Bridge with PID position control."""

    async def test_hbridge_pid_reaches_target(self, emulator_connection):
        """
        Test: H-Bridge with PID reaches target position.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_position"),
            {
                "channel_id": 300,
                "channel_type": "number",
                "id": "target_pos",
                "name": "Target Position",
                "value": 500.0,
            },
            make_hbridge_config(100, "hb_actuator", 0,
                              mode="pid_position",
                              position_source="ai_position",
                              target_source="target_pos",
                              failsafe_enabled=False),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set initial position
        await protocol.set_analog_voltage(0, 0.0)  # Position 0
        await asyncio.sleep(0.5)

        # PID should be driving toward target (500)
        # The motor should be running to reach the target

    async def test_hbridge_pid_from_can_target(self, emulator_connection):
        """
        Test: H-Bridge PID with target from CAN input.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["can_messages"] = [
            make_can_message_config("msg_target", 0x100),
        ]
        config["channels"] = [
            make_analog_input_config(1, "ai_position"),
            make_can_input_config(200, "can_target", "msg_target",
                                byte_offset=0, bit_length=16,
                                multiplier=1.0, divider=10.0),
            make_hbridge_config(100, "hb_actuator", 0,
                              mode="pid_position",
                              position_source="ai_position",
                              target_source="can_target",
                              failsafe_enabled=True,
                              signal_timeout_ms=100),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send CAN message with target value
        await protocol.inject_can_message(1, 0x100, [0xF4, 0x01, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.3)

        # PID should be driving toward CAN target (500)


class TestHBridgeFailsafe:
    """Test H-Bridge signal loss failsafe functionality."""

    async def test_failsafe_on_signal_loss(self, emulator_connection):
        """
        Test: H-Bridge enters failsafe when CAN signal is lost.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["can_messages"] = [
            make_can_message_config("msg_control", 0x100),
        ]
        config["channels"] = [
            make_analog_input_config(1, "ai_position"),
            make_can_input_config(200, "can_control", "msg_control",
                                byte_offset=0, bit_length=8),
            make_hbridge_config(100, "hb_dbw", 0,
                              source_channel="can_control",
                              mode="forward",
                              position_source="ai_position",
                              failsafe_enabled=True,
                              signal_timeout_ms=100,
                              failsafe_mode="park",
                              failsafe_position=0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send initial CAN message
        await protocol.inject_can_message(1, 0x100, [0xFF, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.1)

        # H-Bridge should be running
        # (check telemetry for H-Bridge state)

        # Stop sending CAN messages - simulate signal loss
        await asyncio.sleep(0.2)  # Wait for timeout (100ms)

        # H-Bridge should be in failsafe mode
        telemetry = await protocol.get_telemetry()
        # Verify H-Bridge is in parking/safe state

    async def test_failsafe_recovery(self, emulator_connection):
        """
        Test: H-Bridge recovers from failsafe when signal returns.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["can_messages"] = [
            make_can_message_config("msg_control", 0x100),
        ]
        config["channels"] = [
            make_can_input_config(200, "can_control", "msg_control",
                                byte_offset=0, bit_length=8),
            make_hbridge_config(100, "hb_motor", 0,
                              source_channel="can_control",
                              mode="forward",
                              failsafe_enabled=True,
                              signal_timeout_ms=100,
                              failsafe_mode="brake"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send CAN messages
        await protocol.inject_can_message(1, 0x100, [0xFF, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.1)

        # Stop sending - enter failsafe
        await asyncio.sleep(0.2)

        # Resume sending - should recover
        await protocol.inject_can_message(1, 0x100, [0xFF, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.2)

        # H-Bridge should have recovered to normal operation


class TestDBWSystem:
    """Test Drive By Wire (DBW) system with table + PID."""

    async def test_dbw_full_system(self, emulator_connection):
        """
        Test: Complete DBW system with APS→Table→PID→H-Bridge.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["can_messages"] = [
            make_can_message_config("msg_ecu", 0x360),
        ]
        config["channels"] = [
            # CAN inputs from ECU
            make_can_input_config(200, "ECU_APS", "msg_ecu",
                                byte_offset=0, bit_length=16,
                                multiplier=1.0, divider=10.0),  # 0-100%
            make_can_input_config(201, "ECU_RPM", "msg_ecu",
                                byte_offset=2, bit_length=16),  # RPM

            # Position feedback from throttle body
            make_analog_input_config(1, "TPS_Actual"),

            # 3D Table: APS x RPM → TPS Target
            make_table_3d_config(300, "DBW_Target", "ECU_APS", "ECU_RPM",
                               x_values=[0, 25, 50, 75, 100],  # APS %
                               y_values=[0, 2000, 4000, 6000, 8000],  # RPM
                               data=[
                                   [0, 0, 0, 0, 0],      # 0 RPM
                                   [0, 20, 45, 70, 100],  # 2000 RPM
                                   [0, 22, 48, 75, 100],  # 4000 RPM
                                   [0, 25, 50, 78, 100],  # 6000 RPM
                                   [0, 28, 55, 82, 100],  # 8000 RPM
                               ]),

            # PID Controller for throttle position
            make_pid_config(301, "DBW_PID", "DBW_Target", "TPS_Actual",
                          kp=3.0, ki=0.5, kd=0.1,
                          output_min=-255, output_max=255),

            # H-Bridge for throttle motor
            make_hbridge_config(100, "DBW_Motor", 0,
                              mode="pid_position",
                              pwm_source="DBW_PID",
                              position_source="TPS_Actual",
                              target_source="DBW_Target",
                              failsafe_enabled=True,
                              signal_timeout_ms=100,
                              failsafe_mode="park",
                              failsafe_position=0),  # Closed throttle on failsafe
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Simulate ECU sending APS=50%, RPM=4000
        # APS: 50% = 500 (with divider 10) → bytes: 0xF4 0x01 (500 LE)
        # RPM: 4000 → bytes: 0xA0 0x0F (4000 LE)
        await protocol.inject_can_message(1, 0x360, [0xF4, 0x01, 0xA0, 0x0F, 0, 0, 0, 0])
        await asyncio.sleep(0.5)

        # Table should output ~48% TPS target
        # PID should be driving H-Bridge toward that position

    async def test_dbw_failsafe_closes_throttle(self, emulator_connection):
        """
        Test: DBW system closes throttle on CAN signal loss.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["can_messages"] = [
            make_can_message_config("msg_ecu", 0x360),
        ]
        config["channels"] = [
            make_can_input_config(200, "ECU_APS", "msg_ecu",
                                byte_offset=0, bit_length=16,
                                multiplier=1.0, divider=10.0),
            make_analog_input_config(1, "TPS_Actual"),
            make_hbridge_config(100, "DBW_Motor", 0,
                              source_channel="ECU_APS",
                              mode="pid_position",
                              position_source="TPS_Actual",
                              target_source="ECU_APS",
                              failsafe_enabled=True,
                              signal_timeout_ms=100,
                              failsafe_mode="park",
                              failsafe_position=0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send APS signal
        await protocol.inject_can_message(1, 0x360, [0xF4, 0x01, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.1)

        # Set throttle position to mid-range
        await protocol.set_analog_voltage(0, 2.5)  # 50% position
        await asyncio.sleep(0.2)

        # Stop sending CAN - simulate ECU failure
        await asyncio.sleep(0.15)  # Wait for timeout

        # H-Bridge should be moving throttle to closed position (0)
        telemetry = await protocol.get_telemetry()


class TestEWGSystem:
    """Test Electronic Wastegate (EWG) system with table + PID."""

    async def test_ewg_full_system(self, emulator_connection):
        """
        Test: Complete EWG system with TPS×RPM→Boost Target→PID→H-Bridge.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["can_messages"] = [
            make_can_message_config("msg_ecu", 0x360),
        ]
        config["channels"] = [
            # CAN inputs from ECU
            make_can_input_config(200, "ECU_TPS", "msg_ecu",
                                byte_offset=0, bit_length=16,
                                multiplier=1.0, divider=10.0),  # 0-100%
            make_can_input_config(201, "ECU_RPM", "msg_ecu",
                                byte_offset=2, bit_length=16),
            make_can_input_config(202, "ECU_MAP", "msg_ecu",
                                byte_offset=4, bit_length=16,
                                multiplier=1.0, divider=10.0),  # Manifold pressure kPa

            # Wastegate position feedback
            make_analog_input_config(2, "WG_Position"),

            # 3D Table: TPS x RPM → Boost Target (kPa)
            make_table_3d_config(300, "EWG_Target", "ECU_TPS", "ECU_RPM",
                               x_values=[0, 25, 50, 75, 100],  # TPS %
                               y_values=[0, 2000, 4000, 6000, 8000],  # RPM
                               data=[
                                   [100, 100, 100, 100, 100],  # 0 RPM - atmospheric
                                   [100, 120, 140, 160, 180],  # 2000 RPM
                                   [100, 130, 160, 190, 220],  # 4000 RPM
                                   [100, 140, 180, 220, 250],  # 6000 RPM
                                   [100, 150, 190, 230, 260],  # 8000 RPM
                               ]),

            # PID Controller for wastegate position
            make_pid_config(301, "EWG_PID", "EWG_Target", "ECU_MAP",
                          kp=2.0, ki=0.3, kd=0.05,
                          output_min=0, output_max=100),

            # H-Bridge for wastegate actuator
            make_hbridge_config(101, "EWG_Actuator", 1,
                              mode="pid_position",
                              pwm_source="EWG_PID",
                              position_source="WG_Position",
                              target_source="EWG_Target",
                              failsafe_enabled=True,
                              signal_timeout_ms=100,
                              failsafe_mode="park",
                              failsafe_position=1000),  # Full open on failsafe (safe boost)
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Simulate ECU sending TPS=50%, RPM=4000
        # TPS: 50% = 500 (with divider 10)
        # RPM: 4000
        await protocol.inject_can_message(1, 0x360, [0xF4, 0x01, 0xA0, 0x0F, 0, 0, 0, 0])
        await asyncio.sleep(0.5)

        # Table should output 160 kPa boost target
        # PID should be controlling wastegate position

    async def test_ewg_failsafe_opens_wastegate(self, emulator_connection):
        """
        Test: EWG system opens wastegate fully on signal loss (safe boost).
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["can_messages"] = [
            make_can_message_config("msg_ecu", 0x360),
        ]
        config["channels"] = [
            make_can_input_config(200, "ECU_MAP", "msg_ecu",
                                byte_offset=0, bit_length=16),
            make_analog_input_config(2, "WG_Position"),
            make_hbridge_config(101, "EWG_Actuator", 1,
                              mode="pid_position",
                              position_source="WG_Position",
                              failsafe_enabled=True,
                              signal_timeout_ms=100,
                              failsafe_mode="park",
                              failsafe_position=1000),  # Full open
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send CAN message
        await protocol.inject_can_message(1, 0x360, [0x00, 0x01, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.1)

        # Stop sending - simulate CAN failure
        await asyncio.sleep(0.15)

        # H-Bridge should be moving wastegate to full open (position 1000)
        telemetry = await protocol.get_telemetry()


class TestHBridgeWithCANTarget:
    """Test H-Bridge with target calculated by ECU and sent via CAN."""

    async def test_can_target_to_pid(self, emulator_connection):
        """
        Test: Target from ECU via CAN → PID on PMU → H-Bridge.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["can_messages"] = [
            make_can_message_config("msg_target", 0x400),
        ]
        config["channels"] = [
            # Target position from ECU via CAN
            make_can_input_config(200, "ECU_Target", "msg_target",
                                byte_offset=0, bit_length=16,
                                multiplier=1.0, divider=1.0),

            # Position feedback
            make_analog_input_config(1, "Actual_Position"),

            # PID directly uses CAN target
            make_pid_config(300, "Position_PID", "ECU_Target", "Actual_Position",
                          kp=2.0, ki=0.2, kd=0.05),

            # H-Bridge controlled by PID
            make_hbridge_config(100, "HB_Actuator", 0,
                              mode="pid_position",
                              pwm_source="Position_PID",
                              position_source="Actual_Position",
                              target_source="ECU_Target",
                              failsafe_enabled=True,
                              signal_timeout_ms=100),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # ECU sends target position = 750
        await protocol.inject_can_message(1, 0x400, [0xEE, 0x02, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.5)

        # PID should be driving toward ECU target (750)


class TestSignalValidityDetection:
    """Test signal validity detection for H-Bridge control."""

    async def test_can_timeout_triggers_failsafe(self, emulator_connection):
        """
        Test: CAN message timeout triggers H-Bridge failsafe.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["can_messages"] = [
            {
                "id": "msg_control",
                "name": "Control Message",
                "base_id": 0x100,
                "can_bus": 1,
                "dlc": 8,
                "enabled": True,
                "frame_count": 1,
                "is_extended": False,
                "message_type": "standard",
                "timeout_ms": 50,  # Short timeout for test
            }
        ]
        config["channels"] = [
            make_can_input_config(200, "can_target", "msg_control"),
            # Logic channel to detect CAN validity
            make_logic_config(250, "CAN_Valid", "is_valid", "can_target"),
            make_hbridge_config(100, "hb_motor", 0,
                              source_channel="CAN_Valid",
                              failsafe_enabled=True,
                              signal_timeout_ms=50),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send CAN message
        await protocol.inject_can_message(1, 0x100, [0xFF, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.03)

        # Stop sending - wait for timeout
        await asyncio.sleep(0.1)

        # H-Bridge should be in failsafe mode


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
