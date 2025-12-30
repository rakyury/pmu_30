"""
Output Channels - Power output and H-Bridge channel types

This module contains output channel classes for controlling physical outputs.
"""

from dataclasses import dataclass
from typing import List, Dict, Any

from .enums import ChannelType, HBridgeMode, HBridgeMotorPreset
from .base import ChannelBase


@dataclass
class PowerOutputChannel(ChannelBase):
    """Power output channel (PROFET)"""
    output_pins: List[int] = None  # O1-O30 -> 0-29
    source_channel: str = ""  # Control source channel
    # PWM
    pwm_enabled: bool = False
    pwm_frequency_hz: int = 1000
    duty_channel: str = ""  # Channel for duty control
    duty_fixed: float = 100.0  # Fixed duty if no channel
    soft_start_ms: int = 0
    # Protection
    current_limit_a: float = 25.0
    inrush_current_a: float = 50.0
    inrush_time_ms: int = 100
    retry_count: int = 3
    retry_forever: bool = False

    def __post_init__(self):
        self.channel_type = ChannelType.POWER_OUTPUT
        if self.output_pins is None:
            self.output_pins = [0]

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "output_pins": self.output_pins,
            "source_channel": self.source_channel,
            "pwm_enabled": self.pwm_enabled,
            "pwm_frequency_hz": self.pwm_frequency_hz,
            "duty_channel": self.duty_channel,
            "duty_fixed": self.duty_fixed,
            "soft_start_ms": self.soft_start_ms,
            "current_limit_a": self.current_limit_a,
            "inrush_current_a": self.inrush_current_a,
            "inrush_time_ms": self.inrush_time_ms,
            "retry_count": self.retry_count,
            "retry_forever": self.retry_forever
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PowerOutputChannel':
        # Support both flat format (from channel.py) and nested format (from dialog)
        # Pins: try "output_pins" first, then "pins"
        output_pins = data.get("output_pins", data.get("pins", [0]))

        # Source channel: try "source_channel" first, then "control_function"
        source_channel = data.get("source_channel", data.get("control_function", ""))

        # PWM settings: try flat format first, then nested "pwm" object
        pwm_obj = data.get("pwm", {})
        pwm_enabled = data.get("pwm_enabled", pwm_obj.get("enabled", False))
        pwm_frequency_hz = data.get("pwm_frequency_hz", pwm_obj.get("frequency", 1000))
        duty_channel = data.get("duty_channel", pwm_obj.get("duty_function", ""))
        duty_fixed = data.get("duty_fixed", pwm_obj.get("duty_value", 100.0))
        soft_start_enabled = pwm_obj.get("soft_start_enabled", False)
        soft_start_ms = data.get("soft_start_ms", pwm_obj.get("soft_start_duration_ms", 0) if soft_start_enabled else 0)

        # Protection settings: try flat format first, then nested "protection" object
        prot_obj = data.get("protection", {})
        current_limit_a = data.get("current_limit_a", prot_obj.get("current_limit", 25.0))
        inrush_current_a = data.get("inrush_current_a", prot_obj.get("inrush_current", 50.0))
        inrush_time_ms = data.get("inrush_time_ms", prot_obj.get("inrush_time_ms", 100))
        retry_count = data.get("retry_count", prot_obj.get("retry_count", 3))
        retry_forever = data.get("retry_forever", prot_obj.get("retry_forever", False))

        # Name is required
        name = data.get("channel_name", "")
        if not name:
            raise ValueError("Power output missing required 'channel_name' field")

        return cls(
            name=name,
            channel_type=ChannelType.POWER_OUTPUT,
            channel_id=data.get("channel_id", 0),
            output_pins=output_pins,
            source_channel=source_channel,
            pwm_enabled=pwm_enabled,
            pwm_frequency_hz=pwm_frequency_hz,
            duty_channel=duty_channel,
            duty_fixed=duty_fixed,
            soft_start_ms=soft_start_ms,
            current_limit_a=current_limit_a,
            inrush_current_a=inrush_current_a,
            inrush_time_ms=inrush_time_ms,
            retry_count=retry_count,
            retry_forever=retry_forever
        )

    def get_input_channels(self) -> List[str]:
        channels = []
        if self.source_channel:
            channels.append(self.source_channel)
        if self.duty_channel:
            channels.append(self.duty_channel)
        return channels


@dataclass
class HBridgeChannel(ChannelBase):
    """H-Bridge motor control channel (Dual H-Bridge output)

    Features:
    - Forward/Reverse/Brake/Coast control
    - PWM speed control
    - Position feedback with potentiometer
    - Wiper park mode
    - PID position control
    - Current sensing and protection
    """
    # H-Bridge hardware
    bridge_number: int = 0                     # 0-3 (HB1-HB4)

    # Control source
    source_channel: str = ""                   # Channel for activation
    mode: HBridgeMode = HBridgeMode.FORWARD    # Operating mode

    # Direction control (for separate FWD/REV sources)
    direction_source_channel: str = ""         # Channel for direction (optional)
    invert_direction: bool = False             # Invert direction logic

    # PWM control
    pwm_enabled: bool = True
    pwm_mode: str = "fixed"                    # "fixed", "channel", "channel_offset" (bidirectional)
    pwm_frequency: int = 1000                  # PWM frequency in Hz
    pwm_value: int = 255                       # Fixed PWM value (0-255)
    pwm_source_channel: str = ""               # Channel for PWM duty cycle
    duty_limit_percent: int = 100              # Maximum duty cycle limit (0-100%)
    soft_start_ms: int = 0                     # Soft-start ramp time

    # Position control
    position_feedback_enabled: bool = False    # Enable position feedback
    position_source_channel: str = ""          # Channel for position feedback
    target_position: int = 0                   # Fixed target position value
    target_source_channel: str = ""            # Channel for target position
    position_min: int = 0                      # Minimum position value
    position_max: int = 65535                  # Maximum position value
    position_deadband: int = 50                # Position tolerance (stops when within deadband)
    position_park: float = 0.0                 # Park position for wiper mode

    # Valid voltage range (ECUMaster feature)
    valid_voltage_min: float = 0.2             # Min valid feedback voltage (V)
    valid_voltage_max: float = 4.8             # Max valid feedback voltage (V)

    # Position margins (ECUMaster feature - avoid hitting end stops)
    lower_margin: int = 50                     # Lower position margin
    upper_margin: int = 50                     # Upper position margin

    # PID position control
    pid_kp: float = 1.0
    pid_ki: float = 0.0
    pid_kd: float = 0.0
    pid_kd_filter: float = 0.1                 # Derivative filter coefficient (0-1)
    pid_output_min: int = -255                 # PID output min
    pid_output_max: int = 255                  # PID output max

    # Protection settings
    current_limit_a: float = 10.0              # Continuous overcurrent limit
    inrush_current_a: float = 30.0             # Inrush current limit
    inrush_time_ms: int = 500                  # Inrush time period
    retry_count: int = 3                       # Retries before lockout
    retry_delay_ms: int = 1000                 # Delay between retries

    # Stall detection
    stall_detection_enabled: bool = True       # Enable stall detection
    stall_current_threshold_a: float = 5.0     # Stall current threshold
    stall_time_threshold_ms: int = 500         # Time before stall fault
    overtemperature_threshold_c: int = 120     # Over-temperature limit

    # Signal loss failsafe
    failsafe_enabled: bool = True              # Enable signal loss protection
    signal_timeout_ms: int = 100               # Signal timeout before failsafe
    failsafe_mode: str = "park"                # "park", "brake", "coast", "custom_position"
    failsafe_position: int = 0                 # Position to move to in failsafe
    failsafe_pwm: int = 100                    # PWM for failsafe movement
    auto_recovery: bool = True                 # Auto-recover when signal returns

    # Motor preset
    motor_preset: HBridgeMotorPreset = HBridgeMotorPreset.WIPER

    def __post_init__(self):
        self.channel_type = ChannelType.HBRIDGE

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "bridge_number": self.bridge_number,
            "source_channel": self.source_channel,
            "mode": self.mode.value if isinstance(self.mode, HBridgeMode) else self.mode,
            "direction_source_channel": self.direction_source_channel,
            "invert_direction": self.invert_direction,
            # PWM control
            "pwm_enabled": self.pwm_enabled,
            "pwm_mode": self.pwm_mode,
            "pwm_frequency": self.pwm_frequency,
            "pwm_value": self.pwm_value,
            "pwm_source_channel": self.pwm_source_channel,
            "duty_limit_percent": self.duty_limit_percent,
            "soft_start_ms": self.soft_start_ms,
            # Position control
            "position_feedback_enabled": self.position_feedback_enabled,
            "position_source_channel": self.position_source_channel,
            "target_position": self.target_position,
            "target_source_channel": self.target_source_channel,
            "position_min": self.position_min,
            "position_max": self.position_max,
            "position_deadband": self.position_deadband,
            "position_park": self.position_park,
            "valid_voltage_min": self.valid_voltage_min,
            "valid_voltage_max": self.valid_voltage_max,
            "lower_margin": self.lower_margin,
            "upper_margin": self.upper_margin,
            # PID
            "pid_kp": self.pid_kp,
            "pid_ki": self.pid_ki,
            "pid_kd": self.pid_kd,
            "pid_kd_filter": self.pid_kd_filter,
            "pid_output_min": self.pid_output_min,
            "pid_output_max": self.pid_output_max,
            # Protection
            "current_limit_a": self.current_limit_a,
            "inrush_current_a": self.inrush_current_a,
            "inrush_time_ms": self.inrush_time_ms,
            "retry_count": self.retry_count,
            "retry_delay_ms": self.retry_delay_ms,
            # Stall detection
            "stall_detection_enabled": self.stall_detection_enabled,
            "stall_current_threshold_a": self.stall_current_threshold_a,
            "stall_time_threshold_ms": self.stall_time_threshold_ms,
            "overtemperature_threshold_c": self.overtemperature_threshold_c,
            # Failsafe
            "failsafe_enabled": self.failsafe_enabled,
            "signal_timeout_ms": self.signal_timeout_ms,
            "failsafe_mode": self.failsafe_mode,
            "failsafe_position": self.failsafe_position,
            "failsafe_pwm": self.failsafe_pwm,
            "auto_recovery": self.auto_recovery,
            # Preset
            "motor_preset": self.motor_preset.value if isinstance(self.motor_preset, HBridgeMotorPreset) else self.motor_preset,
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HBridgeChannel':
        # Parse mode
        mode_str = data.get("mode", "forward")
        try:
            mode = HBridgeMode(mode_str)
        except ValueError:
            mode = HBridgeMode.FORWARD

        # Parse motor preset
        preset_str = data.get("motor_preset", "wiper")
        try:
            motor_preset = HBridgeMotorPreset(preset_str)
        except ValueError:
            motor_preset = HBridgeMotorPreset.CUSTOM

        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.HBRIDGE,
            channel_id=data.get("channel_id", 0),
            bridge_number=data.get("bridge_number", 0),
            source_channel=data.get("source_channel", ""),
            mode=mode,
            direction_source_channel=data.get("direction_source_channel", ""),
            invert_direction=data.get("invert_direction", False),
            # PWM control
            pwm_enabled=data.get("pwm_enabled", True),
            pwm_mode=data.get("pwm_mode", "fixed"),
            pwm_frequency=data.get("pwm_frequency", 1000),
            pwm_value=data.get("pwm_value", 255),
            pwm_source_channel=data.get("pwm_source_channel", ""),
            duty_limit_percent=data.get("duty_limit_percent", 100),
            soft_start_ms=data.get("soft_start_ms", 0),
            # Position control
            position_feedback_enabled=data.get("position_feedback_enabled", False),
            position_source_channel=data.get("position_source_channel", ""),
            target_position=data.get("target_position", 0),
            target_source_channel=data.get("target_source_channel", ""),
            position_min=data.get("position_min", 0),
            position_max=data.get("position_max", 65535),
            position_deadband=data.get("position_deadband", 50),
            position_park=data.get("position_park", 0.0),
            valid_voltage_min=data.get("valid_voltage_min", 0.2),
            valid_voltage_max=data.get("valid_voltage_max", 4.8),
            lower_margin=data.get("lower_margin", 50),
            upper_margin=data.get("upper_margin", 50),
            # PID
            pid_kp=data.get("pid_kp", 1.0),
            pid_ki=data.get("pid_ki", 0.0),
            pid_kd=data.get("pid_kd", 0.0),
            pid_kd_filter=data.get("pid_kd_filter", 0.1),
            pid_output_min=data.get("pid_output_min", -255),
            pid_output_max=data.get("pid_output_max", 255),
            # Protection
            current_limit_a=data.get("current_limit_a", 10.0),
            inrush_current_a=data.get("inrush_current_a", 30.0),
            inrush_time_ms=data.get("inrush_time_ms", 500),
            retry_count=data.get("retry_count", 3),
            retry_delay_ms=data.get("retry_delay_ms", 1000),
            # Stall detection
            stall_detection_enabled=data.get("stall_detection_enabled", True),
            stall_current_threshold_a=data.get("stall_current_threshold_a", 5.0),
            stall_time_threshold_ms=data.get("stall_time_threshold_ms", 500),
            overtemperature_threshold_c=data.get("overtemperature_threshold_c", 120),
            # Failsafe
            failsafe_enabled=data.get("failsafe_enabled", True),
            signal_timeout_ms=data.get("signal_timeout_ms", 100),
            failsafe_mode=data.get("failsafe_mode", "park"),
            failsafe_position=data.get("failsafe_position", 0),
            failsafe_pwm=data.get("failsafe_pwm", 100),
            auto_recovery=data.get("auto_recovery", True),
            motor_preset=motor_preset,
        )

    def get_input_channels(self) -> List[str]:
        channels = []
        if self.source_channel:
            channels.append(self.source_channel)
        if self.direction_source_channel:
            channels.append(self.direction_source_channel)
        if self.pwm_source_channel:
            channels.append(self.pwm_source_channel)
        if self.position_source_channel:
            channels.append(self.position_source_channel)
        if self.target_source_channel:
            channels.append(self.target_source_channel)
        return channels

    def validate(self) -> List[str]:
        errors = super().validate()
        if not 0 <= self.bridge_number <= 3:
            errors.append("Bridge number must be between 0 and 3 (HB1-HB4)")
        if self.pwm_frequency not in [1000, 4000, 10000, 20000]:
            errors.append("PWM frequency must be 1000, 4000, 10000, or 20000 Hz")
        if self.duty_limit_percent < 0 or self.duty_limit_percent > 100:
            errors.append("Duty limit must be between 0 and 100%")
        if self.position_feedback_enabled:
            if self.position_min >= self.position_max:
                errors.append("Position min must be less than position max")
            if self.valid_voltage_min >= self.valid_voltage_max:
                errors.append("Valid voltage min must be less than valid voltage max")
        if self.current_limit_a <= 0 or self.current_limit_a > 50:
            errors.append("Current limit must be between 0 and 50A")
        if self.inrush_current_a < self.current_limit_a:
            errors.append("Inrush current should be greater than or equal to current limit")
        return errors
