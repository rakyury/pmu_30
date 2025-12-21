"""
PMU-30 Configurator Launcher
Choose between Classic and ECUMaster style UI
"""

import sys
import os

def show_launcher():
    """Show launcher dialog to choose UI style."""

    print("=" * 60)
    print("PMU-30 Configurator Launcher")
    print("© 2025 R2 m-sport. All rights reserved.")
    print("=" * 60)
    print()
    print("Choose UI Style:")
    print()
    print("1. ECUMaster Style (Recommended)")
    print("   - Dock-based layout")
    print("   - Project tree with hierarchy")
    print("   - Real-time monitoring panels")
    print("   - Drag & drop panels")
    print("   - All features on one screen")
    print()
    print("2. Classic Style")
    print("   - Tab-based interface")
    print("   - Traditional layout")
    print("   - Simple navigation")
    print()
    print("3. Exit")
    print()

    while True:
        try:
            choice = input("Enter your choice (1-3): ").strip()

            if choice == "1":
                print("\nLaunching ECUMaster Style...")
                os.chdir(os.path.dirname(os.path.abspath(__file__)))
                os.system("python src/main_ecumaster.py")
                break

            elif choice == "2":
                print("\nLaunching Classic Style...")
                os.chdir(os.path.dirname(os.path.abspath(__file__)))
                os.system("python src/main.py")
                break

            elif choice == "3":
                print("\nExiting...")
                break

            else:
                print("Invalid choice. Please enter 1, 2, or 3.")

        except (KeyboardInterrupt, EOFError):
            print("\n\nExiting...")
            break


if __name__ == "__main__":
    show_launcher()
