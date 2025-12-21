"""
Unit tests for ConfigManager
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


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.manager = ConfigManager()

    def test_initialization(self):
        """Test ConfigManager initialization"""
        self.assertIsNotNone(self.manager.config)
        self.assertIn("version", self.manager.config)
        self.assertIn("device", self.manager.config)
        self.assertIn("inputs", self.manager.config)
        self.assertIn("outputs", self.manager.config)

    def test_get_config(self):
        """Test get_config returns configuration"""
        config = self.manager.get_config()
        self.assertIsInstance(config, dict)
        self.assertEqual(config["version"], "1.0")

    def test_new_config(self):
        """Test creating new configuration"""
        # Modify config
        self.manager.config["device"]["name"] = "Test Device"
        self.manager.modified = True

        # Create new config
        self.manager.new_config()

        # Check defaults restored
        self.assertEqual(self.manager.config["device"]["name"], "PMU-30")
        self.assertFalse(self.manager.modified)
        self.assertIsNone(self.manager.current_file)

    def test_is_modified(self):
        """Test is_modified flag"""
        self.assertFalse(self.manager.is_modified())

        self.manager.modified = True
        self.assertTrue(self.manager.is_modified())

    def test_add_input(self):
        """Test adding input configuration"""
        input_config = {
            "channel": 0,
            "name": "Test Input",
            "type": "Switch Active Low",
            "parameters": {}
        }

        self.manager.add_input(input_config)

        self.assertEqual(len(self.manager.config["inputs"]), 1)
        self.assertEqual(self.manager.config["inputs"][0]["name"], "Test Input")
        self.assertTrue(self.manager.modified)

    def test_add_input_max_limit(self):
        """Test adding more than 20 inputs raises error"""
        # Add 20 inputs
        for i in range(20):
            self.manager.add_input({
                "channel": i,
                "name": f"Input {i}",
                "type": "Switch Active Low",
                "parameters": {}
            })

        # Try to add 21st input
        with self.assertRaises(ValueError):
            self.manager.add_input({
                "channel": 20,
                "name": "Input 20",
                "type": "Switch Active Low",
                "parameters": {}
            })

    def test_add_output(self):
        """Test adding output configuration"""
        output_config = {
            "channel": 0,
            "name": "Test Output",
            "enabled": True,
            "protection": {},
            "pwm": {}
        }

        self.manager.add_output(output_config)

        self.assertEqual(len(self.manager.config["outputs"]), 1)
        self.assertEqual(self.manager.config["outputs"][0]["name"], "Test Output")

    def test_add_output_max_limit(self):
        """Test adding more than 30 outputs raises error"""
        # Add 30 outputs
        for i in range(30):
            self.manager.add_output({
                "channel": i,
                "name": f"Output {i}",
                "enabled": True
            })

        # Try to add 31st output
        with self.assertRaises(ValueError):
            self.manager.add_output({
                "channel": 30,
                "name": "Output 30",
                "enabled": True
            })

    def test_save_and_load_config(self):
        """Test saving and loading configuration"""
        # Add some data
        self.manager.add_input({
            "channel": 0,
            "name": "Test Input",
            "type": "Switch Active Low",
            "parameters": {}
        })

        self.manager.add_output({
            "channel": 0,
            "name": "Test Output",
            "enabled": True
        })

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            # Save
            result = self.manager.save_to_file(temp_file)
            self.assertTrue(result)

            # Create new manager and load
            new_manager = ConfigManager()
            success, error_msg = new_manager.load_from_file(temp_file)
            self.assertTrue(success, f"Load failed: {error_msg}")

            # Verify data
            self.assertEqual(len(new_manager.config["inputs"]), 1)
            self.assertEqual(new_manager.config["inputs"][0]["name"], "Test Input")
            self.assertEqual(len(new_manager.config["outputs"]), 1)
            self.assertEqual(new_manager.config["outputs"][0]["name"], "Test Output")

        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_load_nonexistent_file(self):
        """Test loading from non-existent file"""
        success, error_msg = self.manager.load_from_file("/nonexistent/file.json")
        self.assertFalse(success)
        self.assertIsNotNone(error_msg)

    def test_update_input(self):
        """Test updating input configuration"""
        # Add input
        self.manager.add_input({
            "channel": 0,
            "name": "Original",
            "type": "Switch Active Low"
        })

        # Update input
        updated_config = {
            "channel": 0,
            "name": "Updated",
            "type": "Switch Active High"
        }
        self.manager.update_input(0, updated_config)

        # Verify
        self.assertEqual(self.manager.config["inputs"][0]["name"], "Updated")
        self.assertEqual(self.manager.config["inputs"][0]["type"], "Switch Active High")

    def test_delete_input(self):
        """Test deleting input configuration"""
        # Add inputs
        self.manager.add_input({"channel": 0, "name": "Input 0"})
        self.manager.add_input({"channel": 1, "name": "Input 1"})

        # Delete first input
        self.manager.delete_input(0)

        # Verify
        self.assertEqual(len(self.manager.config["inputs"]), 1)
        self.assertEqual(self.manager.config["inputs"][0]["name"], "Input 1")

    def test_clear_inputs(self):
        """Test clearing all inputs"""
        # Add inputs
        for i in range(5):
            self.manager.add_input({"channel": i, "name": f"Input {i}"})

        # Clear
        self.manager.clear_inputs()

        # Verify
        self.assertEqual(len(self.manager.config["inputs"]), 0)


if __name__ == '__main__':
    unittest.main()
