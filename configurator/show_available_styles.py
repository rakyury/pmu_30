"""
Show available Qt styles on this system
"""

import sys
from PyQt6.QtWidgets import QApplication, QStyleFactory

def show_available_styles():
    """Display all available Qt styles."""

    # Create temporary QApplication to access QStyleFactory
    app = QApplication(sys.argv)

    print("=" * 60)
    print("AVAILABLE QT6 STYLES ON THIS SYSTEM")
    print("=" * 60)
    print()

    # Get available styles
    styles = QStyleFactory.keys()

    print(f"Total styles available: {len(styles)}")
    print()

    for i, style in enumerate(styles, 1):
        print(f"{i}. {style}")

    print()
    print("=" * 60)
    print("CUSTOM STYLES")
    print("=" * 60)
    print()
    print("✓ Fluent Design (Custom) - Our custom Windows 11 theme")
    print()

    print("=" * 60)
    print("USAGE")
    print("=" * 60)
    print()
    print("1. Open PMU-30 Configurator")
    print("2. Go to: View → Application Style")
    print("3. Select desired style from the menu")
    print()
    print("Current default: Fluent Design (Custom)")
    print()

if __name__ == "__main__":
    show_available_styles()
