"""
Critical Config Integrity Test

Generates a complex real-world configuration with 300+ interconnected items,
saves it to a file, loads it back, and verifies no data is lost.

This test catches:
- Serialization bugs
- Deserialization bugs
- Field omission
- Type conversion errors
- Reference resolution issues

Run:
    python -m pytest tests/unit/test_config_integrity.py -v -s
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List
import copy
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from models.config_manager import ConfigManager


def generate_real_world_config() -> Dict[str, Any]:
    """
    Generate a comprehensive real-world configuration with 300+ items.

    Includes all channel types interconnected as they would be in a real application:
    - Analog inputs for sensors
    - Digital inputs for switches and buttons
    - Power outputs controlled by logic
    - CAN messages for ECU communication
    - Timers for delayed actions
    - Filters for signal conditioning
    - Tables for lookup
    - PID controllers
    - H-Bridges for motors
    - Logic functions connecting everything
    """
    config = {
        "version": "3.0",
        "device": {
            "name": "PMU-30 Race Car",
            "serial_number": "PMU30-2024-12345",
            "firmware_version": "2.1.0",
            "hardware_revision": "C",
            "created": "2024-12-28T10:00:00Z",
            "modified": "2024-12-28T12:00:00Z"
        },
        "can_messages": [],
        "channels": [],
        "system": {
            "control_frequency_hz": 1000,
            "logic_frequency_hz": 500,
            "startup_delay_ms": 500,
            "undervoltage_threshold_v": 10.5,
            "overvoltage_threshold_v": 16.0
        },
        "can_bus": {
            "can_a": {
                "baudrate": 500000,
                "fd_enabled": False
            },
            "can_b": {
                "baudrate": 1000000,
                "fd_enabled": True
            }
        },
        "standard_can_stream": {
            "enabled": True,
            "can_bus": 1,
            "base_id": 0x600,
            "is_extended": False
        }
    }

    # ==================== CAN MESSAGES (20 items) ====================
    can_messages = [
        # Engine ECU messages
        {"id": "ecu_engine_1", "name": "ECU Engine 1", "can_bus": 1, "base_id": 0x100,
         "dlc": 8, "timeout_ms": 100, "description": "RPM, TPS, MAP"},
        {"id": "ecu_engine_2", "name": "ECU Engine 2", "can_bus": 1, "base_id": 0x101,
         "dlc": 8, "timeout_ms": 100, "description": "Coolant, Oil, Fuel"},
        {"id": "ecu_engine_3", "name": "ECU Engine 3", "can_bus": 1, "base_id": 0x102,
         "dlc": 8, "timeout_ms": 100, "description": "Lambda, Ignition, Boost"},
        # Dashboard messages
        {"id": "dash_inputs", "name": "Dashboard Inputs", "can_bus": 1, "base_id": 0x200,
         "dlc": 8, "timeout_ms": 50, "description": "Buttons, Rotary"},
        {"id": "dash_status", "name": "Dashboard Status", "can_bus": 1, "base_id": 0x201,
         "dlc": 8, "timeout_ms": 200, "description": "Screen state"},
        # PDM status messages (TX)
        {"id": "pdm_status_1", "name": "PDM Status 1", "can_bus": 1, "base_id": 0x300,
         "dlc": 8, "timeout_ms": 0, "is_extended": False, "description": "Output currents 1-8"},
        {"id": "pdm_status_2", "name": "PDM Status 2", "can_bus": 1, "base_id": 0x301,
         "dlc": 8, "timeout_ms": 0, "description": "Output currents 9-16"},
        {"id": "pdm_status_3", "name": "PDM Status 3", "can_bus": 1, "base_id": 0x302,
         "dlc": 8, "timeout_ms": 0, "description": "Temperatures, voltages"},
        # ABS/TC messages
        {"id": "abs_wheel_speeds", "name": "ABS Wheel Speeds", "can_bus": 2, "base_id": 0x400,
         "dlc": 8, "timeout_ms": 20, "description": "FL, FR, RL, RR speeds"},
        {"id": "abs_status", "name": "ABS Status", "can_bus": 2, "base_id": 0x401,
         "dlc": 4, "timeout_ms": 50, "description": "ABS/TC active flags"},
        # Gear position
        {"id": "gearbox_pos", "name": "Gearbox Position", "can_bus": 1, "base_id": 0x500,
         "dlc": 2, "timeout_ms": 100, "description": "Current gear"},
        # Fuel level
        {"id": "fuel_level_msg", "name": "Fuel Level Message", "can_bus": 1, "base_id": 0x501,
         "dlc": 4, "timeout_ms": 500, "description": "Fuel level and consumption"},
        # GPS
        {"id": "gps_position", "name": "GPS Position", "can_bus": 2, "base_id": 0x600,
         "dlc": 8, "timeout_ms": 200, "is_extended": True, "description": "Lat/Lon"},
        {"id": "gps_speed", "name": "GPS Speed", "can_bus": 2, "base_id": 0x601,
         "dlc": 4, "timeout_ms": 200, "is_extended": True, "description": "Ground speed"},
        # Data logger
        {"id": "logger_sync", "name": "Logger Sync", "can_bus": 2, "base_id": 0x700,
         "dlc": 8, "timeout_ms": 0, "description": "Data logger sync"},
        # Telemetry
        {"id": "telemetry_cmd", "name": "Telemetry Command", "can_bus": 2, "base_id": 0x7F0,
         "dlc": 8, "timeout_ms": 1000, "description": "Telemetry commands"},
        # Pit-to-car
        {"id": "pit_commands", "name": "Pit Commands", "can_bus": 2, "base_id": 0x7F8,
         "dlc": 8, "timeout_ms": 5000, "is_extended": False, "description": "Pit board messages"},
        # BlinkMarine keypad
        {"id": "keypad_rx", "name": "Keypad RX", "can_bus": 1, "base_id": 0x18EF0000,
         "dlc": 8, "timeout_ms": 100, "is_extended": True, "description": "Keypad buttons"},
        # Steering wheel
        {"id": "steering_buttons", "name": "Steering Buttons", "can_bus": 1, "base_id": 0x150,
         "dlc": 4, "timeout_ms": 50, "description": "Steering wheel buttons"},
        # Chassis sensors
        {"id": "chassis_sensors", "name": "Chassis Sensors", "can_bus": 2, "base_id": 0x450,
         "dlc": 8, "timeout_ms": 100, "description": "Damper positions, brake pressure"}
    ]
    config["can_messages"] = can_messages

    channels = []
    channel_id = 1

    # ==================== ANALOG INPUTS (20 items) ====================
    analog_inputs = [
        {"id": "ai_coolant_temp", "name": "Coolant Temperature", "input_pin": 0,
         "subtype": "calibrated", "unit": "C", "min_value": -40, "max_value": 150},
        {"id": "ai_oil_temp", "name": "Oil Temperature", "input_pin": 1,
         "subtype": "calibrated", "unit": "C", "min_value": -40, "max_value": 180},
        {"id": "ai_oil_pressure", "name": "Oil Pressure", "input_pin": 2,
         "subtype": "linear", "unit": "bar", "min_voltage": 0.5, "max_voltage": 4.5,
         "min_value": 0, "max_value": 10},
        {"id": "ai_fuel_pressure", "name": "Fuel Pressure", "input_pin": 3,
         "subtype": "linear", "unit": "bar", "min_voltage": 0.5, "max_voltage": 4.5,
         "min_value": 0, "max_value": 6},
        {"id": "ai_brake_pressure_f", "name": "Front Brake Pressure", "input_pin": 4,
         "subtype": "linear", "unit": "bar", "min_voltage": 0.5, "max_voltage": 4.5,
         "min_value": 0, "max_value": 100},
        {"id": "ai_brake_pressure_r", "name": "Rear Brake Pressure", "input_pin": 5,
         "subtype": "linear", "unit": "bar", "min_voltage": 0.5, "max_voltage": 4.5,
         "min_value": 0, "max_value": 100},
        {"id": "ai_tps_main", "name": "TPS Main", "input_pin": 6,
         "subtype": "linear", "unit": "%", "min_voltage": 0.5, "max_voltage": 4.5,
         "min_value": 0, "max_value": 100},
        {"id": "ai_tps_backup", "name": "TPS Backup", "input_pin": 7,
         "subtype": "linear", "unit": "%", "min_voltage": 0.5, "max_voltage": 4.5,
         "min_value": 0, "max_value": 100},
        {"id": "ai_steering_angle", "name": "Steering Angle", "input_pin": 8,
         "subtype": "linear", "unit": "deg", "min_voltage": 0.5, "max_voltage": 4.5,
         "min_value": -540, "max_value": 540},
        {"id": "ai_damper_fl", "name": "Damper FL", "input_pin": 9,
         "subtype": "linear", "unit": "mm", "min_voltage": 0, "max_voltage": 5,
         "min_value": 0, "max_value": 100},
        {"id": "ai_damper_fr", "name": "Damper FR", "input_pin": 10,
         "subtype": "linear", "unit": "mm", "min_voltage": 0, "max_voltage": 5,
         "min_value": 0, "max_value": 100},
        {"id": "ai_damper_rl", "name": "Damper RL", "input_pin": 11,
         "subtype": "linear", "unit": "mm", "min_voltage": 0, "max_voltage": 5,
         "min_value": 0, "max_value": 100},
        {"id": "ai_damper_rr", "name": "Damper RR", "input_pin": 12,
         "subtype": "linear", "unit": "mm", "min_voltage": 0, "max_voltage": 5,
         "min_value": 0, "max_value": 100},
        {"id": "ai_battery_voltage", "name": "Battery Voltage", "input_pin": 13,
         "subtype": "linear", "unit": "V", "min_voltage": 0, "max_voltage": 5,
         "min_value": 0, "max_value": 20},
        {"id": "ai_alternator_voltage", "name": "Alternator Voltage", "input_pin": 14,
         "subtype": "linear", "unit": "V", "min_voltage": 0, "max_voltage": 5,
         "min_value": 0, "max_value": 20},
        {"id": "ai_fuel_level", "name": "Fuel Level", "input_pin": 15,
         "subtype": "calibrated", "unit": "L", "min_value": 0, "max_value": 80},
        {"id": "ai_exhaust_temp_l", "name": "Exhaust Temp Left", "input_pin": 16,
         "subtype": "calibrated", "unit": "C", "min_value": 0, "max_value": 1200},
        {"id": "ai_exhaust_temp_r", "name": "Exhaust Temp Right", "input_pin": 17,
         "subtype": "calibrated", "unit": "C", "min_value": 0, "max_value": 1200},
        {"id": "ai_boost_pressure", "name": "Boost Pressure", "input_pin": 18,
         "subtype": "linear", "unit": "bar", "min_voltage": 0.5, "max_voltage": 4.5,
         "min_value": -1, "max_value": 3},
        {"id": "ai_ambient_temp", "name": "Ambient Temperature", "input_pin": 19,
         "subtype": "calibrated", "unit": "C", "min_value": -40, "max_value": 60}
    ]
    for ai in analog_inputs:
        ai["channel_type"] = "analog_input"
        ai["channel_id"] = channel_id
        channel_id += 1
        channels.append(ai)

    # ==================== DIGITAL INPUTS (20 items) ====================
    digital_inputs = [
        {"id": "di_ignition", "name": "Ignition Switch", "input_pin": 0, "subtype": "switch_active_high"},
        {"id": "di_start_btn", "name": "Start Button", "input_pin": 1, "subtype": "switch_active_low"},
        {"id": "di_horn_btn", "name": "Horn Button", "input_pin": 2, "subtype": "switch_active_low"},
        {"id": "di_wiper_low", "name": "Wiper Low", "input_pin": 3, "subtype": "switch_active_low"},
        {"id": "di_wiper_high", "name": "Wiper High", "input_pin": 4, "subtype": "switch_active_low"},
        {"id": "di_lights_low", "name": "Lights Low Beam", "input_pin": 5, "subtype": "switch_active_low"},
        {"id": "di_lights_high", "name": "Lights High Beam", "input_pin": 6, "subtype": "switch_active_low"},
        {"id": "di_turn_left", "name": "Turn Signal Left", "input_pin": 7, "subtype": "switch_active_low"},
        {"id": "di_turn_right", "name": "Turn Signal Right", "input_pin": 8, "subtype": "switch_active_low"},
        {"id": "di_hazard", "name": "Hazard Switch", "input_pin": 9, "subtype": "switch_active_low"},
        {"id": "di_brake_pedal", "name": "Brake Pedal Switch", "input_pin": 10, "subtype": "switch_active_low"},
        {"id": "di_clutch_pedal", "name": "Clutch Pedal Switch", "input_pin": 11, "subtype": "switch_active_low"},
        {"id": "di_neutral", "name": "Neutral Switch", "input_pin": 12, "subtype": "switch_active_high"},
        {"id": "di_reverse", "name": "Reverse Switch", "input_pin": 13, "subtype": "switch_active_high"},
        {"id": "di_door_left", "name": "Door Left", "input_pin": 14, "subtype": "switch_active_low"},
        {"id": "di_door_right", "name": "Door Right", "input_pin": 15, "subtype": "switch_active_low"},
        {"id": "di_hood", "name": "Hood Switch", "input_pin": 16, "subtype": "switch_active_low"},
        {"id": "di_trunk", "name": "Trunk Switch", "input_pin": 17, "subtype": "switch_active_low"},
        {"id": "di_rain_sensor", "name": "Rain Sensor", "input_pin": 18, "subtype": "switch_active_high"},
        {"id": "di_speed_pulse", "name": "Speed Pulse", "input_pin": 19, "subtype": "frequency",
         "multiplier": 1.0, "divider": 1.0}
    ]
    for di in digital_inputs:
        di["channel_type"] = "digital_input"
        di["channel_id"] = channel_id
        di["debounce_ms"] = 20
        channel_id += 1
        channels.append(di)

    # ==================== CAN INPUTS (30 items) ====================
    can_inputs = [
        {"id": "can_rpm", "name": "Engine RPM", "message_ref": "ecu_engine_1",
         "start_bit": 0, "bit_length": 16, "data_type": "unsigned", "scale": 1.0, "offset": 0, "unit": "rpm"},
        {"id": "can_tps", "name": "TPS (CAN)", "message_ref": "ecu_engine_1",
         "start_bit": 16, "bit_length": 16, "data_type": "unsigned", "scale": 0.1, "offset": 0, "unit": "%"},
        {"id": "can_map", "name": "MAP", "message_ref": "ecu_engine_1",
         "start_bit": 32, "bit_length": 16, "data_type": "unsigned", "scale": 0.1, "offset": 0, "unit": "kPa"},
        {"id": "can_iat", "name": "Intake Air Temp", "message_ref": "ecu_engine_1",
         "start_bit": 48, "bit_length": 16, "data_type": "signed", "scale": 0.1, "offset": -40, "unit": "C"},
        {"id": "can_coolant", "name": "Coolant (CAN)", "message_ref": "ecu_engine_2",
         "start_bit": 0, "bit_length": 16, "data_type": "signed", "scale": 0.1, "offset": -40, "unit": "C"},
        {"id": "can_oil_temp", "name": "Oil Temp (CAN)", "message_ref": "ecu_engine_2",
         "start_bit": 16, "bit_length": 16, "data_type": "signed", "scale": 0.1, "offset": -40, "unit": "C"},
        {"id": "can_fuel_temp", "name": "Fuel Temp", "message_ref": "ecu_engine_2",
         "start_bit": 32, "bit_length": 16, "data_type": "signed", "scale": 0.1, "offset": -40, "unit": "C"},
        {"id": "can_oil_pres", "name": "Oil Pressure (CAN)", "message_ref": "ecu_engine_2",
         "start_bit": 48, "bit_length": 16, "data_type": "unsigned", "scale": 0.01, "offset": 0, "unit": "bar"},
        {"id": "can_lambda", "name": "Lambda", "message_ref": "ecu_engine_3",
         "start_bit": 0, "bit_length": 16, "data_type": "unsigned", "scale": 0.001, "offset": 0, "unit": ""},
        {"id": "can_ign_angle", "name": "Ignition Angle", "message_ref": "ecu_engine_3",
         "start_bit": 16, "bit_length": 16, "data_type": "signed", "scale": 0.1, "offset": 0, "unit": "deg"},
        {"id": "can_boost_target", "name": "Boost Target", "message_ref": "ecu_engine_3",
         "start_bit": 32, "bit_length": 16, "data_type": "unsigned", "scale": 0.01, "offset": -1, "unit": "bar"},
        {"id": "can_fuel_cut", "name": "Fuel Cut Active", "message_ref": "ecu_engine_3",
         "start_bit": 48, "bit_length": 1, "data_type": "unsigned", "scale": 1, "offset": 0, "unit": ""},
        {"id": "can_wheel_fl", "name": "Wheel Speed FL", "message_ref": "abs_wheel_speeds",
         "start_bit": 0, "bit_length": 16, "data_type": "unsigned", "scale": 0.1, "offset": 0, "unit": "km/h"},
        {"id": "can_wheel_fr", "name": "Wheel Speed FR", "message_ref": "abs_wheel_speeds",
         "start_bit": 16, "bit_length": 16, "data_type": "unsigned", "scale": 0.1, "offset": 0, "unit": "km/h"},
        {"id": "can_wheel_rl", "name": "Wheel Speed RL", "message_ref": "abs_wheel_speeds",
         "start_bit": 32, "bit_length": 16, "data_type": "unsigned", "scale": 0.1, "offset": 0, "unit": "km/h"},
        {"id": "can_wheel_rr", "name": "Wheel Speed RR", "message_ref": "abs_wheel_speeds",
         "start_bit": 48, "bit_length": 16, "data_type": "unsigned", "scale": 0.1, "offset": 0, "unit": "km/h"},
        {"id": "can_abs_active", "name": "ABS Active", "message_ref": "abs_status",
         "start_bit": 0, "bit_length": 1, "data_type": "unsigned", "scale": 1, "offset": 0, "unit": ""},
        {"id": "can_tc_active", "name": "TC Active", "message_ref": "abs_status",
         "start_bit": 1, "bit_length": 1, "data_type": "unsigned", "scale": 1, "offset": 0, "unit": ""},
        {"id": "can_gear", "name": "Current Gear", "message_ref": "gearbox_pos",
         "start_bit": 0, "bit_length": 8, "data_type": "signed", "scale": 1, "offset": 0, "unit": ""},
        {"id": "can_fuel_level", "name": "Fuel Level (CAN)", "message_ref": "fuel_level_msg",
         "start_bit": 0, "bit_length": 16, "data_type": "unsigned", "scale": 0.1, "offset": 0, "unit": "L"},
        {"id": "can_fuel_used", "name": "Fuel Used", "message_ref": "fuel_level_msg",
         "start_bit": 16, "bit_length": 16, "data_type": "unsigned", "scale": 0.01, "offset": 0, "unit": "L"},
        {"id": "can_gps_lat", "name": "GPS Latitude", "message_ref": "gps_position",
         "start_bit": 0, "bit_length": 32, "data_type": "signed", "scale": 0.0000001, "offset": 0, "unit": "deg"},
        {"id": "can_gps_lon", "name": "GPS Longitude", "message_ref": "gps_position",
         "start_bit": 32, "bit_length": 32, "data_type": "signed", "scale": 0.0000001, "offset": 0, "unit": "deg"},
        {"id": "can_gps_speed", "name": "GPS Speed", "message_ref": "gps_speed",
         "start_bit": 0, "bit_length": 16, "data_type": "unsigned", "scale": 0.1, "offset": 0, "unit": "km/h"},
        {"id": "can_gps_course", "name": "GPS Course", "message_ref": "gps_speed",
         "start_bit": 16, "bit_length": 16, "data_type": "unsigned", "scale": 0.1, "offset": 0, "unit": "deg"},
        {"id": "can_pit_msg_type", "name": "Pit Message Type", "message_ref": "pit_commands",
         "start_bit": 0, "bit_length": 8, "data_type": "unsigned", "scale": 1, "offset": 0, "unit": ""},
        {"id": "can_pit_lap_delta", "name": "Pit Lap Delta", "message_ref": "pit_commands",
         "start_bit": 8, "bit_length": 16, "data_type": "signed", "scale": 0.001, "offset": 0, "unit": "s"},
        {"id": "can_dash_btn_1", "name": "Dash Button 1", "message_ref": "dash_inputs",
         "start_bit": 0, "bit_length": 1, "data_type": "unsigned", "scale": 1, "offset": 0, "unit": ""},
        {"id": "can_dash_btn_2", "name": "Dash Button 2", "message_ref": "dash_inputs",
         "start_bit": 1, "bit_length": 1, "data_type": "unsigned", "scale": 1, "offset": 0, "unit": ""},
        {"id": "can_dash_rotary", "name": "Dash Rotary", "message_ref": "dash_inputs",
         "start_bit": 8, "bit_length": 8, "data_type": "unsigned", "scale": 1, "offset": 0, "unit": ""}
    ]
    for ci in can_inputs:
        ci["channel_type"] = "can_rx"
        ci["channel_id"] = channel_id
        channel_id += 1
        channels.append(ci)

    # ==================== POWER OUTPUTS (30 items) ====================
    power_outputs = [
        {"id": "out_headlights", "name": "Headlights", "output_pins": [0], "source_channel": "logic_lights_on",
         "current_limit_a": 15, "inrush_current_a": 25, "inrush_time_ms": 100},
        {"id": "out_high_beam", "name": "High Beam", "output_pins": [1], "source_channel": "logic_high_beam",
         "current_limit_a": 10, "inrush_current_a": 20, "inrush_time_ms": 50},
        {"id": "out_fog_lights", "name": "Fog Lights", "output_pins": [2], "source_channel": "logic_fog",
         "current_limit_a": 8},
        {"id": "out_turn_left", "name": "Turn Left", "output_pins": [3], "source_channel": "logic_turn_left",
         "current_limit_a": 5, "pwm_enabled": True, "pwm_frequency_hz": 2},
        {"id": "out_turn_right", "name": "Turn Right", "output_pins": [4], "source_channel": "logic_turn_right",
         "current_limit_a": 5, "pwm_enabled": True, "pwm_frequency_hz": 2},
        {"id": "out_brake_lights", "name": "Brake Lights", "output_pins": [5], "source_channel": "di_brake_pedal",
         "current_limit_a": 10},
        {"id": "out_reverse_lights", "name": "Reverse Lights", "output_pins": [6], "source_channel": "di_reverse",
         "current_limit_a": 5},
        {"id": "out_horn", "name": "Horn", "output_pins": [7], "source_channel": "di_horn_btn",
         "current_limit_a": 10},
        {"id": "out_wiper_low", "name": "Wiper Low", "output_pins": [8], "source_channel": "logic_wiper_low",
         "current_limit_a": 8},
        {"id": "out_wiper_high", "name": "Wiper High", "output_pins": [9], "source_channel": "logic_wiper_high",
         "current_limit_a": 8},
        {"id": "out_washer", "name": "Washer Pump", "output_pins": [10], "source_channel": "timer_washer",
         "current_limit_a": 5},
        {"id": "out_fuel_pump", "name": "Fuel Pump", "output_pins": [11], "source_channel": "logic_fuel_pump",
         "current_limit_a": 15, "soft_start_ms": 500},
        {"id": "out_fan_1", "name": "Cooling Fan 1", "output_pins": [12], "source_channel": "logic_fan_1",
         "current_limit_a": 20, "pwm_enabled": True, "pwm_frequency_hz": 100, "duty_channel": "table_fan_duty"},
        {"id": "out_fan_2", "name": "Cooling Fan 2", "output_pins": [13], "source_channel": "logic_fan_2",
         "current_limit_a": 20, "pwm_enabled": True, "pwm_frequency_hz": 100, "duty_channel": "table_fan_duty"},
        {"id": "out_water_pump", "name": "Water Pump", "output_pins": [14], "source_channel": "logic_water_pump",
         "current_limit_a": 10},
        {"id": "out_oil_pump", "name": "Oil Pump", "output_pins": [15], "source_channel": "logic_oil_pump",
         "current_limit_a": 8},
        {"id": "out_starter", "name": "Starter Motor", "output_pins": [16], "source_channel": "logic_starter",
         "current_limit_a": 150, "inrush_current_a": 300, "inrush_time_ms": 2000},
        {"id": "out_ignition", "name": "Ignition Coils", "output_pins": [17], "source_channel": "logic_ignition_on",
         "current_limit_a": 15},
        {"id": "out_injectors", "name": "Injector Power", "output_pins": [18], "source_channel": "logic_ignition_on",
         "current_limit_a": 10},
        {"id": "out_ecu", "name": "ECU Power", "output_pins": [19], "source_channel": "logic_ignition_on",
         "current_limit_a": 5},
        {"id": "out_radio", "name": "Radio", "output_pins": [20], "source_channel": "logic_acc_on",
         "current_limit_a": 5},
        {"id": "out_usb", "name": "USB Ports", "output_pins": [21], "source_channel": "logic_acc_on",
         "current_limit_a": 3},
        {"id": "out_dash", "name": "Dashboard", "output_pins": [22], "source_channel": "logic_acc_on",
         "current_limit_a": 5},
        {"id": "out_data_logger", "name": "Data Logger", "output_pins": [23], "source_channel": "logic_ignition_on",
         "current_limit_a": 3},
        {"id": "out_telemetry", "name": "Telemetry", "output_pins": [24], "source_channel": "logic_ignition_on",
         "current_limit_a": 2},
        {"id": "out_camera", "name": "Camera", "output_pins": [25], "source_channel": "logic_ignition_on",
         "current_limit_a": 3},
        {"id": "out_boost_solenoid", "name": "Boost Solenoid", "output_pins": [26], "source_channel": "pid_boost",
         "current_limit_a": 3, "pwm_enabled": True, "pwm_frequency_hz": 50, "duty_channel": "pid_boost"},
        {"id": "out_pit_limiter", "name": "Pit Limiter LED", "output_pins": [27], "source_channel": "logic_pit_limiter",
         "current_limit_a": 1},
        {"id": "out_warning_led", "name": "Warning LED", "output_pins": [28], "source_channel": "logic_warning",
         "current_limit_a": 1, "pwm_enabled": True, "pwm_frequency_hz": 5},
        {"id": "out_shift_light", "name": "Shift Light", "output_pins": [29], "source_channel": "logic_shift",
         "current_limit_a": 2}
    ]
    for po in power_outputs:
        po["channel_type"] = "power_output"
        po["channel_id"] = channel_id
        channel_id += 1
        channels.append(po)

    # ==================== LOGIC FUNCTIONS (60 items) ====================
    logic_functions = [
        # Ignition sequence
        {"id": "logic_ignition_on", "name": "Ignition On", "operation": "and",
         "input1": "di_ignition", "input2": "logic_voltage_ok"},
        {"id": "logic_acc_on", "name": "Accessory On", "operation": "or",
         "input1": "logic_ignition_on", "input2": "di_ignition"},
        {"id": "logic_voltage_ok", "name": "Voltage OK", "operation": "and",
         "input1": "logic_undervolt_ok", "input2": "logic_overvolt_ok"},
        {"id": "logic_undervolt_ok", "name": "Undervolt OK", "operation": "greater",
         "input1": "ai_battery_voltage", "constant": 10.5},
        {"id": "logic_overvolt_ok", "name": "Overvolt OK", "operation": "less",
         "input1": "ai_battery_voltage", "constant": 16.0},
        # Starter logic
        {"id": "logic_starter_enable", "name": "Starter Enable", "operation": "and",
         "input1": "di_start_btn", "input2": "logic_ignition_on"},
        {"id": "logic_starter_neutral", "name": "Starter Neutral", "operation": "and",
         "input1": "logic_starter_enable", "input2": "di_neutral"},
        {"id": "logic_starter_clutch", "name": "Starter Clutch", "operation": "and",
         "input1": "logic_starter_enable", "input2": "di_clutch_pedal"},
        {"id": "logic_starter", "name": "Starter", "operation": "or",
         "input1": "logic_starter_neutral", "input2": "logic_starter_clutch"},
        # Fuel pump
        {"id": "logic_fuel_pump", "name": "Fuel Pump Logic", "operation": "and",
         "input1": "logic_ignition_on", "input2": "logic_engine_running"},
        {"id": "logic_engine_running", "name": "Engine Running", "operation": "greater",
         "input1": "can_rpm", "constant": 300},
        # Cooling fans
        {"id": "logic_fan_temp", "name": "Fan Temp Trigger", "operation": "greater",
         "input1": "ai_coolant_temp", "constant": 95},
        {"id": "logic_fan_1", "name": "Fan 1 Logic", "operation": "and",
         "input1": "logic_ignition_on", "input2": "logic_fan_temp"},
        {"id": "logic_fan_2_temp", "name": "Fan 2 Temp", "operation": "greater",
         "input1": "ai_coolant_temp", "constant": 100},
        {"id": "logic_fan_2", "name": "Fan 2 Logic", "operation": "and",
         "input1": "logic_ignition_on", "input2": "logic_fan_2_temp"},
        # Water pump
        {"id": "logic_water_pump", "name": "Water Pump Logic", "operation": "and",
         "input1": "logic_ignition_on", "input2": "logic_water_pump_needed"},
        {"id": "logic_water_pump_needed", "name": "Water Pump Need", "operation": "greater",
         "input1": "ai_coolant_temp", "constant": 50},
        # Oil pump
        {"id": "logic_oil_pump", "name": "Oil Pump Logic", "operation": "and",
         "input1": "logic_ignition_on", "input2": "logic_engine_running"},
        # Lights
        {"id": "logic_lights_on", "name": "Lights On", "operation": "or",
         "input1": "di_lights_low", "input2": "di_lights_high"},
        {"id": "logic_high_beam", "name": "High Beam Logic", "operation": "and",
         "input1": "di_lights_high", "input2": "logic_lights_on"},
        {"id": "logic_fog", "name": "Fog Lights Logic", "operation": "and",
         "input1": "di_lights_low", "input2": "logic_fog_enable"},
        {"id": "logic_fog_enable", "name": "Fog Enable", "operation": "or",
         "input1": "di_rain_sensor", "constant": 0},
        # Turn signals with hazard
        {"id": "logic_turn_left_req", "name": "Turn Left Request", "operation": "or",
         "input1": "di_turn_left", "input2": "di_hazard"},
        {"id": "logic_turn_right_req", "name": "Turn Right Request", "operation": "or",
         "input1": "di_turn_right", "input2": "di_hazard"},
        {"id": "logic_turn_left", "name": "Turn Left", "operation": "and",
         "input1": "logic_turn_left_req", "input2": "timer_turn_blink"},
        {"id": "logic_turn_right", "name": "Turn Right", "operation": "and",
         "input1": "logic_turn_right_req", "input2": "timer_turn_blink"},
        # Wipers
        {"id": "logic_wiper_low", "name": "Wiper Low", "operation": "and",
         "input1": "di_wiper_low", "input2": "logic_not_wiper_high"},
        {"id": "logic_not_wiper_high", "name": "Not Wiper High", "operation": "not",
         "input1": "di_wiper_high"},
        {"id": "logic_wiper_high", "name": "Wiper High", "operation": "or",
         "input1": "di_wiper_high", "input2": "logic_auto_wiper_high"},
        {"id": "logic_auto_wiper_high", "name": "Auto Wiper High", "operation": "and",
         "input1": "di_rain_sensor", "input2": "di_wiper_low"},
        # Warnings
        {"id": "logic_oil_warn", "name": "Oil Pressure Warning", "operation": "and",
         "input1": "logic_oil_low", "input2": "logic_engine_running"},
        {"id": "logic_oil_low", "name": "Oil Low", "operation": "less",
         "input1": "ai_oil_pressure", "constant": 1.5},
        {"id": "logic_temp_warn", "name": "Temp Warning", "operation": "greater",
         "input1": "ai_coolant_temp", "constant": 105},
        {"id": "logic_fuel_warn", "name": "Fuel Warning", "operation": "less",
         "input1": "ai_fuel_level", "constant": 10},
        {"id": "logic_warning", "name": "Any Warning", "operation": "or",
         "input1": "logic_oil_warn", "input2": "logic_temp_warn"},
        # Shift light
        {"id": "logic_shift_rpm", "name": "Shift RPM", "operation": "greater",
         "input1": "can_rpm", "constant": 6500},
        {"id": "logic_shift", "name": "Shift Light", "operation": "and",
         "input1": "logic_shift_rpm", "input2": "logic_engine_running"},
        # Pit limiter
        {"id": "logic_pit_limiter", "name": "Pit Limiter", "operation": "and",
         "input1": "can_dash_btn_1", "input2": "logic_pit_speed"},
        {"id": "logic_pit_speed", "name": "Pit Speed", "operation": "less",
         "input1": "can_gps_speed", "constant": 80},
        # TPS plausibility
        {"id": "logic_tps_diff", "name": "TPS Difference", "operation": "subtract",
         "input1": "ai_tps_main", "input2": "ai_tps_backup"},
        {"id": "logic_tps_valid", "name": "TPS Valid", "operation": "less",
         "input1": "filter_tps_diff", "constant": 10},
        # Speed calculation
        {"id": "logic_speed_avg_fr", "name": "Speed Avg Front", "operation": "add",
         "input1": "can_wheel_fl", "input2": "can_wheel_fr"},
        {"id": "logic_speed_avg", "name": "Speed Average", "operation": "divide",
         "input1": "logic_speed_avg_fr", "constant": 2},
        # Brake bias
        {"id": "logic_brake_total", "name": "Brake Total", "operation": "add",
         "input1": "ai_brake_pressure_f", "input2": "ai_brake_pressure_r"},
        {"id": "logic_brake_bias", "name": "Brake Bias", "operation": "divide",
         "input1": "ai_brake_pressure_f", "input2": "logic_brake_total"},
        # Fuel consumption
        {"id": "logic_fuel_remaining", "name": "Fuel Remaining", "operation": "subtract",
         "input1": "ai_fuel_level", "input2": "can_fuel_used"},
        {"id": "logic_laps_remaining", "name": "Laps Remaining", "operation": "divide",
         "input1": "logic_fuel_remaining", "input2": "number_fuel_per_lap"},
        # Wheel slip
        {"id": "logic_slip_fl", "name": "Slip FL", "operation": "subtract",
         "input1": "can_wheel_fl", "input2": "logic_speed_avg"},
        {"id": "logic_slip_fr", "name": "Slip FR", "operation": "subtract",
         "input1": "can_wheel_fr", "input2": "logic_speed_avg"},
        {"id": "logic_slip_rl", "name": "Slip RL", "operation": "subtract",
         "input1": "can_wheel_rl", "input2": "logic_speed_avg"},
        {"id": "logic_slip_rr", "name": "Slip RR", "operation": "subtract",
         "input1": "can_wheel_rr", "input2": "logic_speed_avg"},
        # Door logic
        {"id": "logic_any_door", "name": "Any Door Open", "operation": "or",
         "input1": "di_door_left", "input2": "di_door_right"},
        {"id": "logic_door_warn", "name": "Door Warning", "operation": "and",
         "input1": "logic_any_door", "input2": "logic_engine_running"},
        # Hood/trunk
        {"id": "logic_hood_warn", "name": "Hood Warning", "operation": "and",
         "input1": "di_hood", "input2": "logic_engine_running"},
        {"id": "logic_trunk_warn", "name": "Trunk Warning", "operation": "and",
         "input1": "di_trunk", "input2": "logic_speed_moving"},
        {"id": "logic_speed_moving", "name": "Speed Moving", "operation": "greater",
         "input1": "can_gps_speed", "constant": 5},
        # ABS/TC indication
        {"id": "logic_abs_tc_active", "name": "ABS/TC Active", "operation": "or",
         "input1": "can_abs_active", "input2": "can_tc_active"},
        # Gear validation
        {"id": "logic_gear_valid", "name": "Gear Valid", "operation": "and",
         "input1": "logic_gear_min", "input2": "logic_gear_max"},
        {"id": "logic_gear_min", "name": "Gear Min", "operation": "greater_equal",
         "input1": "can_gear", "constant": -1},
        {"id": "logic_gear_max", "name": "Gear Max", "operation": "less_equal",
         "input1": "can_gear", "constant": 6}
    ]
    for lf in logic_functions:
        lf["channel_type"] = "logic"
        lf["channel_id"] = channel_id
        lf["delay_on_ms"] = 0
        lf["delay_off_ms"] = 0
        channel_id += 1
        channels.append(lf)

    # ==================== NUMBER CHANNELS (20 items) ====================
    number_channels = [
        {"id": "number_fuel_per_lap", "name": "Fuel Per Lap", "operation": "constant", "constant": 2.5},
        {"id": "number_tire_circumference", "name": "Tire Circumference", "operation": "constant", "constant": 2.0},
        {"id": "number_final_drive", "name": "Final Drive Ratio", "operation": "constant", "constant": 4.1},
        {"id": "number_shift_rpm_target", "name": "Shift RPM Target", "operation": "constant", "constant": 7000},
        {"id": "number_pit_speed_limit", "name": "Pit Speed Limit", "operation": "constant", "constant": 60},
        {"id": "number_fan_on_temp", "name": "Fan On Temp", "operation": "constant", "constant": 95},
        {"id": "number_fan_off_temp", "name": "Fan Off Temp", "operation": "constant", "constant": 85},
        {"id": "number_oil_min_pres", "name": "Oil Min Pressure", "operation": "constant", "constant": 1.5},
        {"id": "number_max_coolant", "name": "Max Coolant Temp", "operation": "constant", "constant": 110},
        {"id": "number_speed_mph", "name": "Speed MPH", "operation": "multiply",
         "input1": "can_gps_speed", "constant": 0.621371},
        {"id": "number_rpm_percent", "name": "RPM Percent", "operation": "divide",
         "input1": "can_rpm", "constant": 8000},
        {"id": "number_boost_psi", "name": "Boost PSI", "operation": "multiply",
         "input1": "ai_boost_pressure", "constant": 14.5038},
        {"id": "number_oil_pres_psi", "name": "Oil Pressure PSI", "operation": "multiply",
         "input1": "ai_oil_pressure", "constant": 14.5038},
        {"id": "number_fuel_pres_psi", "name": "Fuel Pressure PSI", "operation": "multiply",
         "input1": "ai_fuel_pressure", "constant": 14.5038},
        {"id": "number_coolant_f", "name": "Coolant F", "operation": "add",
         "input1": "number_coolant_f_conv", "constant": 32},
        {"id": "number_coolant_f_conv", "name": "Coolant F Conv", "operation": "multiply",
         "input1": "ai_coolant_temp", "constant": 1.8},
        {"id": "number_steering_ratio", "name": "Steering Ratio", "operation": "divide",
         "input1": "ai_steering_angle", "constant": 15},
        {"id": "number_brake_balance", "name": "Brake Balance %", "operation": "multiply",
         "input1": "logic_brake_bias", "constant": 100},
        {"id": "number_gear_indicator", "name": "Gear Indicator", "operation": "add",
         "input1": "can_gear", "constant": 0},
        {"id": "number_lap_time_ms", "name": "Lap Time MS", "operation": "multiply",
         "input1": "can_pit_lap_delta", "constant": 1000}
    ]
    for nc in number_channels:
        nc["channel_type"] = "number"
        nc["channel_id"] = channel_id
        nc["decimal_places"] = 2
        channel_id += 1
        channels.append(nc)

    # ==================== TIMERS (15 items) ====================
    timers = [
        {"id": "timer_turn_blink", "name": "Turn Signal Blink", "mode": "oscillator",
         "time_on_ms": 500, "time_off_ms": 500, "trigger_channel": "logic_turn_left_req"},
        {"id": "timer_washer", "name": "Washer Pump Timer", "mode": "oneshot",
         "duration_ms": 2000, "trigger_channel": "di_wiper_low"},
        {"id": "timer_start_cutoff", "name": "Start Cutoff", "mode": "oneshot",
         "duration_ms": 3000, "trigger_channel": "logic_starter"},
        {"id": "timer_fuel_prime", "name": "Fuel Prime", "mode": "oneshot",
         "duration_ms": 5000, "trigger_channel": "di_ignition"},
        {"id": "timer_cooling_delay", "name": "Cooling Delay", "mode": "delay_on",
         "delay_ms": 30000, "trigger_channel": "logic_ignition_on"},
        {"id": "timer_door_chime", "name": "Door Chime", "mode": "oscillator",
         "time_on_ms": 200, "time_off_ms": 800, "trigger_channel": "logic_door_warn"},
        {"id": "timer_warning_flash", "name": "Warning Flash", "mode": "oscillator",
         "time_on_ms": 300, "time_off_ms": 300, "trigger_channel": "logic_warning"},
        {"id": "timer_shift_hold", "name": "Shift Light Hold", "mode": "oneshot",
         "duration_ms": 100, "trigger_channel": "logic_shift"},
        {"id": "timer_pit_active", "name": "Pit Limiter Active", "mode": "oneshot",
         "duration_ms": 60000, "trigger_channel": "logic_pit_limiter"},
        {"id": "timer_abs_flash", "name": "ABS Flash", "mode": "oscillator",
         "time_on_ms": 100, "time_off_ms": 100, "trigger_channel": "logic_abs_tc_active"},
        {"id": "timer_horn_limit", "name": "Horn Time Limit", "mode": "oneshot",
         "duration_ms": 5000, "trigger_channel": "di_horn_btn"},
        {"id": "timer_wiper_park", "name": "Wiper Park Delay", "mode": "delay_off",
         "delay_ms": 500, "trigger_channel": "logic_wiper_low"},
        {"id": "timer_light_delay", "name": "Light Off Delay", "mode": "delay_off",
         "delay_ms": 30000, "trigger_channel": "logic_lights_on"},
        {"id": "timer_startup_seq", "name": "Startup Sequence", "mode": "oneshot",
         "duration_ms": 2000, "trigger_channel": "di_ignition"},
        {"id": "timer_cooldown", "name": "Cooldown Timer", "mode": "delay_off",
         "delay_ms": 120000, "trigger_channel": "logic_ignition_on"}
    ]
    for t in timers:
        t["channel_type"] = "timer"
        t["channel_id"] = channel_id
        channel_id += 1
        channels.append(t)

    # ==================== FILTERS (10 items) ====================
    filters = [
        {"id": "filter_tps_diff", "name": "TPS Diff Filter", "filter_type": "moving_average",
         "input_channel": "logic_tps_diff", "window_size": 10},
        {"id": "filter_oil_pres", "name": "Oil Pressure Filter", "filter_type": "lowpass",
         "input_channel": "ai_oil_pressure", "cutoff_hz": 2.0},
        {"id": "filter_coolant", "name": "Coolant Filter", "filter_type": "lowpass",
         "input_channel": "ai_coolant_temp", "cutoff_hz": 0.5},
        {"id": "filter_speed", "name": "Speed Filter", "filter_type": "moving_average",
         "input_channel": "can_gps_speed", "window_size": 5},
        {"id": "filter_boost", "name": "Boost Filter", "filter_type": "lowpass",
         "input_channel": "ai_boost_pressure", "cutoff_hz": 5.0},
        {"id": "filter_rpm", "name": "RPM Filter", "filter_type": "moving_average",
         "input_channel": "can_rpm", "window_size": 3},
        {"id": "filter_steering", "name": "Steering Filter", "filter_type": "lowpass",
         "input_channel": "ai_steering_angle", "cutoff_hz": 10.0},
        {"id": "filter_damper_fl", "name": "Damper FL Filter", "filter_type": "lowpass",
         "input_channel": "ai_damper_fl", "cutoff_hz": 20.0},
        {"id": "filter_lambda", "name": "Lambda Filter", "filter_type": "moving_average",
         "input_channel": "can_lambda", "window_size": 10},
        {"id": "filter_battery", "name": "Battery Filter", "filter_type": "lowpass",
         "input_channel": "ai_battery_voltage", "cutoff_hz": 1.0}
    ]
    for f in filters:
        f["channel_type"] = "filter"
        f["channel_id"] = channel_id
        channel_id += 1
        channels.append(f)

    # ==================== TABLES (10 items) ====================
    tables_2d = [
        {"id": "table_fan_duty", "name": "Fan Duty vs Temp",
         "input_channel": "ai_coolant_temp",
         "x_values": [80, 85, 90, 95, 100, 105, 110],
         "y_values": [0, 30, 50, 70, 85, 95, 100]},
        {"id": "table_boost_target", "name": "Boost vs RPM",
         "input_channel": "can_rpm",
         "x_values": [2000, 3000, 4000, 5000, 6000, 7000],
         "y_values": [0.5, 1.0, 1.5, 2.0, 2.0, 1.8]},
        {"id": "table_tps_deadband", "name": "TPS Deadband",
         "input_channel": "ai_tps_main",
         "x_values": [0, 2, 5, 95, 98, 100],
         "y_values": [0, 0, 5, 95, 100, 100]},
        {"id": "table_wiper_speed", "name": "Wiper Speed vs Rain",
         "input_channel": "ai_rain_sensor",
         "x_values": [0, 1, 2, 3, 4, 5],
         "y_values": [0, 30, 50, 70, 90, 100]},
        {"id": "table_light_dim", "name": "Light Dimming",
         "input_channel": "ai_ambient_temp",
         "x_values": [0, 50, 100, 200, 500, 1000],
         "y_values": [100, 90, 70, 50, 30, 20]}
    ]
    for t in tables_2d:
        t["channel_type"] = "table_2d"
        t["channel_id"] = channel_id
        channel_id += 1
        channels.append(t)

    # ==================== SWITCHES (10 items) ====================
    switches = [
        {"id": "switch_gear_display", "name": "Gear Display",
         "input_channel": "can_gear",
         "cases": [
             {"value": -1, "output": -1},  # Reverse
             {"value": 0, "output": 0},    # Neutral
             {"value": 1, "output": 1},
             {"value": 2, "output": 2},
             {"value": 3, "output": 3},
             {"value": 4, "output": 4},
             {"value": 5, "output": 5},
             {"value": 6, "output": 6}
         ], "default_output": 0},
        {"id": "switch_drive_mode", "name": "Drive Mode",
         "input_channel": "can_dash_rotary",
         "cases": [
             {"value": 0, "output": 0},  # Comfort
             {"value": 1, "output": 1},  # Sport
             {"value": 2, "output": 2},  # Track
             {"value": 3, "output": 3}   # Rain
         ], "default_output": 0},
        {"id": "switch_tc_level", "name": "TC Level",
         "input_channel": "can_dash_rotary",
         "cases": [
             {"value": 0, "output": 0},
             {"value": 1, "output": 25},
             {"value": 2, "output": 50},
             {"value": 3, "output": 75},
             {"value": 4, "output": 100}
         ], "default_output": 50},
        {"id": "switch_abs_level", "name": "ABS Level",
         "input_channel": "can_dash_rotary",
         "cases": [
             {"value": 0, "output": 0},
             {"value": 1, "output": 33},
             {"value": 2, "output": 66},
             {"value": 3, "output": 100}
         ], "default_output": 66}
    ]
    for s in switches:
        s["channel_type"] = "switch"
        s["channel_id"] = channel_id
        channel_id += 1
        channels.append(s)

    # ==================== PID CONTROLLERS (5 items) ====================
    pids = [
        {"id": "pid_boost", "name": "Boost Controller",
         "input_channel": "ai_boost_pressure", "setpoint_channel": "table_boost_target",
         "kp": 50.0, "ki": 10.0, "kd": 5.0,
         "output_min": 0, "output_max": 100,
         "anti_windup": True, "reversed": False},
        {"id": "pid_idle", "name": "Idle Controller",
         "input_channel": "can_rpm", "setpoint_channel": "number_idle_target",
         "kp": 0.5, "ki": 0.1, "kd": 0.05,
         "output_min": 0, "output_max": 50,
         "anti_windup": True, "reversed": False},
        {"id": "pid_coolant_fan", "name": "Coolant Fan PID",
         "input_channel": "ai_coolant_temp", "setpoint_channel": "number_fan_on_temp",
         "kp": 10.0, "ki": 2.0, "kd": 1.0,
         "output_min": 0, "output_max": 100,
         "anti_windup": True, "reversed": False},
        {"id": "pid_oil_temp", "name": "Oil Cooler PID",
         "input_channel": "ai_oil_temp", "setpoint_channel": "number_oil_target_temp",
         "kp": 8.0, "ki": 1.5, "kd": 0.5,
         "output_min": 0, "output_max": 100,
         "anti_windup": True, "reversed": False},
        {"id": "pid_tc", "name": "Traction Control PID",
         "input_channel": "logic_slip_rr", "setpoint_channel": "switch_tc_level",
         "kp": 100.0, "ki": 50.0, "kd": 10.0,
         "output_min": 0, "output_max": 100,
         "anti_windup": True, "reversed": True}
    ]
    for p in pids:
        p["channel_type"] = "pid"
        p["channel_id"] = channel_id
        channel_id += 1
        channels.append(p)

    # ==================== H-BRIDGES (4 items) ====================
    hbridges = [
        {"id": "hbridge_throttle", "name": "Throttle Actuator",
         "bridge_number": 0, "mode": "coast",
         "pwm_frequency_hz": 20000,
         "direction_source_channel": "logic_throttle_dir",
         "duty_source_channel": "pid_idle",
         "current_limit_a": 10, "stall_detection_enabled": True},
        {"id": "hbridge_wastegate", "name": "Wastegate Actuator",
         "bridge_number": 1, "mode": "brake",
         "pwm_frequency_hz": 1000,
         "direction_source_channel": "logic_wastegate_dir",
         "duty_source_channel": "pid_boost",
         "current_limit_a": 5, "stall_detection_enabled": True},
        {"id": "hbridge_mirror_l", "name": "Mirror Left",
         "bridge_number": 2, "mode": "coast",
         "pwm_frequency_hz": 100,
         "current_limit_a": 3, "stall_detection_enabled": False},
        {"id": "hbridge_mirror_r", "name": "Mirror Right",
         "bridge_number": 3, "mode": "coast",
         "pwm_frequency_hz": 100,
         "current_limit_a": 3, "stall_detection_enabled": False}
    ]
    for h in hbridges:
        h["channel_type"] = "hbridge"
        h["channel_id"] = channel_id
        channel_id += 1
        channels.append(h)

    # Add extra number channels referenced by PIDs
    extra_numbers = [
        {"id": "number_idle_target", "name": "Idle Target", "operation": "constant",
         "constant": 850, "channel_type": "number", "channel_id": channel_id, "decimal_places": 0},
        {"id": "number_oil_target_temp", "name": "Oil Target Temp", "operation": "constant",
         "constant": 90, "channel_type": "number", "channel_id": channel_id + 1, "decimal_places": 0},
        {"id": "ai_rain_sensor", "name": "Rain Sensor Analog", "channel_type": "analog_input",
         "input_pin": 19, "subtype": "linear", "channel_id": channel_id + 2,
         "min_voltage": 0, "max_voltage": 5, "min_value": 0, "max_value": 5}
    ]
    for en in extra_numbers:
        channel_id += 1
        channels.append(en)

    # Add logic channels referenced by H-bridges
    hbridge_logic = [
        {"id": "logic_throttle_dir", "name": "Throttle Direction", "operation": "greater",
         "input1": "pid_idle", "constant": 50, "channel_type": "logic", "channel_id": channel_id + 1},
        {"id": "logic_wastegate_dir", "name": "Wastegate Direction", "operation": "greater",
         "input1": "pid_boost", "constant": 50, "channel_type": "logic", "channel_id": channel_id + 2}
    ]
    for hl in hbridge_logic:
        channels.append(hl)
    channel_id += 3

    # ==================== CAN TX OUTPUTS (20 items) ====================
    can_outputs = [
        {"id": "can_tx_rpm", "name": "TX RPM", "message_ref": "pdm_status_1",
         "start_bit": 0, "bit_length": 16, "source_channel": "can_rpm"},
        {"id": "can_tx_coolant", "name": "TX Coolant", "message_ref": "pdm_status_1",
         "start_bit": 16, "bit_length": 16, "source_channel": "filter_coolant"},
        {"id": "can_tx_oil_temp", "name": "TX Oil Temp", "message_ref": "pdm_status_1",
         "start_bit": 32, "bit_length": 16, "source_channel": "ai_oil_temp"},
        {"id": "can_tx_oil_pres", "name": "TX Oil Pressure", "message_ref": "pdm_status_1",
         "start_bit": 48, "bit_length": 16, "source_channel": "filter_oil_pres"},
        {"id": "can_tx_tps", "name": "TX TPS", "message_ref": "pdm_status_2",
         "start_bit": 0, "bit_length": 16, "source_channel": "ai_tps_main"},
        {"id": "can_tx_boost", "name": "TX Boost", "message_ref": "pdm_status_2",
         "start_bit": 16, "bit_length": 16, "source_channel": "filter_boost"},
        {"id": "can_tx_gear", "name": "TX Gear", "message_ref": "pdm_status_2",
         "start_bit": 32, "bit_length": 8, "source_channel": "can_gear"},
        {"id": "can_tx_fuel", "name": "TX Fuel Level", "message_ref": "pdm_status_2",
         "start_bit": 40, "bit_length": 16, "source_channel": "ai_fuel_level"},
        {"id": "can_tx_speed", "name": "TX Speed", "message_ref": "pdm_status_3",
         "start_bit": 0, "bit_length": 16, "source_channel": "filter_speed"},
        {"id": "can_tx_battery", "name": "TX Battery", "message_ref": "pdm_status_3",
         "start_bit": 16, "bit_length": 16, "source_channel": "filter_battery"},
        {"id": "can_tx_current_1", "name": "TX Current 1", "message_ref": "pdm_status_3",
         "start_bit": 32, "bit_length": 8, "source_channel": "out_headlights"},
        {"id": "can_tx_current_2", "name": "TX Current 2", "message_ref": "pdm_status_3",
         "start_bit": 40, "bit_length": 8, "source_channel": "out_fan_1"},
        {"id": "can_tx_steering", "name": "TX Steering", "message_ref": "logger_sync",
         "start_bit": 0, "bit_length": 16, "source_channel": "filter_steering"},
        {"id": "can_tx_damper_fl", "name": "TX Damper FL", "message_ref": "logger_sync",
         "start_bit": 16, "bit_length": 16, "source_channel": "filter_damper_fl"},
        {"id": "can_tx_brake_f", "name": "TX Brake F", "message_ref": "logger_sync",
         "start_bit": 32, "bit_length": 16, "source_channel": "ai_brake_pressure_f"},
        {"id": "can_tx_brake_r", "name": "TX Brake R", "message_ref": "logger_sync",
         "start_bit": 48, "bit_length": 16, "source_channel": "ai_brake_pressure_r"},
        {"id": "can_tx_lambda", "name": "TX Lambda", "message_ref": "telemetry_cmd",
         "start_bit": 0, "bit_length": 16, "source_channel": "filter_lambda"},
        {"id": "can_tx_exhaust_l", "name": "TX Exhaust L", "message_ref": "telemetry_cmd",
         "start_bit": 16, "bit_length": 16, "source_channel": "ai_exhaust_temp_l"},
        {"id": "can_tx_exhaust_r", "name": "TX Exhaust R", "message_ref": "telemetry_cmd",
         "start_bit": 32, "bit_length": 16, "source_channel": "ai_exhaust_temp_r"},
        {"id": "can_tx_warnings", "name": "TX Warnings", "message_ref": "telemetry_cmd",
         "start_bit": 48, "bit_length": 8, "source_channel": "logic_warning"}
    ]
    for co in can_outputs:
        co["channel_type"] = "can_tx"
        co["channel_id"] = channel_id
        co["multiplier"] = 1.0
        co["offset"] = 0.0
        channel_id += 1
        channels.append(co)

    # ==================== EXTRA SWITCHES (10 items) ====================
    extra_switches = [
        {"id": "switch_fan_speed", "name": "Fan Speed Mode",
         "input_channel": "filter_coolant",
         "cases": [
             {"value": 80, "output": 0},
             {"value": 90, "output": 50},
             {"value": 100, "output": 100}
         ], "default_output": 0},
        {"id": "switch_wiper_mode", "name": "Wiper Mode Select",
         "input_channel": "ai_rain_sensor",
         "cases": [
             {"value": 0, "output": 0},
             {"value": 1, "output": 30},
             {"value": 2, "output": 60},
             {"value": 3, "output": 100}
         ], "default_output": 0},
        {"id": "switch_launch_control", "name": "Launch Control",
         "input_channel": "can_rpm",
         "cases": [
             {"value": 3000, "output": 0},
             {"value": 4000, "output": 50},
             {"value": 5000, "output": 100}
         ], "default_output": 0},
        {"id": "switch_brake_light_mode", "name": "Brake Light Mode",
         "input_channel": "ai_brake_pressure_f",
         "cases": [
             {"value": 5, "output": 0},
             {"value": 20, "output": 50},
             {"value": 50, "output": 100}
         ], "default_output": 0},
        {"id": "switch_fuel_map", "name": "Fuel Map Select",
         "input_channel": "can_dash_rotary",
         "cases": [
             {"value": 0, "output": 0},
             {"value": 1, "output": 1},
             {"value": 2, "output": 2}
         ], "default_output": 0},
        {"id": "switch_ignition_map", "name": "Ignition Map Select",
         "input_channel": "can_dash_rotary",
         "cases": [
             {"value": 0, "output": 0},
             {"value": 1, "output": 1},
             {"value": 2, "output": 2}
         ], "default_output": 0},
        {"id": "switch_boost_map", "name": "Boost Map Select",
         "input_channel": "can_dash_rotary",
         "cases": [
             {"value": 0, "output": 0},
             {"value": 1, "output": 1},
             {"value": 2, "output": 2}
         ], "default_output": 0},
        {"id": "switch_speed_unit", "name": "Speed Unit",
         "input_channel": "can_dash_btn_2",
         "cases": [
             {"value": 0, "output": 0},
             {"value": 1, "output": 1}
         ], "default_output": 0},
        {"id": "switch_temp_unit", "name": "Temperature Unit",
         "input_channel": "can_dash_btn_2",
         "cases": [
             {"value": 0, "output": 0},
             {"value": 1, "output": 1}
         ], "default_output": 0},
        {"id": "switch_pressure_unit", "name": "Pressure Unit",
         "input_channel": "can_dash_btn_2",
         "cases": [
             {"value": 0, "output": 0},
             {"value": 1, "output": 1}
         ], "default_output": 0}
    ]
    for es in extra_switches:
        es["channel_type"] = "switch"
        es["channel_id"] = channel_id
        channel_id += 1
        channels.append(es)

    # ==================== TABLES 3D (5 items) ====================
    tables_3d = [
        {"id": "table3d_boost_map", "name": "Boost Map 3D",
         "input_x_channel": "can_rpm", "input_y_channel": "can_tps",
         "x_values": [2000, 4000, 6000, 8000],
         "y_values": [0, 50, 100],
         "z_values": [[0, 0.5, 1.0, 1.0], [0.5, 1.0, 1.5, 1.5], [1.0, 1.5, 2.0, 1.8]]},
        {"id": "table3d_fuel_trim", "name": "Fuel Trim 3D",
         "input_x_channel": "can_rpm", "input_y_channel": "can_tps",
         "x_values": [1000, 3000, 5000, 7000],
         "y_values": [0, 25, 50, 75, 100],
         "z_values": [[0, 0, 0, 0], [5, 5, 0, -5], [10, 5, 0, -5], [10, 5, 0, -10], [5, 0, -5, -10]]},
        {"id": "table3d_ign_timing", "name": "Ignition Timing 3D",
         "input_x_channel": "can_rpm", "input_y_channel": "can_map",
         "x_values": [1000, 2000, 4000, 6000, 8000],
         "y_values": [20, 50, 80, 100],
         "z_values": [[10, 15, 25, 30, 28], [8, 12, 22, 28, 25], [5, 10, 18, 22, 20], [2, 8, 15, 18, 15]]},
        {"id": "table3d_idle_target", "name": "Idle Target 3D",
         "input_x_channel": "ai_coolant_temp", "input_y_channel": "ai_battery_voltage",
         "x_values": [-20, 0, 40, 80],
         "y_values": [10, 12, 14],
         "z_values": [[1500, 1200, 900, 850], [1400, 1100, 850, 800], [1300, 1000, 800, 750]]},
        {"id": "table3d_fan_duty", "name": "Fan Duty 3D",
         "input_x_channel": "ai_coolant_temp", "input_y_channel": "can_gps_speed",
         "x_values": [80, 90, 100, 110],
         "y_values": [0, 50, 100],
         "z_values": [[0, 30, 70, 100], [0, 20, 60, 90], [0, 10, 50, 80]]}
    ]
    for t3 in tables_3d:
        t3["channel_type"] = "table_3d"
        t3["channel_id"] = channel_id
        channel_id += 1
        channels.append(t3)

    # ==================== EXTRA LOGIC (10 items) ====================
    extra_logic = [
        {"id": "logic_launch_ready", "name": "Launch Ready", "operation": "and",
         "input1": "di_clutch_pedal", "input2": "di_brake_pedal"},
        {"id": "logic_launch_armed", "name": "Launch Armed", "operation": "and",
         "input1": "logic_launch_ready", "input2": "can_dash_btn_1"},
        {"id": "logic_overrev", "name": "Over Rev", "operation": "greater",
         "input1": "can_rpm", "constant": 7500},
        {"id": "logic_overboost", "name": "Over Boost", "operation": "greater",
         "input1": "ai_boost_pressure", "constant": 2.5},
        {"id": "logic_low_fuel", "name": "Low Fuel", "operation": "less",
         "input1": "ai_fuel_level", "constant": 5},
        {"id": "logic_high_egt", "name": "High EGT", "operation": "greater",
         "input1": "ai_exhaust_temp_l", "constant": 950},
        {"id": "logic_engine_warm", "name": "Engine Warm", "operation": "greater",
         "input1": "ai_coolant_temp", "constant": 70},
        {"id": "logic_oil_warm", "name": "Oil Warm", "operation": "greater",
         "input1": "ai_oil_temp", "constant": 60},
        {"id": "logic_ready_to_race", "name": "Ready to Race", "operation": "and",
         "input1": "logic_engine_warm", "input2": "logic_oil_warm"},
        {"id": "logic_pit_entry", "name": "Pit Entry", "operation": "and",
         "input1": "can_dash_btn_1", "input2": "logic_pit_speed"}
    ]
    for el in extra_logic:
        el["channel_type"] = "logic"
        el["channel_id"] = channel_id
        el["delay_on_ms"] = 0
        el["delay_off_ms"] = 0
        channel_id += 1
        channels.append(el)

    # ==================== EXTRA NUMBERS (10 items) ====================
    extra_numbers2 = [
        {"id": "number_fuel_laps", "name": "Fuel Laps Remaining", "operation": "divide",
         "input1": "ai_fuel_level", "input2": "number_fuel_per_lap"},
        {"id": "number_avg_speed", "name": "Average Speed", "operation": "add",
         "input1": "filter_speed", "constant": 0},
        {"id": "number_max_rpm", "name": "Max RPM Session", "operation": "max",
         "input1": "can_rpm", "constant": 0},
        {"id": "number_min_oil", "name": "Min Oil Pressure", "operation": "min",
         "input1": "filter_oil_pres", "constant": 100},
        {"id": "number_max_coolant_session", "name": "Max Coolant Session", "operation": "max",
         "input1": "filter_coolant", "constant": 0},
        {"id": "number_max_egt", "name": "Max EGT", "operation": "max",
         "input1": "ai_exhaust_temp_l", "constant": 0},
        {"id": "number_total_current", "name": "Total Current Draw", "operation": "add",
         "input1": "out_headlights", "input2": "out_fan_1"},
        {"id": "number_battery_pct", "name": "Battery Percentage", "operation": "multiply",
         "input1": "filter_battery", "constant": 7.14},
        {"id": "number_slip_total", "name": "Total Slip", "operation": "add",
         "input1": "logic_slip_rl", "input2": "logic_slip_rr"},
        {"id": "number_brake_effort", "name": "Brake Effort", "operation": "multiply",
         "input1": "logic_brake_total", "constant": 0.5}
    ]
    for en2 in extra_numbers2:
        en2["channel_type"] = "number"
        en2["channel_id"] = channel_id
        en2["decimal_places"] = 2
        channel_id += 1
        channels.append(en2)

    config["channels"] = channels

    return config


def normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize config for comparison.
    Handles differences in:
    - Field ordering
    - Default values that may be omitted
    - Floating point precision
    """
    # Deep copy to avoid modifying original
    normalized = copy.deepcopy(config)

    # Sort channels by channel_id for consistent comparison
    if "channels" in normalized:
        normalized["channels"] = sorted(
            normalized["channels"],
            key=lambda c: (c.get("channel_type", ""), c.get("id", ""))
        )

    # Sort can_messages by id
    if "can_messages" in normalized:
        normalized["can_messages"] = sorted(
            normalized["can_messages"],
            key=lambda m: m.get("id", "")
        )

    return normalized


def compare_configs(original: Dict[str, Any], loaded: Dict[str, Any]) -> List[str]:
    """
    Deep compare two configs and return list of differences.
    """
    differences = []

    # Fields that are expected to change on load (auto-updated by ConfigManager)
    ignored_paths = {
        "device.modified",  # Updated to current timestamp on load
        "device.created",   # May be regenerated
    }

    def compare_dict(path: str, d1: dict, d2: dict):
        all_keys = set(d1.keys()) | set(d2.keys())
        for key in sorted(all_keys):
            new_path = f"{path}.{key}" if path else key
            # Skip ignored paths
            if new_path in ignored_paths:
                continue
            if key not in d1:
                differences.append(f"MISSING in original: {new_path}")
            elif key not in d2:
                differences.append(f"MISSING in loaded: {new_path}")
            else:
                compare_values(new_path, d1[key], d2[key])

    def compare_list(path: str, l1: list, l2: list):
        if len(l1) != len(l2):
            differences.append(f"LENGTH MISMATCH at {path}: {len(l1)} vs {len(l2)}")
            return

        for i, (v1, v2) in enumerate(zip(l1, l2)):
            compare_values(f"{path}[{i}]", v1, v2)

    def compare_values(path: str, v1, v2):
        if type(v1) != type(v2):
            # Allow int/float comparison
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                if abs(float(v1) - float(v2)) > 0.0001:
                    differences.append(f"VALUE MISMATCH at {path}: {v1} vs {v2}")
            else:
                differences.append(f"TYPE MISMATCH at {path}: {type(v1).__name__} vs {type(v2).__name__}")
        elif isinstance(v1, dict):
            compare_dict(path, v1, v2)
        elif isinstance(v1, list):
            compare_list(path, v1, v2)
        elif isinstance(v1, float):
            if abs(v1 - v2) > 0.0001:
                differences.append(f"VALUE MISMATCH at {path}: {v1} vs {v2}")
        elif v1 != v2:
            differences.append(f"VALUE MISMATCH at {path}: {v1} vs {v2}")

    compare_values("", original, loaded)
    return differences


class TestConfigIntegrity:
    """
    Critical test: Config save/load integrity with 300+ items.
    """

    def test_large_config_roundtrip(self):
        """
        CRITICAL TEST:
        1. Generate a complex real-world config (300+ items)
        2. Save to file via ConfigManager
        3. Load from file
        4. Compare - MUST be identical
        """
        # Step 1: Generate config
        original_config = generate_real_world_config()

        # Count items
        num_channels = len(original_config.get("channels", []))
        num_can_msgs = len(original_config.get("can_messages", []))
        total_items = num_channels + num_can_msgs

        print(f"\n{'='*60}")
        print(f"Config Integrity Test")
        print(f"{'='*60}")
        print(f"Channels: {num_channels}")
        print(f"CAN Messages: {num_can_msgs}")
        print(f"Total Items: {total_items}")
        print(f"{'='*60}")

        assert total_items >= 300, f"Config should have 300+ items, got {total_items}"

        # Step 2: Create temp files
        with tempfile.TemporaryDirectory() as tmpdir:
            original_file = Path(tmpdir) / "original.json"
            saved_file = Path(tmpdir) / "saved.json"

            # Save original JSON directly
            with open(original_file, 'w', encoding='utf-8') as f:
                json.dump(original_config, f, indent=2)
            print(f"Saved original to: {original_file}")

            # Step 3: Load via ConfigManager
            config_manager = ConfigManager()
            success = config_manager.load_from_file(str(original_file))
            assert success, "Failed to load config"
            print(f"Loaded config via ConfigManager")

            # Step 4: Save via ConfigManager
            success = config_manager.save_to_file(str(saved_file))
            assert success, "Failed to save config"
            print(f"Saved config via ConfigManager")

            # Step 5: Load saved config
            with open(saved_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)

            # Step 6: Compare
            orig_normalized = normalize_config(original_config)
            loaded_normalized = normalize_config(loaded_config)

            differences = compare_configs(orig_normalized, loaded_normalized)

            if differences:
                print(f"\n{len(differences)} DIFFERENCES FOUND:")
                for diff in differences[:20]:  # Show first 20
                    print(f"  - {diff}")
                if len(differences) > 20:
                    print(f"  ... and {len(differences) - 20} more")

                # Write diff files for debugging
                with open(Path(tmpdir) / "orig_normalized.json", 'w') as f:
                    json.dump(orig_normalized, f, indent=2)
                with open(Path(tmpdir) / "loaded_normalized.json", 'w') as f:
                    json.dump(loaded_normalized, f, indent=2)

                pytest.fail(f"Config integrity failed: {len(differences)} differences found")

            print(f"\n{'='*60}")
            print(f"CONFIG INTEGRITY TEST PASSED")
            print(f"All {total_items} items preserved correctly!")
            print(f"{'='*60}\n")

    def test_channel_type_coverage(self):
        """Verify the test config covers all channel types."""
        config = generate_real_world_config()
        channel_types = set()

        for ch in config.get("channels", []):
            channel_types.add(ch.get("channel_type"))

        expected_types = {
            "digital_input", "analog_input", "power_output",
            "can_rx", "logic", "number", "timer", "filter",
            "table_2d", "switch", "pid", "hbridge"
        }

        missing = expected_types - channel_types
        assert not missing, f"Missing channel types in test config: {missing}"

        print(f"\nChannel types covered: {sorted(channel_types)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
