"""
Quantity and Unit System for PMU-30 Configurator

This module defines physical quantities and their units for display purposes.
Internally all values are stored as integers - this system is for presentation only.

Based on ECUMaster PMU Client conventions.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


@dataclass
class Unit:
    """Represents a unit of measurement."""
    symbol: str           # Display symbol (e.g., "°C", "V", "A")
    name: str             # Full name (e.g., "Celsius", "Volts", "Amperes")
    multiplier: float     # Conversion multiplier from base unit
    offset: float = 0.0   # Conversion offset (for temperature)


@dataclass
class Quantity:
    """Represents a physical quantity with available units."""
    name: str             # Quantity name (e.g., "Temperature", "Voltage")
    units: List[Unit]     # Available units for this quantity
    default_unit: str     # Default unit symbol


# Define all quantities and their units (ECUMaster-compatible)
QUANTITIES: Dict[str, Quantity] = {
    "User": Quantity(
        name="User",
        units=[
            Unit("user", "User defined", 1.0),
        ],
        default_unit="user"
    ),

    "Acceleration": Quantity(
        name="Acceleration",
        units=[
            Unit("m/s²", "Meters per second squared", 1.0),
            Unit("g", "G-force", 9.80665),
            Unit("ft/s²", "Feet per second squared", 0.3048),
        ],
        default_unit="m/s²"
    ),

    "Air fuel ratio": Quantity(
        name="Air fuel ratio",
        units=[
            Unit("AFR", "Air fuel ratio", 1.0),
            Unit("λ", "Lambda", 14.7),
        ],
        default_unit="AFR"
    ),

    "Angle": Quantity(
        name="Angle",
        units=[
            Unit("°", "Degrees", 1.0),
            Unit("rad", "Radians", 57.2958),
        ],
        default_unit="°"
    ),

    "Angular velocity": Quantity(
        name="Angular velocity",
        units=[
            Unit("rpm", "Revolutions per minute", 1.0),
            Unit("krpm", "Kilo-RPM", 1000.0),
            Unit("rps", "Revolutions per second", 60.0),
            Unit("°/s", "Degrees per second", 1/6.0),
        ],
        default_unit="rpm"
    ),

    "Current": Quantity(
        name="Current",
        units=[
            Unit("A", "Amperes", 1.0),
            Unit("mA", "Milliamperes", 0.001),
            Unit("kA", "Kiloamperes", 1000.0),
        ],
        default_unit="A"
    ),

    "Distance": Quantity(
        name="Distance",
        units=[
            Unit("m", "Meters", 1.0),
            Unit("km", "Kilometers", 1000.0),
            Unit("cm", "Centimeters", 0.01),
            Unit("mm", "Millimeters", 0.001),
            Unit("mi", "Miles", 1609.34),
            Unit("in", "Inches", 0.0254),
            Unit("ft", "Feet", 0.3048),
            Unit("yd", "Yards", 0.9144),
        ],
        default_unit="m"
    ),

    "Energy": Quantity(
        name="Energy",
        units=[
            Unit("J", "Joules", 1.0),
            Unit("kJ", "Kilojoules", 1000.0),
            Unit("Wh", "Watt-hours", 3600.0),
            Unit("kWh", "Kilowatt-hours", 3600000.0),
            Unit("cal", "Calories", 4.184),
        ],
        default_unit="J"
    ),

    "Force": Quantity(
        name="Force",
        units=[
            Unit("N", "Newtons", 1.0),
            Unit("kN", "Kilonewtons", 1000.0),
            Unit("lbf", "Pound-force", 4.44822),
            Unit("kgf", "Kilogram-force", 9.80665),
        ],
        default_unit="N"
    ),

    "Frequency": Quantity(
        name="Frequency",
        units=[
            Unit("Hz", "Hertz", 1.0),
            Unit("kHz", "Kilohertz", 1000.0),
            Unit("MHz", "Megahertz", 1000000.0),
            Unit("rpm", "RPM", 1/60.0),
        ],
        default_unit="Hz"
    ),

    "Ignition advance": Quantity(
        name="Ignition advance",
        units=[
            Unit("°BTDC", "Degrees before TDC", 1.0),
            Unit("°ATDC", "Degrees after TDC", -1.0),
        ],
        default_unit="°BTDC"
    ),

    "Illuminance": Quantity(
        name="Illuminance",
        units=[
            Unit("lx", "Lux", 1.0),
            Unit("fc", "Foot-candles", 10.764),
        ],
        default_unit="lx"
    ),

    "Lambda": Quantity(
        name="Lambda",
        units=[
            Unit("λ", "Lambda", 1.0),
            Unit("AFR", "Air fuel ratio", 1/14.7),
        ],
        default_unit="λ"
    ),

    "Mass": Quantity(
        name="Mass",
        units=[
            Unit("kg", "Kilograms", 1.0),
            Unit("g", "Grams", 0.001),
            Unit("mg", "Milligrams", 0.000001),
            Unit("lb", "Pounds", 0.453592),
            Unit("oz", "Ounces", 0.0283495),
        ],
        default_unit="kg"
    ),

    "Mass flow rate": Quantity(
        name="Mass flow rate",
        units=[
            Unit("kg/h", "Kilograms per hour", 1.0),
            Unit("g/s", "Grams per second", 3.6),
            Unit("lb/h", "Pounds per hour", 0.453592),
        ],
        default_unit="kg/h"
    ),

    "Memory size": Quantity(
        name="Memory size",
        units=[
            Unit("B", "Bytes", 1.0),
            Unit("KB", "Kilobytes", 1024.0),
            Unit("MB", "Megabytes", 1048576.0),
            Unit("GB", "Gigabytes", 1073741824.0),
        ],
        default_unit="B"
    ),

    "Percentage": Quantity(
        name="Percentage",
        units=[
            Unit("%", "Percent", 1.0),
            Unit("‰", "Per mille", 0.1),
        ],
        default_unit="%"
    ),

    "Power": Quantity(
        name="Power",
        units=[
            Unit("W", "Watts", 1.0),
            Unit("kW", "Kilowatts", 1000.0),
            Unit("HP", "Horsepower", 745.7),
            Unit("PS", "Metric horsepower", 735.5),
        ],
        default_unit="W"
    ),

    "Pressure": Quantity(
        name="Pressure",
        units=[
            Unit("kPa", "Kilopascals", 1.0),
            Unit("Pa", "Pascals", 0.001),
            Unit("bar", "Bar", 100.0),
            Unit("mbar", "Millibar", 0.1),
            Unit("psi", "PSI", 6.89476),
            Unit("atm", "Atmospheres", 101.325),
            Unit("mmHg", "Millimeters of mercury", 0.133322),
            Unit("inHg", "Inches of mercury", 3.38639),
        ],
        default_unit="kPa"
    ),

    "Ratio": Quantity(
        name="Ratio",
        units=[
            Unit(":1", "Ratio", 1.0),
            Unit("x", "Times", 1.0),
        ],
        default_unit=":1"
    ),

    "Resistance": Quantity(
        name="Resistance",
        units=[
            Unit("Ω", "Ohms", 1.0),
            Unit("kΩ", "Kilohms", 1000.0),
            Unit("MΩ", "Megohms", 1000000.0),
        ],
        default_unit="Ω"
    ),

    "Temperature": Quantity(
        name="Temperature",
        units=[
            Unit("°C", "Celsius", 1.0, 0.0),
            Unit("°F", "Fahrenheit", 1.8, 32.0),
            Unit("K", "Kelvin", 1.0, 273.15),
        ],
        default_unit="°C"
    ),

    "Time": Quantity(
        name="Time",
        units=[
            Unit("s", "Seconds", 1.0),
            Unit("ms", "Milliseconds", 0.001),
            Unit("µs", "Microseconds", 0.000001),
            Unit("min", "Minutes", 60.0),
            Unit("h", "Hours", 3600.0),
        ],
        default_unit="s"
    ),

    "Velocity": Quantity(
        name="Velocity",
        units=[
            Unit("km/h", "Kilometers per hour", 1.0),
            Unit("m/s", "Meters per second", 3.6),
            Unit("mph", "Miles per hour", 1.60934),
            Unit("kn", "Knots", 1.852),
        ],
        default_unit="km/h"
    ),

    "Voltage": Quantity(
        name="Voltage",
        units=[
            Unit("V", "Volts", 1.0),
            Unit("mV", "Millivolts", 0.001),
            Unit("kV", "Kilovolts", 1000.0),
        ],
        default_unit="V"
    ),

    "Volume": Quantity(
        name="Volume",
        units=[
            Unit("L", "Liters", 1.0),
            Unit("mL", "Milliliters", 0.001),
            Unit("m³", "Cubic meters", 1000.0),
            Unit("gal", "Gallons (US)", 3.78541),
            Unit("qt", "Quarts (US)", 0.946353),
        ],
        default_unit="L"
    ),

    "Volume flow rate": Quantity(
        name="Volume flow rate",
        units=[
            Unit("L/min", "Liters per minute", 1.0),
            Unit("L/h", "Liters per hour", 1/60.0),
            Unit("mL/min", "Milliliters per minute", 0.001),
            Unit("gal/h", "Gallons per hour", 3.78541/60.0),
        ],
        default_unit="L/min"
    ),
}


def get_quantity_names() -> List[str]:
    """Get list of all quantity names."""
    return list(QUANTITIES.keys())


def get_quantity(name: str) -> Optional[Quantity]:
    """Get quantity by name."""
    return QUANTITIES.get(name)


def get_units_for_quantity(quantity_name: str) -> List[Unit]:
    """Get available units for a quantity."""
    quantity = QUANTITIES.get(quantity_name)
    if quantity:
        return quantity.units
    return [Unit("user", "User defined", 1.0)]


def get_unit_symbols_for_quantity(quantity_name: str) -> List[str]:
    """Get list of unit symbols for a quantity."""
    return [u.symbol for u in get_units_for_quantity(quantity_name)]


def get_default_unit(quantity_name: str) -> str:
    """Get default unit symbol for a quantity."""
    quantity = QUANTITIES.get(quantity_name)
    if quantity:
        return quantity.default_unit
    return "user"


def format_value(value: int, decimal_places: int, unit_symbol: str = "") -> str:
    """
    Format an integer value for display.

    Args:
        value: Raw integer value
        decimal_places: Number of decimal places (0-4)
        unit_symbol: Unit symbol to append

    Returns:
        Formatted string (e.g., "12.34 °C")
    """
    if decimal_places <= 0:
        formatted = str(value)
    else:
        divisor = 10 ** decimal_places
        float_val = value / divisor
        formatted = f"{float_val:.{decimal_places}f}"

    if unit_symbol:
        return f"{formatted} {unit_symbol}"
    return formatted


def parse_value(text: str, decimal_places: int) -> int:
    """
    Parse a display value back to internal integer.

    Args:
        text: Text to parse (may include unit symbol)
        decimal_places: Number of decimal places

    Returns:
        Integer value for internal storage
    """
    # Remove any non-numeric characters except minus and decimal point
    cleaned = ""
    for char in text:
        if char.isdigit() or char == '-' or char == '.':
            cleaned += char

    if not cleaned:
        return 0

    try:
        float_val = float(cleaned)
        if decimal_places > 0:
            return int(float_val * (10 ** decimal_places))
        return int(float_val)
    except ValueError:
        return 0


@dataclass
class DisplayConfig:
    """Configuration for value display."""
    quantity: str = "User"
    unit: str = "user"
    decimal_places: int = 0

    def format(self, value: int) -> str:
        """Format value for display."""
        return format_value(value, self.decimal_places, self.unit)

    def parse(self, text: str) -> int:
        """Parse display text to internal value."""
        return parse_value(text, self.decimal_places)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "quantity": self.quantity,
            "unit": self.unit,
            "decimal_places": self.decimal_places,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DisplayConfig":
        """Create from dictionary."""
        return cls(
            quantity=data.get("quantity", "User"),
            unit=data.get("unit", "user"),
            decimal_places=data.get("decimal_places", 0),
        )


# Convenience mapping for common channel types to suggested quantities
CHANNEL_TYPE_QUANTITIES = {
    "analog_input": ["Voltage", "Temperature", "Pressure", "Percentage", "User"],
    "can_input": ["User", "Temperature", "Pressure", "Velocity", "Angular velocity", "Voltage", "Current"],
    "number": ["User", "Percentage", "Temperature", "Pressure", "Velocity"],
    "table_2d": ["User", "Percentage", "Temperature", "Pressure"],
    "table_3d": ["User", "Percentage", "Temperature", "Pressure"],
    "timer": ["Time"],
    "power_output": ["Current", "Voltage", "Percentage"],
}


def get_suggested_quantities(channel_type: str) -> List[str]:
    """Get suggested quantities for a channel type."""
    suggested = CHANNEL_TYPE_QUANTITIES.get(channel_type, [])
    # Return suggested first, then all others
    all_quantities = get_quantity_names()
    result = list(suggested)
    for q in all_quantities:
        if q not in result:
            result.append(q)
    return result
