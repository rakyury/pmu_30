"""
PMU-30 Channel ID Constants

These constants define FIXED channel IDs that are IDENTICAL in firmware and configurator.
IDs are assigned based on channel type and hardware index, ensuring predictable mapping
without runtime translation.

IMPORTANT: These constants must match firmware/include/pmu_channel_ids.h
"""

from typing import Optional


# ============================================================================
# Channel ID Ranges
# ============================================================================

# Analog Inputs: 0-19 (direct ADC channel number)
CHID_ANALOG_BASE = 0
CHID_ANALOG_MAX = 19

# Digital Inputs: 50-69 (50 + pin number)
CHID_DIGITAL_BASE = 50
CHID_DIGITAL_MAX = 69

# Power Outputs (PROFET): 100-129 (100 + output number)
CHID_OUTPUT_BASE = 100
CHID_OUTPUT_MAX = 129

# H-Bridge Outputs: 130-133 (130 + bridge index)
CHID_HBRIDGE_BASE = 130
CHID_HBRIDGE_MAX = 133

# CAN RX Channels: 200-299 (200 + allocation index)
CHID_CAN_RX_BASE = 200
CHID_CAN_RX_MAX = 299

# CAN TX Channels: 300-399 (300 + allocation index)
CHID_CAN_TX_BASE = 300
CHID_CAN_TX_MAX = 399

# Logic Channels: 400-499 (400 + allocation index)
CHID_LOGIC_BASE = 400
CHID_LOGIC_MAX = 499

# Number (Math) Channels: 500-599 (500 + allocation index)
CHID_NUMBER_BASE = 500
CHID_NUMBER_MAX = 599

# Timer Channels: 600-699 (600 + allocation index)
CHID_TIMER_BASE = 600
CHID_TIMER_MAX = 699

# Filter Channels: 700-799 (700 + allocation index)
CHID_FILTER_BASE = 700
CHID_FILTER_MAX = 799

# Switch Channels: 800-899 (800 + allocation index)
CHID_SWITCH_BASE = 800
CHID_SWITCH_MAX = 899

# PID Controllers: 900-915 (900 + controller index)
CHID_PID_BASE = 900
CHID_PID_MAX = 915

# User-defined Channels: 1000+ (dynamically allocated)
CHID_USER_BASE = 1000


# ============================================================================
# Helper Functions
# ============================================================================

def analog_channel_id(pin: int) -> int:
    """Get channel ID for analog input pin (0-19)."""
    if not 0 <= pin <= 19:
        raise ValueError(f"Analog pin must be 0-19, got {pin}")
    return CHID_ANALOG_BASE + pin


def digital_channel_id(pin: int) -> int:
    """Get channel ID for digital input pin (0-19)."""
    if not 0 <= pin <= 19:
        raise ValueError(f"Digital pin must be 0-19, got {pin}")
    return CHID_DIGITAL_BASE + pin


def output_channel_id(pin: int) -> int:
    """Get channel ID for power output pin (0-29)."""
    if not 0 <= pin <= 29:
        raise ValueError(f"Output pin must be 0-29, got {pin}")
    return CHID_OUTPUT_BASE + pin


def hbridge_channel_id(idx: int) -> int:
    """Get channel ID for H-bridge (0-3)."""
    if not 0 <= idx <= 3:
        raise ValueError(f"H-bridge index must be 0-3, got {idx}")
    return CHID_HBRIDGE_BASE + idx


def can_rx_channel_id(idx: int) -> int:
    """Get channel ID for CAN RX channel."""
    return CHID_CAN_RX_BASE + idx


def can_tx_channel_id(idx: int) -> int:
    """Get channel ID for CAN TX channel."""
    return CHID_CAN_TX_BASE + idx


def logic_channel_id(idx: int) -> int:
    """Get channel ID for logic channel."""
    return CHID_LOGIC_BASE + idx


def number_channel_id(idx: int) -> int:
    """Get channel ID for number/math channel."""
    return CHID_NUMBER_BASE + idx


def timer_channel_id(idx: int) -> int:
    """Get channel ID for timer channel."""
    return CHID_TIMER_BASE + idx


def filter_channel_id(idx: int) -> int:
    """Get channel ID for filter channel."""
    return CHID_FILTER_BASE + idx


def switch_channel_id(idx: int) -> int:
    """Get channel ID for switch channel."""
    return CHID_SWITCH_BASE + idx


def pid_channel_id(idx: int) -> int:
    """Get channel ID for PID controller."""
    return CHID_PID_BASE + idx


# ============================================================================
# Type Detection
# ============================================================================

def is_analog_channel(channel_id: int) -> bool:
    """Check if channel ID belongs to analog inputs."""
    return CHID_ANALOG_BASE <= channel_id <= CHID_ANALOG_MAX


def is_digital_channel(channel_id: int) -> bool:
    """Check if channel ID belongs to digital inputs."""
    return CHID_DIGITAL_BASE <= channel_id <= CHID_DIGITAL_MAX


def is_output_channel(channel_id: int) -> bool:
    """Check if channel ID belongs to power outputs."""
    return CHID_OUTPUT_BASE <= channel_id <= CHID_OUTPUT_MAX


def is_hbridge_channel(channel_id: int) -> bool:
    """Check if channel ID belongs to H-bridges."""
    return CHID_HBRIDGE_BASE <= channel_id <= CHID_HBRIDGE_MAX


def is_can_rx_channel(channel_id: int) -> bool:
    """Check if channel ID belongs to CAN RX channels."""
    return CHID_CAN_RX_BASE <= channel_id <= CHID_CAN_RX_MAX


def is_can_tx_channel(channel_id: int) -> bool:
    """Check if channel ID belongs to CAN TX channels."""
    return CHID_CAN_TX_BASE <= channel_id <= CHID_CAN_TX_MAX


def is_logic_channel(channel_id: int) -> bool:
    """Check if channel ID belongs to logic channels."""
    return CHID_LOGIC_BASE <= channel_id <= CHID_LOGIC_MAX


def is_number_channel(channel_id: int) -> bool:
    """Check if channel ID belongs to number/math channels."""
    return CHID_NUMBER_BASE <= channel_id <= CHID_NUMBER_MAX


def is_timer_channel(channel_id: int) -> bool:
    """Check if channel ID belongs to timer channels."""
    return CHID_TIMER_BASE <= channel_id <= CHID_TIMER_MAX


def is_filter_channel(channel_id: int) -> bool:
    """Check if channel ID belongs to filter channels."""
    return CHID_FILTER_BASE <= channel_id <= CHID_FILTER_MAX


def is_switch_channel(channel_id: int) -> bool:
    """Check if channel ID belongs to switch channels."""
    return CHID_SWITCH_BASE <= channel_id <= CHID_SWITCH_MAX


def is_pid_channel(channel_id: int) -> bool:
    """Check if channel ID belongs to PID controllers."""
    return CHID_PID_BASE <= channel_id <= CHID_PID_MAX


def is_user_channel(channel_id: int) -> bool:
    """Check if channel ID is user-defined."""
    return channel_id >= CHID_USER_BASE


def is_hardware_channel(channel_id: int) -> bool:
    """Check if channel ID belongs to hardware (fixed) channels."""
    return (is_analog_channel(channel_id) or
            is_digital_channel(channel_id) or
            is_output_channel(channel_id) or
            is_hbridge_channel(channel_id))


# ============================================================================
# Channel ID to Hardware Index
# ============================================================================

def channel_id_to_pin(channel_id: int) -> Optional[int]:
    """
    Get hardware pin/index from channel ID.
    Returns None if channel is not hardware-based.
    """
    if is_analog_channel(channel_id):
        return channel_id - CHID_ANALOG_BASE
    elif is_digital_channel(channel_id):
        return channel_id - CHID_DIGITAL_BASE
    elif is_output_channel(channel_id):
        return channel_id - CHID_OUTPUT_BASE
    elif is_hbridge_channel(channel_id):
        return channel_id - CHID_HBRIDGE_BASE
    return None


def get_channel_type_name(channel_id: int) -> str:
    """Get human-readable channel type name from channel ID."""
    if is_analog_channel(channel_id):
        return "analog_input"
    elif is_digital_channel(channel_id):
        return "digital_input"
    elif is_output_channel(channel_id):
        return "power_output"
    elif is_hbridge_channel(channel_id):
        return "hbridge"
    elif is_can_rx_channel(channel_id):
        return "can_input"
    elif is_can_tx_channel(channel_id):
        return "can_output"
    elif is_logic_channel(channel_id):
        return "logic"
    elif is_number_channel(channel_id):
        return "number"
    elif is_timer_channel(channel_id):
        return "timer"
    elif is_filter_channel(channel_id):
        return "filter"
    elif is_switch_channel(channel_id):
        return "switch"
    elif is_pid_channel(channel_id):
        return "pid"
    elif is_user_channel(channel_id):
        return "user"
    return "unknown"
