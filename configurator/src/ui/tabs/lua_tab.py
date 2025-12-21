"""Lua Scripts Tab"""
from .base_tab import BaseTab
from PyQt6.QtWidgets import QVBoxLayout, QLabel
class LuaTab(BaseTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Lua 5.4 Scripting"))
    def load_configuration(self, config: dict): pass
    def get_configuration(self) -> dict: return {}
    def reset_to_defaults(self): pass
