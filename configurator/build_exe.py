#!/usr/bin/env python3
"""
PMU-30 Configurator - Build Script
Creates a portable executable with all dependencies

Usage:
    python build_exe.py [--onefile] [--debug]

Options:
    --onefile   Create single-file executable (larger, slower startup)
    --debug     Include debug console
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path


def check_python_version():
    """Check Python version is 3.10+"""
    if sys.version_info < (3, 10):
        print("ERROR: Python 3.10 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    return True


def install_dependencies():
    """Install required dependencies"""
    print("\n" + "=" * 60)
    print("Installing dependencies...")
    print("=" * 60)

    requirements_file = Path(__file__).parent / "requirements.txt"

    if not requirements_file.exists():
        print(f"ERROR: {requirements_file} not found")
        return False

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
        capture_output=False
    )

    if result.returncode != 0:
        print("ERROR: Failed to install dependencies")
        return False

    # Ensure PyInstaller is installed
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "pyinstaller>=6.0.0"],
        capture_output=False
    )

    return True


def clean_build():
    """Clean previous build artifacts"""
    print("\n" + "=" * 60)
    print("Cleaning previous build...")
    print("=" * 60)

    project_dir = Path(__file__).parent

    for folder in ["build", "dist"]:
        path = project_dir / folder
        if path.exists():
            print(f"  Removing {folder}/...")
            shutil.rmtree(path)

    # Remove .pyc files
    for pyc in project_dir.rglob("*.pyc"):
        pyc.unlink()

    # Remove __pycache__ directories
    for pycache in project_dir.rglob("__pycache__"):
        if pycache.is_dir():
            shutil.rmtree(pycache)


def build_executable(onefile: bool = False, debug: bool = False):
    """Build the executable using PyInstaller"""
    print("\n" + "=" * 60)
    print("Building PMU-30 Configurator...")
    print("This may take several minutes...")
    print("=" * 60)

    project_dir = Path(__file__).parent
    src_dir = project_dir / "src"

    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--name", "PMU-30 Configurator",
        "--windowed" if not debug else "--console",
    ]

    # Add paths
    cmd.extend(["--paths", str(src_dir)])
    cmd.extend(["--paths", str(project_dir)])

    # Hidden imports
    hidden_imports = [
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtSvg",
        "PyQt6.QtNetwork",
        "serial",
        "serial.tools",
        "serial.tools.list_ports",
        "serial.tools.list_ports_windows",
        "can",
        "cantools",
        "pyqtgraph",
        "numpy",
        "yaml",
        "json5",
        "pydantic",
        "websockets",
        "requests",
    ]

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Collect data
    cmd.extend(["--collect-data", "pyqtgraph"])
    cmd.extend(["--collect-data", "cantools"])

    # Excludes
    excludes = ["black", "pylint", "pytest", "pytest_qt", "tkinter", "matplotlib"]
    for exc in excludes:
        cmd.extend(["--exclude-module", exc])

    # One file or one folder
    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # Version info
    version_file = project_dir / "version_info.txt"
    if version_file.exists():
        cmd.extend(["--version-file", str(version_file)])

    # Runtime hook for portable execution
    runtime_hook = project_dir / "runtime_hook.py"
    if runtime_hook.exists():
        cmd.extend(["--runtime-hook", str(runtime_hook)])

    # Entry point
    cmd.append(str(src_dir / "main.py"))

    print(f"\nRunning: {' '.join(cmd[:5])}...")

    result = subprocess.run(cmd, cwd=str(project_dir))

    if result.returncode != 0:
        print("\nERROR: Build failed!")
        return False

    return True


def print_success():
    """Print success message with location info"""
    project_dir = Path(__file__).parent
    dist_dir = project_dir / "dist" / "PMU-30 Configurator"

    print("\n" + "=" * 60)
    print("BUILD SUCCESSFUL!")
    print("=" * 60)
    print()
    print("The portable application is located at:")
    print(f"  {dist_dir}")
    print()
    print("To run the application:")
    print(f"  {dist_dir / 'PMU-30 Configurator.exe'}")
    print()
    print("You can copy the entire folder to any location")
    print("and run it without Python installation.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Build PMU-30 Configurator portable executable"
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Create single-file executable (larger, slower startup)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Include debug console window"
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip dependency installation"
    )
    parser.add_argument(
        "--skip-clean",
        action="store_true",
        help="Skip cleaning previous build"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("PMU-30 Configurator - Build Script")
    print("=" * 60)

    # Check Python version
    if not check_python_version():
        return 1

    print(f"Python version: {sys.version}")

    # Install dependencies
    if not args.skip_deps:
        if not install_dependencies():
            return 1

    # Clean previous build
    if not args.skip_clean:
        clean_build()

    # Build executable
    if not build_executable(onefile=args.onefile, debug=args.debug):
        return 1

    print_success()
    return 0


if __name__ == "__main__":
    sys.exit(main())
