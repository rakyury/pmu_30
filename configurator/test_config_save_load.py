"""
Test configuration save/load functionality
Tests all tabs: Outputs, Inputs, H-Bridge, Logic, PID, LUA, CAN, Settings
"""

import json
import os
import sys
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.config_manager import ConfigManager


def test_configuration_save_load():
    """Test configuration save and load with all tabs."""

    # Create config manager
    config_manager = ConfigManager()

    # Create comprehensive test configuration
    test_config = {
        "version": "1.0.0",
        "device": {
            "name": "PMU-30 Test",
            "type": "PMU-30",
            "serial_number": "TEST001"
        },
        "outputs": [
            {"channel": 0, "name": "Headlights", "current_limit": 10.0},
            {"channel": 1, "name": "Fuel Pump", "current_limit": 15.0}
        ],
        "inputs": [
            {"channel": 0, "name": "Brake Pedal", "type": "Switch Active Low"},
            {"channel": 1, "name": "Throttle Position", "type": "Linear Analog"}
        ],
        "hbridge": [
            {
                "name": "Cooling Fan",
                "mode": "Bidirectional",
                "control": {
                    "mode": "PWM (0-100%)",
                    "forward": {"type": "Physical Input (0-19)", "channel": 0},
                    "reverse": {"type": "Physical Input (0-19)", "channel": 1},
                    "speed": {"type": "Physical Input (0-19)", "channel": 2}
                },
                "pwm": {"frequency": "5 kHz", "min_duty": 10, "max_duty": 100},
                "protection": {
                    "current_limit_a": 10.0,
                    "thermal_protection": True,
                    "overcurrent_action": "Disable Output"
                },
                "advanced": {
                    "soft_start_ms": 100,
                    "soft_stop_ms": 100,
                    "active_braking": False,
                    "invert_direction": False
                }
            },
            {
                "name": "H-Bridge 1",
                "mode": "Bidirectional",
                "control": {
                    "mode": "PWM (0-100%)",
                    "forward": {"type": "Physical Input (0-19)", "channel": 3},
                    "reverse": {"type": "Physical Input (0-19)", "channel": 4},
                    "speed": {"type": "Physical Input (0-19)", "channel": 5}
                },
                "pwm": {"frequency": "5 kHz", "min_duty": 10, "max_duty": 100},
                "protection": {
                    "current_limit_a": 10.0,
                    "thermal_protection": True,
                    "overcurrent_action": "Disable Output"
                },
                "advanced": {
                    "soft_start_ms": 100,
                    "soft_stop_ms": 100,
                    "active_braking": False,
                    "invert_direction": False
                }
            },
            {
                "name": "H-Bridge 2",
                "mode": "Bidirectional",
                "control": {
                    "mode": "PWM (0-100%)",
                    "forward": {"type": "Physical Input (0-19)", "channel": 6},
                    "reverse": {"type": "Physical Input (0-19)", "channel": 7},
                    "speed": {"type": "Physical Input (0-19)", "channel": 8}
                },
                "pwm": {"frequency": "5 kHz", "min_duty": 10, "max_duty": 100},
                "protection": {
                    "current_limit_a": 10.0,
                    "thermal_protection": True,
                    "overcurrent_action": "Disable Output"
                },
                "advanced": {
                    "soft_start_ms": 100,
                    "soft_stop_ms": 100,
                    "active_braking": False,
                    "invert_direction": False
                }
            },
            {
                "name": "H-Bridge 3",
                "mode": "Bidirectional",
                "control": {
                    "mode": "PWM (0-100%)",
                    "forward": {"type": "Physical Input (0-19)", "channel": 9},
                    "reverse": {"type": "Physical Input (0-19)", "channel": 10},
                    "speed": {"type": "Physical Input (0-19)", "channel": 11}
                },
                "pwm": {"frequency": "5 kHz", "min_duty": 10, "max_duty": 100},
                "protection": {
                    "current_limit_a": 10.0,
                    "thermal_protection": True,
                    "overcurrent_action": "Disable Output"
                },
                "advanced": {
                    "soft_start_ms": 100,
                    "soft_stop_ms": 100,
                    "active_braking": False,
                    "invert_direction": False
                }
            }
        ],
        "logic_functions": [
            {
                "name": "Headlight Logic",
                "operation": "AND",
                "virtual_channel": 0,
                "inputs": [
                    {"type": "Physical Input", "channel": 0, "inverted": False},
                    {"type": "Physical Input", "channel": 1, "inverted": False}
                ],
                "parameters": {}
            }
        ],
        "pid_controllers": [
            {
                "name": "Engine Temp Control",
                "input_source": {"type": "Physical Input (0-19)", "channel": 5},
                "output_target": {"type": "Physical Output (0-29)", "channel": 10},
                "parameters": {"kp": 1.0, "ki": 0.1, "kd": 0.05},
                "setpoint": 80.0,
                "output_min": 0.0,
                "output_max": 100.0,
                "advanced": {
                    "sample_time_ms": 100,
                    "anti_windup": True,
                    "derivative_filter": True
                }
            }
        ],
        "lua_scripts": [
            {
                "name": "Custom Logic",
                "description": "Test script",
                "trigger": {
                    "type": "Periodic (Timer)",
                    "period_ms": 100,
                    "channel": 0
                },
                "script": "-- Test script\nlocal val = pmu.getInput(0)\npmu.setOutput(0, val * 2)",
                "settings": {
                    "max_execution_ms": 50,
                    "priority": "Normal",
                    "error_action": "Disable Script"
                }
            }
        ],
        "can_messages": [
            {
                "name": "Engine RPM",
                "can_id": 0x100,
                "extended": False,
                "dlc": 8,
                "transmit_enabled": True,
                "period_ms": 10,
                "signals": [
                    {
                        "name": "RPM",
                        "start_bit": 0,
                        "length": 16,
                        "type": "uint16",
                        "byte_order": "Little Endian",
                        "scale": 1.0,
                        "offset": 0.0,
                        "mapping": {
                            "type": "Physical Input",
                            "channel": 3
                        }
                    }
                ]
            }
        ],
        "settings": {
            "device": {
                "name": "PMU-30 Test",
                "description": "Test configuration",
                "serial_number": "TEST001"
            },
            "can": {
                "bitrate": "500 kbps",
                "node_id": 1,
                "terminator": False,
                "listen_only": False,
                "auto_retransmit": True
            },
            "power": {
                "nominal_voltage": 12.0,
                "low_voltage_warning": 10.5,
                "low_voltage_cutoff": 9.0,
                "high_voltage_cutoff": 16.0
            },
            "system": {
                "units": "Metric (°C, km/h)",
                "log_level": "Warning",
                "watchdog_timeout_ms": 1000,
                "heartbeat_interval_ms": 1000
            },
            "safety": {
                "safe_state": "All Outputs Off",
                "startup_delay_ms": 500,
                "max_total_current_a": 100.0
            }
        }
    }

    # Set config
    config_manager.config = test_config

    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = f.name

    print(f"Testing configuration save/load...")
    print(f"Temp file: {temp_file}")

    # Test save
    success = config_manager.save_to_file(temp_file)
    print(f"Save result: {success}")

    if success:
        print(f"Configuration saved successfully")

        # Verify file exists and is valid JSON
        with open(temp_file, 'r') as f:
            saved_data = json.load(f)

        print(f"Saved configuration contains:")
        print(f"  - {len(saved_data.get('outputs', []))} outputs")
        print(f"  - {len(saved_data.get('inputs', []))} inputs")
        print(f"  - {len(saved_data.get('hbridge', []))} H-Bridge channels")
        print(f"  - {len(saved_data.get('logic_functions', []))} logic functions")
        print(f"  - {len(saved_data.get('pid_controllers', []))} PID controllers")
        print(f"  - {len(saved_data.get('lua_scripts', []))} LUA scripts")
        print(f"  - {len(saved_data.get('can_messages', []))} CAN messages")
        print(f"  - Settings: {list(saved_data.get('settings', {}).keys())}")

        # Test load
        config_manager2 = ConfigManager()
        load_success, error_msg = config_manager2.load_from_file(temp_file)

        print(f"\nLoad result: {load_success}")
        if load_success:
            print("Configuration loaded successfully")

            # Verify loaded data
            loaded_config = config_manager2.config
            print(f"\nLoaded configuration contains:")
            print(f"  - {len(loaded_config.get('outputs', []))} outputs")
            print(f"  - {len(loaded_config.get('inputs', []))} inputs")
            print(f"  - {len(loaded_config.get('hbridge', []))} H-Bridge channels")
            print(f"  - {len(loaded_config.get('logic_functions', []))} logic functions")
            print(f"  - {len(loaded_config.get('pid_controllers', []))} PID controllers")
            print(f"  - {len(loaded_config.get('lua_scripts', []))} LUA scripts")
            print(f"  - {len(loaded_config.get('can_messages', []))} CAN messages")
            print(f"  - Settings device name: {loaded_config.get('settings', {}).get('device', {}).get('name')}")

            # Verify specific values
            assert loaded_config['outputs'][0]['name'] == "Headlights"
            assert loaded_config['inputs'][0]['name'] == "Brake Pedal"
            assert loaded_config['hbridge'][0]['name'] == "Cooling Fan"
            assert loaded_config['logic_functions'][0]['name'] == "Headlight Logic"
            assert loaded_config['pid_controllers'][0]['name'] == "Engine Temp Control"
            assert loaded_config['lua_scripts'][0]['name'] == "Custom Logic"
            assert loaded_config['can_messages'][0]['name'] == "Engine RPM"
            assert loaded_config['settings']['device']['name'] == "PMU-30 Test"

            print("\n✓ All verifications passed!")
            print("✓ Configuration save/load working correctly!")
        else:
            print(f"Load failed: {error_msg}")
    else:
        print("Save failed")

    # Cleanup
    if os.path.exists(temp_file):
        os.remove(temp_file)
        print(f"\nCleaned up temp file")


if __name__ == "__main__":
    test_configuration_save_load()
