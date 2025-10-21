import asyncio
import json
import logging
import os
import signal
import serial
import serial.tools.list_ports
import time
from typing import Any, Dict, Set, Optional, List

import websockets
from gcs_core import MavSerialCore, RELAY_TYPES
from survey_planner import SurveyPlanner, CameraSpec

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("GCS")

class WebSocketHub:
    def __init__(self):
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self._telemetry_cache = {}  # Cache last telemetry values
        
    async def broadcast(self, payload: Dict[str, Any]):
        if not self.clients:
            return
        # Only broadcast if values changed significantly
        msg_type = payload.get("type")
        if msg_type in self._telemetry_cache:
            if not self._is_significant_change(payload, self._telemetry_cache[msg_type]):
                return
        self._telemetry_cache[msg_type] = payload
        data = json.dumps(payload)
        await asyncio.gather(*[c.send(data) for c in list(self.clients)], return_exceptions=True)
        
    def _is_significant_change(self, new_data: Dict, old_data: Dict, threshold: float = 0.1) -> bool:
        # Compare numeric values with threshold
        return True  # Implement comparison logic based on message type

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

async def handle_client(ws, _path, core: MavSerialCore, hub: WebSocketHub):
    hub.clients.add(ws)
    log.info("Client connected")
    try:
        await ws.send(json.dumps({
            "type": "HELLO",
            "mode": core.mode_str,
            "armed": core.armed,
            "link_ok": core.link_ok(),
        }))
        async for raw in ws:
            try:
                cmd = json.loads(raw)
            except Exception as e:
                await ws.send(json.dumps({"type": "ERROR", "message": f"invalid JSON: {e}"}))
                continue
            c = cmd.get("cmd")
            if not c:
                await ws.send(json.dumps({"type": "ERROR", "message": "missing 'cmd'"}))
                continue
            try:
                if c == "arm":
                    core.arm(bool(cmd.get("value", True)))
                elif c == "mode":
                    core.set_mode(str(cmd["mode"]))
                elif c == "goto":
                    core.goto_guided(float(cmd["lat"]), float(cmd["lon"]), float(cmd["alt_rel"]))
                elif c == "speed":
                    core.set_speed(float(cmd["m_s"]))
                elif c == "rtl":
                    core.rtl()
                elif c == "mission_clear":
                    core.mission_clear_all()
                elif c == "mission_upload":
                    items = cmd.get("items", [])
                    core.mission_upload_begin(items)
                elif c == "mission_start":
                    core.mission_start(int(cmd.get("first_item", 0)), int(cmd.get("last_item", 0xFFFF)))
                elif c == "survey_plan":
                    # Generate survey mission from polygon
                    polygon = cmd.get("polygon", [])  # List of {"lat": x, "lon": y}
                    camera_config = cmd.get("camera", {})
                    altitude = float(cmd.get("altitude", 50.0))
                    overlap_front = float(cmd.get("overlap_front", 75.0))
                    overlap_side = float(cmd.get("overlap_side", 75.0))  #standard is 65% but 75% minimum from ER
                    grid_angle = float(cmd.get("grid_angle", 0.0))
                    hover_and_capture = bool(cmd.get("hover_and_capture", False))

                    # Create camera from config or use default
                    camera = CameraSpec(
                        name=camera_config.get("name", "Custom"),
                        sensor_width=float(camera_config.get("sensor_width", 6.17)),
                        sensor_height=float(camera_config.get("sensor_height", 4.55)),
                        focal_length=float(camera_config.get("focal_length", 4.15)),
                        image_width=int(camera_config.get("image_width", 4000)),
                        image_height=int(camera_config.get("image_height", 3000))
                    )

                    planner = SurveyPlanner(camera)
                    result = planner.generate_survey(
                        polygon=[(p["lat"], p["lon"]) for p in polygon],
                        altitude_rel=altitude,
                        overlap_front=overlap_front,
                        overlap_side=overlap_side,
                        grid_angle_deg=grid_angle,
                        hover_and_capture=hover_and_capture
                    )

                    # Send back mission items and statistics
                    await ws.send(json.dumps({
                        "type": "SURVEY_RESULT",
                        "items": result["mission_items"],
                        "statistics": result["statistics"],
                        "transects": result["transects"]
                    }))
                    continue
                else:
                    await ws.send(json.dumps({"type": "ERROR", "message": f"unknown cmd {c}"}))
                    continue
                await ws.send(json.dumps({"type": "ACK", "cmd": c}))
            except Exception as e:
                await ws.send(json.dumps({"type": "ERROR", "message": str(e)}))
    finally:
        hub.clients.discard(ws)
        log.info("Client disconnected")

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
    # Try to get device from environment variable first
    serial_dev = os.environ.get("GCS_SERIAL", None)
    baud = int(os.environ.get("GCS_BAUD", "57600"))
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
        lambda ws, path: handle_client(ws, path, core, hub, rate_limiter),
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