"""
Unit tests for JSON configuration validation
"""

import unittest
import json
import tempfile
import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from models.config_manager import ConfigManager
from models.config_schema import ConfigValidator


class TestConfigValidation(unittest.TestCase):
    """Test cases for configuration validation"""

    def setUp(self):
        """Set up test fixtures"""
        self.manager = ConfigManager()

    def test_valid_default_config(self):
        """Test that default configuration is valid"""
        config = self.manager.get_config()
        is_valid, errors = ConfigValidator.validate_config(config)

        self.assertTrue(is_valid, f"Default config should be valid. Errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_missing_required_field_version(self):
        """Test validation fails when version is missing"""
        config = self.manager.get_config()
        del config["version"]

        is_valid, errors = ConfigValidator.validate_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("version" in err for err in errors))

    def test_missing_required_field_device(self):
        """Test validation fails when device is missing"""
        config = self.manager.get_config()
        del config["device"]

        is_valid, errors = ConfigValidator.validate_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("device" in err for err in errors))

    def test_too_many_inputs(self):
        """Test validation fails with more than 20 inputs"""
        config = self.manager.get_config()

        # Add 21 inputs
        for i in range(21):
            config["inputs"].append({
                "channel": i,
                "name": f"Input {i}",
                "type": "Switch Active Low"
            })

        is_valid, errors = ConfigValidator.validate_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("20" in err and "inputs" in err for err in errors))

    def test_too_many_outputs(self):
        """Test validation fails with more than 30 outputs"""
        config = self.manager.get_config()

        # Add 31 outputs
        for i in range(31):
            config["outputs"].append({
                "channel": i,
                "name": f"Output {i}",
                "enabled": True
            })

        is_valid, errors = ConfigValidator.validate_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("30" in err and "outputs" in err for err in errors))

    def test_invalid_input_type(self):
        """Test validation fails with invalid input type"""
        config = self.manager.get_config()
        config["inputs"].append({
            "channel": 0,
            "name": "Test Input",
            "type": "Invalid Type"
        })

        is_valid, errors = ConfigValidator.validate_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("type" in err for err in errors))

    def test_duplicate_input_channels(self):
        """Test validation fails with duplicate input channels"""
        config = self.manager.get_config()

        # Add two inputs with same channel
        config["inputs"].append({
            "channel": 0,
            "name": "Input 1",
            "type": "Switch Active Low"
        })
        config["inputs"].append({
            "channel": 0,
            "name": "Input 2",
            "type": "Switch Active High"
        })

        is_valid, errors = ConfigValidator.validate_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("Duplicate" in err and "channel" in err for err in errors))

    def test_duplicate_output_channels(self):
        """Test validation fails with duplicate output channels"""
        config = self.manager.get_config()

        # Add two outputs with same channel
        config["outputs"].append({
            "channel": 0,
            "name": "Output 1",
            "enabled": True
        })
        config["outputs"].append({
            "channel": 0,
            "name": "Output 2",
            "enabled": True
        })

        is_valid, errors = ConfigValidator.validate_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("Duplicate" in err and "channel" in err for err in errors))

    def test_input_channel_out_of_range(self):
        """Test validation fails with input channel out of range"""
        config = self.manager.get_config()
        config["inputs"].append({
            "channel": 25,  # Max is 19
            "name": "Invalid Channel",
            "type": "Switch Active Low"
        })

        is_valid, errors = ConfigValidator.validate_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("channel" in err and "19" in err for err in errors))

    def test_output_channel_out_of_range(self):
        """Test validation fails with output channel out of range"""
        config = self.manager.get_config()
        config["outputs"].append({
            "channel": 35,  # Max is 29
            "name": "Invalid Channel",
            "enabled": True
        })

        is_valid, errors = ConfigValidator.validate_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("channel" in err and "29" in err for err in errors))

    def test_load_invalid_json_syntax(self):
        """Test loading file with invalid JSON syntax"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
            f.write('{ "invalid": json syntax }')  # Missing quotes

        try:
            success, error_msg = self.manager.load_from_file(temp_file)

            self.assertFalse(success)
            self.assertIsNotNone(error_msg)
            self.assertIn("JSON", error_msg)

        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_load_config_missing_required_fields(self):
        """Test loading config with missing required fields"""
        invalid_config = {
            "version": "1.0"
            # Missing device, inputs, outputs
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
            json.dump(invalid_config, f)

        try:
            success, error_msg = self.manager.load_from_file(temp_file)

            self.assertFalse(success)
            self.assertIsNotNone(error_msg)
            self.assertIn("device", error_msg.lower())

        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_load_config_with_validation_errors(self):
        """Test loading config with validation errors shows helpful message"""
        invalid_config = {
            "version": "1.0",
            "device": {
                "name": "PMU-30",
                "serial_number": "TEST123"
            },
            "inputs": [
                {
                    "channel": 0,
                    "name": "Input 1",
                    "type": "Invalid Type"  # Invalid type
                }
            ],
            "outputs": []
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
            json.dump(invalid_config, f)

        try:
            success, error_msg = self.manager.load_from_file(temp_file)

            self.assertFalse(success)
            self.assertIsNotNone(error_msg)
            self.assertIn("validation", error_msg.lower())
            self.assertIn("type", error_msg.lower())

        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_save_and_load_preserves_all_data(self):
        """Test that save and load preserves all configuration data"""
        # Add various configuration items
        self.manager.add_input({
            "channel": 0,
            "name": "Brake Pressure",
            "type": "Calibrated Analog",
            "pull_up": False,
            "pull_down": False,
            "filter_samples": 10,
            "parameters": {
                "multiplier": 100.0,
                "offset": -50.0,
                "unit": "bar"
            }
        })

        self.manager.add_output({
            "channel": 5,
            "name": "Fuel Pump",
            "enabled": True,
            "protection": {
                "current_limit": 15.0,
                "inrush_current": 30.0,
                "inrush_time_ms": 500
            },
            "pwm": {
                "enabled": True,
                "frequency": 1000,
                "default_duty": 75.0
            }
        })

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            # Save
            self.manager.save_to_file(temp_file)

            # Load into new manager
            new_manager = ConfigManager()
            success, error_msg = new_manager.load_from_file(temp_file)

            self.assertTrue(success, f"Load failed: {error_msg}")

            # Verify all data preserved
            inputs = new_manager.get_inputs()
            self.assertEqual(len(inputs), 1)
            self.assertEqual(inputs[0]["name"], "Brake Pressure")
            self.assertEqual(inputs[0]["parameters"]["multiplier"], 100.0)
            self.assertEqual(inputs[0]["parameters"]["unit"], "bar")

            outputs = new_manager.config["outputs"]
            self.assertEqual(len(outputs), 1)
            self.assertEqual(outputs[0]["name"], "Fuel Pump")
            self.assertEqual(outputs[0]["protection"]["current_limit"], 15.0)
            self.assertTrue(outputs[0]["pwm"]["enabled"])

        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_error_message_formatting(self):
        """Test that validation errors are formatted nicely"""
        errors = [
            "Missing required field: 'version'",
            "inputs[0].channel must be between 0 and 19",
            "outputs[2].type must be one of [...]"
        ]

        formatted = ConfigValidator.format_validation_errors(errors)

        self.assertIn("1.", formatted)
        self.assertIn("2.", formatted)
        self.assertIn("3.", formatted)
        self.assertIn("validation failed", formatted.lower())


if __name__ == '__main__':
    unittest.main()
