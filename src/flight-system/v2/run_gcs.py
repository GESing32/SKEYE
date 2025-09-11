import asyncio
import json
import logging
import os
import signal
from typing import Any, Dict, Set

import websockets
from gcs_core import MavSerialCore, RELAY_TYPES

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("GCS")

class WebSocketHub:
    def __init__(self):
        self.clients: Set[websockets.WebSocketServerProtocol] = set()

    async def broadcast(self, payload: Dict[str, Any]):
        if not self.clients:
            return
        data = json.dumps(payload)
        await asyncio.gather(*[c.send(data) for c in list(self.clients)], return_exceptions=True)

async def telemetry_loop(core: MavSerialCore, hub: WebSocketHub):
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
    serial_dev = os.environ.get("GCS_SERIAL", "/dev/ttyUSB0")
    baud = int(os.environ.get("GCS_BAUD", "57600"))
    ws_host = os.environ.get("GCS_WS_HOST", "0.0.0.0")
    ws_port = int(os.environ.get("GCS_WS_PORT", "8765"))

    core = MavSerialCore(serial_dev=serial_dev, baud=baud)
    core.wait_heartbeat(timeout=60.0)

    hub = WebSocketHub()
    server = await websockets.serve(lambda ws, path: handle_client(ws, path, core, hub), ws_host, ws_port)
    log.info(f"WebSocket server on ws://{ws_host}:{ws_port}")

    loop = asyncio.get_event_loop()
    stop = loop.create_future()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set_result, None)

    tasks = [asyncio.create_task(telemetry_loop(core, hub))]
    await stop
    for t in tasks: t.cancel()
    server.close()
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())