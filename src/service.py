import asyncio, json
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from mavlink_bridge import MavlinkBridge

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Adjust device/baud to your setup (USB or TELEM)
bridge = MavlinkBridge("/dev/ttyAMA0", baud=57600)

@app.on_event("startup")
def on_start():
    bridge.start()

@app.get("/telemetry")
def telemetry():
    return bridge.get_telemetry_snapshot()

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await asyncio.sleep(0.2)
            await ws.send_text(json.dumps(bridge.get_telemetry_snapshot()))
    except Exception:
        await ws.close()

@app.post("/mode/{mode}")
def set_mode(mode: str):
    bridge.set_mode(mode)
    return {"ok": True, "mode": mode.upper()}

@app.post("/arm/{state}")
def arm(state: str):
    bridge.arm(state.lower() == "true")
    return {"ok": True}

@app.post("/guided_goto")
def guided_goto(lat: float, lon: float, alt: float, gs: float | None = None):
    bridge.guided_goto(lat, lon, alt, gs)
    return {"ok": True}

@app.post("/rtl")
def rtl():
    bridge.rtl(); return {"ok": True}

@app.post("/loiter")
def loiter():
    bridge.loiter(); return {"ok": True}

@app.post("/manual")
def manual():
    bridge.manual(); return {"ok": True}

@app.post("/mission")
def mission(waypoints: list[dict]):
    bridge.upload_mission(waypoints)
    return {"ok": True, "count": len(waypoints)}

@app.post("/camera/start")
def cam_start(interval: float = 0.0, count: int = 1):
    bridge.start_image_capture(interval, count)
    return {"ok": True}

@app.post("/camera/stop")
def cam_stop():
    bridge.stop_image_capture()
    return {"ok": True}
