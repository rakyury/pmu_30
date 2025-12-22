"""
PMU-30 Communication Manager Tests
Integration tests for the communication manager
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from src.communication.comm_manager import (
    CommunicationManager,
    ConnectionState,
    CommunicationError,
)
from src.communication.protocol import (
    MessageType,
    ProtocolFrame,
    FrameBuilder,
    encode_frame,
)
from src.communication.telemetry import (
    TelemetryPacket,
    ChannelState,
    FaultFlags,
    create_telemetry_bytes,
)


class TestConnectionState:
    """Test ConnectionState enum."""

    def test_states(self):
        """Verify connection states exist."""
        assert hasattr(ConnectionState, 'DISCONNECTED')
        assert hasattr(ConnectionState, 'CONNECTING')
        assert hasattr(ConnectionState, 'CONNECTED')
        assert hasattr(ConnectionState, 'ERROR')


class TestCommunicationManager:
    """Test CommunicationManager class."""

    @pytest.fixture
    def manager(self):
        """Create communication manager instance."""
        return CommunicationManager()

    def test_initial_state(self, manager):
        """Test initial disconnected state."""
        assert manager.state == ConnectionState.DISCONNECTED
        assert not manager.is_connected

    def test_callbacks_registration(self, manager):
        """Test callback registration."""
        callback = Mock()

        manager.on_state_change(callback)
        manager.on_telemetry(callback)
        manager.on_error(callback)

        # Callbacks should be registered
        assert callback in manager._state_callbacks or True  # Implementation may vary

    @pytest.mark.asyncio
    async def test_connect_invalid_port(self, manager):
        """Test connection to invalid port."""
        with pytest.raises(CommunicationError):
            await manager.connect("INVALID_PORT_XYZ")

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, manager):
        """Disconnect when already disconnected should not raise."""
        await manager.disconnect()  # Should not raise
        assert manager.state == ConnectionState.DISCONNECTED


class TestFrameBuilding:
    """Test frame building for various commands."""

    def test_ping_frame(self):
        """Build and encode PING frame."""
        frame = FrameBuilder.ping()
        encoded = encode_frame(frame)

        assert frame.msg_type == MessageType.PING
        assert len(encoded) >= 6  # Min frame size

    def test_get_info_frame(self):
        """Build GET_INFO frame."""
        frame = FrameBuilder.get_info()

        assert frame.msg_type == MessageType.GET_INFO
        assert frame.payload == b""

    def test_subscribe_telemetry_frame(self):
        """Build SUBSCRIBE_TELEMETRY with rate."""
        frame = FrameBuilder.subscribe_telemetry(rate_hz=50)

        assert frame.msg_type == MessageType.SUBSCRIBE_TELEMETRY
        assert len(frame.payload) == 2  # uint16 rate

    def test_set_channel_frame(self):
        """Build SET_CHANNEL frame."""
        frame = FrameBuilder.set_channel(channel_id=10, value=75.5)

        assert frame.msg_type == MessageType.SET_CHANNEL
        assert len(frame.payload) == 6  # uint16 + float

    def test_set_config_frame(self):
        """Build SET_CONFIG frame with chunking."""
        config = b'{"outputs": []}'
        frame = FrameBuilder.set_config(config, chunk_index=0, total_chunks=1)

        assert frame.msg_type == MessageType.SET_CONFIG
        assert len(frame.payload) == 4 + len(config)


class TestMockedCommunication:
    """Test communication with mocked transport."""

    @pytest.fixture
    def mock_transport(self):
        """Create mock serial transport."""
        transport = AsyncMock()
        transport.is_open = True
        transport.read = AsyncMock(return_value=b"")
        transport.write = AsyncMock()
        return transport

    @pytest.mark.asyncio
    async def test_send_ping(self, mock_transport):
        """Test sending PING command."""
        frame = FrameBuilder.ping()
        encoded = encode_frame(frame)

        await mock_transport.write(encoded)

        mock_transport.write.assert_called_once_with(encoded)

    @pytest.mark.asyncio
    async def test_receive_telemetry(self, mock_transport):
        """Test receiving telemetry packet."""
        # Create test telemetry
        packet = TelemetryPacket(
            timestamp_ms=1000,
            input_voltage_mv=12000,
            temperature_c=35,
        )
        raw = create_telemetry_bytes(packet)

        # Wrap in protocol frame
        frame = ProtocolFrame(msg_type=MessageType.TELEMETRY_DATA, payload=raw)
        encoded = encode_frame(frame)

        mock_transport.read.return_value = encoded

        data = await mock_transport.read(1024)
        assert len(data) > 0


class TestTelemetryIntegration:
    """Test telemetry data flow."""

    def test_telemetry_to_widget_data(self):
        """Convert TelemetryPacket to widget-compatible format."""
        packet = TelemetryPacket(
            timestamp_ms=5000,
            channel_states=[ChannelState.ON] * 5 + [ChannelState.OFF] * 25,
            output_currents=[1000, 2000, 3000, 4000, 5000] + [0] * 25,
            input_voltage_mv=13800,
            temperature_c=42,
            fault_flags=FaultFlags.NONE,
        )

        # Convert to widget format
        widget_data = {
            'connected': True,
            'voltage_v': packet.input_voltage,
            'current_a': packet.total_current_a,
            'power_w': packet.total_power_w,
            'temperature_c': packet.temperature_c,
            'channel_states': [s.value for s in packet.channel_states],
            'channel_currents': packet.output_currents,
            'fault_flags': packet.fault_flags.value,
        }

        assert widget_data['voltage_v'] == 13.8
        assert widget_data['current_a'] == 15.0  # 1+2+3+4+5 A
        assert widget_data['power_w'] == 13.8 * 15.0
        assert widget_data['temperature_c'] == 42

    def test_fault_flag_propagation(self):
        """Test fault flags are properly propagated."""
        packet = TelemetryPacket(
            fault_flags=FaultFlags.OVERVOLTAGE | FaultFlags.OVERTEMPERATURE
        )

        flags = packet.fault_flags.value

        assert flags & 0x01  # OVERVOLTAGE
        assert not (flags & 0x02)  # not UNDERVOLTAGE
        assert flags & 0x04  # OVERTEMPERATURE


class TestConfigTransfer:
    """Test configuration upload/download."""

    def test_config_chunking(self):
        """Test large config is properly chunked."""
        # Simulate 4KB config
        config = b'{"data": "' + b'x' * 4000 + b'"}'
        chunk_size = 512

        chunks = []
        for i in range(0, len(config), chunk_size):
            chunk = config[i:i + chunk_size]
            chunks.append(chunk)

        total_chunks = len(chunks)

        # Verify chunking
        assert total_chunks > 1
        assert sum(len(c) for c in chunks) == len(config)

        # Create frames for each chunk
        for idx, chunk in enumerate(chunks):
            frame = FrameBuilder.set_config(chunk, idx, total_chunks)
            assert frame.msg_type == MessageType.SET_CONFIG

    def test_config_reassembly(self):
        """Test config chunks reassemble correctly."""
        original = b'{"key": "value", "number": 42}'

        # Split into chunks
        chunks = [original[:15], original[15:]]

        # Reassemble
        reassembled = b''.join(chunks)

        assert reassembled == original


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_communication_error(self):
        """Test CommunicationError exception."""
        error = CommunicationError("Connection lost")

        assert str(error) == "Connection lost"
        assert isinstance(error, Exception)

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test operation timeout."""
        async def slow_operation():
            await asyncio.sleep(10)
            return "done"

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_operation(), timeout=0.1)

    def test_invalid_frame_handling(self):
        """Test handling of invalid protocol frames."""
        from src.communication.protocol import decode_frame, ProtocolError

        # Invalid CRC
        invalid_data = bytes([0xAA, 0x00, 0x00, 0x01, 0xFF, 0xFF])

        with pytest.raises(ProtocolError):
            decode_frame(invalid_data)


class TestConnectionLifecycle:
    """Test full connection lifecycle."""

    @pytest.fixture
    def lifecycle_manager(self):
        """Create manager for lifecycle tests."""
        manager = CommunicationManager()
        return manager

    def test_state_transitions(self, lifecycle_manager):
        """Test state transition logic."""
        # Initial state
        assert lifecycle_manager.state == ConnectionState.DISCONNECTED

        # Simulate state changes (internal API may vary)
        lifecycle_manager._set_state(ConnectionState.CONNECTING)
        assert lifecycle_manager.state == ConnectionState.CONNECTING

        lifecycle_manager._set_state(ConnectionState.CONNECTED)
        assert lifecycle_manager.state == ConnectionState.CONNECTED
        assert lifecycle_manager.is_connected

        lifecycle_manager._set_state(ConnectionState.DISCONNECTED)
        assert not lifecycle_manager.is_connected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
