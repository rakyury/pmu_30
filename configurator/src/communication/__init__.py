"""
PMU-30 Communication Package

This package provides real-time communication between the PMU-30 Configurator
and the PMU-30 hardware device.

Modules:
    protocol: Binary protocol implementation
    transport_base: Abstract transport interface
    serial_transport: USB Serial transport implementation
    comm_manager: High-level communication manager
    telemetry: Telemetry data structures

Example usage:
    from communication import CommManager, SerialTransport

    transport = SerialTransport()
    manager = CommManager(transport)

    await manager.connect("COM3")
    await manager.subscribe_telemetry()

    async for packet in manager.telemetry_stream():
        print(f"Voltage: {packet.input_voltage}V")
"""

from .protocol import (
    MessageType,
    ProtocolFrame,
    ProtocolError,
    encode_frame,
    decode_frame,
)
from .transport_base import TransportBase, TransportError
from .serial_transport import SerialTransport
from .emulator_transport import EmulatorTransport
from .comm_manager import CommManager, ConnectionState
from .telemetry import TelemetryPacket, ChannelState, FaultFlags
from .device_simulator import DeviceSimulator, VirtualSerialPort

__all__ = [
    # Protocol
    "MessageType",
    "ProtocolFrame",
    "ProtocolError",
    "encode_frame",
    "decode_frame",
    # Transport
    "TransportBase",
    "TransportError",
    "SerialTransport",
    "EmulatorTransport",
    # Manager
    "CommManager",
    "ConnectionState",
    # Telemetry
    "TelemetryPacket",
    "ChannelState",
    "FaultFlags",
    # Simulator
    "DeviceSimulator",
    "VirtualSerialPort",
]

__version__ = "1.0.0"
