"""
Channel Formatter - Display formatting for channel tree items

This module contains pure functions for formatting channel data for display
in the project tree. Extracted from project_tree.py for better maintainability.

All functions take channel_type and data dict, and return formatted strings.
"""

from typing import Dict, Any
from models.channel import ChannelType


def format_channel_details(channel_type: ChannelType, data: Dict[str, Any]) -> str:
    """Get display details string for channel.

    Returns a short string describing the channel's configuration,
    displayed in the "Details" column of the tree.
    """
    if channel_type == ChannelType.DIGITAL_INPUT:
        return _format_digital_input_details(data)
    elif channel_type == ChannelType.ANALOG_INPUT:
        return _format_analog_input_details(data)
    elif channel_type == ChannelType.POWER_OUTPUT:
        return _format_power_output_details(data)
    elif channel_type == ChannelType.LOGIC:
        return _format_logic_details(data)
    elif channel_type == ChannelType.NUMBER:
        return _format_number_details(data)
    elif channel_type == ChannelType.TIMER:
        return _format_timer_details(data)
    elif channel_type == ChannelType.SWITCH:
        return _format_switch_details(data)
    elif channel_type in (ChannelType.TABLE_2D, ChannelType.TABLE_3D):
        return _format_table_details(data)
    elif channel_type == ChannelType.CAN_RX:
        return _format_can_rx_details(data)
    elif channel_type == ChannelType.CAN_TX:
        return _format_can_tx_details(data)
    elif channel_type == ChannelType.FILTER:
        return _format_filter_details(data)
    elif channel_type == ChannelType.LUA_SCRIPT:
        return _format_lua_details(data)
    elif channel_type == ChannelType.PID:
        return _format_pid_details(data)
    elif channel_type == ChannelType.HBRIDGE:
        return _format_hbridge_details(data)
    elif channel_type == ChannelType.BLINKMARINE_KEYPAD:
        return _format_blinkmarine_details(data)
    elif channel_type == ChannelType.HANDLER:
        return _format_handler_details(data)
    return ""


def format_channel_source(channel_type: ChannelType, data: Dict[str, Any]) -> str:
    """Get source/control channel info for display in Source column."""
    if channel_type == ChannelType.POWER_OUTPUT:
        source = data.get('source_channel')
        if source:
            return f"Channel #{source}" if isinstance(source, int) else str(source)
        return "Manual"

    elif channel_type == ChannelType.HBRIDGE:
        dir_src = data.get('direction_source')
        speed_src = data.get('speed_source')
        parts = []
        if dir_src:
            parts.append(f"Dir: #{dir_src}" if isinstance(dir_src, int) else f"Dir: {dir_src}")
        if speed_src:
            parts.append(f"Spd: #{speed_src}" if isinstance(speed_src, int) else f"Spd: {speed_src}")
        return ", ".join(parts) if parts else "Manual"

    elif channel_type == ChannelType.LOGIC:
        inputs = data.get('input_channels', [])
        if inputs:
            if len(inputs) <= 2:
                src_list = [f"#{i}" if isinstance(i, int) else str(i) for i in inputs]
                return ", ".join(src_list)
            return f"{len(inputs)} inputs"
        return ""

    elif channel_type == ChannelType.NUMBER:
        op = data.get('operation', 'constant')
        if op == 'constant':
            return ""
        inputs = data.get('input_channels', [])
        if inputs:
            if len(inputs) <= 2:
                src_list = [f"#{i}" if isinstance(i, int) else str(i) for i in inputs]
                return ", ".join(src_list)
            return f"{len(inputs)} inputs"
        return ""

    elif channel_type == ChannelType.FILTER:
        input_ch = data.get('input_channel')
        if input_ch:
            return f"#{input_ch}" if isinstance(input_ch, int) else str(input_ch)
        return ""

    elif channel_type == ChannelType.PID:
        setpoint = data.get('setpoint_source')
        input_ch = data.get('input_source')
        parts = []
        if setpoint:
            parts.append(f"SP: #{setpoint}" if isinstance(setpoint, int) else f"SP: {setpoint}")
        if input_ch:
            parts.append(f"PV: #{input_ch}" if isinstance(input_ch, int) else f"PV: {input_ch}")
        return ", ".join(parts) if parts else ""

    elif channel_type == ChannelType.TIMER:
        if data.get('auto_start', False):
            return "Auto-start on boot"
        start_ch = data.get('start_channel')
        if start_ch:
            return f"Start: #{start_ch}" if isinstance(start_ch, int) else f"Start: {start_ch}"
        return ""

    elif channel_type == ChannelType.SWITCH:
        ctrl = data.get('control_channel')
        if ctrl:
            return f"#{ctrl}" if isinstance(ctrl, int) else str(ctrl)
        return ""

    elif channel_type == ChannelType.TABLE_2D:
        x_src = data.get('x_source')
        if x_src:
            return f"X: #{x_src}" if isinstance(x_src, int) else f"X: {x_src}"
        return ""

    elif channel_type == ChannelType.TABLE_3D:
        x_src = data.get('x_source')
        y_src = data.get('y_source')
        parts = []
        if x_src:
            parts.append(f"X: #{x_src}" if isinstance(x_src, int) else f"X: {x_src}")
        if y_src:
            parts.append(f"Y: #{y_src}" if isinstance(y_src, int) else f"Y: {y_src}")
        return ", ".join(parts) if parts else ""

    elif channel_type == ChannelType.CAN_TX:
        signals = data.get('signals', [])
        if signals:
            sources = []
            for sig in signals[:2]:
                src = sig.get('source_channel')
                if src:
                    sources.append(f"#{src}" if isinstance(src, int) else str(src))
            if len(signals) > 2:
                return f"{', '.join(sources)}, +{len(signals) - 2}"
            return ", ".join(sources)
        return ""

    elif channel_type == ChannelType.CAN_RX:
        msg_ref = data.get('message_ref', '')
        return msg_ref if msg_ref else ""

    elif channel_type == ChannelType.LUA_SCRIPT:
        trigger_ch = data.get('trigger_channel')
        if trigger_ch:
            return f"#{trigger_ch}" if isinstance(trigger_ch, int) else str(trigger_ch)
        return data.get('trigger_type', 'manual').capitalize()

    elif channel_type == ChannelType.HANDLER:
        source = data.get('source_channel', '')
        condition = data.get('condition_channel', '')
        parts = []
        if source:
            parts.append(f"Src: {source}")
        if condition:
            parts.append(f"If: {condition}")
        return ", ".join(parts) if parts else ""

    return ""


def format_channel_tooltip(channel_type: ChannelType, data: Dict[str, Any]) -> str:
    """Get detailed tooltip for channel (HTML formatted)."""
    lines = []
    channel_name = data.get("channel_name", "") or data.get("name", "") or data.get("id", "") or "unnamed"
    channel_id = data.get("channel_id", "")

    lines.append(f"<b>{channel_name}</b>")
    if channel_id:
        lines.append(f"Channel ID: #{channel_id}")
    lines.append(f"Type: {channel_type.value.replace('_', ' ').title()}")
    lines.append("")

    # Type-specific tooltip content
    if channel_type == ChannelType.DIGITAL_INPUT:
        lines.extend(_tooltip_digital_input(data))
    elif channel_type == ChannelType.ANALOG_INPUT:
        lines.extend(_tooltip_analog_input(data))
    elif channel_type == ChannelType.POWER_OUTPUT:
        lines.extend(_tooltip_power_output(data))
    elif channel_type == ChannelType.LOGIC:
        lines.extend(_tooltip_logic(data))
    elif channel_type == ChannelType.NUMBER:
        lines.extend(_tooltip_number(data))
    elif channel_type == ChannelType.TIMER:
        lines.extend(_tooltip_timer(data))
    elif channel_type == ChannelType.PID:
        lines.extend(_tooltip_pid(data))
    elif channel_type == ChannelType.HBRIDGE:
        lines.extend(_tooltip_hbridge(data))
    elif channel_type == ChannelType.CAN_RX:
        lines.extend(_tooltip_can_rx(data))
    elif channel_type == ChannelType.CAN_TX:
        lines.extend(_tooltip_can_tx(data))
    elif channel_type == ChannelType.LUA_SCRIPT:
        lines.extend(_tooltip_lua(data))
    elif channel_type == ChannelType.BLINKMARINE_KEYPAD:
        lines.extend(_tooltip_blinkmarine(data))
    elif channel_type == ChannelType.HANDLER:
        lines.extend(_tooltip_handler(data))

    return "<br>".join(lines)


# ========== Detail formatters (private) ==========

def _format_digital_input_details(data: Dict[str, Any]) -> str:
    subtype = data.get("subtype", "switch_active_low")

    # Special handling for keypad buttons
    if subtype == "keypad_button":
        keypad_id = data.get("keypad_id", "")
        btn_idx = data.get("button_index", 0)
        btn_mode = data.get("button_mode", "momentary")
        mode_display = {
            "momentary": "Momentary",
            "toggle": "Toggle",
            "latching": "Latching",
            "direct": "Direct"
        }.get(btn_mode, btn_mode.title())
        return f"Keypad Button {btn_idx + 1} ({mode_display})"

    pin = data.get("input_pin", 0)
    subtype_display = {
        "switch_active_low": "Switch Active Low",
        "switch_active_high": "Switch Active High",
        "frequency": "Frequency",
        "rpm": "RPM",
        "flex_fuel": "Flex Fuel",
        "beacon": "Beacon",
        "puls_oil_sensor": "PULS Oil"
    }.get(subtype, subtype.replace("_", " ").title())
    return f"D{pin + 1} {subtype_display}"


def _format_analog_input_details(data: Dict[str, Any]) -> str:
    pin = data.get("input_pin", 0)
    subtype = data.get("subtype", "linear")
    pullup = data.get("pullup_option", "1m_down")

    subtype_display = {
        "switch_active_low": "Switch Low",
        "switch_active_high": "Switch High",
        "rotary_switch": "Rotary",
        "linear": "Linear",
        "calibrated": "Calibrated"
    }.get(subtype, subtype)

    pullup_display = ""
    if pullup and pullup != "none" and pullup != "1m_down":
        pullup_map = {
            "10k_up": "10K↑",
            "10k_down": "10K↓",
            "100k_up": "100K↑",
            "100k_down": "100K↓"
        }
        pullup_display = f" {pullup_map.get(pullup, '')}"

    return f"A{pin + 1} {subtype_display}{pullup_display}"


def _format_power_output_details(data: Dict[str, Any]) -> str:
    parts = []

    # Pins
    pins = data.get('pins', [data.get('channel', 0)])
    if isinstance(pins, list) and pins:
        pins_str = ", ".join([f"O{p + 1}" for p in pins])
    else:
        pins_str = f"O{data.get('channel', 0) + 1}"
    parts.append(pins_str)

    # Current limit
    current_limit = data.get('current_limit_a', 0) or data.get('current_limit', 0)
    if current_limit:
        parts.append(f"{current_limit}A")

    # Retry count
    retry_count = data.get('retry_count', 0)
    if retry_count:
        parts.append(f"x{retry_count}")

    # Control source
    source_channel = data.get('source_channel')
    if source_channel:
        if isinstance(source_channel, int):
            parts.append(f"Ch#{source_channel}")
        else:
            parts.append(str(source_channel))

    # PWM indicator
    pwm_enabled = data.get('pwm_enabled', False) or data.get('pwm', {}).get('enabled', False)
    if pwm_enabled:
        freq = data.get('pwm_frequency_hz', 0) or data.get('pwm', {}).get('frequency', 0)
        duty = data.get('pwm', {}).get('duty_value', 100)
        parts.append(f"PWM {freq}Hz {duty}%")

    return " ".join(parts)


def _format_logic_details(data: Dict[str, Any]) -> str:
    op = data.get("operation", "and").upper()
    delay_on = data.get("delay_on_ms", 0)
    delay_off = data.get("delay_off_ms", 0)
    if delay_on or delay_off:
        return f"{op} (+{delay_on}/-{delay_off}ms)"
    return op


def _format_number_details(data: Dict[str, Any]) -> str:
    op = data.get("operation", "constant")
    if op == "constant":
        val = data.get("constant_value", 0)
        unit = data.get("unit", "")
        return f"{val} {unit}".strip()
    return op


def _format_timer_details(data: Dict[str, Any]) -> str:
    mode = data.get("mode", "count_up")
    h = data.get("limit_hours", 0)
    m = data.get("limit_minutes", 0)
    s = data.get("limit_seconds", 0)
    auto_start = " [AUTO]" if data.get("auto_start", False) else ""
    return f"{mode} ({h}:{m:02d}:{s:02d}){auto_start}"


def _format_switch_details(data: Dict[str, Any]) -> str:
    states = data.get("states", [])
    return f"{len(states)} states"


def _format_table_details(data: Dict[str, Any]) -> str:
    points = data.get("table_data", [])
    return f"{len(points)} points"


def _format_can_rx_details(data: Dict[str, Any]) -> str:
    msg_ref = data.get("message_ref", "")
    data_format = data.get("data_format", "16bit")
    if hasattr(data_format, 'value'):
        data_format = data_format.value
    byte_order = data.get("byte_order", "little_endian")
    order_short = "LE" if byte_order == "little_endian" else "BE"
    format_short = {"8bit": "8", "16bit": "16", "32bit": "32", "custom": "C"}.get(data_format, "?")
    return f"{msg_ref} [{format_short}{order_short}]"


def _format_can_tx_details(data: Dict[str, Any]) -> str:
    msg_id = data.get("message_id", 0)
    can_bus = data.get("can_bus", 1)
    tx_mode = data.get("transmit_mode", "cycle")
    if tx_mode == "cycle":
        freq = data.get("frequency_hz", 10)
        return f"CAN{can_bus} 0x{msg_id:X} @ {freq}Hz"
    return f"CAN{can_bus} 0x{msg_id:X} (Triggered)"


def _format_filter_details(data: Dict[str, Any]) -> str:
    filter_type = data.get("filter_type", "moving_avg")
    return filter_type.replace("_", " ").title()


def _format_lua_details(data: Dict[str, Any]) -> str:
    trigger = data.get("trigger_type", "manual")
    return f"{trigger}"


def _format_pid_details(data: Dict[str, Any]) -> str:
    kp = data.get("kp", 1.0)
    ki = data.get("ki", 0.0)
    kd = data.get("kd", 0.0)
    return f"P:{kp:.2f} I:{ki:.2f} D:{kd:.2f}"


def _format_hbridge_details(data: Dict[str, Any]) -> str:
    bridge = data.get("bridge_number", 0)
    mode = data.get("mode", "coast")
    if hasattr(mode, 'value'):
        mode = mode.value
    preset = data.get("motor_preset", "custom")
    if hasattr(preset, 'value'):
        preset = preset.value
    return f"HB{bridge + 1} {mode} ({preset})"


def _format_blinkmarine_details(data: Dict[str, Any]) -> str:
    keypad_type = data.get("keypad_type", "2x6")
    rx_id = data.get("rx_base_id", 0x100)
    can_bus = data.get("can_bus", 1)
    button_count = 12 if keypad_type == "2x6" else 16
    return f"{keypad_type} ({button_count} btns) CAN{can_bus} RX:0x{rx_id:03X}"


def _format_handler_details(data: Dict[str, Any]) -> str:
    event = data.get("event", "channel_on")
    action = data.get("action", "write_channel")
    event_display = {
        "channel_on": "ON",
        "channel_off": "OFF",
        "channel_fault": "FAULT",
        "channel_cleared": "CLEARED",
        "threshold_high": "THR↑",
        "threshold_low": "THR↓",
        "system_undervolt": "UNDERVOLT",
        "system_overvolt": "OVERVOLT",
        "system_overtemp": "OVERTEMP",
    }.get(event, event)
    action_display = {
        "write_channel": "→CH",
        "send_can": "→CAN",
        "send_lin": "→LIN",
        "run_lua": "→LUA",
        "set_output": "→OUT",
    }.get(action, action)
    return f"{event_display} {action_display}"


# ========== Tooltip helpers (private) ==========

def _tooltip_digital_input(data: Dict[str, Any]) -> list:
    lines = []
    lines.append(f"<b>Pin:</b> D{data.get('input_pin', 0) + 1}")
    lines.append(f"<b>Subtype:</b> {data.get('subtype', 'switch_active_low')}")
    if data.get('invert', False):
        lines.append("<b>Inverted:</b> Yes")
    return lines


def _tooltip_analog_input(data: Dict[str, Any]) -> list:
    lines = []
    lines.append(f"<b>Pin:</b> A{data.get('input_pin', 0) + 1}")
    lines.append(f"<b>Subtype:</b> {data.get('subtype', 'linear')}")
    pullup = data.get('pullup_option', 'none')
    if pullup and pullup != 'none':
        lines.append(f"<b>Pull:</b> {pullup}")
    min_v = data.get('min_voltage', 0)
    max_v = data.get('max_voltage', 5.0)
    min_val = data.get('min_value', 0)
    max_val = data.get('max_value', 100)
    lines.append(f"<b>Range:</b> {min_v}V-{max_v}V -> {min_val}-{max_val}")
    return lines


def _tooltip_power_output(data: Dict[str, Any]) -> list:
    lines = []
    pins = data.get('pins', [data.get('channel', 0)])
    if isinstance(pins, list):
        pins_str = ", ".join([f"O{p + 1}" for p in pins])
    else:
        pins_str = f"O{pins + 1}"
    lines.append(f"<b>Pins:</b> {pins_str}")
    lines.append(f"<b>Current Limit:</b> {data.get('current_limit_a', 0)}A")
    lines.append(f"<b>Retry:</b> {data.get('retry_count', 0)} times")
    lines.append(f"<b>Retry Delay:</b> {data.get('retry_delay_ms', 0)}ms")
    lines.append(f"<b>Inrush Time:</b> {data.get('inrush_time_ms', 0)}ms")
    if data.get('pwm_enabled') or data.get('pwm', {}).get('enabled'):
        freq = data.get('pwm_frequency_hz', 0) or data.get('pwm', {}).get('frequency', 0)
        lines.append(f"<b>PWM:</b> {freq}Hz")
    return lines


def _tooltip_logic(data: Dict[str, Any]) -> list:
    lines = []
    lines.append(f"<b>Operation:</b> {data.get('operation', 'and').upper()}")
    lines.append(f"<b>Delay ON:</b> {data.get('delay_on_ms', 0)}ms")
    lines.append(f"<b>Delay OFF:</b> {data.get('delay_off_ms', 0)}ms")
    inputs = data.get('input_channels', [])
    if inputs:
        lines.append(f"<b>Inputs:</b> {len(inputs)} channels")
    return lines


def _tooltip_number(data: Dict[str, Any]) -> list:
    lines = []
    op = data.get('operation', 'constant')
    lines.append(f"<b>Operation:</b> {op}")
    if op == 'constant':
        lines.append(f"<b>Value:</b> {data.get('constant_value', 0)} {data.get('unit', '')}")
    lines.append(f"<b>Min:</b> {data.get('min_value', 0)}")
    lines.append(f"<b>Max:</b> {data.get('max_value', 100)}")
    return lines


def _tooltip_timer(data: Dict[str, Any]) -> list:
    lines = []
    lines.append(f"<b>Mode:</b> {data.get('mode', 'count_up')}")
    h = data.get('limit_hours', 0)
    m = data.get('limit_minutes', 0)
    s = data.get('limit_seconds', 0)
    lines.append(f"<b>Limit:</b> {h}:{m:02d}:{s:02d}")
    if data.get('auto_start', False):
        lines.append("<b>Auto-start:</b> Yes (starts on boot)")
    else:
        start_ch = data.get('start_channel', '')
        if start_ch:
            lines.append(f"<b>Start Channel:</b> {start_ch}")
    stop_ch = data.get('stop_channel', '')
    if stop_ch:
        lines.append(f"<b>Stop Channel:</b> {stop_ch}")
    return lines


def _tooltip_pid(data: Dict[str, Any]) -> list:
    lines = []
    lines.append(f"<b>Kp:</b> {data.get('kp', 1.0)}")
    lines.append(f"<b>Ki:</b> {data.get('ki', 0.0)}")
    lines.append(f"<b>Kd:</b> {data.get('kd', 0.0)}")
    lines.append(f"<b>Output Min:</b> {data.get('output_min', 0)}")
    lines.append(f"<b>Output Max:</b> {data.get('output_max', 1000)}")
    lines.append(f"<b>Sample Time:</b> {data.get('sample_time_ms', 100)}ms")
    return lines


def _tooltip_hbridge(data: Dict[str, Any]) -> list:
    lines = []
    lines.append(f"<b>Bridge:</b> HB{data.get('bridge_number', 0) + 1}")
    mode = data.get('mode', 'coast')
    if hasattr(mode, 'value'):
        mode = mode.value
    lines.append(f"<b>Mode:</b> {mode}")
    preset = data.get('motor_preset', 'custom')
    if hasattr(preset, 'value'):
        preset = preset.value
    lines.append(f"<b>Preset:</b> {preset}")
    return lines


def _tooltip_can_rx(data: Dict[str, Any]) -> list:
    lines = []
    lines.append(f"<b>Message:</b> {data.get('message_ref', '')}")
    data_format = data.get('data_format', '16bit')
    if hasattr(data_format, 'value'):
        data_format = data_format.value
    lines.append(f"<b>Format:</b> {data_format}")
    lines.append(f"<b>Byte Order:</b> {data.get('byte_order', 'little_endian')}")
    lines.append(f"<b>Start Bit:</b> {data.get('start_bit', 0)}")
    return lines


def _tooltip_can_tx(data: Dict[str, Any]) -> list:
    lines = []
    lines.append(f"<b>Message ID:</b> 0x{data.get('message_id', 0):X}")
    lines.append(f"<b>CAN Bus:</b> {data.get('can_bus', 1)}")
    lines.append(f"<b>Mode:</b> {data.get('transmit_mode', 'cycle')}")
    if data.get('transmit_mode') == 'cycle':
        lines.append(f"<b>Frequency:</b> {data.get('frequency_hz', 10)}Hz")
    return lines


def _tooltip_lua(data: Dict[str, Any]) -> list:
    lines = []
    lines.append(f"<b>Trigger:</b> {data.get('trigger_type', 'manual')}")
    code = data.get('code', '')
    if code:
        lines.append(f"<b>Code Lines:</b> {len(code.splitlines())}")
    return lines


def _tooltip_blinkmarine(data: Dict[str, Any]) -> list:
    lines = []
    lines.append(f"<b>Type:</b> {data.get('keypad_type', '2x6')}")
    lines.append(f"<b>CAN Bus:</b> {data.get('can_bus', 1)}")
    lines.append(f"<b>RX Base ID:</b> 0x{data.get('rx_base_id', 0x100):03X}")
    lines.append(f"<b>TX Base ID:</b> 0x{data.get('tx_base_id', 0x200):03X}")
    buttons = data.get('buttons', [])
    configured = sum(1 for b in buttons if b.get('channel_id'))
    lines.append(f"<b>Configured Buttons:</b> {configured}/{len(buttons)}")
    return lines


def _tooltip_handler(data: Dict[str, Any]) -> list:
    lines = []
    event = data.get('event', 'channel_on')
    action = data.get('action', 'write_channel')
    lines.append(f"<b>Event:</b> {event.replace('_', ' ').title()}")
    source = data.get('source_channel', '')
    if source:
        lines.append(f"<b>Source Channel:</b> {source}")
    condition = data.get('condition_channel', '')
    if condition:
        lines.append(f"<b>Condition:</b> {condition}")
    lines.append(f"<b>Action:</b> {action.replace('_', ' ').title()}")
    target = data.get('target_channel', '')
    if target:
        lines.append(f"<b>Target:</b> {target}")
    if action == 'run_lua':
        lua_func = data.get('lua_function', '')
        if lua_func:
            lines.append(f"<b>Lua Function:</b> {lua_func}")
    return lines
