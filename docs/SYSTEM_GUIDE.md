# SKEYE System Guide

Architecture, design decisions, and technical implementation details.

---

## System Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Flutter UI (Dart)                     │
│  - Map display (flutter_map)                            │
│  - Survey polygon editor                                │
│  - Telemetry dashboard                                  │
│  - Control panel                                        │
└────────────────────┬────────────────────────────────────┘
                     │ WebSocket (localhost:8765)
                     │ JSON messages
                     ▼
┌─────────────────────────────────────────────────────────┐
│              WebSocket Server (Python)                   │
│  - run_gcs.py                                           │
│  - Async I/O (websockets + asyncio)                    │
│  - Message broadcasting                                 │
│  - Command routing                                      │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌───────────────┐        ┌───────────────────┐
│  gcs_core.py  │        │ survey_planner.py │
│  MAVLink      │        │  Mission          │
│  Communication│        │  Generation       │
└───────┬───────┘        └─────────┬─────────┘
        │                          │
        │                          │ uses
        ▼                          ▼
┌───────────────┐        ┌───────────────────┐
│  Pixhawk 6x   │        │ geometry_utils.py │
│  Flight       │        │  Geodetic Math    │
│  Controller   │        │                   │
└───────┬───────┘        └───────────────────┘
        │
        │ TELEM2
        ▼
┌───────────────┐
│ Sentera Camera│
│ (MAVLink trig)│
└───────────────┘
```

---

## Data Flow

### Telemetry Flow (Real-time)

```
Pixhawk → Serial → gcs_core.py → run_gcs.py → WebSocket → Flutter UI
         (57600)   (pymavlink)   (async loop)  (JSON)     (display)
```

**Update Rate:**
- Heartbeat: 1 Hz
- GPS: 5 Hz
- Attitude: 10 Hz
- VFR_HUD: 5 Hz

**Optimization:**
- Non-blocking async I/O
- Message throttling (min period per type)
- Efficient JSON serialization

### Command Flow (User → Vehicle)

```
Flutter UI → WebSocket → run_gcs.py → gcs_core.py → MAVLink → Pixhawk
  (button)    (JSON)      (parse)      (encode)     (serial)
```

**Commands:**
- `arm` / `disarm`
- `set_mode` (GUIDED, AUTO, RTL, etc.)
- `goto` (lat, lon, alt)
- `set_speed`
- `mission_upload`
- `mission_start`

### Survey Generation Flow

```
User draws polygon → Flutter sends coords → run_gcs.py
                                               ↓
                                    survey_planner.generate_transects()
                                               ↓
                                    geometry_utils (geodesic calculations)
                                               ↓
                                    Mission items generated
                                               ↓
                                    gcs_core.mission_upload()
                                               ↓
                                            Pixhawk
```

---

## Core Components

### 1. gcs_core.py (400 lines)

**Purpose:** MAVLink communication layer

**Key Classes:**
- `MavSerialCore` - Main MAVLink handler

**Key Methods:**
```python
wait_heartbeat()              # Connect and wait for heartbeat
arm(force=False)              # Arm vehicle
set_mode(mode_name)           # Change flight mode
goto_guided(lat, lon, alt)    # Send GOTO command
mission_upload_begin(items)   # Upload mission
do_set_cam_trigg_dist(dist)   # Set camera trigger
```

**Dependencies:**
- pymavlink (MAVLink protocol)

---

### 2. geometry_utils.py (525 lines)

**Purpose:** Geodetic calculations for survey planning

**Key Classes:**
- `LatLon` - Geographic coordinate (lat/lon)
- `LocalCoord` - Local NE coordinate (meters)
- `GeodeticUtils` - Geodesic calculations
- `PolygonUtils` - Polygon operations

**Algorithms:**
```python
# Karney's geodesic algorithms (survey-grade accuracy)
geodesic_distance(p1, p2)      # Distance in meters (15nm accuracy)
geodesic_bearing(p1, p2)       # Initial bearing
geodesic_destination(p, d, b)  # Destination point

# Coordinate transformations
to_local_coords(coords, origin)      # Geographic → Local NE
to_geographic_coords(locals, origin) # Local NE → Geographic

# Polygon operations
calculate_area(polygon)              # Area in m² (geodesic)
polygon_line_intersections(...)      # Line-polygon intersections
validate_edge_coverage(...)          # Survey coverage validation
```

**Dependencies:**
- geographiclib (optional, for geodesic accuracy)
- Falls back to Haversine if not available

---

### 3. survey_planner.py (830 lines)

**Purpose:** QGroundControl-style survey mission generation

**Key Classes:**
- `CameraSpec` - Camera specifications
- `SurveyConfig` - Survey parameters
- `SurveyPlanner` - Mission generator

**Camera Specifications:**
```python
CameraSpec.sentera_double_4k_default()
  - Sensor: 6.3mm × 4.7mm (1/2.3")
  - Resolution: 4000×3000 px
  - HFOV: 60°
  - Focal length: 5.4mm
  - GSD @ 50m: ~1.75 cm/px
```

**Survey Generation Algorithm:**
```python
1. Convert polygon to local coordinates
2. Calculate bounding box
3. Calculate transect spacing (from camera FOV + overlap)
4. Generate parallel lines across bounding box
5. Find intersections with polygon
6. Optimize transect order (lawnmower pattern)
7. Add turnaround points
8. Validate edge coverage (recursive)
9. Convert back to geographic coordinates
10. Generate MAVLink mission items
```

**Key Calculations:**
```python
# Ground Sample Distance
GSD = (sensor_width × altitude) / (focal_length × image_width)

# Trigger distance (spacing between photos)
trigger_distance = GSD × image_height × (1 - front_overlap)

# Transect spacing (spacing between flight lines)
transect_spacing = GSD × image_width × (1 - side_overlap)
```

---

### 4. run_gcs.py (220 lines)

**Purpose:** WebSocket server and command router

**Key Classes:**
- `WebSocketHub` - Message broadcasting
- `ConnectionManager` - Auto-reconnect
- `MessageQueue` - Telemetry buffering

**Architecture:**
```python
async def main():
    # 1. Connect to vehicle
    gcs = MavSerialCore(serial_dev, baud)

    # 2. Start telemetry loop (non-blocking)
    asyncio.create_task(telemetry_loop(gcs, hub))

    # 3. Start WebSocket server
    async with websockets.serve(handle_client, host, port):
        await asyncio.Future()  # Run forever

async def handle_client(websocket):
    # Handle JSON commands from Flutter
    if command == "arm": gcs.arm()
    elif command == "set_mode": gcs.set_mode(mode)
    elif command == "generate_survey": ...
    # etc.
```

**Performance:**
- CPU usage: ~8% (optimized async I/O)
- Memory: ~50 MB
- WebSocket latency: <10ms

---

## Design Decisions

### 1. Python Backend + Flutter Frontend

**Rationale:**
- Python: Excellent MAVLink support (pymavlink)
- Python: Rich geodetic libraries (geographiclib)
- Python: Easy serial communication
- Flutter: Fast cross-platform UI
- Flutter: Excellent map widgets (flutter_map)
- WebSocket: Clean separation, easy debugging

**Trade-offs:**
- Two processes to manage
- Network overhead (minimal with localhost)
- Benefits outweigh complexity

---

### 2. WebSocket vs Direct Integration

**Why WebSocket:**
- Language-agnostic interface
- Easy to test backend independently
- Could support remote GCS in future
- Clean separation of concerns
- JSON is human-readable for debugging

**Protocol Design:**
```json
// Command (Flutter → Python)
{"command": "set_mode", "mode": "GUIDED"}

// Telemetry (Python → Flutter)
{"type": "HEARTBEAT", "mode": "GUIDED", "armed": false}

// Response (Python → Flutter)
{"type": "ACK", "command": "set_mode", "success": true}
```

---

### 3. Async I/O Architecture

**Before (blocking):**
- Serial reads blocked event loop
- 15% CPU usage
- Laggy UI

**After (non-blocking):**
- Asyncio with ThreadPoolExecutor
- 8% CPU usage (47% reduction)
- Smooth UI updates

**Implementation:**
```python
async def telemetry_loop(gcs, hub):
    loop = asyncio.get_event_loop()
    while True:
        # Non-blocking serial read
        msg = await loop.run_in_executor(None, gcs.recv_match_cached)
        if msg:
            await hub.broadcast(msg)
        await asyncio.sleep(0.01)  # Small delay
```

---

### 4. Single Camera Support

**Decision:** Only support Sentera Double 4K

**Rationale:**
- Simplifies codebase
- No camera selection complexity
- Optimized for specific hardware
- Easier maintenance
- Can add more cameras later if needed

**How to Add Cameras:**
```python
# In survey_planner.py
class CameraSpec:
    @staticmethod
    def your_camera_name() -> 'CameraSpec':
        return CameraSpec(
            name="Your Camera",
            sensor_width_mm=...,
            sensor_height_mm=...,
            image_width_px=...,
            image_height_px=...,
            focal_length_mm=...,
        )
```

---

### 5. Geodesic vs Spherical Math

**Decision:** Use Karney's geodesic algorithms (geographiclib)

**Accuracy Comparison:**
- Haversine (spherical): ±0.5% error
- Vincenty (ellipsoidal): ±0.00005% error, but can fail to converge
- Karney (geodesic): 15 nanometer accuracy, always converges

**Fallback:**
- If geographiclib not installed → Haversine
- Still accurate enough for most surveys (<100km)

**Why It Matters:**
- Survey-grade accuracy needed
- Correct photo overlap calculations
- No missing areas in coverage

---

## Performance Metrics

| Component | Metric | Value |
|-----------|--------|-------|
| Backend CPU | Idle | 8% |
| Backend Memory | Total | ~50 MB |
| Telemetry Rate | GPS/Attitude | 5-10 Hz |
| WebSocket Latency | Localhost | <10 ms |
| Survey Generation | 100 waypoints | <50 ms |
| Mission Upload | 100 items | ~2 seconds |
| UI Framerate | Flutter | 60 fps |
| Frontend Memory | Total | ~150 MB |

---

## File Structure

```
src/flight-system/v2/
├── Python Backend (~1,975 lines)
│   ├── gcs_core.py           (400 lines) - MAVLink
│   ├── geometry_utils.py     (525 lines) - Geodetics
│   ├── survey_planner.py     (830 lines) - Survey generation
│   └── run_gcs.py            (220 lines) - WebSocket server
│
└── Flutter Frontend (~1,300 lines)
    └── lib/
        ├── main.dart                  (800 lines) - Main app
        ├── constants/
        │   └── app_constants.dart     (100 lines) - Config
        └── models/
            ├── camera_config.dart     (130 lines) - Camera specs
            └── survey_config.dart     (160 lines) - Survey models
```

**Total:** ~3,275 lines (lean and focused)

---

## Security Considerations

### Current Status

**Not Implemented:**
- WebSocket authentication (localhost only)
- Input validation on mission parameters
- Flight envelope validation
- Geofence checking

**Recommendations for Production:**
1. Add API key authentication for WebSocket
2. Validate all mission parameters (altitude, speed limits)
3. Implement geofence checking
4. Add pre-flight safety checks
5. Use TLS for WebSocket if remote access needed

---

## Extension Points

### Adding New Features

**1. New WebSocket Command:**
```python
# In run_gcs.py, handle_client()
elif command == "your_command":
    result = your_function(data)
    await websocket.send(json.dumps({
        "type": "ACK",
        "command": "your_command",
        "result": result
    }))
```

**2. New Telemetry Message:**
```python
# In gcs_core.py
RELAY_TYPES = [
    'HEARTBEAT',
    'GPS_RAW_INT',
    'YOUR_NEW_MESSAGE',  # Add here
]

# In run_gcs.py telemetry_loop()
# Will automatically broadcast to all clients
```

**3. New Survey Parameter:**
```python
# In survey_planner.py SurveyConfig
@dataclass
class SurveyConfig:
    altitude_m: float = 50.0
    # ... existing params ...
    your_new_param: float = 0.0  # Add here

# Update generate_transects_from_polygon() to use it
```

**4. Terrain Following:**
```python
# Already implemented, just needs UI
config = SurveyConfig(
    terrain_follow=True,
    terrain_provider=your_elevation_function
)
```

---

## Known Limitations

### Backend
- No mission verification after upload
- No retry logic for failed commands
- No telemetry logging to file
- Limited error recovery

### Frontend
- No offline map tiles
- No mission save/load
- Survey settings hardcoded (not in UI)
- No real-time path preview

### Hardware
- Single vehicle only
- Serial connection only (no TCP/UDP failover)
- No redundant connections

---

## Dependencies

### Python
```
pymavlink >= 2.4.0      # MAVLink protocol
websockets >= 10.0      # WebSocket server
geographiclib           # Geodesic calculations (optional)
asyncio (built-in)      # Async I/O
```

### Flutter
```yaml
flutter_map: ^7.0.2              # Map widget
latlong2: ^0.9.1                 # Coordinates
web_socket_channel: ^3.0.1       # WebSocket client
```

---

## Testing Architecture

See [Developer Guide](DEVELOPER_GUIDE.md) for complete testing details.

**Test Levels:**
1. Unit tests (pytest) - 300+ tests
2. Integration tests (SITL) - End-to-end validation
3. Widget tests (Flutter) - UI components
4. Performance tests - Benchmarks

---

**Last Updated:** November 19, 2025
