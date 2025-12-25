"""
PMU-30 Desktop Suite Launcher
Launches the emulator and configurator together for desktop development/testing.

Owner: R2 m-sport
Date: 2025-12-25
License: Proprietary
"""

import os
import sys
import time
import subprocess
import threading
from pathlib import Path


def get_base_path():
    """Get the base path for bundled resources."""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return Path(sys._MEIPASS)
    else:
        # Running as script
        return Path(__file__).parent


def find_emulator():
    """Find the emulator executable."""
    base = get_base_path()

    # Check bundled location first
    bundled = base / "pmu30_emulator.exe"
    if bundled.exists():
        return str(bundled)

    # Check releases folder
    releases = Path(__file__).parent / "pmu30_emulator.exe"
    if releases.exists():
        return str(releases)

    # Check build folder
    build = Path(__file__).parent.parent / "firmware" / ".pio" / "build" / "pmu30_emulator" / "program.exe"
    if build.exists():
        return str(build)

    return None


def find_configurator():
    """Find the configurator main script or executable."""
    base = get_base_path()

    # Check bundled location
    bundled = base / "configurator" / "main.py"
    if bundled.exists():
        return str(bundled)

    # Check source location
    src = Path(__file__).parent.parent / "configurator" / "src" / "main.py"
    if src.exists():
        return str(src)

    return None


def launch_emulator(emulator_path):
    """Launch the emulator in a separate process."""
    print("[Launcher] Starting PMU-30 Emulator...")

    # Set working directory to firmware folder for config loading
    work_dir = Path(emulator_path).parent
    if "build" in str(work_dir):
        # If running from build folder, use firmware as work dir
        work_dir = work_dir.parent.parent.parent

    try:
        process = subprocess.Popen(
            [emulator_path],
            cwd=str(work_dir),
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
        )
        return process
    except Exception as e:
        print(f"[Launcher] ERROR: Failed to start emulator: {e}")
        return None


def launch_configurator(configurator_path):
    """Launch the configurator with auto-connect to emulator."""
    print("[Launcher] Starting PMU-30 Configurator (auto-connecting to emulator)...")

    work_dir = Path(configurator_path).parent

    try:
        # Use pythonw for GUI app (no console window)
        python_exe = "pythonw" if sys.platform == 'win32' else "python3"

        process = subprocess.Popen(
            [python_exe, configurator_path, "--connect", "localhost:9876"],
            cwd=str(work_dir)
        )
        return process
    except Exception as e:
        print(f"[Launcher] ERROR: Failed to start configurator: {e}")
        return None


def main():
    print("=" * 60)
    print("       PMU-30 Desktop Suite v0.2.1")
    print("       R2 m-sport (c) 2025")
    print("=" * 60)
    print()

    # Find components
    emulator_path = find_emulator()
    configurator_path = find_configurator()

    if not emulator_path:
        print("[Launcher] ERROR: Emulator not found!")
        print("  Expected at: releases/pmu30_emulator.exe")
        input("Press Enter to exit...")
        return 1

    if not configurator_path:
        print("[Launcher] ERROR: Configurator not found!")
        print("  Expected at: configurator/src/main.py")
        input("Press Enter to exit...")
        return 1

    print(f"[Launcher] Emulator: {emulator_path}")
    print(f"[Launcher] Configurator: {configurator_path}")
    print()

    # Launch emulator first
    emu_process = launch_emulator(emulator_path)
    if not emu_process:
        input("Press Enter to exit...")
        return 1

    # Wait for emulator to start
    print("[Launcher] Waiting for emulator to initialize...")
    time.sleep(2)

    # Check if emulator is still running
    if emu_process.poll() is not None:
        print("[Launcher] ERROR: Emulator exited unexpectedly!")
        input("Press Enter to exit...")
        return 1

    # Launch configurator
    cfg_process = launch_configurator(configurator_path)
    if not cfg_process:
        emu_process.terminate()
        input("Press Enter to exit...")
        return 1

    print()
    print("[Launcher] Both applications started successfully!")
    print()
    print("  Emulator:     http://localhost:8080 (WebUI)")
    print("  Protocol:     localhost:9876 (TCP)")
    print()
    print("  Close the configurator window to exit both applications.")
    print()

    # Wait for configurator to exit
    try:
        cfg_process.wait()
    except KeyboardInterrupt:
        print("\n[Launcher] Interrupted by user")

    # Terminate emulator when configurator exits
    print("[Launcher] Configurator closed, stopping emulator...")
    emu_process.terminate()

    try:
        emu_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        emu_process.kill()

    print("[Launcher] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
