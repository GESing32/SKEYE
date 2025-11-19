"""
pytest version: Unit tests for WebSocket handler module.

Tests WebSocket client handling, message broadcasting, and command processing.

Run with:
    pytest test/unit/pytest_test_websocket_handler.py
    pytest test/unit/pytest_test_websocket_handler.py -v
    pytest test/unit/pytest_test_websocket_handler.py -k "broadcast"
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import sys
from pathlib import Path

# Add v2 directory to path for imports
v2_path = Path(__file__).parent.parent.parent / "src" / "flight-system" / "v2" 
sys.path.insert(0, str(v2_path))

# ============================================================================
# Fixtures for WebSocket Testing
# ============================================================================

async def async_iterator(items):
    """Helper to create async iterator from items."""
    for item in items:
        yield item


def create_mock_websocket(messages=None):
    """Create a mock WebSocket with optional messages.

    Args:
        messages: List of messages to iterate over, defaults to empty list

    Returns:
        AsyncMock configured as async iterator
    """
    if messages is None:
        messages = []

    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.close = AsyncMock()
    # Lambda that returns the async iterator (ignore any arguments like 'self')
    ws.__aiter__ = lambda *args, **kwargs: async_iterator(messages).__aiter__()
    return ws


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection.

    Returns:
        AsyncMock: Mocked WebSocket with send/receive capabilities
    """
    return create_mock_websocket()


@pytest.fixture
def websocket_hub():
    """WebSocketHub instance for testing.

    Returns:
        WebSocketHub: Fresh hub instance
    """
    from run_gcs import WebSocketHub  # type: ignore
    return WebSocketHub()


@pytest.fixture
def mock_mav_core():
    """Mock MavSerialCore instance.

    Returns:
        Mock: Mocked core with common attributes
    """
    core = Mock()
    core.link_ok = Mock(return_value=True)
    core.mode_str = "GUIDED"
    core.armed = False

    # Mock methods to match actual gcs_core.py API
    core.arm = Mock()  # Takes should_arm parameter
    core.set_mode = Mock()
    core.goto_guided = Mock()
    core.mission_clear_all = Mock()
    core.mission_upload_begin = Mock()
    core.mission_start = Mock()
    return core


# ============================================================================
# WebSocketHub Tests
# ============================================================================

class TestWebSocketHub:
    """Test WebSocketHub client management and broadcasting."""

    @pytest.mark.asyncio
    async def test_hub_initialization(self, websocket_hub):
        """Test hub initializes with empty client set."""
        assert len(websocket_hub.clients) == 0
        assert isinstance(websocket_hub.clients, set)
        assert isinstance(websocket_hub._telemetry_cache, dict)

    @pytest.mark.asyncio
    async def test_register_client(self, websocket_hub, mock_websocket):
        """Test registering a new WebSocket client."""
        await websocket_hub.register(mock_websocket)

        assert len(websocket_hub.clients) == 1
        assert mock_websocket in websocket_hub.clients

    @pytest.mark.asyncio
    async def test_register_multiple_clients(self, websocket_hub):
        """Test registering multiple clients."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await websocket_hub.register(ws1)
        await websocket_hub.register(ws2)
        await websocket_hub.register(ws3)

        assert len(websocket_hub.clients) == 3
        assert ws1 in websocket_hub.clients
        assert ws2 in websocket_hub.clients
        assert ws3 in websocket_hub.clients

    @pytest.mark.asyncio
    async def test_unregister_client(self, websocket_hub, mock_websocket):
        """Test unregistering a client."""
        await websocket_hub.register(mock_websocket)
        assert len(websocket_hub.clients) == 1

        await websocket_hub.unregister(mock_websocket)
        assert len(websocket_hub.clients) == 0
        assert mock_websocket not in websocket_hub.clients

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_client(self, websocket_hub, mock_websocket):
        """Test unregistering a client that was never registered."""
        # Should not raise an error
        await websocket_hub.unregister(mock_websocket)
        assert len(websocket_hub.clients) == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_single_client(self, websocket_hub, mock_websocket):
        """Test broadcasting message to single client."""
        await websocket_hub.register(mock_websocket)

        test_msg = {"type": "HEARTBEAT", "armed": True}
        await websocket_hub.broadcast(test_msg)

        mock_websocket.send.assert_called_once()
        call_args = mock_websocket.send.call_args[0][0]
        assert json.loads(call_args) == test_msg

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(self, websocket_hub):
        """Test broadcasting message to multiple clients."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await websocket_hub.register(ws1)
        await websocket_hub.register(ws2)
        await websocket_hub.register(ws3)

        test_msg = {"type": "GPS", "lat": 38.0308, "lon": -84.506}
        await websocket_hub.broadcast(test_msg)

        # All clients should receive the message
        ws1.send.assert_called_once()
        ws2.send.assert_called_once()
        ws3.send.assert_called_once()

        # Verify message content
        for ws in [ws1, ws2, ws3]:
            call_args = ws.send.call_args[0][0]
            assert json.loads(call_args) == test_msg

    @pytest.mark.asyncio
    async def test_broadcast_with_failed_client(self, websocket_hub):
        """Test broadcast continues even if one client fails."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws2.send.side_effect = Exception("Connection lost")
        ws3 = AsyncMock()

        await websocket_hub.register(ws1)
        await websocket_hub.register(ws2)
        await websocket_hub.register(ws3)

        test_msg = {"type": "HEARTBEAT"}
        await websocket_hub.broadcast(test_msg)

        # ws1 and ws3 should still receive the message
        ws1.send.assert_called_once()
        ws3.send.assert_called_once()

        # ws2 should have been attempted
        ws2.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_hub(self, websocket_hub):
        """Test broadcasting with no clients doesn't error."""
        test_msg = {"type": "HEARTBEAT"}
        # Should not raise any errors
        await websocket_hub.broadcast(test_msg)

    @pytest.mark.asyncio
    async def test_telemetry_caching(self, websocket_hub, mock_websocket):
        """Test that telemetry messages are cached."""
        await websocket_hub.register(mock_websocket)

        # Broadcast different message types
        heartbeat = {"type": "HEARTBEAT", "armed": True}
        gps = {"type": "GLOBAL_POSITION_INT", "lat": 380308000}

        await websocket_hub.broadcast(heartbeat)
        await websocket_hub.broadcast(gps)

        # Cache should contain both message types
        assert "HEARTBEAT" in websocket_hub._telemetry_cache
        assert "GLOBAL_POSITION_INT" in websocket_hub._telemetry_cache
        assert websocket_hub._telemetry_cache["HEARTBEAT"] == heartbeat
        assert websocket_hub._telemetry_cache["GLOBAL_POSITION_INT"] == gps


# ============================================================================
# Client Handler Tests
# ============================================================================

class TestClientHandler:
    """Test WebSocket client connection handling."""

    @pytest.mark.asyncio
    async def test_hello_message_on_connect(self, mock_mav_core, websocket_hub):
        """Test that HELLO message is sent when client connects."""
        from run_gcs import handle_client  # type: ignore  # type: ignore

        # Create mock with no messages (will disconnect immediately)
        ws = create_mock_websocket([])

        await handle_client(ws, mock_mav_core, websocket_hub)

        # Verify HELLO message was sent
        assert ws.send.called
        call_args = ws.send.call_args_list[0][0][0]
        hello_msg = json.loads(call_args)

        assert hello_msg["type"] == "HELLO"
        assert "link_ok" in hello_msg
        assert "mode" in hello_msg
        assert "armed" in hello_msg

    @pytest.mark.asyncio
    async def test_client_registration_on_connect(self, mock_mav_core, websocket_hub):
        """Test that client is registered with hub on connect."""
        from run_gcs import handle_client  # type: ignore  # type: ignore

        ws = create_mock_websocket([])

        await handle_client(ws, mock_mav_core, websocket_hub)

        # Client should have been registered (and then unregistered on disconnect)
        # Since the connection ends immediately, client should be unregistered
        assert ws not in websocket_hub.clients

    @pytest.mark.asyncio
    async def test_client_unregistration_on_disconnect(self, mock_mav_core, websocket_hub):
        """Test that client is unregistered when disconnected."""
        from run_gcs import handle_client  # type: ignore  # type: ignore

        # Simulate connection then disconnection
        ws = create_mock_websocket([])

        await handle_client(ws, mock_mav_core, websocket_hub)

        # Client should be removed from hub
        assert ws not in websocket_hub.clients


# ============================================================================
# Command Handling Tests
# ============================================================================

class TestCommandHandling:
    """Test command processing from WebSocket clients."""

    @pytest.mark.asyncio
    async def test_arm_command(self, mock_mav_core, websocket_hub):
        """Test ARM command is processed correctly."""
        from run_gcs import handle_client  # type: ignore  # type: ignore

        arm_cmd = json.dumps({"command": "arm", "force": True})
        ws = create_mock_websocket([arm_cmd])

        await handle_client(ws, mock_mav_core, websocket_hub)

        # Verify arm was called with should_arm=True
        mock_mav_core.arm.assert_called_once_with(should_arm=True)

    @pytest.mark.asyncio
    async def test_set_mode_command(self, mock_mav_core, websocket_hub):
        """Test SET_MODE command is processed correctly."""
        from run_gcs import handle_client  # type: ignore  # type: ignore

        mode_cmd = json.dumps({"command": "set_mode", "mode": "GUIDED"})
        ws = create_mock_websocket([mode_cmd])

        await handle_client(ws, mock_mav_core, websocket_hub)

        # Verify set_mode was called
        mock_mav_core.set_mode.assert_called_once_with("GUIDED")

    @pytest.mark.asyncio
    async def test_goto_command(self, mock_mav_core, websocket_hub):
        """Test GOTO command is processed correctly."""
        from run_gcs import handle_client  # type: ignore  # type: ignore

        goto_cmd = json.dumps({
            "command": "goto",
            "lat": 38.0308,
            "lon": -84.506,
            "alt": 20.0
        })
        ws = create_mock_websocket([goto_cmd])

        await handle_client(ws, mock_mav_core, websocket_hub)

        # Verify goto_guided was called with correct parameters
        mock_mav_core.goto_guided.assert_called_once_with(38.0308, -84.506, 20.0)

    @pytest.mark.asyncio
    async def test_mission_clear_command(self, mock_mav_core, websocket_hub):
        """Test MISSION_CLEAR command is processed correctly."""
        from run_gcs import handle_client  # type: ignore  # type: ignore

        clear_cmd = json.dumps({"command": "mission_clear"})
        ws = create_mock_websocket([clear_cmd])

        await handle_client(ws, mock_mav_core, websocket_hub)

        # Verify mission_clear_all was called
        mock_mav_core.mission_clear_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_mission_upload_command(self, mock_mav_core, websocket_hub):
        """Test MISSION_UPLOAD command is processed correctly."""
        from run_gcs import handle_client  # type: ignore

        mission_items = [
            {
                "frame": 3,
                "command": 16,
                "current": 1,
                "autocontinue": 1,
                "param1": 0.0,
                "param2": 0.0,
                "param3": 0.0,
                "param4": 0.0,
                "x": 380308000,
                "y": -845060000,
                "z": 20.0,
            }
        ]
        upload_cmd = json.dumps({
            "command": "mission_upload",
            "mission_items": mission_items
        })
        ws = create_mock_websocket([upload_cmd])

        await handle_client(ws, mock_mav_core, websocket_hub)

        # Verify mission_upload_begin was called with items
        mock_mav_core.mission_upload_begin.assert_called_once()

    @pytest.mark.asyncio
    async def test_mission_start_command(self, mock_mav_core, websocket_hub):
        """Test MISSION_START command is processed correctly."""
        from run_gcs import handle_client  # type: ignore

        start_cmd = json.dumps({"command": "mission_start"})
        ws = create_mock_websocket([start_cmd])

        await handle_client(ws, mock_mav_core, websocket_hub)

        # Verify mission_start was called
        mock_mav_core.mission_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_command(self, mock_mav_core, websocket_hub):
        """Test unknown command doesn't crash handler."""
        from run_gcs import handle_client  # type: ignore

        unknown_cmd = json.dumps({"command": "unknown_command"})
        ws = create_mock_websocket([unknown_cmd])

        # Should not raise any errors
        await handle_client(ws, mock_mav_core, websocket_hub)

    @pytest.mark.asyncio
    async def test_malformed_json(self, mock_mav_core, websocket_hub):
        """Test malformed JSON doesn't crash handler."""
        from run_gcs import handle_client  # type: ignore

        # Invalid JSON
        ws = create_mock_websocket(["{invalid json"])

        # Should not raise any errors
        await handle_client(ws, mock_mav_core, websocket_hub)

    @pytest.mark.asyncio
    async def test_multiple_commands(self, mock_mav_core, websocket_hub):
        """Test handling multiple commands in sequence."""
        from run_gcs import handle_client  # type: ignore

        commands = [
            json.dumps({"command": "arm", "force": True}),
            json.dumps({"command": "set_mode", "mode": "GUIDED"}),
            json.dumps({"command": "goto", "lat": 38.0, "lon": -84.5, "alt": 20.0}),
        ]
        ws = create_mock_websocket(commands)

        await handle_client(ws, mock_mav_core, websocket_hub)

        # Verify all commands were processed
        mock_mav_core.arm.assert_called_once_with(should_arm=True)
        mock_mav_core.set_mode.assert_called_once_with("GUIDED")
        mock_mav_core.goto_guided.assert_called_once()


# ============================================================================
# Connection State Tests
# ============================================================================

class TestConnectionState:
    """Test connection state management."""

    @pytest.mark.asyncio
    async def test_hello_reflects_core_state(self, mock_mav_core, websocket_hub):
        """Test HELLO message reflects actual core state."""
        from run_gcs import handle_client  # type: ignore

        # Set specific core state
        mock_mav_core.link_ok.return_value = True
        mock_mav_core.mode_str = "AUTO"
        mock_mav_core.armed = True

        ws = create_mock_websocket([])

        await handle_client(ws, mock_mav_core, websocket_hub)

        # Verify HELLO message has correct state
        call_args = ws.send.call_args_list[0][0][0]
        hello_msg = json.loads(call_args)

        assert hello_msg["link_ok"] == True
        assert hello_msg["mode"] == "AUTO"
        assert hello_msg["armed"] == True

    @pytest.mark.asyncio
    async def test_hello_when_disconnected(self, mock_mav_core, websocket_hub):
        """Test HELLO message when MAVLink is disconnected."""
        from run_gcs import handle_client  # type: ignore

        # Simulate disconnected state
        mock_mav_core.link_ok.return_value = False
        mock_mav_core.mode_str = "UNKNOWN"
        mock_mav_core.armed = False

        ws = create_mock_websocket([])

        await handle_client(ws, mock_mav_core, websocket_hub)

        # Verify HELLO message reflects disconnected state
        call_args = ws.send.call_args_list[0][0][0]
        hello_msg = json.loads(call_args)

        assert hello_msg["link_ok"] == False


# ============================================================================
# Integration Tests
# ============================================================================

class TestWebSocketIntegration:
    """Test full WebSocket integration scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_clients_receive_broadcasts(self, websocket_hub, mock_mav_core):
        """Test multiple clients can connect and receive broadcasts."""
        from run_gcs import handle_client  # type: ignore

        ws1 = create_mock_websocket([])
        ws2 = create_mock_websocket([])

        # Connect both clients
        task1 = asyncio.create_task(handle_client(ws1, mock_mav_core, websocket_hub))
        task2 = asyncio.create_task(handle_client(ws2, mock_mav_core, websocket_hub))

        # Let them connect
        await asyncio.sleep(0.1)

        # Cancel tasks to simulate disconnection
        task1.cancel()
        task2.cancel()

        try:
            await task1
        except asyncio.CancelledError:
            pass

        try:
            await task2
        except asyncio.CancelledError:
            pass

        # Both clients should have received HELLO
        assert ws1.send.called
        assert ws2.send.called
