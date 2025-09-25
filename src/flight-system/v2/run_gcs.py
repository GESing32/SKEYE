import asyncio
import json
import logging
import os
import signal
import serial
import time
from typing import Any, Dict, Set, Optional

import websockets
from gcs_core import MavSerialCore, RELAY_TYPES

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
            msg = core.recv_once()
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
        except Exception as e:
            log.warning(f"telemetry loop error: {e}")
        await asyncio.sleep(0.01)

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
                else:
                    await ws.send(json.dumps({"type": "ERROR", "message": f"unknown cmd {c}"}))
                    continue
                await ws.send(json.dumps({"type": "ACK", "cmd": c}))
            except Exception as e:
                await ws.send(json.dumps({"type": "ERROR", "message": str(e)}))
    finally:
        hub.clients.discard(ws)
        log.info("Client disconnected")

async def main():
    serial_dev = os.environ.get("GCS_SERIAL", "COM4")   #"/dev/ttyUSB0"
    baud = int(os.environ.get("GCS_BAUD", "57600"))
    ws_host = os.environ.get("GCS_WS_HOST", "0.0.0.0")
    ws_port = int(os.environ.get("GCS_WS_PORT", "8765"))

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