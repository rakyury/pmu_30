"""
PMU-30 Configuration Manager

Owner: R2 m-sport
© 2025 R2 m-sport. All rights reserved.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from .config_schema import ConfigValidator

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages PMU-30 configuration files (JSON format)"""

    def __init__(self):
        self.config: Dict[str, Any] = self._create_default_config()
        self.current_file: Optional[Path] = None
        self.modified: bool = False

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration structure"""
        return {
            "version": "1.0",
            "device": {
                "name": "PMU-30",
                "owner": "R2 m-sport",
                "serial_number": "",
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat()
            },
            "inputs": [],  # 20 universal inputs
            "outputs": [],  # 30 PROFET outputs
            "hbridges": [],  # 4 H-Bridge outputs
            "logic_functions": [],  # Logic engine functions
            "virtual_channels": [],  # Virtual channels
            "pid_controllers": [],  # PID controllers
            "can_buses": [],  # CAN configuration
            "wiper_modules": [],  # Wiper control
            "turn_signal_modules": [],  # Turn signal control
            "system": {
                "battery_voltage_range": [6.0, 22.0],
                "overtemp_threshold": 125,
                "control_frequency": 1000,
                "logic_frequency": 500,
                "logging_frequency": 500
            }
        }

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self.config

    def new_config(self) -> None:
        """Create new empty configuration"""
        self.config = self._create_default_config()
        self.current_file = None
        self.modified = False
        logger.info("Created new configuration")

    def load_from_file(self, filepath: str) -> Tuple[bool, Optional[str]]:
        """
        Load configuration from JSON file with validation

        Args:
            filepath: Path to JSON configuration file

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            path = Path(filepath)

            if not path.exists():
                error_msg = f"Configuration file not found: {filepath}"
                logger.error(error_msg)
                return False, error_msg

            # Load JSON
            with open(path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)

            # Validate configuration
            is_valid, validation_errors = ConfigValidator.validate_config(loaded_config)

            if not is_valid:
                error_msg = ConfigValidator.format_validation_errors(validation_errors)
                logger.error(f"Configuration validation failed:\n{error_msg}")
                return False, error_msg

            # Configuration is valid, apply it
            self.config = loaded_config

            # Update modified timestamp
            if "device" in self.config:
                self.config["device"]["modified"] = datetime.now().isoformat()

            self.current_file = path
            self.modified = False

            logger.info(f"Loaded and validated configuration from: {filepath}")
            return True, None

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON format in configuration file:\n\nLine {e.lineno}, Column {e.colno}:\n{e.msg}\n\nPlease check the file syntax."
            logger.error(f"JSON decode error: {e}")
            return False, error_msg

        except Exception as e:
            error_msg = f"Failed to load configuration:\n\n{str(e)}"
            logger.error(f"Failed to load configuration: {e}")
            return False, error_msg

    def save_to_file(self, filepath: Optional[str] = None) -> bool:
        """
        Save configuration to JSON file

        Args:
            filepath: Path to save to (uses current_file if None)

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            if filepath:
                path = Path(filepath)
            elif self.current_file:
                path = self.current_file
            else:
                logger.error("No filepath specified")
                return False

            # Update modified timestamp
            self.config["device"]["modified"] = datetime.now().isoformat()

            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            # Save with pretty formatting
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            self.current_file = path
            self.modified = False

            logger.info(f"Saved configuration to: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def export_to_yaml(self, filepath: str) -> bool:
        """Export configuration to YAML format"""
        try:
            import yaml

            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"Exported configuration to YAML: {filepath}")
            return True

        except ImportError:
            logger.error("PyYAML not installed. Cannot export to YAML.")
            return False
        except Exception as e:
            logger.error(f"Failed to export to YAML: {e}")
            return False

    # Input Channels
    def add_input(self, input_config: Dict[str, Any]) -> None:
        """Add input channel configuration"""
        if len(self.config["inputs"]) >= 20:
            raise ValueError("Maximum 20 inputs allowed")
        self.config["inputs"].append(input_config)
        self.modified = True

    def update_input(self, index: int, input_config: Dict[str, Any]) -> None:
        """Update input channel configuration"""
        if 0 <= index < len(self.config["inputs"]):
            self.config["inputs"][index] = input_config
            self.modified = True

    def delete_input(self, index: int) -> None:
        """Delete input channel configuration"""
        if 0 <= index < len(self.config["inputs"]):
            self.config["inputs"].pop(index)
            self.modified = True

    def get_inputs(self) -> list:
        """Get all input configurations"""
        return self.config["inputs"]

    def clear_inputs(self) -> None:
        """Clear all input configurations"""
        self.config["inputs"] = []
        self.modified = True

    # Output Channels
    def add_output(self, output_config: Dict[str, Any]) -> None:
        """Add output channel configuration"""
        if len(self.config["outputs"]) >= 30:
            raise ValueError("Maximum 30 outputs allowed")
        self.config["outputs"].append(output_config)
        self.modified = True

    def update_output(self, index: int, output_config: Dict[str, Any]) -> None:
        """Update output channel configuration"""
        if 0 <= index < len(self.config["outputs"]):
            self.config["outputs"][index] = output_config
            self.modified = True

    def delete_output(self, index: int) -> None:
        """Delete output channel configuration"""
        if 0 <= index < len(self.config["outputs"]):
            self.config["outputs"].pop(index)
            self.modified = True

    def get_outputs(self) -> list:
        """Get all output configurations"""
        return self.config["outputs"]

    # H-Bridge Channels
    def add_hbridge(self, hbridge_config: Dict[str, Any]) -> None:
        """Add H-Bridge configuration"""
        if len(self.config["hbridges"]) >= 4:
            raise ValueError("Maximum 4 H-Bridges allowed")
        self.config["hbridges"].append(hbridge_config)
        self.modified = True

    def update_hbridge(self, index: int, hbridge_config: Dict[str, Any]) -> None:
        """Update H-Bridge configuration"""
        if 0 <= index < len(self.config["hbridges"]):
            self.config["hbridges"][index] = hbridge_config
            self.modified = True

    def delete_hbridge(self, index: int) -> None:
        """Delete H-Bridge configuration"""
        if 0 <= index < len(self.config["hbridges"]):
            self.config["hbridges"].pop(index)
            self.modified = True

    def get_hbridges(self) -> list:
        """Get all H-Bridge configurations"""
        return self.config["hbridges"]

    # Logic Functions
    def add_logic_function(self, function_config: Dict[str, Any]) -> None:
        """Add logic function"""
        if len(self.config["logic_functions"]) >= 100:
            raise ValueError("Maximum 100 logic functions allowed")
        self.config["logic_functions"].append(function_config)
        self.modified = True

    def update_logic_function(self, index: int, function_config: Dict[str, Any]) -> None:
        """Update logic function"""
        if 0 <= index < len(self.config["logic_functions"]):
            self.config["logic_functions"][index] = function_config
            self.modified = True

    def delete_logic_function(self, index: int) -> None:
        """Delete logic function"""
        if 0 <= index < len(self.config["logic_functions"]):
            self.config["logic_functions"].pop(index)
            self.modified = True

    def get_logic_functions(self) -> list:
        """Get all logic functions"""
        return self.config["logic_functions"]

    # PID Controllers
    def add_pid_controller(self, pid_config: Dict[str, Any]) -> None:
        """Add PID controller"""
        self.config["pid_controllers"].append(pid_config)
        self.modified = True

    def update_pid_controller(self, index: int, pid_config: Dict[str, Any]) -> None:
        """Update PID controller"""
        if 0 <= index < len(self.config["pid_controllers"]):
            self.config["pid_controllers"][index] = pid_config
            self.modified = True

    def delete_pid_controller(self, index: int) -> None:
        """Delete PID controller"""
        if 0 <= index < len(self.config["pid_controllers"]):
            self.config["pid_controllers"].pop(index)
            self.modified = True

    def get_pid_controllers(self) -> list:
        """Get all PID controllers"""
        return self.config["pid_controllers"]

    # CAN Bus
    def add_can_bus(self, can_config: Dict[str, Any]) -> None:
        """Add CAN bus configuration"""
        if len(self.config["can_buses"]) >= 4:
            raise ValueError("Maximum 4 CAN buses allowed")
        self.config["can_buses"].append(can_config)
        self.modified = True

    def update_can_bus(self, index: int, can_config: Dict[str, Any]) -> None:
        """Update CAN bus configuration"""
        if 0 <= index < len(self.config["can_buses"]):
            self.config["can_buses"][index] = can_config
            self.modified = True

    def delete_can_bus(self, index: int) -> None:
        """Delete CAN bus configuration"""
        if 0 <= index < len(self.config["can_buses"]):
            self.config["can_buses"].pop(index)
            self.modified = True

    def get_can_buses(self) -> list:
        """Get all CAN bus configurations"""
        return self.config["can_buses"]

    def is_modified(self) -> bool:
        """Check if configuration has been modified"""
        return self.modified

    def get_current_file(self) -> Optional[Path]:
        """Get current configuration file path"""
        return self.current_file

    def validate_config(self) -> tuple[bool, list[str]]:
        """
        Validate configuration

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check input count
        if len(self.config["inputs"]) > 20:
            errors.append("Too many inputs (maximum 20)")

        # Check output count
        if len(self.config["outputs"]) > 30:
            errors.append("Too many outputs (maximum 30)")

        # Check H-Bridge count
        if len(self.config["hbridges"]) > 4:
            errors.append("Too many H-Bridges (maximum 4)")

        # Check logic function count
        if len(self.config["logic_functions"]) > 100:
            errors.append("Too many logic functions (maximum 100)")

        # Check CAN bus count
        if len(self.config["can_buses"]) > 4:
            errors.append("Too many CAN buses (maximum 4)")

        return (len(errors) == 0, errors)
