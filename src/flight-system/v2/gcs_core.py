# Python 3.9+
import asyncio
import json
import logging
import math
import time
from typing import Any, Dict, List, Optional

from pymavlink import mavutil

RELAY_TYPES = {
    "HEARTBEAT",
    "SYS_STATUS",
    "GLOBAL_POSITION_INT",
    "GPS_RAW_INT",
    "BATTERY_STATUS",
    "VFR_HUD",
    "EKF_STATUS_REPORT",
    "ATTITUDE",
    "HOME_POSITION",
    "MISSION_CURRENT",
}

def now_s() -> float:
    return time.time()

class MavSerialCore:
    def __init__(
        self,
        serial_dev: str = "COM4", #"/dev/ttyUSB0" needs changed depending on OS
        baud: int = 57600,
        heartbeat_timeout: float = 5.0,
        log_level: int = logging.INFO,
    ):
        self.log = logging.getLogger("MavSerialCore")
        self.log.setLevel(log_level)
        self.serial_dev = serial_dev
        self.baud = baud
        self.heartbeat_timeout = heartbeat_timeout

        # Create serial connection (pymavlink will reopen on drop with autoreconnect)
        self.m: mavutil.mavfile = mavutil.mavlink_connection(serial_dev, baud=baud, autoreconnect=True)

        self.target_system: Optional[int] = None
        self.target_component: Optional[int] = None

        self.last_hb: float = 0.0
        self.hb_ok: bool = False
        self.armed: bool = False
        self.mode_str: str = "UNKNOWN"

        # Mission upload state
        self._mission_upload_in_progress: bool = False
        self._mission_items_int: Dict[int, Dict[str, Any]] = {}
        self._mission_expected_count: int = 0
        self._last_mission_ack: Optional[Dict[str, Any]] = None
        self._mission_ack_received: bool = False

    # -------- Link / heartbeat --------
    def wait_heartbeat(self, timeout: float = 30.0):
        self.log.info(f"Opening MAVLink over serial {self.serial_dev} @ {self.baud} ...")
        hb = self.m.wait_heartbeat(timeout=timeout)
        if not hb:
            raise TimeoutError("No heartbeat received")
        self._on_heartbeat(hb)
        self.target_system = self.m.target_system or 1
        self.target_component = self.m.target_component or 1
        self.log.info(f"Connected: sys={self.target_system}, comp={self.target_component}, mode={self.mode_str}")

    def _on_heartbeat(self, msg):
        self.last_hb = now_s()
        self.hb_ok = True
        self.armed = (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0
        try:
            self.mode_str = mavutil.mode_string_v10(msg)
        except Exception:
            pass

    def link_ok(self) -> bool:
        return self.hb_ok and (now_s() - self.last_hb) < self.heartbeat_timeout

    def _ensure_targets(self):
        if self.target_system is None:
            self.target_system = self.m.target_system or 1
        if self.target_component is None:
            self.target_component = self.m.target_component or 1

    # -------- RX loop --------
    def recv_once(self) -> Optional[Dict[str, Any]]:
        msg = self.m.recv_match(blocking=False)
        if not msg:
            return None
        if msg.get_type() == "BAD_DATA":
            return None
        if msg.get_type() == "HEARTBEAT":
            self._on_heartbeat(msg)
            if self.target_system is None:
                self.target_system = self.m.target_system
            if self.target_component is None:
                self.target_component = self.m.target_component
        return {"type": msg.get_type(), **msg.to_dict()}

    # -------- Commands --------
    def set_mode(self, mode_str: str):
        self._ensure_targets()
        self.m.set_mode_apm(mode_str)

    def arm(self, should_arm: bool = True):
        self._ensure_targets()
        self.m.mav.command_long_send(
            self.target_system,
            self.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1 if should_arm else 0,
            0, 0, 0, 0, 0, 0
        )

    def get_armed_status(self):
        """Check if vehicle is armed from HEARTBEAT message"""
        msg = self.mav.recv_match(type='HEARTBEAT', blocking=False)
        if msg:
            armed = msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
            return bool(armed)
        return False
    
    def rtl(self):
        self.set_mode("RTL")

    def goto_guided(self, lat_deg: float, lon_deg: float, alt_rel_m: float, yaw_deg: Optional[float] = None):
        self._ensure_targets()
        # Ensure GUIDED
        self.set_mode("GUIDED")
        # Position-only mask
        type_mask = 0b111111111000
        yaw = float("nan") if yaw_deg is None else math.radians(yaw_deg)
        yaw_rate = 0.0 if yaw_deg is not None else float("nan")  # Fixed: proper yaw_rate handling
        self.m.mav.set_position_target_global_int_send(
            0,
            self.target_system,
            self.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            type_mask,
            int(lat_deg * 1e7),
            int(lon_deg * 1e7),
            float(alt_rel_m),
            0, 0, 0, 0, 0, 0,
            yaw,
            yaw_rate
        )

    def set_speed(self, m_s: float):
        self._ensure_targets()
        self.m.mav.command_long_send(
            self.target_system,
            self.target_component,
            mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED,
            0,
            1, float(m_s), -1, 0, 0, 0, 0
        )

    # -------- Camera control commands --------
    def do_digicam_control(self, session: int = 0, zoom_pos: int = 0, zoom_step: int = 0,
                           focus_lock: int = 0, shoot_command: int = 1, cmd_id: int = 0):
        """
        Control onboard camera (manual trigger).
        MAV_CMD_DO_DIGICAM_CONTROL

        Args:
            session: Session control (0 = ignore)
            zoom_pos: Zoom position (0 = ignore)
            zoom_step: Zoom step (0 = ignore)
            focus_lock: Focus lock (0 = ignore)
            shoot_command: 1 = take photo, 0 = ignore
            cmd_id: Command identity (0 = ignore)
        """
        self._ensure_targets()
        self.m.mav.command_long_send(
            self.target_system,
            self.target_component,
            mavutil.mavlink.MAV_CMD_DO_DIGICAM_CONTROL,
            0,
            float(session),
            float(zoom_pos),
            float(zoom_step),
            float(focus_lock),
            float(shoot_command),
            float(cmd_id),
            0.0
        )
        self.log.info(f"Camera control: shoot={shoot_command}")

    def do_set_cam_trigg_dist(self, distance_m: float, shutter: float = 0.0, trigger_once: int = 1):
        """
        Set camera trigger distance (distance-based triggering).
        MAV_CMD_DO_SET_CAM_TRIGG_DIST - QGC Survey default

        Args:
            distance_m: Distance between triggers in meters (0 = stop triggering)
            shutter: Shutter integration time (0 = ignore)
            trigger_once: 1 = trigger once immediately, 0 = don't
        """
        self._ensure_targets()
        self.m.mav.command_long_send(
            self.target_system,
            self.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_CAM_TRIGG_DIST,
            0,
            float(distance_m),
            float(shutter),
            float(trigger_once),
            0.0, 0.0, 0.0, 0.0
        )
        self.log.info(f"Camera trigger distance set: {distance_m}m")

    def do_set_cam_trigg_interval(self, interval_s: float, count: int = 0):
        """
        Set camera trigger interval (time-based triggering).
        MAV_CMD_DO_SET_CAM_TRIGG_INTERVAL

        Args:
            interval_s: Time between triggers in seconds (-1 = stop triggering)
            count: Number of photos to take (0 = unlimited)
        """
        self._ensure_targets()
        self.m.mav.command_long_send(
            self.target_system,
            self.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_CAM_TRIGG_INTERVAL,
            0,
            float(interval_s),
            float(count),
            0.0, 0.0, 0.0, 0.0, 0.0
        )
        self.log.info(f"Camera trigger interval set: {interval_s}s, count={count}")

    # -------- Mission upload (INT) --------
    def mission_clear_all(self):
        self._ensure_targets()
        self.m.mav.mission_clear_all_send(self.target_system, self.target_component)

    def mission_start(self, first_item: int = 0, last_item: int = 0xFFFF):
        """Start mission by arming vehicle and switching to AUTO mode.

        In ArduPilot, missions require the vehicle to be armed and in AUTO mode.
        IMPORTANT: ArduPilot does NOT allow arming in AUTO mode directly.
        This function:
        1. Checks if armed; if not, switches to GUIDED mode and arms
        2. Switches to AUTO mode to start the mission
        """
        self._ensure_targets()

        # Check if already armed
        if not self.armed:
            self.log.info("Vehicle not armed. Arming in GUIDED mode first...")
            # Switch to GUIDED mode first (AUTO mode doesn't allow arming)
            self.set_mode("GUIDED")
            # Give mode change time to process
            import time
            time.sleep(0.5)
            # Now ARM
            self.arm(should_arm=True)
            # Wait for arm to complete
            time.sleep(1.5)
        else:
            self.log.info("Vehicle already armed, proceeding to AUTO")

        # Now set mode to AUTO to start the mission
        self.log.info("Switching to AUTO mode to start mission")
        self.set_mode("AUTO")

    def _wait_for_ack(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Wait for MISSION_ACK message from vehicle.

        Args:
            timeout: Maximum time to wait for ACK (seconds)

        Returns:
            ACK message dict if received, None on timeout
        """
        self._mission_ack_received = False
        self._last_mission_ack = None
        start_time = now_s()

        while (now_s() - start_time) < timeout:
            msg = self.m.recv_match(type='MISSION_ACK', blocking=False, timeout=0.1)
            if msg:
                self._last_mission_ack = msg.to_dict()
                self._mission_ack_received = True
                return self._last_mission_ack

        return None

    def _wait_for_mission_count(self, timeout: float = 5.0) -> Optional[int]:
        """
        Request and wait for mission count from vehicle.

        Args:
            timeout: Maximum time to wait for response (seconds)

        Returns:
            Mission count if received, None on timeout
        """
        self._ensure_targets()
        # Request mission list
        self.m.mav.mission_request_list_send(self.target_system, self.target_component)

        start_time = now_s()
        while (now_s() - start_time) < timeout:
            msg = self.m.recv_match(type='MISSION_COUNT', blocking=False, timeout=0.1)
            if msg:
                return msg.count

        return None

    def mission_upload_begin(self, items_int: List[Dict[str, Any]], verify: bool = False, timeout: float = 30.0):
        """
        Upload mission items to vehicle with optional verification.

        Args:
            items_int: List of mission item dictionaries
            verify: If True, wait for ACK and verify mission count
            timeout: Total timeout for upload operation (seconds)

        Raises:
            TimeoutError: If upload times out
            RuntimeError: If verification fails
        """
        self._ensure_targets()

        if not items_int:
            raise ValueError("Mission items list cannot be empty")

        # Normalize items into a dict by sequence
        self._mission_items_int = {int(i["seq"]): i for i in items_int}
        self._mission_expected_count = len(items_int)
        self._mission_upload_in_progress = True

        start_time = now_s()

        # Send mission count
        self.m.mav.mission_count_send(self.target_system, self.target_component, self._mission_expected_count)
        self.log.info(f"Sent mission count: {self._mission_expected_count} items")

        if verify:
            # Wait for mission upload to complete (ACK received)
            upload_timeout = timeout - (now_s() - start_time)
            if upload_timeout <= 0:
                raise TimeoutError("Mission upload timed out before completion")

            # Wait for all mission requests and send items
            # The protocol handler will send items as requests come in
            # We just need to wait for the final ACK
            time.sleep(0.5)  # Give time for protocol to process

            # Wait for MISSION_ACK
            ack = self._wait_for_ack(timeout=upload_timeout)

            if not ack:
                raise TimeoutError(f"Did not receive MISSION_ACK within {upload_timeout}s")

            # Check ACK type
            ack_type = ack.get('type', -1)
            if ack_type != mavutil.mavlink.MAV_MISSION_ACCEPTED:
                ack_type_name = mavutil.mavlink.enums['MAV_MISSION_RESULT'].get(ack_type, {}).get('name', 'UNKNOWN')
                raise RuntimeError(f"Mission upload failed with ACK type: {ack_type_name} ({ack_type})")

            self.log.info("Mission upload ACK received: ACCEPTED")

            # Final verification: request mission count back from vehicle
            count = self._wait_for_mission_count(timeout=5.0)

            if count is None:
                self.log.warning("Could not verify mission count (timeout)")
            elif count != self._mission_expected_count:
                raise RuntimeError(
                    f"Mission verification failed: expected {self._mission_expected_count} items, "
                    f"vehicle reports {count} items"
                )
            else:
                self.log.info(f"Mission verification successful: {count}/{self._mission_expected_count} items")
        else:
            # Original non-verified upload behavior
            self.log.info("Mission upload started (no verification)")

    def _handle_mission_request(self, msg: Dict[str, Any]):
        if not self._mission_upload_in_progress:
            return
        if msg["type"] not in ("MISSION_REQUEST_INT", "MISSION_REQUEST"):
            return
        seq = int(msg.get("seq", -1))
        item = self._mission_items_int.get(seq)
        if item is None:
            return
        self.m.mav.mission_item_int_send(
            self.target_system,
            self.target_component,
            int(item["seq"]),
            int(item.get("frame", mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT)),
            int(item["command"]),
            int(item.get("current", 0)),
            int(item.get("autocontinue", 1)),
            float(item.get("param1", 0.0)),
            float(item.get("param2", 0.0)),
            float(item.get("param3", 0.0)),
            float(item.get("param4", 0.0)),
            int(item["x"]),
            int(item["y"]),
            float(item["z"]),
            int(item.get("mission_type", 0)),  # MAV_MISSION_TYPE_MISSION = 0
        )

    def _handle_mission_ack(self, _msg: Dict[str, Any]):
        if not self._mission_upload_in_progress:
            return
        self._mission_upload_in_progress = False
        self._mission_items_int.clear()
        self._mission_expected_count = 0

    # -------- Integration helpers --------
    def process_protocol_side_effects(self, msg: Dict[str, Any]):
        t = msg["type"]
        if t in ("MISSION_REQUEST_INT", "MISSION_REQUEST"):
            self._handle_mission_request(msg)
        elif t == "MISSION_ACK":
            self._handle_mission_ack(msg)