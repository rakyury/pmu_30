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
    /* Fluent Design for Windows 11 - Dark Theme */

    QMainWindow {
        background-color: #202020;
        color: #ffffff;
    }

    QWidget {
        background-color: #202020;
        color: #ffffff;
    }

    QGroupBox {
        border: 1px solid #3d3d3d;
        border-radius: 8px;
        margin-top: 12px;
        padding: 16px;
        padding-top: 24px;
        background-color: rgba(44, 44, 44, 180);
        color: #ffffff;
        font-size: 14px;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        top: 4px;
        padding: 0 8px;
        color: #ffffff;
        font-weight: 600;
    }

    QPushButton {
        background-color: #0078d4;
        color: #ffffff;
        border: 1px solid #0078d4;
        padding: 8px 16px;
        border-radius: 4px;
        font-size: 14px;
    }

    QPushButton:hover {
        background-color: #1a86d9;
        border: 1px solid #1a86d9;
    }

    QPushButton:pressed {
        background-color: #005a9e;
        border: 1px solid #005a9e;
    }

    QPushButton:disabled {
        background-color: #3d3d3d;
        color: #7a7a7a;
        border: 1px solid #3d3d3d;
    }

    QLineEdit {
        background-color: #2c2c2c;
        color: #ffffff;
        border: 1px solid #3d3d3d;
        border-bottom: 2px solid #3d3d3d;
        padding: 8px;
        border-radius: 4px;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
    }

    QLineEdit:hover {
        background-color: #333333;
        border-bottom: 2px solid #505050;
    }

    QLineEdit:focus {
        border-bottom: 2px solid #0078d4;
        background-color: #2c2c2c;
    }

    QSpinBox, QDoubleSpinBox, QComboBox {
        background-color: #2c2c2c;
        color: #ffffff;
        border: 1px solid #3d3d3d;
        border-bottom: 2px solid #3d3d3d;
        padding: 7px 4px 7px 8px;
        padding-right: 24px;
        border-radius: 4px;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
    }

    QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {
        background-color: #333333;
        border-bottom: 2px solid #505050;
    }

    QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
        border-bottom: 2px solid #0078d4;
        background-color: #2c2c2c;
    }

    QTableWidget {
        background-color: #2c2c2c;
        alternate-background-color: #282828;
        gridline-color: #3d3d3d;
        color: #ffffff;
        border: 1px solid #3d3d3d;
        border-radius: 8px;
    }

    QTableWidget::item {
        padding: 6px;
    }

    QTableWidget::item:selected {
        background-color: rgba(0, 120, 212, 0.6);
        color: #ffffff;
    }

    QTableWidget::item:hover {
        background-color: rgba(255, 255, 255, 0.05);
    }

    QHeaderView::section {
        background-color: #2c2c2c;
        color: #ffffff;
        padding: 10px;
        border: none;
        border-bottom: 1px solid #3d3d3d;
        border-right: 1px solid #3d3d3d;
        font-weight: 600;
        font-size: 13px;
    }

    QHeaderView::section:hover {
        background-color: #333333;
    }

    QTabWidget::pane {
        border: 1px solid #3d3d3d;
        background-color: #202020;
        border-radius: 8px;
        top: -1px;
    }

    QTabBar::tab {
        background-color: transparent;
        color: #a0a0a0;
        padding: 10px 20px;
        border: none;
        border-bottom: 3px solid transparent;
        margin-right: 4px;
        font-size: 14px;
    }

    QTabBar::tab:selected {
        background-color: transparent;
        color: #ffffff;
        border-bottom: 3px solid #0078d4;
    }

    QTabBar::tab:hover {
        background-color: rgba(255, 255, 255, 0.05);
        color: #ffffff;
    }

    QMenuBar {
        background-color: #2c2c2c;
        color: #ffffff;
        padding: 4px;
        border-bottom: 1px solid #3d3d3d;
    }

    QMenuBar::item {
        background-color: transparent;
        padding: 6px 12px;
        border-radius: 4px;
    }

    QMenuBar::item:selected {
        background-color: rgba(255, 255, 255, 0.08);
    }

    QMenuBar::item:pressed {
        background-color: rgba(255, 255, 255, 0.05);
    }

    QMenu {
        background-color: #2c2c2c;
        color: #ffffff;
        border: 1px solid #3d3d3d;
        border-radius: 8px;
        padding: 4px;
    }

    QMenu::item {
        padding: 8px 32px 8px 16px;
        border-radius: 4px;
        margin: 2px;
    }

    QMenu::item:selected {
        background-color: rgba(255, 255, 255, 0.08);
    }

    QMenu::separator {
        height: 1px;
        background-color: #3d3d3d;
        margin: 4px 8px;
    }

    QCheckBox {
        color: #ffffff;
        spacing: 10px;
    }

    QCheckBox::indicator {
        width: 20px;
        height: 20px;
        border: 2px solid #646464;
        border-radius: 4px;
        background-color: transparent;
    }

    QCheckBox::indicator:hover {
        border: 2px solid #0078d4;
        background-color: rgba(0, 120, 212, 0.1);
    }

    QCheckBox::indicator:checked {
        background-color: #0078d4;
        border: 2px solid #0078d4;
        image: url(none);
    }

    QCheckBox::indicator:checked:hover {
        background-color: #1a86d9;
        border: 2px solid #1a86d9;
    }

    QLabel {
        color: #ffffff;
        background-color: transparent;
    }

    QDialog {
        background-color: #202020;
    }

    QMessageBox {
        background-color: #202020;
    }

    QToolTip {
        background-color: #2c2c2c;
        color: #ffffff;
        border: 1px solid #0078d4;
        padding: 8px;
        border-radius: 4px;
        font-size: 13px;
    }

    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 28px;
        border-left: none;
        background-color: transparent;
        border-top-right-radius: 4px;
        border-bottom-right-radius: 4px;
    }

    QComboBox::drop-down:hover {
        background-color: rgba(255, 255, 255, 0.05);
    }

    QComboBox::drop-down:pressed {
        background-color: rgba(255, 255, 255, 0.03);
    }

    QComboBox::down-arrow {
        width: 0px;
        height: 0px;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid #a0a0a0;
        margin: 6px;
    }

    QComboBox::down-arrow:hover {
        border-top: 5px solid #ffffff;
    }

    QComboBox QAbstractItemView {
        background-color: #2c2c2c;
        color: #ffffff;
        border: 1px solid #3d3d3d;
        border-radius: 8px;
        selection-background-color: rgba(0, 120, 212, 0.6);
        selection-color: #ffffff;
        outline: none;
        padding: 4px;
    }

    QComboBox QAbstractItemView::item {
        padding: 8px;
        border-radius: 4px;
        margin: 2px;
    }

    QComboBox QAbstractItemView::item:hover {
        background-color: rgba(255, 255, 255, 0.08);
    }

    QScrollBar:vertical {
        background-color: transparent;
        width: 12px;
        margin: 0;
    }

    QScrollBar::handle:vertical {
        background-color: #646464;
        min-height: 30px;
        border-radius: 6px;
        margin: 2px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #7a7a7a;
    }

    QScrollBar::handle:vertical:pressed {
        background-color: #8a8a8a;
    }

    QScrollBar:horizontal {
        background-color: transparent;
        height: 12px;
        margin: 0;
    }

    QScrollBar::handle:horizontal {
        background-color: #646464;
        min-width: 30px;
        border-radius: 6px;
        margin: 2px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: #7a7a7a;
    }

    QScrollBar::handle:horizontal:pressed {
        background-color: #8a8a8a;
    }

    QScrollBar::add-line, QScrollBar::sub-line {
        border: none;
        background: none;
    }

    QScrollBar::add-page, QScrollBar::sub-page {
        background: none;
    }

    QSpinBox::up-button, QDoubleSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        background-color: transparent;
        border: none;
        width: 24px;
        border-top-right-radius: 4px;
    }

    QSpinBox::down-button, QDoubleSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        background-color: transparent;
        border: none;
        width: 24px;
        border-bottom-right-radius: 4px;
    }

    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
        background-color: rgba(255, 255, 255, 0.05);
    }

    QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
    QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {
        background-color: rgba(255, 255, 255, 0.03);
    }

    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
        width: 0px;
        height: 0px;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 5px solid #a0a0a0;
        margin: 4px;
    }

    QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover {
        border-bottom: 5px solid #ffffff;
    }

    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
        width: 0px;
        height: 0px;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid #a0a0a0;
        margin: 4px;
    }

    QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {
        border-top: 5px solid #ffffff;
    }

    QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled,
    QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {
        border-top-color: #505050;
        border-bottom-color: #505050;
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
