"""
Dialog Factory

Centralized factory for creating channel configuration dialogs.
Reduces code duplication and simplifies dialog creation logic.
"""

from typing import Dict, Any, Optional, List, Type, Callable
from PyQt6.QtWidgets import QWidget, QDialog
from models.channel import ChannelType
import logging

logger = logging.getLogger(__name__)


class DialogFactory:
    """
    Factory for creating channel configuration dialogs.

    Provides a centralized way to create dialogs for different channel types.
    Supports lazy loading of dialog modules to improve startup time.
    """

    # Registry of dialog creators: ChannelType -> (module_path, class_name, required_args)
    _registry: Dict[ChannelType, tuple] = {}
    _dialog_classes: Dict[ChannelType, Type[QDialog]] = {}

    @classmethod
    def register(cls, channel_type: ChannelType, module_path: str, class_name: str):
        """
        Register a dialog class for a channel type.

        Args:
            channel_type: The channel type this dialog handles
            module_path: Dot-separated module path (e.g., 'ui.dialogs.analog_input_dialog')
            class_name: Name of the dialog class
        """
        cls._registry[channel_type] = (module_path, class_name)

    @classmethod
    def _get_dialog_class(cls, channel_type: ChannelType) -> Optional[Type[QDialog]]:
        """Get the dialog class for a channel type (lazy loading)."""
        if channel_type in cls._dialog_classes:
            return cls._dialog_classes[channel_type]

        if channel_type not in cls._registry:
            logger.warning(f"No dialog registered for channel type: {channel_type}")
            return None

        module_path, class_name = cls._registry[channel_type]

        try:
            import importlib
            module = importlib.import_module(module_path)
            dialog_class = getattr(module, class_name)
            cls._dialog_classes[channel_type] = dialog_class
            return dialog_class
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load dialog class {class_name} from {module_path}: {e}")
            return None

    @classmethod
    def create(cls, channel_type: ChannelType, parent: QWidget = None,
               config: Dict[str, Any] = None, **kwargs) -> Optional[QDialog]:
        """
        Create a dialog for the specified channel type.

        Args:
            channel_type: Type of channel
            parent: Parent widget
            config: Existing channel config (for editing) or None (for creating)
            **kwargs: Additional arguments passed to dialog constructor

        Returns:
            Dialog instance or None if creation failed
        """
        dialog_class = cls._get_dialog_class(channel_type)
        if dialog_class is None:
            return None

        try:
            # Create dialog with appropriate arguments based on type
            dialog = cls._create_dialog_instance(
                dialog_class, channel_type, parent, config, kwargs
            )
            return dialog
        except Exception as e:
            logger.error(f"Failed to create dialog for {channel_type}: {e}")
            return None

    @classmethod
    def _create_dialog_instance(cls, dialog_class: Type[QDialog],
                                channel_type: ChannelType,
                                parent: QWidget,
                                config: Optional[Dict[str, Any]],
                                kwargs: Dict[str, Any]) -> QDialog:
        """Create dialog instance with type-specific argument handling."""
        # Common arguments
        available_channels = kwargs.get('available_channels', {})
        existing_channels = kwargs.get('existing_channels', [])

        # Type-specific creation
        if channel_type == ChannelType.DIGITAL_INPUT:
            used_pins = kwargs.get('used_pins', [])
            return dialog_class(
                parent, config, available_channels, used_pins, existing_channels
            )

        elif channel_type == ChannelType.ANALOG_INPUT:
            used_pins = kwargs.get('used_pins', [])
            return dialog_class(
                parent, config, available_channels, used_pins, existing_channels
            )

        elif channel_type == ChannelType.POWER_OUTPUT:
            used_pins = kwargs.get('used_pins', [])
            return dialog_class(
                parent, config, used_pins, available_channels, existing_channels
            )

        elif channel_type == ChannelType.HBRIDGE:
            used_numbers = kwargs.get('used_numbers', [])
            return dialog_class(
                parent, config, used_numbers, available_channels, existing_channels
            )

        elif channel_type == ChannelType.WIPER:
            used_numbers = kwargs.get('used_numbers', [])
            return dialog_class(
                parent, config, used_numbers, available_channels, existing_channels
            )

        elif channel_type == ChannelType.BLINKER:
            return dialog_class(
                parent, config, available_channels, existing_channels
            )

        elif channel_type == ChannelType.CAN_RX:
            message_ids = kwargs.get('message_ids', [])
            existing_ids = kwargs.get('existing_ids', [])
            return dialog_class(
                parent, input_config=config, message_ids=message_ids,
                existing_channel_ids=existing_ids
            )

        elif channel_type == ChannelType.CAN_TX:
            existing_ids = kwargs.get('existing_ids', [])
            return dialog_class(
                parent, output_config=config, existing_ids=existing_ids,
                available_channels=available_channels
            )

        elif channel_type == ChannelType.SWITCH:
            # Switch dialog doesn't take existing_channels
            return dialog_class(parent, config, available_channels)

        else:
            # Generic dialog creation for most channel types
            return dialog_class(parent, config, available_channels, existing_channels)

    @classmethod
    def create_for_add(cls, channel_type: ChannelType, parent: QWidget = None,
                       **kwargs) -> Optional[QDialog]:
        """Create a dialog for adding a new channel."""
        return cls.create(channel_type, parent, config=None, **kwargs)

    @classmethod
    def create_for_edit(cls, channel_type: ChannelType, config: Dict[str, Any],
                        parent: QWidget = None, **kwargs) -> Optional[QDialog]:
        """Create a dialog for editing an existing channel."""
        return cls.create(channel_type, parent, config=config, **kwargs)

    @classmethod
    def get_registered_types(cls) -> List[ChannelType]:
        """Get list of channel types that have registered dialogs."""
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, channel_type: ChannelType) -> bool:
        """Check if a dialog is registered for the channel type."""
        return channel_type in cls._registry


def _register_default_dialogs():
    """Register all default channel dialogs."""

    # Inputs
    DialogFactory.register(
        ChannelType.DIGITAL_INPUT,
        'ui.dialogs.digital_input_dialog', 'DigitalInputDialog'
    )
    DialogFactory.register(
        ChannelType.ANALOG_INPUT,
        'ui.dialogs.analog_input_dialog', 'AnalogInputDialog'
    )
    DialogFactory.register(
        ChannelType.CAN_RX,
        'ui.dialogs.can_input_dialog', 'CANInputDialog'
    )

    # Outputs
    DialogFactory.register(
        ChannelType.POWER_OUTPUT,
        'ui.dialogs.output_config_dialog', 'OutputConfigDialog'
    )
    DialogFactory.register(
        ChannelType.HBRIDGE,
        'ui.dialogs.hbridge_dialog', 'HBridgeDialog'
    )
    DialogFactory.register(
        ChannelType.CAN_TX,
        'ui.dialogs.can_output_dialog', 'CANOutputDialog'
    )

    # Functions
    DialogFactory.register(
        ChannelType.LOGIC,
        'ui.dialogs.logic_dialog', 'LogicDialog'
    )
    DialogFactory.register(
        ChannelType.NUMBER,
        'ui.dialogs.number_dialog', 'NumberDialog'
    )
    DialogFactory.register(
        ChannelType.FILTER,
        'ui.dialogs.filter_dialog', 'FilterDialog'
    )
    DialogFactory.register(
        ChannelType.PID,
        'ui.dialogs.pid_controller_dialog', 'PIDControllerDialog'
    )

    # Tables
    DialogFactory.register(
        ChannelType.TABLE_2D,
        'ui.dialogs.table_2d_dialog', 'Table2DDialog'
    )
    DialogFactory.register(
        ChannelType.TABLE_3D,
        'ui.dialogs.table_3d_dialog', 'Table3DDialog'
    )

    # State
    DialogFactory.register(
        ChannelType.SWITCH,
        'ui.dialogs.switch_dialog', 'SwitchDialog'
    )
    DialogFactory.register(
        ChannelType.TIMER,
        'ui.dialogs.timer_dialog', 'TimerDialog'
    )

    # Data
    DialogFactory.register(
        ChannelType.ENUM,
        'ui.dialogs.enum_dialog', 'EnumDialog'
    )

    # Scripts
    DialogFactory.register(
        ChannelType.LUA_SCRIPT,
        'ui.dialogs.lua_script_tree_dialog', 'LuaScriptTreeDialog'
    )

    # Handlers
    DialogFactory.register(
        ChannelType.HANDLER,
        'ui.dialogs.handler_dialog', 'HandlerDialog'
    )

    # Peripherals
    DialogFactory.register(
        ChannelType.BLINKMARINE_KEYPAD,
        'ui.dialogs.blinkmarine_keypad_dialog', 'BlinkMarineKeypadDialog'
    )

    # Vehicle Modules
    DialogFactory.register(
        ChannelType.WIPER,
        'ui.dialogs.wiper_dialog', 'WiperDialog'
    )
    DialogFactory.register(
        ChannelType.BLINKER,
        'ui.dialogs.blinker_dialog', 'BlinkerDialog'
    )


# Register default dialogs on module import
_register_default_dialogs()
