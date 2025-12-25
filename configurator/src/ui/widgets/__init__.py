"""UI Widgets for PMU-30 Configurator"""

from .project_tree import ProjectTree
from .tree_model import TreeModel
from .output_monitor import OutputMonitor
from .analog_monitor import AnalogMonitor
from .digital_monitor import DigitalMonitor
from .variables_inspector import VariablesInspector
from .pmu_monitor import PMUMonitorWidget
from .lua_editor import LuaCodeEditor
from .hbridge_monitor import HBridgeMonitor
from .pid_tuner import PIDTuner
from .can_monitor import CANMonitor
from .data_logger import DataLoggerWidget
from .channel_graph import ChannelGraphWidget
from .log_viewer import LogViewerWidget
from .channel_search import ChannelSearchDialog
from .connection_status import ConnectionStatusWidget
from .led_indicator import LEDWidget, LEDIndicatorBar, LEDColor, LEDPattern, SystemStatus, OutputChannelLEDBar
from .quantity_selector import (
    QuantityUnitSelector, QuantityUnitGroup, CompactQuantitySelector
)
from .time_input import (
    SecondsSpinBox, MillisecondsSpinBox, TimeInputWidget,
    DelayInputWidget, RetryDelayWidget, DebounceWidget
)
from .constant_spinbox import (
    ConstantSpinBox, ConstantSpinBoxWithSuffix, ScalingFactorSpinBox,
    ThresholdSpinBox, PercentageSpinBox, VoltageSpinBox, CurrentSpinBox,
    create_constant_spinbox
)

__all__ = [
    'ProjectTree',
    'TreeModel',
    'OutputMonitor',
    'AnalogMonitor',
    'DigitalMonitor',
    'VariablesInspector',
    'PMUMonitorWidget',
    'LuaCodeEditor',
    'HBridgeMonitor',
    'PIDTuner',
    'CANMonitor',
    'DataLoggerWidget',
    'ChannelGraphWidget',
    'LogViewerWidget',
    'ChannelSearchDialog',
    'ConnectionStatusWidget',
    # LED indicator widgets
    'LEDWidget',
    'LEDIndicatorBar',
    'LEDColor',
    'LEDPattern',
    'SystemStatus',
    'OutputChannelLEDBar',
    # Quantity/Unit widgets
    'QuantityUnitSelector',
    'QuantityUnitGroup',
    'CompactQuantitySelector',
    # Time input widgets
    'SecondsSpinBox',
    'MillisecondsSpinBox',
    'TimeInputWidget',
    'DelayInputWidget',
    'RetryDelayWidget',
    'DebounceWidget',
    # Constant spinboxes (2 decimal display, integer storage)
    'ConstantSpinBox',
    'ConstantSpinBoxWithSuffix',
    'ScalingFactorSpinBox',
    'ThresholdSpinBox',
    'PercentageSpinBox',
    'VoltageSpinBox',
    'CurrentSpinBox',
    'create_constant_spinbox',
]
