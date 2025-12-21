"""
JSON Schema для валидации конфигурации PMU-30
"""

from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

# JSON Schema для конфигурации PMU-30
PMU_CONFIG_SCHEMA = {
    "type": "object",
    "required": ["version", "device", "inputs", "outputs"],
    "properties": {
        "version": {
            "type": "string",
            "pattern": "^\\d+\\.\\d+$"
        },
        "device": {
            "type": "object",
            "required": ["name", "serial_number"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "serial_number": {"type": "string"},
                "firmware_version": {"type": "string"},
                "hardware_revision": {"type": "string"},
                "created": {"type": "string"},
                "modified": {"type": "string"}
            }
        },
        "inputs": {
            "type": "array",
            "maxItems": 20,
            "items": {
                "type": "object",
                "required": ["channel", "name", "type"],
                "properties": {
                    "channel": {"type": "integer", "minimum": 0, "maximum": 19},
                    "name": {"type": "string", "minLength": 1},
                    "type": {
                        "type": "string",
                        "enum": [
                            "Switch Active Low",
                            "Switch Active High",
                            "Rotary Switch",
                            "Linear Analog",
                            "Calibrated Analog",
                            "Frequency Input"
                        ]
                    },
                    "pull_up": {"type": "boolean"},
                    "pull_down": {"type": "boolean"},
                    "filter_samples": {"type": "integer", "minimum": 1, "maximum": 100},
                    "parameters": {"type": "object"}
                }
            }
        },
        "outputs": {
            "type": "array",
            "maxItems": 30,
            "items": {
                "type": "object",
                "required": ["channel", "name", "enabled"],
                "properties": {
                    "channel": {"type": "integer", "minimum": 0, "maximum": 29},
                    "name": {"type": "string", "minLength": 1},
                    "enabled": {"type": "boolean"},
                    "protection": {"type": "object"},
                    "pwm": {"type": "object"},
                    "advanced": {"type": "object"}
                }
            }
        },
        "hbridges": {
            "type": "array",
            "maxItems": 4,
            "items": {"type": "object"}
        },
        "logic_functions": {
            "type": "array",
            "maxItems": 100,
            "items": {"type": "object"}
        },
        "virtual_channels": {
            "type": "array",
            "maxItems": 256,
            "items": {"type": "object"}
        },
        "pid_controllers": {
            "type": "array",
            "items": {"type": "object"}
        },
        "can_buses": {
            "type": "array",
            "maxItems": 4,
            "items": {"type": "object"}
        },
        "wiper_modules": {
            "type": "array",
            "items": {"type": "object"}
        },
        "turn_signal_modules": {
            "type": "array",
            "items": {"type": "object"}
        },
        "system": {
            "type": "object"
        }
    }
}


class ConfigValidator:
    """Валидатор конфигурации PMU-30"""

    @staticmethod
    def validate_type(value: Any, expected_type: str, path: str) -> Tuple[bool, str]:
        """Проверка типа значения"""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict
        }

        expected_py_type = type_map.get(expected_type)
        if not isinstance(value, expected_py_type):
            return False, f"{path}: expected {expected_type}, got {type(value).__name__}"
        return True, ""

    @staticmethod
    def validate_range(value: int, minimum: int = None, maximum: int = None, path: str = "") -> Tuple[bool, str]:
        """Проверка диапазона числового значения"""
        if minimum is not None and value < minimum:
            return False, f"{path}: value {value} is less than minimum {minimum}"
        if maximum is not None and value > maximum:
            return False, f"{path}: value {value} is greater than maximum {maximum}"
        return True, ""

    @staticmethod
    def validate_enum(value: str, allowed_values: List[str], path: str) -> Tuple[bool, str]:
        """Проверка значения из перечисления"""
        if value not in allowed_values:
            return False, f"{path}: '{value}' is not one of {allowed_values}"
        return True, ""

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Валидация полной конфигурации

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        errors = []

        # Проверка обязательных полей верхнего уровня
        required_fields = ["version", "device", "inputs", "outputs"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: '{field}'")

        if errors:
            return False, errors

        # Проверка версии
        if not isinstance(config.get("version"), str):
            errors.append("Field 'version' must be a string")
        elif not config["version"]:
            errors.append("Field 'version' cannot be empty")

        # Проверка device
        device = config.get("device", {})
        if not isinstance(device, dict):
            errors.append("Field 'device' must be an object")
        else:
            if "name" not in device:
                errors.append("device.name is required")
            elif not device["name"]:
                errors.append("device.name cannot be empty")

            if "serial_number" not in device:
                errors.append("device.serial_number is required")

        # Проверка inputs
        inputs = config.get("inputs", [])
        if not isinstance(inputs, list):
            errors.append("Field 'inputs' must be an array")
        else:
            if len(inputs) > 20:
                errors.append(f"Too many inputs: {len(inputs)} (maximum 20)")

            for i, input_cfg in enumerate(inputs):
                path = f"inputs[{i}]"

                # Обязательные поля
                for field in ["channel", "name", "type"]:
                    if field not in input_cfg:
                        errors.append(f"{path}.{field} is required")

                # Проверка типов
                if "channel" in input_cfg:
                    if not isinstance(input_cfg["channel"], int):
                        errors.append(f"{path}.channel must be an integer")
                    elif not (0 <= input_cfg["channel"] <= 19):
                        errors.append(f"{path}.channel must be between 0 and 19")

                if "type" in input_cfg:
                    allowed_types = [
                        "Switch Active Low", "Switch Active High", "Rotary Switch",
                        "Linear Analog", "Calibrated Analog", "Frequency Input"
                    ]
                    if input_cfg["type"] not in allowed_types:
                        errors.append(f"{path}.type must be one of {allowed_types}")

                # Проверка уникальности каналов
                channels = [inp.get("channel") for inp in inputs]
                if len(channels) != len(set(channels)):
                    duplicates = [ch for ch in channels if channels.count(ch) > 1]
                    errors.append(f"Duplicate input channels: {set(duplicates)}")

        # Проверка outputs
        outputs = config.get("outputs", [])
        if not isinstance(outputs, list):
            errors.append("Field 'outputs' must be an array")
        else:
            if len(outputs) > 30:
                errors.append(f"Too many outputs: {len(outputs)} (maximum 30)")

            for i, output_cfg in enumerate(outputs):
                path = f"outputs[{i}]"

                # Обязательные поля
                for field in ["channel", "name", "enabled"]:
                    if field not in output_cfg:
                        errors.append(f"{path}.{field} is required")

                # Проверка типов
                if "channel" in output_cfg:
                    if not isinstance(output_cfg["channel"], int):
                        errors.append(f"{path}.channel must be an integer")
                    elif not (0 <= output_cfg["channel"] <= 29):
                        errors.append(f"{path}.channel must be between 0 and 29")

                if "enabled" in output_cfg and not isinstance(output_cfg["enabled"], bool):
                    errors.append(f"{path}.enabled must be a boolean")

                # Проверка уникальности каналов
                channels = [out.get("channel") for out in outputs]
                if len(channels) != len(set(channels)):
                    duplicates = [ch for ch in channels if channels.count(ch) > 1]
                    errors.append(f"Duplicate output channels: {set(duplicates)}")

        # Проверка массивов с ограничениями
        array_limits = {
            "hbridges": 4,
            "logic_functions": 100,
            "virtual_channels": 256,
            "can_buses": 4
        }

        for field, max_items in array_limits.items():
            if field in config:
                items = config[field]
                if not isinstance(items, list):
                    errors.append(f"Field '{field}' must be an array")
                elif len(items) > max_items:
                    errors.append(f"Too many {field}: {len(items)} (maximum {max_items})")

        is_valid = len(errors) == 0
        return is_valid, errors

    @staticmethod
    def format_validation_errors(errors: List[str]) -> str:
        """Форматирование ошибок валидации для пользователя"""
        if not errors:
            return ""

        error_msg = "Configuration validation failed:\n\n"
        for i, error in enumerate(errors, 1):
            error_msg += f"{i}. {error}\n"

        return error_msg
