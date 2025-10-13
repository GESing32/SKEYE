"""
Unit tests for gcs_core module.
Tests MAVLink communication, command generation, and state management.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import sys
from pathlib import Path

# Add v2 directory to path for imports
v2_path = Path(__file__).parent.parent.parent / "src" / "flight-system" / "v2"
sys.path.insert(0, str(v2_path))


class TestMavSerialCore(unittest.TestCase):
    """Tests for MavSerialCore class."""

    @patch('gcs_core.mavutil.mavlink_connection')
    def setUp(self, mock_connection):
        """Set up test fixtures with mocked MAVLink connection."""
        from gcs_core import MavSerialCore

        # Mock the mavlink connection
        self.mock_mav = MagicMock()
        mock_connection.return_value = self.mock_mav

        # Create instance
        self.core = MavSerialCore(
            serial_dev="/dev/ttyUSB0",
            baud=57600,
            heartbeat_timeout=5.0
        )

    def test_initialization(self):
        """Test MavSerialCore initialization."""
        self.assertEqual(self.core.serial_dev, "/dev/ttyUSB0")
        self.assertEqual(self.core.baud, 57600)
        self.assertEqual(self.core.heartbeat_timeout, 5.0)
        self.assertIsNone(self.core.target_system)
        self.assertIsNone(self.core.target_component)
        self.assertFalse(self.core.hb_ok)
        self.assertFalse(self.core.armed)
        self.assertEqual(self.core.mode_str, "UNKNOWN")

    def test_link_ok_no_heartbeat(self):
        """Test link_ok returns False when no heartbeat received."""
        self.assertFalse(self.core.link_ok())

    @patch('gcs_core.now_s')
    def test_link_ok_recent_heartbeat(self, mock_now):
        """Test link_ok returns True when recent heartbeat received."""
        mock_now.return_value = 100.0
        self.core.last_hb = 98.0
        self.core.hb_ok = True

        self.assertTrue(self.core.link_ok())

    @patch('gcs_core.now_s')
    def test_link_ok_timeout(self, mock_now):
        """Test link_ok returns False when heartbeat timeout exceeded."""
        mock_now.return_value = 100.0
        self.core.last_hb = 90.0  # 10 seconds ago
        self.core.hb_ok = True

        self.assertFalse(self.core.link_ok())

    @patch('gcs_core.now_s')
    @patch('gcs_core.mavutil.mode_string_v10')
    def test_on_heartbeat_armed(self, mock_mode_string, mock_now):
        """Test heartbeat processing with armed status."""
        mock_now.return_value = 100.0
        mock_mode_string.return_value = "GUIDED"

        # Mock heartbeat message with armed bit set
        mock_msg = Mock()
        mock_msg.base_mode = 0x80  # MAV_MODE_FLAG_SAFETY_ARMED

        self.core._on_heartbeat(mock_msg)

        self.assertEqual(self.core.last_hb, 100.0)
        self.assertTrue(self.core.hb_ok)
        self.assertTrue(self.core.armed)
        self.assertEqual(self.core.mode_str, "GUIDED")

    @patch('gcs_core.now_s')
    @patch('gcs_core.mavutil.mode_string_v10')
    def test_on_heartbeat_disarmed(self, mock_mode_string, mock_now):
        """Test heartbeat processing with disarmed status."""
        mock_now.return_value = 100.0
        mock_mode_string.return_value = "STABILIZE"

        # Mock heartbeat message without armed bit
        mock_msg = Mock()
        mock_msg.base_mode = 0x00

        self.core._on_heartbeat(mock_msg)

        self.assertFalse(self.core.armed)
        self.assertEqual(self.core.mode_str, "STABILIZE")

    @patch('gcs_core.mavutil')
    def test_recv_once_no_message(self, mock_mavutil):
        """Test recv_once with no message available."""
        self.mock_mav.recv_match.return_value = None

        result = self.core.recv_once()

        self.assertIsNone(result)

    @patch('gcs_core.mavutil')
    def test_recv_once_bad_data(self, mock_mavutil):
        """Test recv_once filters out BAD_DATA messages."""
        mock_msg = Mock()
        mock_msg.get_type.return_value = "BAD_DATA"
        self.mock_mav.recv_match.return_value = mock_msg

        result = self.core.recv_once()

        self.assertIsNone(result)

    @patch('gcs_core.now_s')
    @patch('gcs_core.mavutil.mode_string_v10')
    def test_recv_once_heartbeat(self, mock_mode_string, mock_now):
        """Test recv_once processes HEARTBEAT messages."""
        mock_now.return_value = 100.0
        mock_mode_string.return_value = "LOITER"

        mock_msg = Mock()
        mock_msg.get_type.return_value = "HEARTBEAT"
        mock_msg.base_mode = 0x80
        mock_msg.to_dict.return_value = {"base_mode": 128}

        self.mock_mav.recv_match.return_value = mock_msg

        result = self.core.recv_once()

        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "HEARTBEAT")
        self.assertTrue(self.core.armed)

    def test_ensure_targets_defaults(self):
        """Test _ensure_targets sets default values."""
        self.core.target_system = None
        self.core.target_component = None
        self.mock_mav.target_system = None
        self.mock_mav.target_component = None

        self.core._ensure_targets()

        self.assertEqual(self.core.target_system, 1)
        self.assertEqual(self.core.target_component, 1)

    @patch('gcs_core.mavutil')
    def test_set_mode(self, mock_mavutil):
        """Test set_mode command."""
        self.core.target_system = 1
        self.core.target_component = 1

        self.core.set_mode("GUIDED")

        self.mock_mav.set_mode_apm.assert_called_once_with("GUIDED")

    @patch('gcs_core.mavutil')
    def test_arm_command(self, mock_mavutil):
        """Test arm command generation."""
        mock_mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM = 400

        self.core.target_system = 1
        self.core.target_component = 1

        self.core.arm(True)

        self.mock_mav.mav.command_long_send.assert_called_once()
        args = self.mock_mav.mav.command_long_send.call_args[0]
        self.assertEqual(args[0], 1)  # target_system
        self.assertEqual(args[1], 1)  # target_component
        self.assertEqual(args[2], 400)  # MAV_CMD_COMPONENT_ARM_DISARM
        self.assertEqual(args[4], 1)  # param1 = 1 (arm)

    @patch('gcs_core.mavutil')
    def test_disarm_command(self, mock_mavutil):
        """Test disarm command generation."""
        mock_mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM = 400

        self.core.target_system = 1
        self.core.target_component = 1

        self.core.arm(False)

        args = self.mock_mav.mav.command_long_send.call_args[0]
        self.assertEqual(args[4], 0)  # param1 = 0 (disarm)

    def test_rtl_command(self):
        """Test RTL command sets mode to RTL."""
        self.core.target_system = 1
        self.core.target_component = 1

        with patch.object(self.core, 'set_mode') as mock_set_mode:
            self.core.rtl()
            mock_set_mode.assert_called_once_with("RTL")

    @patch('gcs_core.mavutil')
    def test_goto_guided(self, mock_mavutil):
        """Test goto_guided command generation."""
        mock_mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT = 6

        self.core.target_system = 1
        self.core.target_component = 1

        with patch.object(self.core, 'set_mode'):
            self.core.goto_guided(38.0308, -84.506, 20.0)

        self.mock_mav.mav.set_position_target_global_int_send.assert_called_once()
        args = self.mock_mav.mav.set_position_target_global_int_send.call_args[0]
        self.assertEqual(args[1], 1)  # target_system
        self.assertEqual(args[5], 380308000)  # lat * 1e7
        self.assertEqual(args[6], -845060000)  # lon * 1e7
        self.assertEqual(args[7], 20.0)  # alt_rel_m

    @patch('gcs_core.mavutil')
    def test_set_speed(self, mock_mavutil):
        """Test set_speed command generation."""
        mock_mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED = 178

        self.core.target_system = 1
        self.core.target_component = 1

        self.core.set_speed(5.0)

        self.mock_mav.mav.command_long_send.assert_called_once()
        args = self.mock_mav.mav.command_long_send.call_args[0]
        self.assertEqual(args[2], 178)  # MAV_CMD_DO_CHANGE_SPEED
        self.assertEqual(args[5], 5.0)  # param2 = speed

    @patch('gcs_core.mavutil')
    def test_do_digicam_control(self, mock_mavutil):
        """Test camera control command."""
        mock_mavutil.mavlink.MAV_CMD_DO_DIGICAM_CONTROL = 203

        self.core.target_system = 1
        self.core.target_component = 1

        self.core.do_digicam_control(shoot_command=1)

        self.mock_mav.mav.command_long_send.assert_called_once()
        args = self.mock_mav.mav.command_long_send.call_args[0]
        self.assertEqual(args[2], 203)  # MAV_CMD_DO_DIGICAM_CONTROL
        self.assertEqual(args[8], 1.0)  # param5 = shoot_command


class TestRelayTypes(unittest.TestCase):
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
            self.assertIn(msg_type, RELAY_TYPES)


class TestNowFunction(unittest.TestCase):
    """Tests for now_s() utility function."""

    @patch('gcs_core.time.time')
    def test_now_s(self, mock_time):
        """Test now_s returns current time."""
        from gcs_core import now_s

        mock_time.return_value = 12345.678
        self.assertEqual(now_s(), 12345.678)


if __name__ == '__main__':
    unittest.main(verbosity=2)
