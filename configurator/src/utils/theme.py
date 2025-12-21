"""
Theme Manager for PMU-30 Configurator
Handles dark/light mode switching
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt


class ThemeManager:
    """Manages application themes"""

    DARK_STYLESHEET = """
    QMainWindow {
        background-color: #1e1e1e;
        color: #d4d4d4;
    }

    QWidget {
        background-color: #1e1e1e;
        color: #d4d4d4;
    }

    QGroupBox {
        border: 1px solid #3e3e3e;
        border-radius: 5px;
        margin-top: 1ex;
        padding: 10px;
        background-color: #252526;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }

    QPushButton {
        background-color: #0e639c;
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 3px;
    }

    QPushButton:hover {
        background-color: #1177bb;
    }

    QPushButton:pressed {
        background-color: #0d5488;
    }

    QPushButton:disabled {
        background-color: #3e3e3e;
        color: #808080;
    }

    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
        background-color: #3c3c3c;
        color: #d4d4d4;
        border: 1px solid #555555;
        padding: 4px;
        border-radius: 3px;
    }

    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
        border: 1px solid #007acc;
    }

    QTableWidget {
        background-color: #252526;
        alternate-background-color: #2d2d2d;
        gridline-color: #3e3e3e;
        color: #d4d4d4;
        border: 1px solid #3e3e3e;
    }

    QTableWidget::item:selected {
        background-color: #094771;
    }

    QHeaderView::section {
        background-color: #2d2d2d;
        color: #d4d4d4;
        padding: 4px;
        border: 1px solid #3e3e3e;
    }

    QTabWidget::pane {
        border: 1px solid #3e3e3e;
        background-color: #1e1e1e;
    }

    QTabBar::tab {
        background-color: #2d2d2d;
        color: #d4d4d4;
        padding: 8px 16px;
        border: 1px solid #3e3e3e;
        border-bottom: none;
        margin-right: 2px;
    }

    QTabBar::tab:selected {
        background-color: #1e1e1e;
        border-bottom: 2px solid #007acc;
    }

    QTabBar::tab:hover {
        background-color: #383838;
    }

    QMenuBar {
        background-color: #2d2d2d;
        color: #d4d4d4;
    }

    QMenuBar::item:selected {
        background-color: #094771;
    }

    QMenu {
        background-color: #2d2d2d;
        color: #d4d4d4;
        border: 1px solid #3e3e3e;
    }

    QMenu::item:selected {
        background-color: #094771;
    }

    QCheckBox {
        color: #d4d4d4;
    }

    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #555555;
        border-radius: 3px;
        background-color: #3c3c3c;
    }

    QCheckBox::indicator:checked {
        background-color: #007acc;
        border: 1px solid #007acc;
    }

    QLabel {
        color: #d4d4d4;
        background-color: transparent;
    }

    QDialog {
        background-color: #1e1e1e;
    }

    QMessageBox {
        background-color: #1e1e1e;
    }

    QScrollBar:vertical {
        background-color: #1e1e1e;
        width: 12px;
        margin: 0;
    }

    QScrollBar::handle:vertical {
        background-color: #424242;
        min-height: 20px;
        border-radius: 6px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #4e4e4e;
    }

    QScrollBar:horizontal {
        background-color: #1e1e1e;
        height: 12px;
        margin: 0;
    }

    QScrollBar::handle:horizontal {
        background-color: #424242;
        min-width: 20px;
        border-radius: 6px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: #4e4e4e;
    }

    QScrollBar::add-line, QScrollBar::sub-line {
        border: none;
        background: none;
    }
    """

    LIGHT_STYLESHEET = """
    /* Light theme - use default Qt styling */
    """

    @staticmethod
    def apply_dark_theme(app: QApplication):
        """Apply dark theme to application"""
        app.setStyleSheet(ThemeManager.DARK_STYLESHEET)

    @staticmethod
    def apply_light_theme(app: QApplication):
        """Apply light theme to application"""
        app.setStyleSheet(ThemeManager.LIGHT_STYLESHEET)

    @staticmethod
    def toggle_theme(app: QApplication, is_dark: bool):
        """Toggle between dark and light themes"""
        if is_dark:
            ThemeManager.apply_dark_theme(app)
        else:
            ThemeManager.apply_light_theme(app)
