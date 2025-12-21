"""
LUA Scripts Tab
Manages LUA 5.4 scripts for PMU-30
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QLabel, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from ..dialogs.lua_script_dialog import LuaScriptDialog
from typing import Dict, Any, List


class LuaTab(QWidget):
    """LUA scripting configuration tab."""

    configuration_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lua_scripts = []
        self._init_ui()

    def _init_ui(self):
        """Initialize user interface."""
        layout = QVBoxLayout(self)

        # Info label
        info_group = QGroupBox("LUA 5.4 Scripting")
        info_layout = QVBoxLayout()
        info_label = QLabel(
            "Create custom control logic using LUA 5.4 scripting language.\n"
            "Scripts can access physical inputs/outputs, virtual channels, and CAN bus.\n"
            "Use for advanced control algorithms, data processing, and custom automation."
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Name", "Trigger", "Priority", "Max Time (ms)", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemDoubleClicked.connect(self.edit_script)
        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Script")
        self.add_btn.clicked.connect(self.add_script)
        button_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self.edit_script)
        button_layout.addWidget(self.edit_btn)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.clicked.connect(self.copy_script)
        button_layout.addWidget(self.copy_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_script)
        button_layout.addWidget(self.delete_btn)

        button_layout.addStretch()

        self.import_btn = QPushButton("Import Script...")
        self.import_btn.clicked.connect(self.import_script)
        button_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("Export Script...")
        self.export_btn.clicked.connect(self.export_script)
        button_layout.addWidget(self.export_btn)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_btn)

        layout.addLayout(button_layout)

        # Stats label
        self.stats_label = QLabel("Scripts: 0 (Enabled: 0)")
        layout.addWidget(self.stats_label)

        self._update_table()

    def _update_table(self):
        """Update table with current LUA scripts."""
        self.table.setRowCount(0)

        for idx, script in enumerate(self.lua_scripts):
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Name
            name = QTableWidgetItem(script.get("name", "Unnamed"))
            if not script.get("enabled", True):
                name.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, 0, name)

            # Trigger
            trigger = script.get("trigger", {})
            trigger_type = trigger.get("type", "Manual")
            trigger_str = trigger_type
            if "Periodic" in trigger_type:
                trigger_str = f"Every {trigger.get('period_ms', 0)} ms"
            elif "Input" in trigger_type or "Virtual" in trigger_type:
                trigger_str = f"{trigger_type.split('(')[0].strip()} Ch{trigger.get('channel', 0)}"

            trigger_item = QTableWidgetItem(trigger_str)
            self.table.setItem(row, 1, trigger_item)

            # Priority
            settings = script.get("settings", {})
            priority = QTableWidgetItem(settings.get("priority", "Normal"))
            priority.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, priority)

            # Max execution time
            max_time = QTableWidgetItem(str(settings.get("max_execution_ms", 50)))
            max_time.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, max_time)

            # Status
            status_text = "Enabled" if script.get("enabled", True) else "Disabled"
            status = QTableWidgetItem(status_text)
            status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if script.get("enabled", True):
                status.setForeground(Qt.GlobalColor.darkGreen)
            else:
                status.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, 4, status)

        self._update_stats()

    def _update_stats(self):
        """Update statistics label."""
        total = len(self.lua_scripts)
        enabled = sum(1 for script in self.lua_scripts if script.get("enabled", True))

        self.stats_label.setText(f"Scripts: {total} (Enabled: {enabled})")

    def add_script(self):
        """Add new LUA script."""
        dialog = LuaScriptDialog(self, script_config=None)

        if dialog.exec():
            config = dialog.get_config()
            self.lua_scripts.append(config)
            self._update_table()
            self.configuration_changed.emit()

    def edit_script(self):
        """Edit selected LUA script."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.lua_scripts):
            QMessageBox.warning(self, "No Selection", "Please select a script to edit.")
            return

        dialog = LuaScriptDialog(
            self,
            script_config=self.lua_scripts[row]
        )

        if dialog.exec():
            config = dialog.get_config()
            self.lua_scripts[row] = config
            self._update_table()
            self.configuration_changed.emit()

    def copy_script(self):
        """Copy selected LUA script."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.lua_scripts):
            QMessageBox.warning(self, "No Selection", "Please select a script to copy.")
            return

        # Copy config
        import copy
        new_config = copy.deepcopy(self.lua_scripts[row])
        new_config["name"] = new_config.get("name", "") + " (Copy)"

        dialog = LuaScriptDialog(
            self,
            script_config=new_config
        )

        if dialog.exec():
            config = dialog.get_config()
            self.lua_scripts.append(config)
            self._update_table()
            self.configuration_changed.emit()

    def delete_script(self):
        """Delete selected LUA script."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.lua_scripts):
            QMessageBox.warning(self, "No Selection", "Please select a script to delete.")
            return

        script_name = self.lua_scripts[row].get("name", "Unnamed")

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete LUA script '{script_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.lua_scripts[row]
            self._update_table()
            self.configuration_changed.emit()

    def clear_all(self):
        """Clear all LUA scripts."""
        if not self.lua_scripts:
            return

        reply = QMessageBox.question(
            self, "Confirm Clear All",
            f"Delete all {len(self.lua_scripts)} LUA scripts?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.lua_scripts.clear()
            self._update_table()
            self.configuration_changed.emit()

    def import_script(self):
        """Import LUA script from file."""
        from PyQt6.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import LUA Script",
            "",
            "LUA Files (*.lua);;Text Files (*.txt);;All Files (*)"
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    script_content = f.read()

                # Create new script config with imported content
                import os
                script_name = os.path.splitext(os.path.basename(filename))[0]

                new_config = {
                    "name": script_name,
                    "enabled": False,  # Disabled by default for safety
                    "description": f"Imported from {os.path.basename(filename)}",
                    "trigger": {
                        "type": "Manual Trigger Only",
                        "period_ms": 100,
                        "channel": 0
                    },
                    "script": script_content,
                    "settings": {
                        "max_execution_ms": 50,
                        "priority": "Normal",
                        "error_action": "Disable Script"
                    }
                }

                dialog = LuaScriptDialog(self, script_config=new_config)

                if dialog.exec():
                    config = dialog.get_config()
                    self.lua_scripts.append(config)
                    self._update_table()
                    self.configuration_changed.emit()

            except Exception as e:
                QMessageBox.critical(
                    self, "Import Error",
                    f"Failed to import script:\n{str(e)}"
                )

    def export_script(self):
        """Export selected LUA script to file."""
        from PyQt6.QtWidgets import QFileDialog

        row = self.table.currentRow()
        if row < 0 or row >= len(self.lua_scripts):
            QMessageBox.warning(self, "No Selection", "Please select a script to export.")
            return

        script = self.lua_scripts[row]
        script_name = script.get("name", "script")

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export LUA Script",
            f"{script_name}.lua",
            "LUA Files (*.lua);;Text Files (*.txt);;All Files (*)"
        )

        if filename:
            try:
                script_content = script.get("script", "")

                # Add header comment
                header = (
                    f"-- {script.get('name', 'Unnamed Script')}\n"
                    f"-- {script.get('description', 'No description')}\n"
                    f"-- Exported from PMU-30 Configurator\n"
                    f"-- Trigger: {script.get('trigger', {}).get('type', 'Manual')}\n"
                    f"-- Priority: {script.get('settings', {}).get('priority', 'Normal')}\n\n"
                )

                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(header + script_content)

                QMessageBox.information(
                    self, "Export Successful",
                    f"Script exported to:\n{filename}"
                )

            except Exception as e:
                QMessageBox.critical(
                    self, "Export Error",
                    f"Failed to export script:\n{str(e)}"
                )

    def load_configuration(self, config: dict):
        """Load LUA scripts from configuration."""
        self.lua_scripts = config.get("lua_scripts", [])
        self._update_table()

    def get_configuration(self) -> dict:
        """Get current LUA scripts configuration."""
        return {
            "lua_scripts": self.lua_scripts
        }

    def reset_to_defaults(self):
        """Reset to default configuration."""
        self.lua_scripts.clear()
        self._update_table()
