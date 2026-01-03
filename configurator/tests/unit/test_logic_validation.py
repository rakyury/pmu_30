"""
Test Logic Channel Validation

Verifies that Logic channel validation correctly accepts channel names (strings)
and rejects invalid inputs.
"""

import sys
from pathlib import Path

# Add paths for imports
CONFIGURATOR_SRC = Path(__file__).parent.parent.parent / "src"
SHARED_PYTHON = Path(__file__).parent.parent.parent.parent / "shared" / "python"
sys.path.insert(0, str(CONFIGURATOR_SRC))
sys.path.insert(0, str(SHARED_PYTHON))

from channel_validation import validate_logic, ValidationError


def test_logic_accepts_string_channel_names():
    """Test that Logic validation accepts channel names as strings."""
    # Config with string channel names (as stored by UI)
    config = {
        "operation": "and",  # AND operation requires 2 inputs
        "channel": "one",    # System channel name
        "channel_2": "Digital Input 1"
    }

    result = validate_logic(config)
    assert result.is_valid, f"Expected valid, got error: {result.error} for field {result.field}"
    print("OK: Logic validation accepts string channel names")


def test_logic_accepts_is_true_single_channel():
    """Test IS_TRUE operation with single channel."""
    config = {
        "operation": "is_true",
        "channel": "one"
    }

    result = validate_logic(config)
    assert result.is_valid, f"Expected valid, got error: {result.error} for field {result.field}"
    print("OK: IS_TRUE with single channel works")


def test_logic_accepts_comparison_operations():
    """Test comparison operations (equal, less, greater, etc.)."""
    for op in ["equal", "not_equal", "less", "greater", "less_equal", "greater_equal"]:
        config = {
            "operation": op,
            "channel": "Analog Input 1",
            "constant": 100
        }

        result = validate_logic(config)
        assert result.is_valid, f"Expected valid for {op}, got error: {result.error}"
    print("OK: All comparison operations work with string channel names")


def test_logic_rejects_empty_inputs():
    """Test that empty channel name is rejected."""
    config = {
        "operation": "is_true",
        "channel": ""  # Empty string
    }

    result = validate_logic(config)
    assert not result.is_valid, "Expected rejection for empty channel"
    assert result.error == ValidationError.LOGIC_NO_INPUTS
    print("OK: Empty channel names are rejected")


def test_logic_rejects_integer_channel_ids():
    """Test that integer channel IDs are rejected (must be strings)."""
    config = {
        "operation": "is_true",
        "channel": 50  # Integer ID - should be rejected
    }

    result = validate_logic(config)
    assert not result.is_valid, "Expected rejection for integer channel ID"
    assert result.error == ValidationError.LOGIC_INVALID_INPUT_ID
    print("OK: Integer channel IDs are rejected (must be strings)")


def test_logic_and_requires_two_inputs():
    """Test that AND operation requires at least 2 inputs."""
    config = {
        "operation": "and",
        "channel": "one"
        # Missing channel_2
    }

    result = validate_logic(config)
    assert not result.is_valid, "Expected rejection for AND with single input"
    assert result.error == ValidationError.LOGIC_INSUFFICIENT_INPUTS
    print("OK: AND operation requires 2 inputs")


def test_logic_with_inputs_list():
    """Test validation with inputs as list."""
    config = {
        "operation": "or",
        "inputs": ["one", "zero", "Digital Input 1"]
    }

    result = validate_logic(config)
    assert result.is_valid, f"Expected valid, got error: {result.error}"
    print("OK: inputs list with string names works")


def test_operation_string_to_int_conversion():
    """Test that operation string names are properly converted."""
    operations = [
        "and", "or", "xor", "nand", "nor",
        "is_true", "is_false",
        "greater", "gt", "greater_equal", "ge",
        "less", "lt", "less_equal", "le",
        "equal", "eq", "not_equal", "ne",
        "range", "outside"
    ]

    for op in operations:
        config = {
            "operation": op,
            "channel": "test_channel"
        }
        # For multi-input ops, add second channel
        if op in ["and", "or", "xor", "nand", "nor"]:
            config["channel_2"] = "test_channel_2"

        result = validate_logic(config)
        # Should not fail with LOGIC_INVALID_OPERATION
        if not result.is_valid:
            assert result.error != ValidationError.LOGIC_INVALID_OPERATION, \
                f"Operation '{op}' was not recognized"

    print("OK: All operation string names are recognized")


if __name__ == "__main__":
    print("=" * 60)
    print("Logic Channel Validation Tests")
    print("=" * 60)

    test_logic_accepts_string_channel_names()
    test_logic_accepts_is_true_single_channel()
    test_logic_accepts_comparison_operations()
    test_logic_rejects_empty_inputs()
    test_logic_rejects_integer_channel_ids()
    test_logic_and_requires_two_inputs()
    test_logic_with_inputs_list()
    test_operation_string_to_int_conversion()

    print("=" * 60)
    print("All tests PASSED!")
    print("=" * 60)
