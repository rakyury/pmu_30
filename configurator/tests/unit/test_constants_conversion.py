"""
Unit Tests: Constants Display <-> Internal Conversion

Tests the GLOBAL RULE:
- Display values with 2 decimal places
- Store as integers (multiplied by 100)

Example:
  Display: 12.34 -> Internal: 1234
  Internal: 1234 -> Display: 12.34
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from utils.constants import (
    CONSTANT_DECIMAL_PLACES,
    CONSTANT_SCALE,
    display_to_internal,
    internal_to_display,
    format_constant,
    parse_constant,
    clamp_internal,
    display_range_to_internal,
    migrate_float_to_internal,
)


class TestConstantConversion:
    """Test basic display <-> internal conversion."""

    def test_display_to_internal_basic(self):
        """Test basic display to internal conversion."""
        assert display_to_internal(12.34) == 1234
        assert display_to_internal(0.0) == 0
        assert display_to_internal(1.0) == 100
        assert display_to_internal(100.0) == 10000

    def test_display_to_internal_negative(self):
        """Test negative value conversion."""
        assert display_to_internal(-12.34) == -1234
        assert display_to_internal(-1.0) == -100
        assert display_to_internal(-0.5) == -50

    def test_display_to_internal_rounding(self):
        """Test rounding behavior (Python banker's rounding - half to even)."""
        # Python uses banker's rounding: 0.5 rounds to nearest even
        assert display_to_internal(12.345) == 1234  # 1234.5 rounds to 1234 (even)
        assert display_to_internal(12.355) == 1236  # 1235.5 rounds to 1236 (even)
        assert display_to_internal(12.344) == 1234  # 1234.4 rounds to 1234
        assert display_to_internal(0.006) == 1      # 0.6 rounds to 1
        assert display_to_internal(0.004) == 0      # 0.4 rounds to 0

    def test_display_to_internal_large_values(self):
        """Test large value conversion."""
        assert display_to_internal(10000.0) == 1000000
        assert display_to_internal(99999.99) == 9999999

    def test_internal_to_display_basic(self):
        """Test basic internal to display conversion."""
        assert internal_to_display(1234) == 12.34
        assert internal_to_display(0) == 0.0
        assert internal_to_display(100) == 1.0
        assert internal_to_display(10000) == 100.0

    def test_internal_to_display_negative(self):
        """Test negative internal to display."""
        assert internal_to_display(-1234) == -12.34
        assert internal_to_display(-100) == -1.0
        assert internal_to_display(-50) == -0.5

    def test_roundtrip_conversion(self):
        """Test that display -> internal -> display preserves value."""
        test_values = [0.0, 1.0, -1.0, 12.34, -12.34, 100.0, 0.01, 0.99]
        for val in test_values:
            internal = display_to_internal(val)
            result = internal_to_display(internal)
            assert abs(result - val) < 0.001, f"Roundtrip failed for {val}"

    def test_roundtrip_internal(self):
        """Test that internal -> display -> internal preserves value."""
        test_values = [0, 100, -100, 1234, -1234, 10000, 1, 99]
        for val in test_values:
            display = internal_to_display(val)
            result = display_to_internal(display)
            assert result == val, f"Roundtrip failed for {val}"


class TestConstantFormatting:
    """Test string formatting of constants."""

    def test_format_constant_basic(self):
        """Test basic formatting."""
        assert format_constant(1234) == "12.34"
        assert format_constant(0) == "0.00"
        assert format_constant(100) == "1.00"

    def test_format_constant_negative(self):
        """Test formatting negative values."""
        assert format_constant(-1234) == "-12.34"
        assert format_constant(-100) == "-1.00"

    def test_format_constant_with_suffix(self):
        """Test formatting with unit suffix."""
        assert format_constant(1234, " V") == "12.34 V"
        assert format_constant(500, " A") == "5.00 A"
        assert format_constant(0, " °C") == "0.00 °C"

    def test_format_constant_precision(self):
        """Test that formatting always shows 2 decimal places."""
        assert format_constant(100) == "1.00"  # Not "1.0"
        assert format_constant(1000) == "10.00"  # Not "10.0"
        assert format_constant(10) == "0.10"  # Not "0.1"


class TestConstantParsing:
    """Test parsing display strings to internal values."""

    def test_parse_constant_basic(self):
        """Test basic parsing."""
        assert parse_constant("12.34") == 1234
        assert parse_constant("0.00") == 0
        assert parse_constant("1.00") == 100

    def test_parse_constant_negative(self):
        """Test parsing negative values."""
        assert parse_constant("-12.34") == -1234
        assert parse_constant("-1.00") == -100

    def test_parse_constant_with_suffix(self):
        """Test parsing with unit suffix."""
        assert parse_constant("12.34 V") == 1234
        assert parse_constant("5.00 A") == 500
        assert parse_constant("0.00 °C") == 0

    def test_parse_constant_invalid(self):
        """Test parsing invalid input."""
        assert parse_constant("") == 0
        assert parse_constant("abc") == 0
        assert parse_constant("   ") == 0

    def test_parse_constant_integer_input(self):
        """Test parsing integer input (no decimal)."""
        assert parse_constant("12") == 1200
        assert parse_constant("-5") == -500

    def test_format_parse_roundtrip(self):
        """Test format -> parse roundtrip."""
        test_values = [0, 100, -100, 1234, -1234, 50, 9999]
        for val in test_values:
            formatted = format_constant(val)
            parsed = parse_constant(formatted)
            assert parsed == val, f"Format/parse failed for {val}"


class TestClampInternal:
    """Test internal value clamping."""

    def test_clamp_within_bounds(self):
        """Test value within bounds is unchanged."""
        assert clamp_internal(500, 0, 1000) == 500
        assert clamp_internal(0, 0, 1000) == 0
        assert clamp_internal(1000, 0, 1000) == 1000

    def test_clamp_below_minimum(self):
        """Test value below minimum is clamped."""
        assert clamp_internal(-100, 0, 1000) == 0
        assert clamp_internal(-1, 0, 1000) == 0

    def test_clamp_above_maximum(self):
        """Test value above maximum is clamped."""
        assert clamp_internal(1500, 0, 1000) == 1000
        assert clamp_internal(1001, 0, 1000) == 1000

    def test_clamp_negative_range(self):
        """Test clamping with negative bounds."""
        assert clamp_internal(0, -1000, 1000) == 0
        assert clamp_internal(-1500, -1000, 1000) == -1000
        assert clamp_internal(1500, -1000, 1000) == 1000


class TestDisplayRangeConversion:
    """Test display range to internal conversion."""

    def test_display_range_basic(self):
        """Test basic range conversion."""
        min_i, max_i = display_range_to_internal(0.0, 100.0)
        assert min_i == 0
        assert max_i == 10000

    def test_display_range_negative(self):
        """Test range with negative values."""
        min_i, max_i = display_range_to_internal(-50.0, 50.0)
        assert min_i == -5000
        assert max_i == 5000


class TestMigration:
    """Test migration from old float format to new internal format."""

    def test_migrate_float(self):
        """Test migrating float values."""
        assert migrate_float_to_internal(12.34) == 1234
        assert migrate_float_to_internal(0.0) == 0
        assert migrate_float_to_internal(-5.5) == -550

    def test_migrate_small_int(self):
        """Test migrating small integers (should be converted)."""
        # Small integers are interpreted as display values
        assert migrate_float_to_internal(12) == 1200
        assert migrate_float_to_internal(0) == 0

    def test_migrate_large_int(self):
        """Test migrating large integers (likely already internal)."""
        # Large integers are assumed to be internal format
        assert migrate_float_to_internal(1234567) == 1234567


class TestScaleConstants:
    """Test that scale constants are correct."""

    def test_decimal_places(self):
        """Verify 2 decimal places."""
        assert CONSTANT_DECIMAL_PLACES == 2

    def test_scale_factor(self):
        """Verify scale factor is 100."""
        assert CONSTANT_SCALE == 100
        assert CONSTANT_SCALE == 10 ** CONSTANT_DECIMAL_PLACES


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_small_values(self):
        """Test very small display values."""
        assert display_to_internal(0.01) == 1
        assert display_to_internal(0.001) == 0  # Rounds to 0
        assert internal_to_display(1) == 0.01

    def test_very_large_values(self):
        """Test very large values."""
        large = 1000000.0
        internal = display_to_internal(large)
        assert internal == 100000000
        assert internal_to_display(internal) == large

    def test_floating_point_precision(self):
        """Test that conversion handles floating point precision issues."""
        # This might cause precision issues: 0.1 + 0.2 != 0.3 in floats
        val = 0.1 + 0.2
        internal = display_to_internal(val)
        result = internal_to_display(internal)
        assert abs(result - 0.3) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
