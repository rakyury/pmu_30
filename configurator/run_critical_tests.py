#!/usr/bin/env python3
"""
Run Critical Tests for PMU-30 Configurator

This script runs the critical control flow tests that MUST PASS
after any firmware or configurator change.

Usage:
    python run_critical_tests.py [--start-emulator] [--verbose]

Options:
    --start-emulator    Start the emulator before running tests
    --verbose           Show detailed test output
    --help              Show this help

Test Coverage:
    - Digital Input (LOW-SIDE) -> Power Output
    - Digital Input (HIGH-SIDE) -> Power Output
    - Timer (oneshot) -> Power Output
    - Timer (retriggerable) -> Power Output
    - Input type change -> Output state update
"""

import sys
import os
import subprocess
import time
import argparse
from pathlib import Path

# Add src to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "src"))

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header():
    """Print script header."""
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}  PMU-30 Critical Control Flow Tests{RESET}")
    print(f"{CYAN}{'='*60}{RESET}\n")


def check_emulator_running() -> bool:
    """Check if emulator is running."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 9876))
        sock.close()
        return result == 0
    except Exception:
        return False


def start_emulator() -> bool:
    """Start the emulator if not running."""
    emulator_path = SCRIPT_DIR.parent / "firmware" / ".pio" / "build" / "pmu30_emulator" / "program.exe"

    if not emulator_path.exists():
        print(f"{RED}Error: Emulator not found at {emulator_path}{RESET}")
        print(f"Build the emulator first: cd firmware && python -m platformio run -e pmu30_emulator")
        return False

    print(f"{YELLOW}Starting emulator...{RESET}")
    subprocess.Popen(
        [str(emulator_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    )

    # Wait for emulator to start
    for i in range(10):
        time.sleep(0.5)
        if check_emulator_running():
            print(f"{GREEN}Emulator started successfully{RESET}")
            return True

    print(f"{RED}Failed to start emulator{RESET}")
    return False


def run_tests(verbose: bool = False) -> int:
    """Run the critical tests."""
    test_file = SCRIPT_DIR / "tests" / "integration" / "test_control_flow_critical.py"

    if not test_file.exists():
        print(f"{RED}Error: Test file not found at {test_file}{RESET}")
        return 1

    cmd = [
        sys.executable, "-m", "pytest",
        str(test_file),
        "-v" if verbose else "-q",
        "-s" if verbose else "",
        "--timeout=60",
        "--tb=short"
    ]

    # Remove empty strings
    cmd = [c for c in cmd if c]

    print(f"{CYAN}Running tests: {' '.join(cmd)}{RESET}\n")

    result = subprocess.run(cmd, cwd=str(SCRIPT_DIR))
    return result.returncode


def print_summary(success: bool, duration: float):
    """Print test summary."""
    print(f"\n{CYAN}{'='*60}{RESET}")
    if success:
        print(f"{GREEN}{BOLD}  ALL CRITICAL TESTS PASSED{RESET}")
        print(f"{GREEN}  Duration: {duration:.1f}s{RESET}")
    else:
        print(f"{RED}{BOLD}  CRITICAL TESTS FAILED{RESET}")
        print(f"{RED}  Please fix issues before committing!{RESET}")
    print(f"{CYAN}{'='*60}{RESET}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Run PMU-30 Critical Control Flow Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--start-emulator", "-e",
        action="store_true",
        help="Start the emulator before running tests"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed test output"
    )

    args = parser.parse_args()

    print_header()

    # Check/start emulator
    if not check_emulator_running():
        if args.start_emulator:
            if not start_emulator():
                return 1
            time.sleep(1)  # Give emulator time to initialize
        else:
            print(f"{YELLOW}Emulator not running.{RESET}")
            print(f"Start it manually or use --start-emulator flag")
            print(f"\nEmulator path: firmware/.pio/build/pmu30_emulator/program.exe\n")
            return 1
    else:
        print(f"{GREEN}Emulator is running{RESET}")

    # Run tests
    start_time = time.time()
    result = run_tests(args.verbose)
    duration = time.time() - start_time

    # Summary
    print_summary(result == 0, duration)

    return result


if __name__ == "__main__":
    sys.exit(main())
