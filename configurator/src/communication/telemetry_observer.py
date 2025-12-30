"""
Telemetry Observer Pattern

Provides decoupled telemetry distribution to widgets.
Widgets subscribe to specific telemetry fields they need.
"""

from typing import Dict, Any, List, Set, Callable, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
import logging

logger = logging.getLogger(__name__)


class TelemetryField(Enum):
    """Available telemetry fields for subscription."""
    # System
    INPUT_VOLTAGE = auto()
    TEMPERATURE = auto()
    BOARD_TEMP_2 = auto()
    TOTAL_CURRENT = auto()
    UPTIME = auto()
    SYSTEM_STATUS = auto()
    FAULT_FLAGS = auto()

    # Power rails
    OUTPUT_5V = auto()
    OUTPUT_3V3 = auto()

    # Outputs
    PROFET_STATES = auto()
    PROFET_CURRENTS = auto()
    PROFET_DUTIES = auto()

    # Inputs
    ADC_VALUES = auto()
    DIGITAL_INPUTS = auto()

    # CAN
    CAN_RX_VALUES = auto()

    # Virtual channels
    VIRTUAL_CHANNELS = auto()

    # All fields (for widgets that need everything)
    ALL = auto()


@dataclass
class TelemetryUpdate:
    """Container for telemetry update data."""
    field: TelemetryField
    value: Any
    timestamp_ms: int = 0


class TelemetryObserver(ABC):
    """
    Abstract base class for telemetry observers.

    Widgets implement this to receive telemetry updates.
    """

    @abstractmethod
    def on_telemetry_update(self, updates: Dict[TelemetryField, Any]):
        """
        Called when subscribed telemetry fields are updated.

        Args:
            updates: Dict mapping TelemetryField to new value
        """
        pass

    def get_subscribed_fields(self) -> Set[TelemetryField]:
        """
        Return the fields this observer wants to receive.

        Override this to subscribe to specific fields.
        Default returns ALL which receives everything.
        """
        return {TelemetryField.ALL}


class TelemetrySubject(QObject):
    """
    Subject that distributes telemetry to observers.

    Widgets register as observers and receive updates for their subscribed fields.
    Uses Qt signals for thread-safe delivery to GUI widgets.
    """

    # Signal for thread-safe delivery to Qt widgets
    telemetry_updated = pyqtSignal(dict)  # Dict[TelemetryField, Any]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._observers: List[TelemetryObserver] = []
        self._callback_observers: Dict[int, tuple] = {}  # id -> (callback, fields)
        self._last_values: Dict[TelemetryField, Any] = {}

        # Connect signal to distribution method
        self.telemetry_updated.connect(self._distribute_updates)

    def add_observer(self, observer: TelemetryObserver):
        """Add an observer to receive telemetry updates."""
        if observer not in self._observers:
            self._observers.append(observer)
            logger.debug(f"Added telemetry observer: {observer.__class__.__name__}")

    def remove_observer(self, observer: TelemetryObserver):
        """Remove an observer."""
        if observer in self._observers:
            self._observers.remove(observer)
            logger.debug(f"Removed telemetry observer: {observer.__class__.__name__}")

    def subscribe(self, callback: Callable[[Dict[TelemetryField, Any]], None],
                  fields: Set[TelemetryField] = None) -> int:
        """
        Subscribe a callback function to telemetry updates.

        Args:
            callback: Function to call with updates
            fields: Set of fields to subscribe to (default: ALL)

        Returns:
            Subscription ID for unsubscribing
        """
        if fields is None:
            fields = {TelemetryField.ALL}

        sub_id = id(callback)
        self._callback_observers[sub_id] = (callback, fields)
        logger.debug(f"Added callback subscription {sub_id} for fields: {fields}")
        return sub_id

    def unsubscribe(self, subscription_id: int):
        """Unsubscribe a callback by its subscription ID."""
        if subscription_id in self._callback_observers:
            del self._callback_observers[subscription_id]
            logger.debug(f"Removed callback subscription {subscription_id}")

    def notify(self, telemetry_packet):
        """
        Notify all observers of new telemetry data.

        This method converts a TelemetryPacket to field updates
        and distributes them via Qt signal for thread safety.

        Args:
            telemetry_packet: The raw telemetry packet from device
        """
        updates = self._extract_fields(telemetry_packet)
        self._last_values.update(updates)

        # Emit signal for thread-safe delivery
        self.telemetry_updated.emit(updates)

    def _distribute_updates(self, updates: Dict[TelemetryField, Any]):
        """Distribute updates to all observers (called on Qt main thread)."""
        # Notify class-based observers
        for observer in self._observers:
            try:
                subscribed = observer.get_subscribed_fields()
                if TelemetryField.ALL in subscribed:
                    observer.on_telemetry_update(updates)
                else:
                    # Filter to subscribed fields only
                    filtered = {k: v for k, v in updates.items() if k in subscribed}
                    if filtered:
                        observer.on_telemetry_update(filtered)
            except Exception as e:
                logger.error(f"Error notifying observer {observer.__class__.__name__}: {e}")

        # Notify callback observers
        for sub_id, (callback, fields) in self._callback_observers.items():
            try:
                if TelemetryField.ALL in fields:
                    callback(updates)
                else:
                    filtered = {k: v for k, v in updates.items() if k in fields}
                    if filtered:
                        callback(filtered)
            except Exception as e:
                logger.error(f"Error in callback subscription {sub_id}: {e}")

    def get_last_value(self, field: TelemetryField) -> Optional[Any]:
        """Get the last known value for a field."""
        return self._last_values.get(field)

    def get_all_last_values(self) -> Dict[TelemetryField, Any]:
        """Get all last known values."""
        return self._last_values.copy()

    def _extract_fields(self, telemetry) -> Dict[TelemetryField, Any]:
        """Extract telemetry fields from packet."""
        updates = {}

        # System fields
        if hasattr(telemetry, 'input_voltage_mv'):
            updates[TelemetryField.INPUT_VOLTAGE] = telemetry.input_voltage_mv / 1000.0
        if hasattr(telemetry, 'temperature_c'):
            updates[TelemetryField.TEMPERATURE] = telemetry.temperature_c
        if hasattr(telemetry, 'board_temp_2'):
            updates[TelemetryField.BOARD_TEMP_2] = telemetry.board_temp_2
        if hasattr(telemetry, 'total_current_ma'):
            updates[TelemetryField.TOTAL_CURRENT] = telemetry.total_current_ma / 1000.0
        if hasattr(telemetry, 'timestamp_ms'):
            updates[TelemetryField.UPTIME] = telemetry.timestamp_ms
        if hasattr(telemetry, 'system_status'):
            updates[TelemetryField.SYSTEM_STATUS] = telemetry.system_status
        if hasattr(telemetry, 'fault_flags'):
            flags = telemetry.fault_flags
            updates[TelemetryField.FAULT_FLAGS] = flags.value if hasattr(flags, 'value') else flags

        # Power rails
        if hasattr(telemetry, 'output_5v_mv'):
            updates[TelemetryField.OUTPUT_5V] = telemetry.output_5v_mv
        if hasattr(telemetry, 'output_3v3_mv'):
            updates[TelemetryField.OUTPUT_3V3] = telemetry.output_3v3_mv

        # Outputs
        if hasattr(telemetry, 'profet_states'):
            states = [int(s) if hasattr(s, 'value') else s for s in telemetry.profet_states]
            updates[TelemetryField.PROFET_STATES] = states
        if hasattr(telemetry, 'output_currents'):
            updates[TelemetryField.PROFET_CURRENTS] = list(telemetry.output_currents)
        if hasattr(telemetry, 'profet_duties'):
            updates[TelemetryField.PROFET_DUTIES] = list(telemetry.profet_duties)

        # Inputs
        if hasattr(telemetry, 'adc_values'):
            updates[TelemetryField.ADC_VALUES] = list(telemetry.adc_values)
        if hasattr(telemetry, 'digital_inputs'):
            updates[TelemetryField.DIGITAL_INPUTS] = telemetry.digital_inputs

        # CAN
        if hasattr(telemetry, 'can_rx_values') and telemetry.can_rx_values:
            updates[TelemetryField.CAN_RX_VALUES] = telemetry.can_rx_values

        # Virtual channels
        if hasattr(telemetry, 'virtual_channels') and telemetry.virtual_channels:
            updates[TelemetryField.VIRTUAL_CHANNELS] = telemetry.virtual_channels

        return updates


# Singleton instance for global access
_telemetry_subject: Optional[TelemetrySubject] = None


def get_telemetry_subject() -> TelemetrySubject:
    """Get the global telemetry subject instance."""
    global _telemetry_subject
    if _telemetry_subject is None:
        _telemetry_subject = TelemetrySubject()
    return _telemetry_subject


def reset_telemetry_subject():
    """Reset the global telemetry subject (for testing)."""
    global _telemetry_subject
    _telemetry_subject = None
