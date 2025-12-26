"""
PMU-30 Integration Tests

These tests verify channel behavior through the emulator with telemetry verification.
They require a running PMU-30 emulator.

To run:
    python -m pytest tests/integration/ -v

Prerequisites:
    1. Start the PMU-30 emulator (firmware/.pio/build/pmu30_emulator/program.exe)
    2. Ensure it's listening on localhost:9876
"""
