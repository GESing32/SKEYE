import asyncio
import json
import logging
import math
import os
import signal
import serial
import serial.tools.list_ports
import time
from typing import Any, Dict, Set, Optional, List

import websockets
from pymavlink import mavutil
from gcs_core import MavSerialCore, RELAY_TYPES
from survey_planner import SurveyPlanner, CameraSpec

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("GCS")


def clean_for_json(obj):
    """Recursively clean an object for JSON serialization by replacing NaN/Inf with null."""
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj

class WebSocketHub:
    def __init__(self):
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self._telemetry_cache = {}  # Cache last telemetry values
        self._batch_buffer: List[Dict[str, Any]] = []  # Buffer for batched messages
        self._last_batch_time: float = 0.0  # Last batch broadcast time
        self._batch_interval_s: float = 0.1  # Batch interval (100ms)

        # High-frequency message types that benefit from batching
        self.HIGH_FREQUENCY_TYPES = {
            "GLOBAL_POSITION_INT",
            "ATTITUDE",
            "VFR_HUD",
        }

    async def register(self, websocket):
        """Register a new WebSocket client"""
        self.clients.add(websocket)
        log.info(f"Client connected. Total clients: {len(self.clients)}")

    async def unregister(self, websocket):
        """Unregister a WebSocket client"""
        self.clients.discard(websocket)
        log.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def broadcast(self, payload: Dict[str, Any], batch: bool = True):
        """
        Broadcast message to all connected clients with optional batching.

        Args:
            payload: Message to broadcast
            batch: If True, batch high-frequency messages (default: True)
        """
        if not self.clients:
            return

        msg_type = payload.get("type")

        # Special handling for GLOBAL_POSITION_INT to ensure first position is always sent
        if msg_type == "GLOBAL_POSITION_INT":
            is_first = msg_type not in self._telemetry_cache
            lat = payload.get("lat", 0) / 1e7
            lon = payload.get("lon", 0) / 1e7

            if is_first:
                log.info(f"📍 First position: lat={lat:.6f}, lon={lon:.6f} - sending immediately")
                self._telemetry_cache[msg_type] = payload
                await self._send_message(payload)  # Send first position immediately, unbatched
                return

        # Only broadcast if values changed significantly
        if msg_type in self._telemetry_cache:
            if not self._is_significant_change(payload, self._telemetry_cache[msg_type]):
                return

        self._telemetry_cache[msg_type] = payload

        # Batch high-frequency messages
        if batch and msg_type in self.HIGH_FREQUENCY_TYPES:
            self._batch_buffer.append(payload)

            # Send batch if interval elapsed
            current_time = time.time()
            if current_time - self._last_batch_time >= self._batch_interval_s:
                await self._send_batch()
                self._last_batch_time = current_time
        else:
            # Send immediately for critical/low-frequency messages
            await self._send_message(payload)

    async def _send_message(self, payload: Dict[str, Any]):
        """Send a single message to all clients."""
        # Clean NaN/Inf values before JSON serialization
        cleaned_payload = clean_for_json(payload)
        data = json.dumps(cleaned_payload)
        await asyncio.gather(*[c.send(data) for c in list(self.clients)], return_exceptions=True)

    async def _send_batch(self):
        """Send batched messages to all clients."""
        if not self._batch_buffer:
            return

        # Create batch message
        batch_payload = {
            "type": "TELEMETRY_BATCH",
            "messages": self._batch_buffer.copy(),
            "count": len(self._batch_buffer),
            "timestamp": time.time()
        }

        # Clean and send
        cleaned_payload = clean_for_json(batch_payload)
        data = json.dumps(cleaned_payload)
        await asyncio.gather(*[c.send(data) for c in list(self.clients)], return_exceptions=True)

        # Clear buffer
        self._batch_buffer.clear()

    def _is_significant_change(self, new_data: Dict, old_data: Dict, threshold: float = 0.1) -> bool:
        """
        Compare messages to determine if change is significant enough to broadcast.

        Args:
            new_data: New message data
            old_data: Previous message data
            threshold: Threshold for numeric value changes (default: 10%)

        Returns:
            True if change is significant, False otherwise
        """
        msg_type = new_data.get("type")

        # Always broadcast critical message types
        # STATUSTEXT and COMMAND_ACK must always be sent to capture every error occurrence
        critical_types = {
            "HEARTBEAT",
            "SYS_STATUS",
            "MISSION_CURRENT",
            "MISSION_ACK",
            "STATE_UPDATE",
            "ACK",
            "ERROR",
            "STATUSTEXT",      # Always send - user needs every error message
            "COMMAND_ACK",     # Always send - every command failure must be logged
        }
        if msg_type in critical_types:
            return True

        # Compare numeric fields with threshold
        if msg_type == "GLOBAL_POSITION_INT":
            # Always send first position update (when old_data is empty or missing position)
            if not old_data or "lat" not in old_data or old_data.get("lat", 0) == 0:
                return True

            # Check position change (significant if > 0.5m)
            lat_change = abs(new_data.get("lat", 0) - old_data.get("lat", 0)) / 1e7
            lon_change = abs(new_data.get("lon", 0) - old_data.get("lon", 0)) / 1e7
            alt_change = abs(new_data.get("relative_alt", 0) - old_data.get("relative_alt", 0)) / 1000.0

            # More sensitive threshold: 0.5m instead of 1m
            if lat_change > 0.000005 or lon_change > 0.000005 or alt_change > 0.5:
                return True

        elif msg_type == "VFR_HUD":
            # Check airspeed/groundspeed change (> 0.5 m/s)
            airspeed_change = abs(new_data.get("airspeed", 0) - old_data.get("airspeed", 0))
            groundspeed_change = abs(new_data.get("groundspeed", 0) - old_data.get("groundspeed", 0))

            if airspeed_change > 0.5 or groundspeed_change > 0.5:
                return True

        elif msg_type == "ATTITUDE":
            # Check attitude change (> 5 degrees)
            roll_change = abs(new_data.get("roll", 0) - old_data.get("roll", 0))
            pitch_change = abs(new_data.get("pitch", 0) - old_data.get("pitch", 0))
            yaw_change = abs(new_data.get("yaw", 0) - old_data.get("yaw", 0))

            if roll_change > 0.087 or pitch_change > 0.087 or yaw_change > 0.087:  # ~5 degrees
                return True

        # Default: no significant change
        return False

class MessageQueue:
    def __init__(self, maxsize: int = 100):
        self.queue = asyncio.Queue(maxsize=maxsize)
        
    async def put(self, msg: Dict[str, Any]):
        try:
            self.queue.put_nowait(msg)
        except asyncio.QueueFull:
            # Remove oldest message if queue is full
            self.queue.get_nowait()
            await self.queue.put(msg)
            
class CommandRateLimiter:
    def __init__(self):
        self.command_timestamps = {}
        self.min_intervals = {
            "goto": 0.5,  # seconds between position commands
            "mode": 1.0,  # seconds between mode changes
            "arm": 2.0,   # seconds between arm/disarm
        }
        
    async def can_execute(self, command: str) -> bool:
        now = time.time()
        if command in self.command_timestamps:
            last_time = self.command_timestamps[command]
            if now - last_time < self.min_intervals.get(command, 0.5):
                return False
        self.command_timestamps[command] = now
        return True

class ConnectionManager:
    def __init__(self, serial_dev: str, baud: int):
        self.serial_dev = serial_dev
        self.baud = baud
        self.core = None
        self.reconnect_interval = 5.0
        
    async def connect(self) -> Optional[MavSerialCore]:
        while True:
            try:
                self.core = MavSerialCore(self.serial_dev, self.baud)
                await asyncio.get_event_loop().run_in_executor(
                    None, self.core.wait_heartbeat, 10.0
                )
                return self.core
            except Exception as e:
                log.error(f"Connection failed: {e}")
                await asyncio.sleep(self.reconnect_interval)

async def connection_monitor(connection_manager: ConnectionManager):
    """Monitors connection status and attempts reconnection if needed."""
    while True:
        try:
            if not connection_manager.core or not connection_manager.core.link_ok():
                log.warning("Connection lost, attempting reconnection...")
                connection_manager.core = await connection_manager.connect()
                log.info("Reconnected successfully")
        except Exception as e:
            log.error(f"Connection monitor error: {e}")
        await asyncio.sleep(1.0)  # Check connection every second

async def telemetry_loop(core: MavSerialCore, hub: WebSocketHub, queue: MessageQueue):
    """
    Optimized telemetry loop with non-blocking serial reads.
    Uses thread pool executor to prevent blocking the event loop.
    """
    last_sent = {}
    min_period = {
        "HEARTBEAT": 1.0,
        "GLOBAL_POSITION_INT": 0.1,
        "ATTITUDE": 0.1,
        "VFR_HUD": 0.3,
        "BATTERY_STATUS": 1.0,
        "SYS_STATUS": 1.0,
        "GPS_RAW_INT": 1.0,
        "EKF_STATUS_REPORT": 1.0,
        "HOME_POSITION": 2.0,
        "MISSION_CURRENT": 0.5,
    }
    loop = asyncio.get_event_loop()

    while True:
        try:
            # Run blocking serial read in thread pool to avoid blocking event loop
            msg = await loop.run_in_executor(None, core.recv_once)

            if msg:
                core.process_protocol_side_effects(msg)
                t = msg["type"]
                if t in RELAY_TYPES:
                    # Add message to queue regardless of broadcast timing
                    await queue.put(msg)

                    # Broadcast based on rate limiting
                    last = last_sent.get(t, 0.0)
                    period = min_period.get(t, 0.5)
                    now = loop.time()
                    if now - last >= period:
                        await hub.broadcast(msg)
                        last_sent[t] = now
            else:
                # No message available, short sleep to prevent tight loop
                await asyncio.sleep(0.01)
        except Exception as e:
            log.warning(f"telemetry loop error: {e}")
            await asyncio.sleep(0.1)  # Longer sleep on error

async def handle_client(websocket, core: MavSerialCore, hub: WebSocketHub):
    """Handle individual WebSocket client (websockets 14.0+ API)"""
    await hub.register(websocket)
    
    try:
        # Send initial HELLO message
        await websocket.send(json.dumps({
            "type": "HELLO",
            "link_ok": core.link_ok(),
            "mode": core.mode_str,
            "armed": core.armed,
        }))
        
        # Handle incoming commands
        async for message in websocket:
            try:
                data = json.loads(message)
                command = data.get("command")
                
                if command == "arm":
                    force = data.get("force", True)
                    core.arm(should_arm=True)
                    log.info(f"ARM command executed")

                    # Send ACK to requesting client
                    await websocket.send(json.dumps({
                        "type": "ACK",
                        "command": "arm",
                        "success": True
                    }))

                    # Broadcast state change to all clients (no batching for immediate delivery)
                    await hub.broadcast({
                        "type": "STATE_UPDATE",
                        "armed": True
                    }, batch=False)

                elif command == "disarm":
                    core.arm(should_arm=False)
                    log.info(f"DISARM command executed")

                    # Send ACK to requesting client
                    await websocket.send(json.dumps({
                        "type": "ACK",
                        "command": "disarm",
                        "success": True
                    }))

                    # Broadcast state change to all clients (no batching for immediate delivery)
                    await hub.broadcast({
                        "type": "STATE_UPDATE",
                        "armed": False
                    }, batch=False)

                elif command == "set_mode":
                    mode = data.get("mode", "STABILIZE")
                    core.set_mode(mode)
                    log.info(f"SET_MODE command: mode={mode}")

                    # Send ACK to requesting client
                    await websocket.send(json.dumps({
                        "type": "ACK",
                        "command": "set_mode",
                        "mode": mode,
                        "success": True
                    }))

                    # Broadcast state change to all clients (no batching for immediate delivery)
                    await hub.broadcast({
                        "type": "STATE_UPDATE",
                        "mode": mode
                    }, batch=False)

                elif command == "goto":
                    lat = data.get("lat")
                    lon = data.get("lon")
                    alt = data.get("alt", 20.0)
                    if lat and lon:
                        core.goto_guided(lat, lon, alt)
                        log.info(f"GOTO command: lat={lat}, lon={lon}, alt={alt}")
                        await websocket.send(json.dumps({
                            "type": "ACK",
                            "command": "goto",
                            "success": True
                        }))
                
                elif command == "mission_clear":
                    core.mission_clear_all()
                    log.info(f"MISSION_CLEAR executed")
                    await websocket.send(json.dumps({
                        "type": "ACK",
                        "command": "mission_clear",
                        "success": True
                    }))

                elif command == "mission_upload":
                    mission_items = data.get("mission_items", [])
                    log.info(f"MISSION_UPLOAD: {len(mission_items)} items")

                    # Convert Flutter float coordinates to MAVLink int format
                    for i, item in enumerate(mission_items):
                        # Add seq field if missing
                        if "seq" not in item:
                            item["seq"] = i

                        # Convert frame from 3 (GLOBAL_RELATIVE_ALT) to 6 (GLOBAL_RELATIVE_ALT_INT)
                        if item.get("frame") == 3:
                            item["frame"] = 6

                        # Convert x, y from float degrees to int (degrees * 1e7)
                        if "x" in item and isinstance(item["x"], float):
                            item["x"] = int(item["x"] * 1e7)
                        if "y" in item and isinstance(item["y"], float):
                            item["y"] = int(item["y"] * 1e7)

                    # Auto-insert TAKEOFF command if missing (ArduPilot copter requirement)
                    if mission_items:
                        first_cmd = mission_items[0].get("command")
                        log.info(f"First mission item command: {first_cmd}")

                        if first_cmd != 22:
                            # For ArduCopter: TAKEOFF uses lat=0, lon=0 to takeoff from current position
                            # The altitude parameter specifies the target altitude
                            takeoff_alt = data.get("alt", 20.0)  # Default takeoff altitude (meters, relative)

                            takeoff_item = {
                                "seq": 0,
                                "frame": 6,  # MAV_FRAME_GLOBAL_RELATIVE_ALT_INT (must match other waypoints)
                                "command": 22,  # MAV_CMD_NAV_TAKEOFF
                                "current": 1,
                                "autocontinue": 1,
                                "param1": 0.0,  # pitch (copter: min pitch if airspeed sensor)
                                "param2": 0.0,  # empty
                                "param3": 0.0,  # empty
                                "param4": 0.0,  # yaw angle (0 = use current heading)
                                "x": 0,  # lat = 0 for copters (takeoff from current position)
                                "y": 0,  # lon = 0 for copters (takeoff from current position)
                                "z": takeoff_alt,
                                "mission_type": 0,  # MAV_MISSION_TYPE_MISSION
                            }
                            mission_items.insert(0, takeoff_item)
                            log.info(f"✓ Auto-inserted TAKEOFF command (cmd=22) at {takeoff_alt}m altitude (from current position)")

                            # Re-sequence all items
                            for idx, item in enumerate(mission_items):
                                item["seq"] = idx
                                # Only first item (TAKEOFF) should be marked as current
                                item["current"] = 1 if idx == 0 else 0
                                # Ensure mission_type is set for all items
                                if "mission_type" not in item:
                                    item["mission_type"] = 0

                            log.info(f"Mission now has {len(mission_items)} items (including TAKEOFF)")
                        else:
                            log.info("TAKEOFF command already present, no insertion needed")

                    core.mission_upload_begin(mission_items)
                    await websocket.send(json.dumps({
                        "type": "ACK",
                        "command": "mission_upload",
                        "success": True,
                        "count": len(mission_items)
                    }))

                elif command == "mission_start":
                    log.info("MISSION_START command received")
                    core.mission_start()
                    await websocket.send(json.dumps({
                        "type": "ACK",
                        "command": "mission_start",
                        "success": True
                    }))

                elif command == "takeoff":
                    alt = data.get("alt", 20.0)
                    log.info(f"TAKEOFF command received: alt={alt}m")

                    # Send MAV_CMD_NAV_TAKEOFF command
                    core.m.mav.command_long_send(
                        core.target_system,
                        core.target_component,
                        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                        0,  # confirmation
                        0,  # param1: pitch
                        0,  # param2: empty
                        0,  # param3: empty
                        0,  # param4: yaw angle (0 = north)
                        0,  # param5: latitude (0 = current position)
                        0,  # param6: longitude (0 = current position)
                        alt,  # param7: altitude
                    )

                    await websocket.send(json.dumps({
                        "type": "ACK",
                        "command": "takeoff",
                        "success": True,
                        "altitude": alt
                    }))

                elif command == "generate_survey":
                    # QGC-style survey generation from polygon waypoints
                    from survey_planner import SurveyConfig, TriggerMode, EntryPoint, LatLon

                    polygon_points = data.get("polygon", [])
                    if len(polygon_points) < 3:
                        await websocket.send(json.dumps({
                            "type": "ERROR",
                            "command": "generate_survey",
                            "error": "Survey requires at least 3 polygon points"
                        }))
                        log.error("Survey generation failed: insufficient polygon points")
                        return

                    # Convert polygon points to LatLon objects
                    polygon = [LatLon(lat=p["lat"], lon=p["lon"]) for p in polygon_points]

                    # Parse survey configuration
                    altitude = data.get("altitude", 50.0)
                    speed = data.get("speed", 5.0)
                    front_overlap = data.get("front_overlap", 75.0)
                    side_overlap = data.get("side_overlap", 75.0)
                    grid_angle = data.get("grid_angle", 0.0)
                    turnaround_dist = data.get("turnaround_dist", 10.0)

                    log.info(f"GENERATE_SURVEY: {len(polygon_points)} polygon points")
                    log.info(f"  Altitude: {altitude}m, Speed: {speed}m/s")
                    log.info(f"  Overlap: {front_overlap}% front, {side_overlap}% side")
                    log.info(f"  Grid angle: {grid_angle}°")

                    # Create camera and survey config
                    camera = CameraSpec.sentera_double_4k_default()
                    config = SurveyConfig(
                        altitude_m=altitude,
                        speed_m_s=speed,
                        front_overlap_pct=front_overlap,
                        side_overlap_pct=side_overlap,
                        grid_angle_deg=grid_angle,
                        entry_point=EntryPoint.TOP_LEFT,
                        turnaround_dist_m=turnaround_dist,
                        trigger_mode=TriggerMode.DISTANCE,
                        camera_angle_deg=90.0,  # Nadir (straight down)
                    )

                    # Generate survey mission
                    planner = SurveyPlanner(camera)
                    mission_items, statistics = planner.generate_mission_items(polygon, config)

                    log.info(f"✓ Survey generated: {len(mission_items)} waypoints")
                    log.info(f"  Photos: {statistics['photo_count']}")
                    log.info(f"  Distance: {statistics['flight_distance_m']}m")
                    log.info(f"  Flight time: {statistics['flight_time_min']} min")
                    log.info(f"  Coverage: {statistics['coverage_area_acres']} acres")
                    log.info(f"  GSD: {statistics['gsd_cm_px']} cm/px")

                    # Send survey mission back to client (clean NaN/Inf values for JSON)
                    response = clean_for_json({
                        "type": "SURVEY_GENERATED",
                        "command": "generate_survey",
                        "success": True,
                        "mission_items": mission_items,
                        "statistics": statistics
                    })
                    await websocket.send(json.dumps(response))

                else:
                    log.warning(f"Unknown command: {command}")
                    
            except json.JSONDecodeError as e:
                log.error(f"JSON decode error: {e}")
            except Exception as e:
                log.error(f"Command handler error: {e}")
                
    except websockets.ConnectionClosed:
        log.info("Client disconnected")
    except Exception as e:
        log.error(f"Client handler error: {e}")
    finally:
        await hub.unregister(websocket)

def auto_detect_serial_device(preferred_baud: int = 57600) -> Optional[tuple[str, int]]:
    """
    Auto-detect MAVLink serial device by scanning available ports.
    Optimized for Pixhawk 6X with SiK Telemetry Radio (915MHz).

    Pixhawk 6X Port Configuration:
    - TELEM1: MAVLink2 @ 57600  ← SiK Radio (GCS Connection) ✓ TARGET
    - TELEM2: MAVLink1 @ 115200 ← Camera Sensor            ✗ AVOID

    Prioritizes:
    - MAVLink2 protocol at 57600 baud (TELEM1/SiK Radio)
    - SiK Radio / FTDI telemetry devices
    - Excludes 115200 baud (TELEM2/Camera sensor)

    Returns:
        Tuple of (device_path, baud_rate) if found, None otherwise
    """
    # MAVLink baud rates - prioritize 57600 (TELEM1/SiK Radio), exclude 115200 (TELEM2/Camera)
    # SiK Radio on TELEM1 uses 57600 baud for 915MHz operation
    baud_rates = [57600, preferred_baud, 921600, 500000, 230400]
    # Remove duplicates and exclude 115200 (TELEM2 is camera sensor port)
    baud_rates = [b for b in dict.fromkeys(baud_rates) if b != 115200]

    # Known MAVLink device identifiers - prioritized for Pixhawk 6X + SiK Radio
    mavlink_identifiers = [
        # SiK Telemetry Radio (915MHz) - HIGHEST PRIORITY
        ('VID:PID=0403:6001', 'SiK Telemetry Radio (FTDI)'),  # Most common SiK radio
        ('VID:PID=0403:6015', 'SiK Radio v2 (FTDI)'),
        ('VID:PID=26AC:0011', '3DR Radio/SiK'),

        # Pixhawk 6X family
        ('VID:PID=26AC', 'Pixhawk 6X'),  # Holybro Pixhawk 6X
        ('VID:PID=0483:5740', 'Pixhawk 6X (STM32H7)'),
        ('VID:PID=2DAE:1058', 'Pixhawk 6X'),

        # Other FTDI-based telemetry (RFD900, etc.)
        ('VID:PID=0403', 'FTDI Telemetry'),

        # Generic STM32 (if direct USB connection)
        ('VID:PID=0483', 'STM32'),
    ]

    log.info("Scanning for MAVLink devices...")
    ports = serial.tools.list_ports.comports()

    # Priority 1: Check for known MAVLink devices
    for port in ports:
        hwid = port.hwid if hasattr(port, 'hwid') else ''
        for vid_pid, name in mavlink_identifiers:
            if vid_pid in hwid:
                log.info(f"Found {name} device: {port.device} ({hwid})")
                # Try to verify it's actually MAVLink
                for baud in baud_rates[:3]:  # Only try top 3 baud rates for known devices
                    if verify_mavlink_device(port.device, baud):
                        log.info(f"✓ Verified MAVLink at {port.device} @ {baud} baud")
                        return (port.device, baud)

    # Priority 2: Check all USB serial devices
    log.info("Checking all available serial ports...")
    for port in ports:
        # Skip unwanted ports
        skip_keywords = ['bluetooth', 'virtual', 'debug', 'jtag']
        if any(keyword in port.device.lower() or keyword in port.description.lower() for keyword in skip_keywords):
            log.debug(f"Skipping {port.device}: {port.description}")
            continue

        log.info(f"Testing {port.device}: {port.description}")

        # For SiK Radio specifically, only try 57600 baud (standard)
        if 'ftdi' in port.description.lower() or '0403' in (port.hwid if hasattr(port, 'hwid') else ''):
            log.info(f"  Detected FTDI device (likely SiK Radio) - testing 57600 baud only")
            if verify_mavlink_device(port.device, 57600):
                log.info(f"✓ Found SiK Radio at {port.device} @ 57600 baud")
                return (port.device, 57600)
        else:
            # For other devices, try multiple baud rates (but skip 115200)
            for baud in baud_rates[:3]:  # Try top 3 baud rates
                if verify_mavlink_device(port.device, baud):
                    log.info(f"✓ Found MAVLink device at {port.device} @ {baud} baud")
                    return (port.device, baud)

    log.warning("No MAVLink devices found")
    return None

def verify_mavlink_device(port: str, baud: int, timeout: float = 3.0) -> bool:
    """
    Verify if a serial port has a MAVLink device by attempting to receive a heartbeat.

    Args:
        port: Serial port path
        baud: Baud rate to test
        timeout: Maximum time to wait for heartbeat (seconds)

    Returns:
        True if MAVLink heartbeat detected, False otherwise
    """
    try:
        ser = serial.Serial(port, baud, timeout=0.5)
        start_time = time.time()
        buffer = bytearray()

        log.debug(f"  Checking {port} @ {baud} baud...")

        while time.time() - start_time < timeout:
            if ser.in_waiting:
                buffer.extend(ser.read(ser.in_waiting))

                # Look for MAVLink v2 (0xFD) first - prioritized for Pixhawk 6X
                # Then fall back to MAVLink v1 (0xFE)
                for i in range(len(buffer) - 8):
                    if buffer[i] == 0xFD:  # MAVLink v2 (PRIORITY - QGC standard)
                        payload_len = buffer[i + 1]
                        if payload_len < 256 and i + 12 + payload_len <= len(buffer):
                            msg_id_low = buffer[i + 9]
                            msg_id_mid = buffer[i + 10]
                            msg_id_high = buffer[i + 11]
                            msg_id = msg_id_low | (msg_id_mid << 8) | (msg_id_high << 16)
                            if msg_id == 0:  # HEARTBEAT message
                                ser.close()
                                log.info(f"  ✓ MAVLink v2 heartbeat detected (Pixhawk 6X compatible)")
                                return True
                    elif buffer[i] == 0xFE:  # MAVLink v1 (may be camera - skip if at 115200)
                        # Skip MAVLink v1 detection to avoid camera port
                        # MAVLink v1: STX(1) LEN(1) SEQ(1) SYS(1) COMP(1) MSG(1) PAYLOAD(n) CRC(2)
                        if baud == 115200:
                            log.debug(f"  ⚠ MAVLink v1 at 115200 baud - likely camera, skipping")
                            continue
                        payload_len = buffer[i + 1]
                        if payload_len < 256 and i + 8 + payload_len <= len(buffer):
                            msg_id = buffer[i + 5]
                            if msg_id == 0:  # HEARTBEAT message
                                ser.close()
                                log.debug(f"  ✓ MAVLink v1 heartbeat detected")
                                return True

                # Keep buffer size manageable
                if len(buffer) > 1024:
                    buffer = buffer[-512:]
            else:
                time.sleep(0.1)

        ser.close()
        return False

    except (serial.SerialException, OSError) as e:
        log.debug(f"  ✗ Error testing {port}: {e}")
        return False

async def main():
    import sys

    # Priority: Environment variables first (for run_gcs_sitl.py), then command line args
    serial_dev = os.environ.get("GCS_SERIAL", None)
    baud = int(os.environ.get("GCS_BAUD", "57600"))

    # Override with command line arguments if env vars not set
    # Example: python run_gcs.py udp:127.0.0.1:14550 57600
    if not serial_dev and len(sys.argv) >= 2:
        serial_dev = sys.argv[1]
        baud = int(sys.argv[2]) if len(sys.argv) >= 3 else 57600

    ws_host = os.environ.get("GCS_WS_HOST", "0.0.0.0")
    ws_port = int(os.environ.get("GCS_WS_PORT", "8765"))

    # Auto-detect if not specified
    if not serial_dev:
        log.info("No GCS_SERIAL specified, auto-detecting...")
        result = auto_detect_serial_device(preferred_baud=baud)
        if result:
            serial_dev, baud = result
            log.info(f"Auto-detected device: {serial_dev} @ {baud} baud")
        else:
            log.error("Failed to auto-detect MAVLink device")
            log.info("Available ports:")
            for port in serial.tools.list_ports.comports():
                log.info(f"  - {port.device}: {port.description} ({port.hwid if hasattr(port, 'hwid') else 'N/A'})")
            log.error("Please specify device manually with GCS_SERIAL environment variable")
            return
    else:
        log.info(f"Using specified device: {serial_dev} @ {baud} baud")

    connection_manager = ConnectionManager(serial_dev, baud)
    core = await connection_manager.connect()
    
    hub = WebSocketHub()
    message_queue = MessageQueue()
    rate_limiter = CommandRateLimiter()
    
    server = await websockets.serve(
        lambda ws: handle_client(ws, core, hub),
        ws_host, ws_port
    )
    
    tasks = [
        asyncio.create_task(telemetry_loop(core, hub, message_queue)),
        asyncio.create_task(connection_monitor(connection_manager))
    ]
    
    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        log.info("Shutting down gracefully...")
    finally:
        for t in tasks:
            t.cancel()
        server.close()
        await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())