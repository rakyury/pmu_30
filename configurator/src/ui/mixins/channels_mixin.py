"""
Channel Management Mixin
Handles channel CRUD operations for MainWindow
"""

import logging
from PyQt6.QtWidgets import QMessageBox
from models.channel import ChannelType
from models.channel_display_service import ChannelDisplayService

logger = logging.getLogger(__name__)


class MainWindowChannelsMixin:
    """Mixin for channel management operations."""

    def _on_item_add_requested(self, channel_type_str: str):
        """Handle request to add new item by Channel type."""
        try:
            channel_type = ChannelType(channel_type_str)
        except ValueError:
            return

        available_channels = self._get_available_channels()
        existing_channels = self.project_tree.get_all_channels()

        # Dialog map for cleaner code
        dialog = self._create_add_dialog(channel_type, available_channels, existing_channels)
        if dialog is None:
            return

        if dialog.exec():
            config = dialog.get_config()
            self._handle_channel_added(channel_type, config)

    def _create_add_dialog(self, channel_type: ChannelType, available_channels: dict, existing_channels: list):
        """Create appropriate dialog for adding a channel type."""
        from ui.dialogs.digital_input_dialog import DigitalInputDialog
        from ui.dialogs.analog_input_dialog import AnalogInputDialog
        from ui.dialogs.logic_dialog import LogicDialog
        from ui.dialogs.timer_dialog import TimerDialog
        from ui.dialogs.number_dialog import NumberDialog
        from ui.dialogs.filter_dialog import FilterDialog
        from ui.dialogs.table_2d_dialog import Table2DDialog
        from ui.dialogs.table_3d_dialog import Table3DDialog
        from ui.dialogs.output_config_dialog import OutputConfigDialog
        from ui.dialogs.switch_dialog import SwitchDialog
        from ui.dialogs.can_input_dialog import CANInputDialog
        from ui.dialogs.can_output_dialog import CANOutputDialog
        from ui.dialogs.lua_script_tree_dialog import LuaScriptTreeDialog
        from ui.dialogs.pid_controller_dialog import PIDControllerDialog
        from ui.dialogs.hbridge_dialog import HBridgeDialog
        from ui.dialogs.handler_dialog import HandlerDialog
        from ui.dialogs.blinkmarine_keypad_dialog import BlinkMarineKeypadDialog

        dialogs = {
            ChannelType.DIGITAL_INPUT: lambda: DigitalInputDialog(
                self, None, available_channels,
                self.project_tree.get_all_used_digital_input_pins(),
                existing_channels
            ),
            ChannelType.ANALOG_INPUT: lambda: AnalogInputDialog(
                self, None, available_channels,
                self.project_tree.get_all_used_analog_input_pins(),
                existing_channels
            ),
            ChannelType.POWER_OUTPUT: lambda: OutputConfigDialog(
                self, config=None, available_channels=available_channels,
                existing_channels=existing_channels,
                used_pins=self.project_tree.get_all_used_output_pins()
            ),
            ChannelType.HBRIDGE: lambda: HBridgeDialog(
                self, config=None, available_channels=available_channels,
                existing_channels=existing_channels,
                used_bridges=self.project_tree.get_all_used_hbridge_numbers()
            ),
            ChannelType.LOGIC: lambda: LogicDialog(self, None, available_channels, existing_channels),
            ChannelType.NUMBER: lambda: NumberDialog(self, None, available_channels, existing_channels),
            ChannelType.TIMER: lambda: TimerDialog(self, None, available_channels, existing_channels),
            ChannelType.SWITCH: lambda: SwitchDialog(self, None, available_channels),
            ChannelType.TABLE_2D: lambda: Table2DDialog(self, None, available_channels, existing_channels),
            ChannelType.TABLE_3D: lambda: Table3DDialog(self, None, available_channels, existing_channels),
            ChannelType.FILTER: lambda: FilterDialog(self, None, available_channels, existing_channels),
            ChannelType.LUA_SCRIPT: lambda: self._create_lua_dialog(available_channels, existing_channels),
            ChannelType.PID: lambda: PIDControllerDialog(self, None, available_channels, existing_channels),
            ChannelType.BLINKMARINE_KEYPAD: lambda: BlinkMarineKeypadDialog(self, None, available_channels, existing_channels),
            ChannelType.HANDLER: lambda: HandlerDialog(self, None, available_channels, existing_channels),
        }

        # Special handling for CAN channels
        if channel_type == ChannelType.CAN_RX:
            return self._create_can_rx_dialog(existing_channels)
        elif channel_type == ChannelType.CAN_TX:
            return self._create_can_tx_dialog(available_channels, existing_channels)

        creator = dialogs.get(channel_type)
        return creator() if creator else None

    def _create_lua_dialog(self, available_channels: dict, existing_channels: list):
        """Create Lua script dialog with signal connections."""
        from ui.dialogs.lua_script_tree_dialog import LuaScriptTreeDialog
        dialog = LuaScriptTreeDialog(self, None, available_channels, existing_channels)
        dialog.run_requested.connect(self._on_lua_run_requested)
        dialog.stop_requested.connect(self._on_lua_stop_requested)
        return dialog

    def _create_can_rx_dialog(self, existing_channels: list):
        """Create CAN RX dialog with message validation."""
        from ui.dialogs.can_input_dialog import CANInputDialog

        message_ids = [msg.get("id", "") for msg in self.config_manager.get_config().get("can_messages", [])]
        if not message_ids:
            QMessageBox.warning(
                self, "No CAN Messages",
                "Please create at least one CAN Message before adding CAN Inputs.\n\n"
                "Use the CAN Bus tab to create CAN Messages first."
            )
            return None

        existing_ids = [ch.get("id", "") for ch in existing_channels]
        return CANInputDialog(self, input_config=None, message_ids=message_ids, existing_channel_ids=existing_ids)

    def _create_can_tx_dialog(self, available_channels: dict, existing_channels: list):
        """Create CAN TX dialog."""
        from ui.dialogs.can_output_dialog import CANOutputDialog
        existing_ids = [ch.get("id", "") for ch in existing_channels]
        return CANOutputDialog(self, output_config=None, existing_ids=existing_ids, available_channels=available_channels)

    def _handle_channel_added(self, channel_type: ChannelType, config: dict):
        """Handle channel addition with type-specific post-processing."""
        self.project_tree.add_channel(channel_type, config)
        self.configuration_changed.emit()

        # Type-specific updates
        if channel_type == ChannelType.DIGITAL_INPUT:
            self.digital_monitor.set_inputs(self.project_tree.get_all_inputs())
        elif channel_type == ChannelType.ANALOG_INPUT:
            self.analog_monitor.set_inputs(self.project_tree.get_all_inputs())
        elif channel_type == ChannelType.POWER_OUTPUT:
            self.output_monitor.set_outputs(self.project_tree.get_all_outputs())
            self._apply_output_to_device(config)
        elif channel_type == ChannelType.HBRIDGE:
            self.hbridge_monitor.set_hbridges(self.project_tree.get_all_hbridges())
        elif channel_type == ChannelType.BLINKMARINE_KEYPAD:
            self._sync_keypad_button_channels(config)

    def _on_item_deleted(self, channel_type_str: str, data: dict):
        """Handle item deletion - cleanup related channels."""
        try:
            channel_type = ChannelType(channel_type_str)
        except ValueError:
            return

        item_data = data.get("data", {})

        # When a BlinkMarine keypad is deleted, remove all its button channels
        if channel_type == ChannelType.BLINKMARINE_KEYPAD:
            keypad_id = item_data.get("id", "")
            if keypad_id:
                self._remove_keypad_button_channels(keypad_id)
                logger.info(f"Removed button channels for deleted keypad '{keypad_id}'")

    def _get_available_channels(self) -> dict:
        """Get all available channels for selection organized by Channel type.

        Returns dict with lists of tuples: (channel_id, display_name, units, decimal_places)
        where channel_id is the numeric int ID shown in brackets.
        """
        def get_channel_info(ch):
            # Get numeric channel_id for display in brackets
            channel_id = ch.get("channel_id")
            # Get display name: channel_name > name > id (same as main tree)
            display_name = ch.get("channel_name") or ch.get("name") or ch.get("id") or "unnamed"
            # Get units and decimal places for display
            units = ch.get("units") or ch.get("unit") or ""
            decimal_places = ch.get("decimal_places")
            return (channel_id, display_name, units, decimal_places)

        channel_types_map = {
            "digital_inputs": ChannelType.DIGITAL_INPUT,
            "analog_inputs": ChannelType.ANALOG_INPUT,
            "power_outputs": ChannelType.POWER_OUTPUT,
            "logic": ChannelType.LOGIC,
            "numbers": ChannelType.NUMBER,
            "tables_2d": ChannelType.TABLE_2D,
            "tables_3d": ChannelType.TABLE_3D,
            "switches": ChannelType.SWITCH,
            "timers": ChannelType.TIMER,
            "filters": ChannelType.FILTER,
            "can_rx": ChannelType.CAN_RX,
            "can_tx": ChannelType.CAN_TX,
            "lua_scripts": ChannelType.LUA_SCRIPT,
            "pid_controllers": ChannelType.PID,
        }

        channels = {key: [] for key in channel_types_map.keys()}

        for key, channel_type in channel_types_map.items():
            ch_list = self.project_tree.get_channels_by_type(channel_type)
            for ch in ch_list:
                info = get_channel_info(ch)
                channels[key].append(info)

        return channels

    def get_channel_name_by_id(self, channel_id: int) -> str:
        """Lookup channel display name by numeric channel_id.

        For user channels: returns channel_name (e.g., "FuelLevel")
        For system channels: returns string ID (e.g., "pmu.batteryVoltage")

        Args:
            channel_id: Numeric channel ID

        Returns:
            Display name for the channel, or "#{channel_id}" if not found
        """
        if channel_id is None:
            return ""

        # Check user channels in project tree
        for ch in self.project_tree.get_all_channels():
            if ch.get("channel_id") == channel_id:
                return ch.get("channel_name") or ch.get("name") or ch.get("id") or f"#{channel_id}"

        # System channels (1000+) - lookup from predefined list
        if channel_id >= 1000:
            return self._get_system_channel_name(channel_id)

        return f"#{channel_id}"

    def _get_system_channel_name(self, channel_id: int) -> str:
        """Get display name for system channel by ID.

        Delegates to ChannelDisplayService for centralized lookup.
        """
        name = ChannelDisplayService.get_system_channel_name(channel_id)
        return name if name else f"#{channel_id}"

    def _sync_keypad_button_channels(self, keypad_config: dict, old_keypad_name: str = None):
        """Sync virtual channels for keypad buttons (ECUMaster style)."""
        from models.channel import DigitalInputSubtype, ButtonMode

        keypad_name = keypad_config.get("name", "")
        if not keypad_name:
            logger.warning("Keypad has no name, skipping button channel sync")
            return

        keypad_type = keypad_config.get("keypad_type", "2x6")
        button_count = 12 if keypad_type == "2x6" else 16
        button_configs = keypad_config.get("buttons", {})

        if old_keypad_name and old_keypad_name != keypad_name:
            self._remove_keypad_button_channels(old_keypad_name)

        for btn_idx in range(button_count):
            btn_config = button_configs.get(btn_idx, button_configs.get(str(btn_idx), {}))

            btn_label = btn_config.get("name", f"Button {btn_idx + 1}")
            press_action = btn_config.get("press_action", "Set High")

            channel_name = f"{keypad_name} - {btn_label}"

            if "Toggle" in press_action:
                button_mode = ButtonMode.TOGGLE.value
            elif "Latching" in press_action or "Latch" in press_action:
                button_mode = ButtonMode.LATCHING.value
            else:
                button_mode = ButtonMode.MOMENTARY.value

            channel_config = {
                "channel_type": "digital_input",
                "name": channel_name,
                "subtype": DigitalInputSubtype.KEYPAD_BUTTON.value,
                "keypad_name": keypad_name,
                "button_index": btn_idx,
                "button_mode": button_mode,
                "invert": False,
            }

            existing = self._find_channel_by_name(channel_name)
            if existing:
                self.project_tree.update_channel_by_name(channel_name, channel_config)
            else:
                self.project_tree.add_channel(ChannelType.DIGITAL_INPUT, channel_config)

        logger.info(f"Synced {button_count} button channels for keypad '{keypad_name}'")

    def _remove_keypad_button_channels(self, keypad_name: str):
        """Remove all button channels for a keypad by matching name prefix."""
        prefix = f"{keypad_name} - "
        removed_count = 0
        all_channels = self.project_tree.get_all_channels()
        for ch in all_channels:
            ch_name = ch.get("name", "")
            if ch_name.startswith(prefix) and ch.get("subtype") == "keypad_button":
                if self.project_tree.remove_channel_by_name(ch_name):
                    removed_count += 1
        logger.info(f"Removed {removed_count} button channels for keypad '{keypad_name}'")

    def _find_channel_by_name(self, channel_name: str) -> dict:
        """Find a channel by its name."""
        for ch in self.project_tree.get_all_channels():
            if ch.get("name") == channel_name:
                return ch
        return None

    def _find_channel_by_id(self, channel_id: str) -> dict:
        """Find a channel by its ID (legacy, also checks name)."""
        for ch in self.project_tree.get_all_channels():
            if ch.get("id") == channel_id or ch.get("name") == channel_id:
                return ch
        return None
