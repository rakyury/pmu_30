"""
Advanced Channels - Lua, PID, Handler, Wiper, Blinker channel types

This module contains advanced channel classes for complex functionality.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any

from .enums import (
    ChannelType,
    LuaTriggerType,
    LuaPriority,
    EventType,
    ActionType,
    WiperMode,
    BlinkerMode,
)
from .base import ChannelBase


@dataclass
class LuaScriptChannel(ChannelBase):
    """Lua script channel for custom logic"""
    description: str = ""
    script: str = ""
    trigger_type: LuaTriggerType = LuaTriggerType.MANUAL
    trigger_period_ms: int = 100
    trigger_channel: str = ""
    max_execution_ms: int = 50
    priority: LuaPriority = LuaPriority.NORMAL

    def __post_init__(self):
        self.channel_type = ChannelType.LUA_SCRIPT

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "description": self.description,
            "script": self.script,
            "trigger_type": self.trigger_type.value if isinstance(self.trigger_type, LuaTriggerType) else self.trigger_type,
            "trigger_period_ms": self.trigger_period_ms,
            "trigger_channel": self.trigger_channel,
            "max_execution_ms": self.max_execution_ms,
            "priority": self.priority.value if isinstance(self.priority, LuaPriority) else self.priority,
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LuaScriptChannel':
        # Parse trigger_type
        trigger_str = data.get("trigger_type", "manual")
        try:
            trigger_type = LuaTriggerType(trigger_str)
        except ValueError:
            trigger_type = LuaTriggerType.MANUAL

        # Parse priority
        priority_str = data.get("priority", "normal")
        try:
            priority = LuaPriority(priority_str)
        except ValueError:
            priority = LuaPriority.NORMAL

        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.LUA_SCRIPT,
            channel_id=data.get("channel_id", 0),
            description=data.get("description", ""),
            script=data.get("script", ""),
            trigger_type=trigger_type,
            trigger_period_ms=data.get("trigger_period_ms", 100),
            trigger_channel=data.get("trigger_channel", ""),
            max_execution_ms=data.get("max_execution_ms", 50),
            priority=priority,
        )

    def get_input_channels(self) -> List[str]:
        channels = []
        if self.trigger_channel:
            channels.append(self.trigger_channel)
        return channels

    def validate(self) -> List[str]:
        errors = super().validate()
        if not self.script.strip():
            errors.append("Script cannot be empty")
        if self.trigger_type == LuaTriggerType.PERIODIC:
            if self.trigger_period_ms < 10:
                errors.append("Trigger period must be at least 10ms")
        if self.trigger_type in [LuaTriggerType.ON_INPUT_CHANGE, LuaTriggerType.ON_VIRTUAL_CHANGE]:
            if not self.trigger_channel:
                errors.append("Trigger channel is required for this trigger type")
        if self.max_execution_ms < 1:
            errors.append("Max execution time must be at least 1ms")
        return errors


@dataclass
class PIDChannel(ChannelBase):
    """PID controller channel"""
    # Input/Output channels
    setpoint_channel: str = ""           # Channel providing setpoint value
    process_channel: str = ""            # Channel providing process variable (feedback)
    output_channel: str = ""             # Channel to write output to (optional, for driving outputs)

    # PID parameters
    kp: float = 1.0                      # Proportional gain
    ki: float = 0.0                      # Integral gain
    kd: float = 0.0                      # Derivative gain

    # Setpoint (used if setpoint_channel is empty)
    setpoint_value: float = 0.0

    # Output limits
    output_min: float = 0.0
    output_max: float = 100.0

    # Advanced settings
    sample_time_ms: int = 100            # PID loop execution period
    anti_windup: bool = True             # Prevent integral windup
    derivative_filter: bool = True       # Apply low-pass filter to derivative term
    derivative_filter_coeff: float = 0.1 # Filter coefficient (0-1)

    # Control options
    reversed: bool = False               # Reverse acting controller

    def __post_init__(self):
        self.channel_type = ChannelType.PID

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "setpoint_channel": self.setpoint_channel,
            "process_channel": self.process_channel,
            "output_channel": self.output_channel,
            "kp": self.kp,
            "ki": self.ki,
            "kd": self.kd,
            "setpoint_value": self.setpoint_value,
            "output_min": self.output_min,
            "output_max": self.output_max,
            "sample_time_ms": self.sample_time_ms,
            "anti_windup": self.anti_windup,
            "derivative_filter": self.derivative_filter,
            "derivative_filter_coeff": self.derivative_filter_coeff,
            "reversed": self.reversed,
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PIDChannel':
        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.PID,
            channel_id=data.get("channel_id", 0),
            setpoint_channel=data.get("setpoint_channel", ""),
            process_channel=data.get("process_channel", ""),
            output_channel=data.get("output_channel", ""),
            kp=data.get("kp", 1.0),
            ki=data.get("ki", 0.0),
            kd=data.get("kd", 0.0),
            setpoint_value=data.get("setpoint_value", 0.0),
            output_min=data.get("output_min", 0.0),
            output_max=data.get("output_max", 100.0),
            sample_time_ms=data.get("sample_time_ms", 100),
            anti_windup=data.get("anti_windup", True),
            derivative_filter=data.get("derivative_filter", True),
            derivative_filter_coeff=data.get("derivative_filter_coeff", 0.1),
            reversed=data.get("reversed", False),
        )

    def get_input_channels(self) -> List[str]:
        channels = []
        if self.setpoint_channel:
            channels.append(self.setpoint_channel)
        if self.process_channel:
            channels.append(self.process_channel)
        return channels

    def validate(self) -> List[str]:
        errors = super().validate()
        if not self.process_channel:
            errors.append("Process variable channel is required")
        if self.sample_time_ms < 1:
            errors.append("Sample time must be at least 1ms")
        if self.output_min >= self.output_max:
            errors.append("Output min must be less than output max")
        if self.derivative_filter_coeff < 0 or self.derivative_filter_coeff > 1:
            errors.append("Derivative filter coefficient must be between 0 and 1")
        return errors


@dataclass
class HandlerChannel(ChannelBase):
    """Event handler channel - reacts to system events and executes actions

    Features:
    - Triggers on channel state changes, faults, thresholds, system events
    - Can write to virtual channels, send CAN/LIN messages, run Lua, set outputs
    - Optional condition channel for conditional execution
    - One action per handler (multiple handlers can react to same event)
    """
    # Event configuration
    event: EventType = EventType.CHANNEL_ON
    source_channel: str = ""            # Channel that triggers the event

    # Threshold (for THRESHOLD_HIGH/LOW events)
    threshold_value: float = 0.0

    # Condition (optional - handler fires only if condition is true)
    condition_channel: str = ""

    # Action configuration
    action: ActionType = ActionType.WRITE_CHANNEL
    target_channel: str = ""            # Target for WRITE_CHANNEL/SET_OUTPUT
    value: float = 0.0                  # Value to write

    # CAN/LIN message (for SEND_CAN/SEND_LIN actions)
    can_bus: int = 1
    message_id: int = 0
    message_data: List[int] = field(default_factory=lambda: [0] * 8)

    # Lua function (for RUN_LUA action)
    lua_function: str = ""

    # Handler options
    description: str = ""

    def __post_init__(self):
        self.channel_type = ChannelType.HANDLER

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "event": self.event.value if isinstance(self.event, EventType) else self.event,
            "source_channel": self.source_channel,
            "threshold_value": self.threshold_value,
            "condition_channel": self.condition_channel,
            "action": self.action.value if isinstance(self.action, ActionType) else self.action,
            "target_channel": self.target_channel,
            "value": self.value,
            "can_bus": self.can_bus,
            "message_id": self.message_id,
            "message_data": self.message_data,
            "lua_function": self.lua_function,
            "description": self.description,
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HandlerChannel':
        # Parse event type
        event_str = data.get("event", "channel_on")
        try:
            event = EventType(event_str)
        except ValueError:
            event = EventType.CHANNEL_ON

        # Parse action type
        action_str = data.get("action", "write_channel")
        try:
            action = ActionType(action_str)
        except ValueError:
            action = ActionType.WRITE_CHANNEL

        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.HANDLER,
            channel_id=data.get("channel_id", 0),
            event=event,
            source_channel=data.get("source_channel", ""),
            threshold_value=data.get("threshold_value", 0.0),
            condition_channel=data.get("condition_channel", ""),
            action=action,
            target_channel=data.get("target_channel", ""),
            value=data.get("value", 0.0),
            can_bus=data.get("can_bus", 1),
            message_id=data.get("message_id", 0),
            message_data=data.get("message_data", [0] * 8),
            lua_function=data.get("lua_function", ""),
            description=data.get("description", ""),
        )

    def get_input_channels(self) -> List[str]:
        channels = []
        if self.source_channel:
            channels.append(self.source_channel)
        if self.condition_channel:
            channels.append(self.condition_channel)
        return channels

    def validate(self) -> List[str]:
        errors = super().validate()

        # Source channel required for channel events
        if self.event in [EventType.CHANNEL_ON, EventType.CHANNEL_OFF,
                          EventType.CHANNEL_FAULT, EventType.CHANNEL_CLEARED,
                          EventType.THRESHOLD_HIGH, EventType.THRESHOLD_LOW]:
            if not self.source_channel:
                errors.append("Source channel is required for this event type")

        # Action-specific validation
        if self.action == ActionType.WRITE_CHANNEL:
            if not self.target_channel:
                errors.append("Target channel is required for WRITE_CHANNEL action")
        elif self.action == ActionType.SET_OUTPUT:
            if not self.target_channel:
                errors.append("Target output is required for SET_OUTPUT action")
        elif self.action == ActionType.RUN_LUA:
            if not self.lua_function:
                errors.append("Lua function name is required for RUN_LUA action")
        elif self.action in [ActionType.SEND_CAN, ActionType.SEND_LIN]:
            if self.message_id < 0:
                errors.append("Message ID must be non-negative")
            if self.can_bus < 1 or self.can_bus > 4:
                errors.append("CAN/LIN bus must be between 1 and 4")

        return errors


@dataclass
class WiperChannel(ChannelBase):
    """Wiper control module channel

    Features:
    - Multi-speed control (slow/fast)
    - Intermittent mode with adjustable delay
    - Wash and wipe coordination
    - Park position control
    - Rain sensor input support
    """
    # Output assignment
    hbridge_number: int = 0                    # H-Bridge for wiper motor (0-3)
    output_speed: str = ""                     # Speed control channel (optional for relay-based)

    # Control inputs
    control_channel: str = ""                  # Main wiper switch input (0-4: off/int/slow/fast/wash)
    wash_channel: str = ""                     # Wash button input
    rain_sensor_channel: str = ""              # Rain sensor input (optional)

    # Park detection
    park_channel: str = ""                     # Park position sensor input
    park_position: int = 50                    # Park position value (0-100)
    park_timeout_ms: int = 5000                # Max time to reach park

    # Speed settings
    slow_pwm: int = 180                        # PWM value for slow speed (0-255)
    fast_pwm: int = 255                        # PWM value for fast speed

    # Intermittent settings
    intermittent_min_ms: int = 1000            # Minimum intermittent delay
    intermittent_max_ms: int = 10000           # Maximum intermittent delay
    intermittent_delay_channel: str = ""       # Channel for variable delay (0-100%)

    # Wash settings
    wash_wipe_count: int = 3                   # Wipes after wash release
    wash_wipe_delay_ms: int = 500              # Delay after wash before wipe

    # Auto wipe on ignition
    auto_wipe_on_start: bool = False           # Single wipe on ignition

    def __post_init__(self):
        self.channel_type = ChannelType.WIPER

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "hbridge_number": self.hbridge_number,
            "output_speed": self.output_speed,
            "control_channel": self.control_channel,
            "wash_channel": self.wash_channel,
            "rain_sensor_channel": self.rain_sensor_channel,
            "park_channel": self.park_channel,
            "park_position": self.park_position,
            "park_timeout_ms": self.park_timeout_ms,
            "slow_pwm": self.slow_pwm,
            "fast_pwm": self.fast_pwm,
            "intermittent_min_ms": self.intermittent_min_ms,
            "intermittent_max_ms": self.intermittent_max_ms,
            "intermittent_delay_channel": self.intermittent_delay_channel,
            "wash_wipe_count": self.wash_wipe_count,
            "wash_wipe_delay_ms": self.wash_wipe_delay_ms,
            "auto_wipe_on_start": self.auto_wipe_on_start,
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WiperChannel':
        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.WIPER,
            channel_id=data.get("channel_id", 0),
            hbridge_number=data.get("hbridge_number", 0),
            output_speed=data.get("output_speed", ""),
            control_channel=data.get("control_channel", ""),
            wash_channel=data.get("wash_channel", ""),
            rain_sensor_channel=data.get("rain_sensor_channel", ""),
            park_channel=data.get("park_channel", ""),
            park_position=data.get("park_position", 50),
            park_timeout_ms=data.get("park_timeout_ms", 5000),
            slow_pwm=data.get("slow_pwm", 180),
            fast_pwm=data.get("fast_pwm", 255),
            intermittent_min_ms=data.get("intermittent_min_ms", 1000),
            intermittent_max_ms=data.get("intermittent_max_ms", 10000),
            intermittent_delay_channel=data.get("intermittent_delay_channel", ""),
            wash_wipe_count=data.get("wash_wipe_count", 3),
            wash_wipe_delay_ms=data.get("wash_wipe_delay_ms", 500),
            auto_wipe_on_start=data.get("auto_wipe_on_start", False),
        )

    def get_input_channels(self) -> List[str]:
        channels = []
        if self.control_channel:
            channels.append(self.control_channel)
        if self.wash_channel:
            channels.append(self.wash_channel)
        if self.rain_sensor_channel:
            channels.append(self.rain_sensor_channel)
        if self.park_channel:
            channels.append(self.park_channel)
        if self.intermittent_delay_channel:
            channels.append(self.intermittent_delay_channel)
        return channels

    def validate(self) -> List[str]:
        errors = super().validate()
        if not 0 <= self.hbridge_number <= 3:
            errors.append("H-Bridge number must be between 0 and 3")
        if self.slow_pwm > self.fast_pwm:
            errors.append("Slow PWM should be less than or equal to fast PWM")
        if self.intermittent_min_ms >= self.intermittent_max_ms:
            errors.append("Intermittent min delay must be less than max delay")
        return errors


@dataclass
class BlinkerChannel(ChannelBase):
    """Turn signal and hazard light control module

    Features:
    - Left/Right turn signal control
    - Hazard lights (all flashing)
    - Lane change tap (3-flash sequence)
    - Configurable flash rate
    - Thermal flasher emulation
    - Trailer indicators support
    """
    # Output assignment
    left_output: str = ""                      # Left indicator output channel
    right_output: str = ""                     # Right indicator output channel
    left_trailer_output: str = ""              # Left trailer indicator (optional)
    right_trailer_output: str = ""             # Right trailer indicator (optional)

    # Control inputs
    left_channel: str = ""                     # Left turn signal input
    right_channel: str = ""                    # Right turn signal input
    hazard_channel: str = ""                   # Hazard button input

    # Flash timing
    flash_on_ms: int = 500                     # Flash ON duration
    flash_off_ms: int = 500                    # Flash OFF duration
    flash_rate_hz: float = 1.0                 # Alternative: flash rate in Hz

    # Lane change tap
    lane_change_enabled: bool = True           # Enable lane change tap
    lane_change_flashes: int = 3               # Number of flashes for tap
    lane_change_timeout_ms: int = 400          # Max time for tap detection

    # Priority
    hazard_priority: bool = True               # Hazard overrides turn signals

    # Bulb check / thermal flasher emulation
    fast_flash_on_bulb_out: bool = True        # Flash fast if bulb out
    fast_flash_rate_hz: float = 2.0            # Fast flash rate

    # Output mode
    output_mode: str = "toggle"                # "toggle" or "momentary"

    def __post_init__(self):
        self.channel_type = ChannelType.BLINKER

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "left_output": self.left_output,
            "right_output": self.right_output,
            "left_trailer_output": self.left_trailer_output,
            "right_trailer_output": self.right_trailer_output,
            "left_channel": self.left_channel,
            "right_channel": self.right_channel,
            "hazard_channel": self.hazard_channel,
            "flash_on_ms": self.flash_on_ms,
            "flash_off_ms": self.flash_off_ms,
            "flash_rate_hz": self.flash_rate_hz,
            "lane_change_enabled": self.lane_change_enabled,
            "lane_change_flashes": self.lane_change_flashes,
            "lane_change_timeout_ms": self.lane_change_timeout_ms,
            "hazard_priority": self.hazard_priority,
            "fast_flash_on_bulb_out": self.fast_flash_on_bulb_out,
            "fast_flash_rate_hz": self.fast_flash_rate_hz,
            "output_mode": self.output_mode,
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlinkerChannel':
        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.BLINKER,
            channel_id=data.get("channel_id", 0),
            left_output=data.get("left_output", ""),
            right_output=data.get("right_output", ""),
            left_trailer_output=data.get("left_trailer_output", ""),
            right_trailer_output=data.get("right_trailer_output", ""),
            left_channel=data.get("left_channel", ""),
            right_channel=data.get("right_channel", ""),
            hazard_channel=data.get("hazard_channel", ""),
            flash_on_ms=data.get("flash_on_ms", 500),
            flash_off_ms=data.get("flash_off_ms", 500),
            flash_rate_hz=data.get("flash_rate_hz", 1.0),
            lane_change_enabled=data.get("lane_change_enabled", True),
            lane_change_flashes=data.get("lane_change_flashes", 3),
            lane_change_timeout_ms=data.get("lane_change_timeout_ms", 400),
            hazard_priority=data.get("hazard_priority", True),
            fast_flash_on_bulb_out=data.get("fast_flash_on_bulb_out", True),
            fast_flash_rate_hz=data.get("fast_flash_rate_hz", 2.0),
            output_mode=data.get("output_mode", "toggle"),
        )

    def get_input_channels(self) -> List[str]:
        channels = []
        if self.left_channel:
            channels.append(self.left_channel)
        if self.right_channel:
            channels.append(self.right_channel)
        if self.hazard_channel:
            channels.append(self.hazard_channel)
        return channels

    def get_output_channels(self) -> List[str]:
        channels = []
        if self.left_output:
            channels.append(self.left_output)
        if self.right_output:
            channels.append(self.right_output)
        if self.left_trailer_output:
            channels.append(self.left_trailer_output)
        if self.right_trailer_output:
            channels.append(self.right_trailer_output)
        return channels

    def validate(self) -> List[str]:
        errors = super().validate()
        if self.flash_on_ms < 100 or self.flash_on_ms > 2000:
            errors.append("Flash ON time should be between 100ms and 2000ms")
        if self.flash_off_ms < 100 or self.flash_off_ms > 2000:
            errors.append("Flash OFF time should be between 100ms and 2000ms")
        if self.lane_change_flashes < 1 or self.lane_change_flashes > 10:
            errors.append("Lane change flashes should be between 1 and 10")
        return errors
