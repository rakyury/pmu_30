"""
Pytest configuration for integration tests.

Provides fixtures for connecting to the PMU-30 emulator.
"""

import pytest
import asyncio

from .helpers import (
    EmulatorTransport,
    AsyncProtocolHandler,
)


@pytest.fixture
async def emulator_connection():
    """
    Fixture to connect to the emulator.

    Yields an AsyncProtocolHandler connected to the running emulator.
    Skips test if emulator is not running.
    """
    if not EmulatorTransport.is_emulator_running():
        pytest.skip("PMU-30 emulator not running")

    transport = EmulatorTransport()
    try:
        connected = await asyncio.wait_for(
            transport.connect("localhost:9876"),
            timeout=5.0
        )
    except Exception:
        pytest.skip("Could not connect to emulator")

    if not connected:
        pytest.skip("Could not connect to emulator")

    protocol = AsyncProtocolHandler(transport)
    await protocol.start()

    yield protocol

    await protocol.stop()
    await transport.disconnect()


@pytest.fixture
async def protocol_handler(emulator_connection):
    """Alias for emulator_connection for backward compatibility."""
    return emulator_connection
