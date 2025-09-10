# MAVLink bridge for drone control and telemetry
# Uses pymavlink to connect to a flight controller and provides functions to arm, set modes navigate to waypoints, and retrieve telemetry data.
# Author: Niles Roxas

import threading, time
from typing import Optional, List, Dict
from pymavlink import mavutil

class MavlinkBridge:
    def __init__(self, device: str, baud: int = 57600, dialect: Optional[str] = None, udp=False):
        # device like '/dev/ttyAMA0' or 'udpin:0.0.0.0:14540'
        dialect_arg = dialect if dialect else None
        self.m = mavutil.mavlink_connection(device, baud=baud, dialect=dialect_arg)
        self.connected = False
        self._lock = threading.Lock()
        self._telemetry = {}
        self._stop = False

    def start(self):
        # Wait for heartbeat to lock system/component
        self.m.wait_heartbeat()
        self.connected = True
        # Request useful streams
        self.request_message_interval(mavutil.mavlink.MAVLINK_MSG_ID_SYS_STATUS, 2)     # 2 Hz
        self.request_message_interval(mavutil.mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT, 5) # 5 Hz
        self.request_message_interval(mavutil.mavlink.MAVLINK_MSG_ID_ATTITUDE, 10)      # 10 Hz
        self.request_message_interval(mavutil.mavlink.MAVLINK_MSG_ID_BATTERY_STATUS, 1) # 1 Hz
        # Telemetry loop
        threading.Thread(target=self._rx_loop, daemon=True).start()
        # Periodic heartbeat (as GCS/onboard controller)
        threading.Thread(target=self._tx_heartbeat, daemon=True).start()

    def stop(self):
        self._stop = True
        try:
            self.m.close()
        except: pass

    def _tx_heartbeat(self):
        while not self._stop:
            # Identify as onboard controller or GCS
            self.m.mav.heartbeat_send(
                mavutil.mavlink.MAV_TYPE_ONBOARD_CONTROLLER,
                mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0
            )
            time.sleep(1)

    def _rx_loop(self):
        while not self._stop:
            msg = self.m.recv_match(blocking=True, timeout=1)
            if not msg:
                continue
            mtype = msg.get_type()
            with self._lock:
                self._telemetry[mtype] = msg.to_dict()

    def get_telemetry_snapshot(self) -> Dict:
        with self._lock:
            data = dict(self._telemetry)
        # Derive friendly fields
        hb = data.get('HEARTBEAT', {})
        gpi = data.get('GLOBAL_POSITION_INT', {})
        att = data.get('ATTITUDE', {})
        batt = data.get('BATTERY_STATUS', {})
        mode = mavutil.mode_string_human(self.m)
        return {
            'mode': mode,
            'armed': bool(hb.get('base_mode', 0) & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED),
            'lat': gpi.get('lat', 0)/1e7 if gpi else None,
            'lon': gpi.get('lon', 0)/1e7 if gpi else None,
            'rel_alt_m': gpi.get('relative_alt', 0)/1000 if gpi else None,
            'yaw': att.get('yaw'),
            'battery_mV': batt.get('voltages', [None])[0],
            'raw': data,
        }

    def request_message_interval(self, msg_id: int, hz: float):
        interval_us = int(1e6 / max(hz, 0.1))
        self.m.mav.command_long_send(
            self.m.target_system, self.m.target_component,
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
            0, msg_id, interval_us, 0, 0, 0, 0, 0
        )

    # Modes: MANUAL, LOITER, GUIDED, RTL (ArduPilot)
    def set_mode(self, mode_name: str):
        mode_name = mode_name.upper()
        if mode_name not in self.m.mode_mapping():
            raise ValueError(f"Unsupported mode: {mode_name}")
        custom_mode = self.m.mode_mapping()[mode_name]
        self.m.set_mode(custom_mode)

    def arm(self, arm: bool = True, force: bool = False):
        self.m.mav.command_long_send(
            self.m.target_system, self.m.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 1 if arm else 0, 0 if not force else 21196, 0,0,0,0,0
        )

    def guided_goto(self, lat_deg: float, lon_deg: float, alt_m: float, groundspeed: Optional[float]=None):
        # Ensure GUIDED
        self.set_mode('GUIDED')
        if groundspeed is not None:
            self.m.mav.command_long_send(
                self.m.target_system, self.m.target_component,
                mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, 0, 1, groundspeed, -1, 0, 0, 0, 0
            )
        self.m.mav.set_position_target_global_int_send(
            int(time.time()*1000),
            self.m.target_system, self.m.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            0b0000111111111000,  # only lat,lon,alt enabled
            int(lat_deg*1e7), int(lon_deg*1e7), alt_m,
            0,0,0, 0,0,0, 0,0
        )

    def rtl(self):
        self.set_mode('RTL')

    def loiter(self):
        self.set_mode('LOITER')

    def manual(self):
        self.set_mode('MANUAL')

    # Mission upload (simple)
    def upload_mission(self, waypoints: List[Dict]):
        # waypoints list: [{lat, lon, alt, hold_s, acceptance_m, yaw_deg}]
        wp_msgs = []
        seq = 0
        for i, wp in enumerate(waypoints):
            frame = mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT
            cmd = mavutil.mavlink.MAV_CMD_NAV_WAYPOINT
            autocontinue = 1
            wp_msgs.append(mavutil.mavlink.MAVLink_mission_item_message(
                self.m.target_system, self.m.target_component, seq, frame, cmd, 0, autocontinue,
                wp.get('hold_s',0), 0, wp.get('acceptance_m', 5), wp.get('yaw_deg', float('nan')),
                wp['lat'], wp['lon'], wp['alt']
            ))
            seq += 1
        self.m.waypoint_clear_all_send()
        self.m.waypoint_count_send(len(wp_msgs))
        for i, mi in enumerate(wp_msgs):
            self.m.mav.send(mi)
            # Optionally wait for MISSION_REQUEST for index i here for robustness

    # Camera control (through ArduPilot camera or relay)
    def start_image_capture(self, interval_s: float = 0, count: int = 0):
        # 0 interval => single capture if count=1; continuous if interval>0 and count=0
        self.m.mav.command_long_send(
            self.m.target_system, self.m.target_component,
            mavutil.mavlink.MAV_CMD_IMAGE_START_CAPTURE,
            0, 0, interval_s, count, 0, 0, 0, 0
        )

    def stop_image_capture(self):
        self.m.mav.command_long_send(
            self.m.target_system, self.m.target_component,
            mavutil.mavlink.MAV_CMD_IMAGE_STOP_CAPTURE,
            0, 0, 0, 0, 0, 0, 0, 0
        )
