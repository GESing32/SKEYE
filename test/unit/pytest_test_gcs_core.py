"""
pytest version: Unit tests for gcs_core module.

Tests MAVLink communication, command generation, and state management.
This is the pytest-style version of test_gcs_core.py.

Run with:
    pytest test/unit/pytest_test_gcs_core.py
    pytest test/unit/pytest_test_gcs_core.py -v
    pytest test/unit/pytest_test_gcs_core.py -k "heartbeat"
    pytest test/unit/pytest_test_gcs_core.py -m mavlink
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path

# Add v2 directory to path for imports
v2_path = Path(__file__).parent.parent.parent / "src" / "flight-system" / "v2"
sys.path.insert(0, str(v2_path))


# ============================================================================
# Fixtures for MAVLink Testing
# ============================================================================

@pytest.fixture
def mock_mav(mocker):
    """Mock MAVLink connection object.

    Returns:
        MagicMock: Mocked MAVLink connection with common attributes
    """
    mock = MagicMock()
    mocker.patch('gcs_core.mavutil.mavlink_connection', return_value=mock)
    return mock


@pytest.fixture
def mav_serial_core(mock_mav):
    """MavSerialCore instance with mocked MAVLink connection.

    Returns:
        MavSerialCore: Core instance with mocked connection
    """
    from gcs_core import MavSerialCore

    core = MavSerialCore(
        serial_dev="/dev/ttyUSB0",
        baud=57600,
        heartbeat_timeout=5.0
    )
    return core


@pytest.fixture
def mock_now(mocker):
    """Mock the now_s() time function.

    Returns:
        MagicMock: Mocked time function (default: 100.0)
    """
    return mocker.patch('gcs_core.now_s', return_value=100.0)


@pytest.fixture
def mock_mode_string(mocker):
    """Mock mavutil.mode_string_v10 function.

    Returns:
        MagicMock: Mocked mode string function
    """
    return mocker.patch('gcs_core.mavutil.mode_string_v10', return_value="GUIDED")


# ============================================================================
# MavSerialCore Initialization Tests
# ============================================================================

@pytest.mark.mavlink
@pytest.mark.unit
class TestMavSerialCoreInitialization:
    """Tests for MavSerialCore initialization."""

    def test_initialization(self, mav_serial_core):
        """Test MavSerialCore initialization with default values."""
        assert mav_serial_core.serial_dev == "/dev/ttyUSB0"
        assert mav_serial_core.baud == 57600
        assert mav_serial_core.heartbeat_timeout == 5.0
        assert mav_serial_core.target_system is None
        assert mav_serial_core.target_component is None
        assert mav_serial_core.hb_ok is False
        assert mav_serial_core.armed is False
        assert mav_serial_core.mode_str == "UNKNOWN"

    @pytest.mark.parametrize("serial_dev,baud,timeout", [
        ("/dev/ttyUSB0", 57600, 5.0),
        ("/dev/ttyUSB1", 115200, 3.0),
        ("COM3", 921600, 10.0),
        ("tcp:localhost:5760", 0, 2.0),
    ])
    def test_initialization_various_configs(self, mock_mav, serial_dev, baud, timeout):
        """Test initialization with various connection configurations."""
        from gcs_core import MavSerialCore

        core = MavSerialCore(
            serial_dev=serial_dev,
            baud=baud,
            heartbeat_timeout=timeout
        )

        assert core.serial_dev == serial_dev
        assert core.baud == baud
        assert core.heartbeat_timeout == timeout


# ============================================================================
# Link Status Tests
# ============================================================================

@pytest.mark.mavlink
@pytest.mark.unit
class TestLinkStatus:
    """Tests for link status monitoring."""

    def test_link_ok_no_heartbeat(self, mav_serial_core):
        """Test link_ok returns False when no heartbeat received."""
        assert mav_serial_core.link_ok() is False

    def test_link_ok_recent_heartbeat(self, mav_serial_core, mock_now):
        """Test link_ok returns True when recent heartbeat received."""
        mock_now.return_value = 100.0
        mav_serial_core.last_hb = 98.0  # 2 seconds ago
        mav_serial_core.hb_ok = True

        assert mav_serial_core.link_ok() is True

    def test_link_ok_timeout(self, mav_serial_core, mock_now):
        """Test link_ok returns False when heartbeat timeout exceeded."""
        mock_now.return_value = 100.0
        mav_serial_core.last_hb = 90.0  # 10 seconds ago (> 5s timeout)
        mav_serial_core.hb_ok = True

        assert mav_serial_core.link_ok() is False

    @pytest.mark.parametrize("current_time,last_hb,timeout,expected", [
        (100.0, 98.0, 5.0, True),   # Within timeout
        (100.0, 96.0, 5.0, True),   # At edge of timeout
        (100.0, 94.0, 5.0, False),  # Exceeded timeout
        (100.0, 99.5, 1.0, True),   # Short timeout, within
        (100.0, 98.0, 1.0, False),  # Short timeout, exceeded
    ])
    def test_link_ok_various_timeouts(self, mav_serial_core, mocker,
                                      current_time, last_hb, timeout, expected):
        """Test link_ok with various timeout scenarios."""
        mocker.patch('gcs_core.now_s', return_value=current_time)
        mav_serial_core.last_hb = last_hb
        mav_serial_core.heartbeat_timeout = timeout
        mav_serial_core.hb_ok = True

        assert mav_serial_core.link_ok() == expected


# ============================================================================
# Heartbeat Processing Tests
# ============================================================================

@pytest.mark.mavlink
@pytest.mark.unit
class TestHeartbeatProcessing:
    """Tests for heartbeat message processing."""

    def test_on_heartbeat_armed(self, mav_serial_core, mock_now, mock_mode_string):
        """Test heartbeat processing with armed status."""
        mock_now.return_value = 100.0
        mock_mode_string.return_value = "GUIDED"

        # Mock heartbeat message with armed bit set (MAV_MODE_FLAG_SAFETY_ARMED)
        mock_msg = Mock()
        mock_msg.base_mode = 0x80

        mav_serial_core._on_heartbeat(mock_msg)

        assert mav_serial_core.last_hb == 100.0
        assert mav_serial_core.hb_ok is True
        assert mav_serial_core.armed is True
        assert mav_serial_core.mode_str == "GUIDED"

    def test_on_heartbeat_disarmed(self, mav_serial_core, mock_now, mock_mode_string):
        """Test heartbeat processing with disarmed status."""
        mock_now.return_value = 100.0
        mock_mode_string.return_value = "STABILIZE"

        # Mock heartbeat message without armed bit
        mock_msg = Mock()
        mock_msg.base_mode = 0x00

        mav_serial_core._on_heartbeat(mock_msg)

        assert mav_serial_core.armed is False
        assert mav_serial_core.mode_str == "STABILIZE"

    @pytest.mark.parametrize("base_mode,expected_armed", [
        (0x00, False),  # No flags
        (0x80, True),   # MAV_MODE_FLAG_SAFETY_ARMED
        (0x81, True),   # Armed + custom mode enabled
        (0x84, True),   # Armed + guided enabled
        (0xFF, True),   # All flags set (including armed)
    ])
    def test_on_heartbeat_various_modes(self, mav_serial_core, mock_now,
                                        mock_mode_string, base_mode, expected_armed):
        """Test heartbeat processing with various base_mode flags."""
        mock_now.return_value = 100.0
        mock_mode_string.return_value = "TEST_MODE"

        mock_msg = Mock()
        mock_msg.base_mode = base_mode

        mav_serial_core._on_heartbeat(mock_msg)

        assert mav_serial_core.armed == expected_armed
        assert mav_serial_core.hb_ok is True


# ============================================================================
# Message Reception Tests
# ============================================================================

@pytest.mark.mavlink
@pytest.mark.unit
class TestMessageReception:
    """Tests for MAVLink message reception."""

    def test_recv_once_no_message(self, mav_serial_core, mock_mav):
        """Test recv_once with no message available."""
        mock_mav.recv_match.return_value = None

        result = mav_serial_core.recv_once()

        assert result is None

    def test_recv_once_bad_data(self, mav_serial_core, mock_mav):
        """Test recv_once filters out BAD_DATA messages."""
        mock_msg = Mock()
        mock_msg.get_type.return_value = "BAD_DATA"
        mock_mav.recv_match.return_value = mock_msg

        result = mav_serial_core.recv_once()

        assert result is None

    def test_recv_once_heartbeat(self, mav_serial_core, mock_mav, mock_now, mock_mode_string):
        """Test recv_once processes HEARTBEAT messages."""
        mock_now.return_value = 100.0
        mock_mode_string.return_value = "LOITER"

        mock_msg = Mock()
        mock_msg.get_type.return_value = "HEARTBEAT"
        mock_msg.base_mode = 0x80
        mock_msg.to_dict.return_value = {"base_mode": 128}

        mock_mav.recv_match.return_value = mock_msg

        result = mav_serial_core.recv_once()

        assert result is not None
        assert result["type"] == "HEARTBEAT"
        assert mav_serial_core.armed is True

    @pytest.mark.parametrize("msg_type", [
        "GLOBAL_POSITION_INT",
        "VFR_HUD",
        "SYS_STATUS",
        "ATTITUDE",
        "GPS_RAW_INT",
    ])
    def test_recv_once_various_message_types(self, mav_serial_core, mock_mav, msg_type):
        """Test recv_once with various MAVLink message types."""
        mock_msg = Mock()
        mock_msg.get_type.return_value = msg_type
        mock_msg.to_dict.return_value = {"type": msg_type, "data": "test"}

        mock_mav.recv_match.return_value = mock_msg

        result = mav_serial_core.recv_once()

        assert result is not None
        assert result["type"] == msg_type


# ============================================================================
# Target System/Component Tests
# ============================================================================

@pytest.mark.mavlink
@pytest.mark.unit
class TestTargetSystemComponent:
    """Tests for target system and component management."""

    def test_ensure_targets_defaults(self, mav_serial_core, mock_mav):
        """Test _ensure_targets sets default values."""
        mav_serial_core.target_system = None
        mav_serial_core.target_component = None
        mock_mav.target_system = None
        mock_mav.target_component = None

        mav_serial_core._ensure_targets()

        assert mav_serial_core.target_system == 1
        assert mav_serial_core.target_component == 1

    def test_ensure_targets_preserves_existing(self, mav_serial_core, mock_mav):
        """Test _ensure_targets preserves existing values."""
        mav_serial_core.target_system = 5
        mav_serial_core.target_component = 10
        mock_mav.target_system = 5
        mock_mav.target_component = 10

        mav_serial_core._ensure_targets()

        assert mav_serial_core.target_system == 5
        assert mav_serial_core.target_component == 10


# ============================================================================
# Command Generation Tests - Mode Control
# ============================================================================

@pytest.mark.mavlink
@pytest.mark.unit
class TestModeCommands:
    """Tests for flight mode commands."""

    def test_set_mode(self, mav_serial_core, mock_mav):
        """Test set_mode command."""
        mav_serial_core.target_system = 1
        mav_serial_core.target_component = 1

        mav_serial_core.set_mode("GUIDED")

        mock_mav.set_mode_apm.assert_called_once_with("GUIDED")

    @pytest.mark.parametrize("mode", [
        "STABILIZE",
        "LOITER",
        "GUIDED",
        "AUTO",
        "RTL",
        "LAND",
    ])
    def test_set_mode_various_modes(self, mav_serial_core, mock_mav, mode):
        """Test setting various flight modes."""
        mav_serial_core.target_system = 1
        mav_serial_core.target_component = 1

        mav_serial_core.set_mode(mode)

        mock_mav.set_mode_apm.assert_called_once_with(mode)


# ============================================================================
# Command Generation Tests - Arm/Disarm
# ============================================================================

@pytest.mark.mavlink
@pytest.mark.unit
class TestArmDisarmCommands:
    """Tests for arm/disarm commands."""

    def test_arm_command(self, mav_serial_core, mock_mav, mocker):
        """Test arm command generation."""
        mocker.patch('gcs_core.mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM', 400)

        mav_serial_core.target_system = 1
        mav_serial_core.target_component = 1

        mav_serial_core.arm(True)

        mock_mav.mav.command_long_send.assert_called_once()
        args = mock_mav.mav.command_long_send.call_args[0]
        assert args[0] == 1  # target_system
        assert args[1] == 1  # target_component
        assert args[2] == 400  # MAV_CMD_COMPONENT_ARM_DISARM
        assert args[4] == 1  # param1 = 1 (arm)

    def test_disarm_command(self, mav_serial_core, mock_mav, mocker):
        """Test disarm command generation."""
        mocker.patch('gcs_core.mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM', 400)

        mav_serial_core.target_system = 1
        mav_serial_core.target_component = 1

        mav_serial_core.arm(False)

        args = mock_mav.mav.command_long_send.call_args[0]
        assert args[4] == 0  # param1 = 0 (disarm)

    @pytest.mark.parametrize("arm_state,expected_param", [
        (True, 1),   # Arm
        (False, 0),  # Disarm
    ])
    def test_arm_parametrized(self, mav_serial_core, mock_mav, mocker,
                              arm_state, expected_param):
        """Test arm/disarm with parametrization."""
        mocker.patch('gcs_core.mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM', 400)

        mav_serial_core.target_system = 1
        mav_serial_core.target_component = 1

        mav_serial_core.arm(arm_state)

        args = mock_mav.mav.command_long_send.call_args[0]
        assert args[4] == expected_param


# ============================================================================
# Command Generation Tests - RTL
# ============================================================================

@pytest.mark.mavlink
@pytest.mark.unit
class TestRTLCommand:
    """Tests for Return-to-Launch (RTL) command."""

    def test_rtl_command(self, mav_serial_core):
        """Test RTL command sets mode to RTL."""
        mav_serial_core.target_system = 1
        mav_serial_core.target_component = 1

        with patch.object(mav_serial_core, 'set_mode') as mock_set_mode:
            mav_serial_core.rtl()
            mock_set_mode.assert_called_once_with("RTL")


# ============================================================================
# Command Generation Tests - GOTO
# ============================================================================

@pytest.mark.mavlink
@pytest.mark.unit
class TestGotoCommands:
    """Tests for GOTO position commands."""

    def test_goto_guided(self, mav_serial_core, mock_mav, mocker):
        """Test goto_guided command generation."""
        mocker.patch('gcs_core.mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT', 6)

        mav_serial_core.target_system = 1
        mav_serial_core.target_component = 1

        with patch.object(mav_serial_core, 'set_mode'):
            mav_serial_core.goto_guided(38.0308, -84.506, 20.0)

        mock_mav.mav.set_position_target_global_int_send.assert_called_once()
        args = mock_mav.mav.set_position_target_global_int_send.call_args[0]
        assert args[1] == 1  # target_system
        assert args[5] == 380308000  # lat * 1e7
        assert args[6] == -845060000  # lon * 1e7
        assert args[7] == 20.0  # alt_rel_m

    @pytest.mark.parametrize("lat,lon,alt,expected_lat_int,expected_lon_int", [
        (38.0308, -84.506, 20.0, 380308000, -845060000),
        (38.0, -84.5, 50.0, 380000000, -845000000),
        (0.0, 0.0, 100.0, 0, 0),
        (-33.8688, 151.2093, 30.0, -338688000, 1512093000),  # Sydney
    ])
    def test_goto_guided_various_coords(self, mav_serial_core, mock_mav, mocker,
                                        lat, lon, alt, expected_lat_int, expected_lon_int):
        """Test goto_guided with various coordinates."""
        mocker.patch('gcs_core.mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT', 6)

        mav_serial_core.target_system = 1
        mav_serial_core.target_component = 1

        with patch.object(mav_serial_core, 'set_mode'):
            mav_serial_core.goto_guided(lat, lon, alt)

        args = mock_mav.mav.set_position_target_global_int_send.call_args[0]
        assert args[5] == expected_lat_int
        assert args[6] == expected_lon_int
        assert args[7] == alt


# ============================================================================
# Command Generation Tests - Speed Control
# ============================================================================

@pytest.mark.mavlink
@pytest.mark.unit
class TestSpeedCommands:
    """Tests for speed control commands."""

    def test_set_speed(self, mav_serial_core, mock_mav, mocker):
        """Test set_speed command generation."""
        mocker.patch('gcs_core.mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED', 178)

        mav_serial_core.target_system = 1
        mav_serial_core.target_component = 1

        mav_serial_core.set_speed(5.0)

        mock_mav.mav.command_long_send.assert_called_once()
        args = mock_mav.mav.command_long_send.call_args[0]
        assert args[2] == 178  # MAV_CMD_DO_CHANGE_SPEED
        assert args[5] == 5.0  # param2 = speed

    @pytest.mark.parametrize("speed", [1.0, 5.0, 10.0, 15.0, 20.0])
    def test_set_speed_various_speeds(self, mav_serial_core, mock_mav, mocker, speed):
        """Test setting various speeds."""
        mocker.patch('gcs_core.mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED', 178)

        mav_serial_core.target_system = 1
        mav_serial_core.target_component = 1

        mav_serial_core.set_speed(speed)

        args = mock_mav.mav.command_long_send.call_args[0]
        assert args[5] == speed


# ============================================================================
# Command Generation Tests - Camera Control
# ============================================================================

@pytest.mark.mavlink
@pytest.mark.unit
class TestCameraCommands:
    """Tests for camera control commands."""

    def test_do_digicam_control(self, mav_serial_core, mock_mav, mocker):
        """Test camera control command."""
        mocker.patch('gcs_core.mavutil.mavlink.MAV_CMD_DO_DIGICAM_CONTROL', 203)

        mav_serial_core.target_system = 1
        mav_serial_core.target_component = 1

        mav_serial_core.do_digicam_control(shoot_command=1)

        mock_mav.mav.command_long_send.assert_called_once()
        args = mock_mav.mav.command_long_send.call_args[0]
        assert args[2] == 203  # MAV_CMD_DO_DIGICAM_CONTROL
        assert args[8] == 1.0  # param5 = shoot_command

    @pytest.mark.parametrize("shoot_command", [0, 1, 2])
    def test_do_digicam_control_various_commands(self, mav_serial_core, mock_mav,
                                                  mocker, shoot_command):
        """Test camera control with various shoot commands."""
        mocker.patch('gcs_core.mavutil.mavlink.MAV_CMD_DO_DIGICAM_CONTROL', 203)

        mav_serial_core.target_system = 1
        mav_serial_core.target_component = 1

        mav_serial_core.do_digicam_control(shoot_command=shoot_command)

        args = mock_mav.mav.command_long_send.call_args[0]
        assert args[8] == float(shoot_command)


# ============================================================================
# RELAY_TYPES Tests
# ============================================================================

@pytest.mark.mavlink
@pytest.mark.unit
class TestRelayTypes:
    """Tests for RELAY_TYPES constant."""

    def test_relay_types_contains_essential(self):
        """Test RELAY_TYPES contains essential message types."""
        from gcs_core import RELAY_TYPES

        essential_types = [
            "HEARTBEAT",
            "SYS_STATUS",
            "GLOBAL_POSITION_INT",
            "VFR_HUD",
        ]

        for msg_type in essential_types:
            assert msg_type in RELAY_TYPES

    def test_relay_types_is_set(self):
        """Test RELAY_TYPES is a set or list."""
        from gcs_core import RELAY_TYPES

        assert isinstance(RELAY_TYPES, (set, list, tuple))


# ============================================================================
# Utility Function Tests
# ============================================================================

@pytest.mark.unit
class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_now_s(self, mocker):
        """Test now_s returns current time."""
        from gcs_core import now_s

        mock_time = mocker.patch('gcs_core.time.time', return_value=12345.678)
        assert now_s() == 12345.678

    def test_now_s_multiple_calls(self, mocker):
        """Test now_s returns different values on multiple calls."""
        from gcs_core import now_s

        mock_time = mocker.patch('gcs_core.time.time')
        mock_time.side_effect = [100.0, 100.5, 101.0]

        assert now_s() == 100.0
        assert now_s() == 100.5
        assert now_s() == 101.0


# ============================================================================
# Integration-style Tests (Complex Scenarios)
# ============================================================================

@pytest.mark.mavlink
@pytest.mark.integration
class TestComplexScenarios:
    """Integration-style tests for complex MAVLink scenarios."""

    def test_complete_arm_and_takeoff_sequence(self, mav_serial_core, mock_mav, mocker):
        """Test complete arm and takeoff command sequence."""
        mocker.patch('gcs_core.mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM', 400)
        mocker.patch('gcs_core.mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT', 6)

        mav_serial_core.target_system = 1
        mav_serial_core.target_component = 1

        # Sequence: Set mode -> Arm -> GOTO
        with patch.object(mav_serial_core, 'set_mode') as mock_set_mode:
            mav_serial_core.set_mode("GUIDED")
            mav_serial_core.arm(True)
            mav_serial_core.goto_guided(38.0, -84.5, 20.0)

            # Verify command sequence
            assert mock_set_mode.call_count == 2  # set_mode called twice (initial + goto)
            assert mock_mav.mav.command_long_send.called
            assert mock_mav.mav.set_position_target_global_int_send.called

    def test_survey_mission_commands(self, mav_serial_core, mock_mav, mocker):
        """Test typical survey mission command sequence."""
        mocker.patch('gcs_core.mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED', 178)
        mocker.patch('gcs_core.mavutil.mavlink.MAV_CMD_DO_DIGICAM_CONTROL', 203)
        mocker.patch('gcs_core.mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT', 6)

        mav_serial_core.target_system = 1
        mav_serial_core.target_component = 1

        # Survey sequence: Set speed -> GOTO -> Trigger camera
        with patch.object(mav_serial_core, 'set_mode'):
            mav_serial_core.set_speed(5.0)
            mav_serial_core.goto_guided(38.0, -84.5, 50.0)
            mav_serial_core.do_digicam_control(shoot_command=1)

            # Verify all commands were sent
            assert mock_mav.mav.command_long_send.call_count == 2  # Speed + camera
            assert mock_mav.mav.set_position_target_global_int_send.call_count == 1
