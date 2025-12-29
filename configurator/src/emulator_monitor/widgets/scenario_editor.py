"""
Scenario Editor - Widget for creating and running test sequences

This module contains the ScenarioEditorWidget for automated testing.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QListWidget, QLineEdit,
    QSpinBox, QComboBox, QCheckBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from typing import List
import json


class ScenarioEditorWidget(QWidget):
    """Scenario editor for creating and running test sequences."""

    # Signal emitted when a scenario action should be executed
    execute_action = pyqtSignal(dict)  # action dict

    ACTION_TYPES = [
        "Set Output",
        "Set H-Bridge",
        "Set Digital Input",
        "Set Voltage",
        "Set Temperature",
        "Inject Fault",
        "Clear Fault",
        "Wait",
        "Send CAN",
        "Send LIN",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scenario_steps: List[dict] = []
        self._running = False
        self._paused = False
        self._current_step = 0
        self._step_timer = QTimer(self)
        self._step_timer.timeout.connect(self._execute_next_step)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Left side - Step list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()

        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self._new_scenario)
        toolbar.addWidget(self.new_btn)

        self.load_btn = QPushButton("Load")
        self.load_btn.clicked.connect(self._load_scenario)
        toolbar.addWidget(self.load_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save_scenario)
        toolbar.addWidget(self.save_btn)

        toolbar.addStretch()
        left_layout.addLayout(toolbar)

        # Steps list
        self.steps_list = QListWidget()
        self.steps_list.setFont(QFont("Consolas", 10))
        self.steps_list.itemSelectionChanged.connect(self._on_step_selected)
        self.steps_list.itemDoubleClicked.connect(self._edit_step)
        left_layout.addWidget(self.steps_list)

        # Step management buttons
        step_btns = QHBoxLayout()

        self.add_btn = QPushButton("+ Add")
        self.add_btn.clicked.connect(self._add_step)
        step_btns.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._edit_step)
        self.edit_btn.setEnabled(False)
        step_btns.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_step)
        self.delete_btn.setEnabled(False)
        step_btns.addWidget(self.delete_btn)

        self.move_up_btn = QPushButton("^")
        self.move_up_btn.setMaximumWidth(30)
        self.move_up_btn.clicked.connect(self._move_step_up)
        self.move_up_btn.setEnabled(False)
        step_btns.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton("v")
        self.move_down_btn.setMaximumWidth(30)
        self.move_down_btn.clicked.connect(self._move_step_down)
        self.move_down_btn.setEnabled(False)
        step_btns.addWidget(self.move_down_btn)

        left_layout.addLayout(step_btns)

        # Playback controls
        playback_group = QGroupBox("Playback")
        playback_layout = QHBoxLayout(playback_group)

        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self._toggle_playback)
        playback_layout.addWidget(self.play_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop_playback)
        self.stop_btn.setEnabled(False)
        playback_layout.addWidget(self.stop_btn)

        self.loop_check = QCheckBox("Loop")
        playback_layout.addWidget(self.loop_check)

        left_layout.addWidget(playback_group)

        # Progress
        self.progress_label = QLabel("Step: 0 / 0")
        left_layout.addWidget(self.progress_label)

        layout.addWidget(left_panel, 2)

        # Right side - Step editor
        right_panel = QGroupBox("Step Editor")
        right_layout = QVBoxLayout(right_panel)

        # Action type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Action:"))
        self.action_combo = QComboBox()
        self.action_combo.addItems(self.ACTION_TYPES)
        self.action_combo.currentIndexChanged.connect(self._on_action_type_changed)
        type_layout.addWidget(self.action_combo)
        right_layout.addLayout(type_layout)

        # Parameters area (dynamic based on action type)
        self.params_group = QGroupBox("Parameters")
        self.params_layout = QGridLayout(self.params_group)
        right_layout.addWidget(self.params_group)

        # Delay
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay after (ms):"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 60000)
        self.delay_spin.setValue(100)
        self.delay_spin.setSingleStep(100)
        delay_layout.addWidget(self.delay_spin)
        delay_layout.addStretch()
        right_layout.addLayout(delay_layout)

        # Description
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Optional description")
        desc_layout.addWidget(self.desc_edit)
        right_layout.addLayout(desc_layout)

        # Apply button
        self.apply_btn = QPushButton("Apply Changes")
        self.apply_btn.clicked.connect(self._apply_step_changes)
        self.apply_btn.setEnabled(False)
        right_layout.addWidget(self.apply_btn)

        # Test button
        self.test_btn = QPushButton("Test This Step")
        self.test_btn.clicked.connect(self._test_current_step)
        right_layout.addWidget(self.test_btn)

        right_layout.addStretch()
        layout.addWidget(right_panel, 1)

        # Initialize parameters UI
        self._setup_params_for_action(0)

    def _clear_params_layout(self):
        """Clear all widgets from params layout."""
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _setup_params_for_action(self, action_idx: int):
        """Setup parameter inputs for the selected action type."""
        self._clear_params_layout()

        action = self.ACTION_TYPES[action_idx]

        if action == "Set Output":
            self.params_layout.addWidget(QLabel("Channel:"), 0, 0)
            self.param_channel = QSpinBox()
            self.param_channel.setRange(1, 30)
            self.params_layout.addWidget(self.param_channel, 0, 1)

            self.params_layout.addWidget(QLabel("State:"), 1, 0)
            self.param_state = QComboBox()
            self.param_state.addItems(["OFF", "ON"])
            self.params_layout.addWidget(self.param_state, 1, 1)

            self.params_layout.addWidget(QLabel("PWM %:"), 2, 0)
            self.param_pwm = QSpinBox()
            self.param_pwm.setRange(0, 100)
            self.param_pwm.setValue(100)
            self.params_layout.addWidget(self.param_pwm, 2, 1)

        elif action == "Set H-Bridge":
            self.params_layout.addWidget(QLabel("Bridge:"), 0, 0)
            self.param_bridge = QComboBox()
            self.param_bridge.addItems(["HB1", "HB2", "HB3", "HB4"])
            self.params_layout.addWidget(self.param_bridge, 0, 1)

            self.params_layout.addWidget(QLabel("Mode:"), 1, 0)
            self.param_mode = QComboBox()
            self.param_mode.addItems(["COAST", "FORWARD", "REVERSE", "BRAKE", "PARK", "PID"])
            self.params_layout.addWidget(self.param_mode, 1, 1)

            self.params_layout.addWidget(QLabel("PWM %:"), 2, 0)
            self.param_pwm = QSpinBox()
            self.param_pwm.setRange(0, 100)
            self.param_pwm.setValue(50)
            self.params_layout.addWidget(self.param_pwm, 2, 1)

        elif action == "Set Digital Input":
            self.params_layout.addWidget(QLabel("Channel:"), 0, 0)
            self.param_channel = QSpinBox()
            self.param_channel.setRange(1, 20)
            self.params_layout.addWidget(self.param_channel, 0, 1)

            self.params_layout.addWidget(QLabel("State:"), 1, 0)
            self.param_state = QComboBox()
            self.param_state.addItems(["LOW", "HIGH"])
            self.params_layout.addWidget(self.param_state, 1, 1)

        elif action == "Set Voltage":
            self.params_layout.addWidget(QLabel("Voltage (mV):"), 0, 0)
            self.param_voltage = QSpinBox()
            self.param_voltage.setRange(6000, 18000)
            self.param_voltage.setValue(12000)
            self.param_voltage.setSingleStep(100)
            self.params_layout.addWidget(self.param_voltage, 0, 1)

        elif action == "Set Temperature":
            self.params_layout.addWidget(QLabel("Temperature (C):"), 0, 0)
            self.param_temp = QSpinBox()
            self.param_temp.setRange(-40, 150)
            self.param_temp.setValue(25)
            self.params_layout.addWidget(self.param_temp, 0, 1)

        elif action == "Inject Fault":
            self.params_layout.addWidget(QLabel("Channel:"), 0, 0)
            self.param_channel = QSpinBox()
            self.param_channel.setRange(1, 30)
            self.params_layout.addWidget(self.param_channel, 0, 1)

            self.params_layout.addWidget(QLabel("Fault:"), 1, 0)
            self.param_fault = QComboBox()
            self.param_fault.addItems(["Overcurrent (OC)", "Overtemp (OT)", "Short Circuit (SC)", "Open Load (OL)"])
            self.params_layout.addWidget(self.param_fault, 1, 1)

        elif action == "Clear Fault":
            self.params_layout.addWidget(QLabel("Channel:"), 0, 0)
            self.param_channel = QSpinBox()
            self.param_channel.setRange(1, 30)
            self.params_layout.addWidget(self.param_channel, 0, 1)

        elif action == "Wait":
            self.params_layout.addWidget(QLabel("Duration (ms):"), 0, 0)
            self.param_duration = QSpinBox()
            self.param_duration.setRange(10, 60000)
            self.param_duration.setValue(1000)
            self.param_duration.setSingleStep(100)
            self.params_layout.addWidget(self.param_duration, 0, 1)

        elif action == "Send CAN":
            self.params_layout.addWidget(QLabel("Bus:"), 0, 0)
            self.param_bus = QComboBox()
            self.param_bus.addItems(["CAN1", "CAN2", "CAN3", "CAN4"])
            self.params_layout.addWidget(self.param_bus, 0, 1)

            self.params_layout.addWidget(QLabel("ID (hex):"), 1, 0)
            self.param_can_id = QLineEdit("0x100")
            self.params_layout.addWidget(self.param_can_id, 1, 1)

            self.params_layout.addWidget(QLabel("Data (hex):"), 2, 0)
            self.param_can_data = QLineEdit("00 00 00 00 00 00 00 00")
            self.param_can_data.setFont(QFont("Consolas", 9))
            self.params_layout.addWidget(self.param_can_data, 2, 1)

        elif action == "Send LIN":
            self.params_layout.addWidget(QLabel("Bus:"), 0, 0)
            self.param_bus = QComboBox()
            self.param_bus.addItems(["LIN1", "LIN2"])
            self.params_layout.addWidget(self.param_bus, 0, 1)

            self.params_layout.addWidget(QLabel("ID (0-63):"), 1, 0)
            self.param_lin_id = QSpinBox()
            self.param_lin_id.setRange(0, 63)
            self.params_layout.addWidget(self.param_lin_id, 1, 1)

            self.params_layout.addWidget(QLabel("Data (hex):"), 2, 0)
            self.param_lin_data = QLineEdit("00 00 00 00 00 00 00 00")
            self.param_lin_data.setFont(QFont("Consolas", 9))
            self.params_layout.addWidget(self.param_lin_data, 2, 1)

    def _on_action_type_changed(self, index: int):
        """Handle action type combo change."""
        self._setup_params_for_action(index)

    def _on_step_selected(self):
        """Handle step selection in list."""
        selected = self.steps_list.selectedItems()
        has_selection = len(selected) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.move_up_btn.setEnabled(has_selection and self.steps_list.currentRow() > 0)
        self.move_down_btn.setEnabled(has_selection and self.steps_list.currentRow() < len(self.scenario_steps) - 1)
        self.apply_btn.setEnabled(has_selection)

        if has_selection:
            self._load_step_to_editor(self.steps_list.currentRow())

    def _load_step_to_editor(self, index: int):
        """Load step data into the editor."""
        if index < 0 or index >= len(self.scenario_steps):
            return

        step = self.scenario_steps[index]
        action_type = step.get("action", "Set Output")
        action_idx = self.ACTION_TYPES.index(action_type) if action_type in self.ACTION_TYPES else 0

        self.action_combo.setCurrentIndex(action_idx)
        self._setup_params_for_action(action_idx)

        # Load parameters
        params = step.get("params", {})

        if action_type == "Set Output":
            self.param_channel.setValue(params.get("channel", 1))
            self.param_state.setCurrentIndex(1 if params.get("on", False) else 0)
            self.param_pwm.setValue(params.get("pwm", 100))

        elif action_type == "Set H-Bridge":
            self.param_bridge.setCurrentIndex(params.get("bridge", 0))
            self.param_mode.setCurrentIndex(params.get("mode", 0))
            self.param_pwm.setValue(params.get("pwm", 50))

        elif action_type == "Set Digital Input":
            self.param_channel.setValue(params.get("channel", 1))
            self.param_state.setCurrentIndex(1 if params.get("high", False) else 0)

        elif action_type == "Set Voltage":
            self.param_voltage.setValue(params.get("voltage_mv", 12000))

        elif action_type == "Set Temperature":
            self.param_temp.setValue(params.get("temp_c", 25))

        elif action_type == "Inject Fault":
            self.param_channel.setValue(params.get("channel", 1))
            fault_map = {1: 0, 2: 1, 4: 2, 8: 3}
            self.param_fault.setCurrentIndex(fault_map.get(params.get("fault_type", 1), 0))

        elif action_type == "Clear Fault":
            self.param_channel.setValue(params.get("channel", 1))

        elif action_type == "Wait":
            self.param_duration.setValue(params.get("duration_ms", 1000))

        elif action_type == "Send CAN":
            self.param_bus.setCurrentIndex(params.get("bus", 0))
            self.param_can_id.setText(f"0x{params.get('id', 0x100):03X}")
            data = params.get("data", [0]*8)
            self.param_can_data.setText(" ".join(f"{b:02X}" for b in data))

        elif action_type == "Send LIN":
            self.param_bus.setCurrentIndex(params.get("bus", 0))
            self.param_lin_id.setValue(params.get("id", 0))
            data = params.get("data", [0]*8)
            self.param_lin_data.setText(" ".join(f"{b:02X}" for b in data))

        self.delay_spin.setValue(step.get("delay_ms", 100))
        self.desc_edit.setText(step.get("description", ""))

    def _get_step_from_editor(self) -> dict:
        """Get step data from the editor."""
        action_type = self.ACTION_TYPES[self.action_combo.currentIndex()]
        params = {}

        if action_type == "Set Output":
            params = {
                "channel": self.param_channel.value(),
                "on": self.param_state.currentIndex() == 1,
                "pwm": self.param_pwm.value(),
            }
        elif action_type == "Set H-Bridge":
            params = {
                "bridge": self.param_bridge.currentIndex(),
                "mode": self.param_mode.currentIndex(),
                "pwm": self.param_pwm.value(),
            }
        elif action_type == "Set Digital Input":
            params = {
                "channel": self.param_channel.value(),
                "high": self.param_state.currentIndex() == 1,
            }
        elif action_type == "Set Voltage":
            params = {"voltage_mv": self.param_voltage.value()}
        elif action_type == "Set Temperature":
            params = {"temp_c": self.param_temp.value()}
        elif action_type == "Inject Fault":
            fault_values = [1, 2, 4, 8]
            params = {
                "channel": self.param_channel.value(),
                "fault_type": fault_values[self.param_fault.currentIndex()],
            }
        elif action_type == "Clear Fault":
            params = {"channel": self.param_channel.value()}
        elif action_type == "Wait":
            params = {"duration_ms": self.param_duration.value()}
        elif action_type == "Send CAN":
            try:
                can_id = int(self.param_can_id.text(), 0)
                data = bytes.fromhex(self.param_can_data.text().replace(" ", ""))
            except:
                can_id = 0x100
                data = bytes(8)
            params = {
                "bus": self.param_bus.currentIndex(),
                "id": can_id,
                "data": list(data[:8]),
            }
        elif action_type == "Send LIN":
            try:
                data = bytes.fromhex(self.param_lin_data.text().replace(" ", ""))
            except:
                data = bytes(8)
            params = {
                "bus": self.param_bus.currentIndex(),
                "id": self.param_lin_id.value(),
                "data": list(data[:8]),
            }

        return {
            "action": action_type,
            "params": params,
            "delay_ms": self.delay_spin.value(),
            "description": self.desc_edit.text(),
        }

    def _format_step_display(self, step: dict) -> str:
        """Format step for list display."""
        action = step.get("action", "Unknown")
        params = step.get("params", {})
        delay = step.get("delay_ms", 0)
        desc = step.get("description", "")

        if action == "Set Output":
            ch = params.get("channel", 1)
            state = "ON" if params.get("on", False) else "OFF"
            pwm = params.get("pwm", 100)
            text = f"CH{ch} {state} {pwm}%"
        elif action == "Set H-Bridge":
            modes = ["COAST", "FWD", "REV", "BRAKE", "PARK", "PID"]
            br = params.get("bridge", 0) + 1
            mode = modes[params.get("mode", 0)]
            pwm = params.get("pwm", 50)
            text = f"HB{br} {mode} {pwm}%"
        elif action == "Set Digital Input":
            ch = params.get("channel", 1)
            state = "HIGH" if params.get("high", False) else "LOW"
            text = f"DI{ch} {state}"
        elif action == "Set Voltage":
            v = params.get("voltage_mv", 12000)
            text = f"{v/1000:.1f}V"
        elif action == "Set Temperature":
            t = params.get("temp_c", 25)
            text = f"{t}C"
        elif action == "Inject Fault":
            ch = params.get("channel", 1)
            faults = {1: "OC", 2: "OT", 4: "SC", 8: "OL"}
            ft = faults.get(params.get("fault_type", 1), "?")
            text = f"CH{ch} {ft}"
        elif action == "Clear Fault":
            ch = params.get("channel", 1)
            text = f"CH{ch}"
        elif action == "Wait":
            dur = params.get("duration_ms", 1000)
            text = f"{dur}ms"
        elif action == "Send CAN":
            can_id = params.get("id", 0x100)
            text = f"0x{can_id:03X}"
        elif action == "Send LIN":
            lin_id = params.get("id", 0)
            text = f"0x{lin_id:02X}"
        else:
            text = ""

        line = f"{action}: {text}"
        if delay > 0:
            line += f" (+{delay}ms)"
        if desc:
            line += f" [{desc}]"
        return line

    def _refresh_steps_list(self):
        """Refresh the steps list display."""
        self.steps_list.clear()
        for i, step in enumerate(self.scenario_steps):
            text = f"{i+1}. {self._format_step_display(step)}"
            self.steps_list.addItem(text)
        self._update_progress_label()

    def _update_progress_label(self):
        """Update the progress label."""
        total = len(self.scenario_steps)
        if self._running:
            self.progress_label.setText(f"Step: {self._current_step + 1} / {total}")
        else:
            self.progress_label.setText(f"Steps: {total}")

    def _add_step(self):
        """Add a new step."""
        step = self._get_step_from_editor()
        self.scenario_steps.append(step)
        self._refresh_steps_list()
        self.steps_list.setCurrentRow(len(self.scenario_steps) - 1)

    def _edit_step(self):
        """Edit the selected step (loads into editor)."""
        current = self.steps_list.currentRow()
        if current >= 0:
            self._load_step_to_editor(current)

    def _apply_step_changes(self):
        """Apply changes from editor to selected step."""
        current = self.steps_list.currentRow()
        if current >= 0:
            self.scenario_steps[current] = self._get_step_from_editor()
            self._refresh_steps_list()
            self.steps_list.setCurrentRow(current)

    def _delete_step(self):
        """Delete the selected step."""
        current = self.steps_list.currentRow()
        if current >= 0:
            del self.scenario_steps[current]
            self._refresh_steps_list()

    def _move_step_up(self):
        """Move selected step up."""
        current = self.steps_list.currentRow()
        if current > 0:
            self.scenario_steps[current], self.scenario_steps[current-1] = \
                self.scenario_steps[current-1], self.scenario_steps[current]
            self._refresh_steps_list()
            self.steps_list.setCurrentRow(current - 1)

    def _move_step_down(self):
        """Move selected step down."""
        current = self.steps_list.currentRow()
        if current < len(self.scenario_steps) - 1:
            self.scenario_steps[current], self.scenario_steps[current+1] = \
                self.scenario_steps[current+1], self.scenario_steps[current]
            self._refresh_steps_list()
            self.steps_list.setCurrentRow(current + 1)

    def _new_scenario(self):
        """Create a new empty scenario."""
        if self.scenario_steps:
            reply = QMessageBox.question(
                self, "New Scenario",
                "Clear current scenario?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.scenario_steps = []
        self._refresh_steps_list()

    def _load_scenario(self):
        """Load scenario from file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Scenario",
            "", "JSON Files (*.json);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                self.scenario_steps = data.get("steps", [])
                self._refresh_steps_list()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load scenario:\n{e}")

    def _save_scenario(self):
        """Save scenario to file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Scenario",
            "scenario.json", "JSON Files (*.json);;All Files (*)"
        )
        if filename:
            try:
                data = {
                    "version": 1,
                    "steps": self.scenario_steps,
                }
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save scenario:\n{e}")

    def _toggle_playback(self):
        """Toggle scenario playback."""
        if self._running:
            if self._paused:
                self._paused = False
                self.play_btn.setText("Pause")
                self._execute_next_step()
            else:
                self._paused = True
                self.play_btn.setText("Resume")
                self._step_timer.stop()
        else:
            if not self.scenario_steps:
                return
            self._running = True
            self._paused = False
            self._current_step = 0
            self.play_btn.setText("Pause")
            self.stop_btn.setEnabled(True)
            self._execute_next_step()

    def _stop_playback(self):
        """Stop scenario playback."""
        self._running = False
        self._paused = False
        self._step_timer.stop()
        self.play_btn.setText("Play")
        self.stop_btn.setEnabled(False)
        self._update_progress_label()

    def _execute_next_step(self):
        """Execute the next step in the scenario."""
        if not self._running or self._paused:
            return

        if self._current_step >= len(self.scenario_steps):
            if self.loop_check.isChecked():
                self._current_step = 0
            else:
                self._stop_playback()
                return

        # Highlight current step
        self.steps_list.setCurrentRow(self._current_step)
        self._update_progress_label()

        # Get and execute step
        step = self.scenario_steps[self._current_step]
        self.execute_action.emit(step)

        # Get delay and schedule next step
        delay = step.get("delay_ms", 100)
        if step.get("action") == "Wait":
            delay = step.get("params", {}).get("duration_ms", 1000)

        self._current_step += 1
        self._step_timer.start(delay)

    def _test_current_step(self):
        """Test the step currently in the editor."""
        step = self._get_step_from_editor()
        self.execute_action.emit(step)
