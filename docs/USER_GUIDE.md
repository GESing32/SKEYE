# SKEYE User Guide

Complete guide to operating SKEYE Ground Control Station.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Flight Modes](#flight-modes)
3. [Manual Mission Planning](#manual-mission-planning)
4. [Survey Mode](#survey-mode)
5. [SITL Testing](#sitl-testing)
6. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Hardware Setup

**Components:**
- Pixhawk 6x flight controller
- Sentera Double 4K camera
- USB cable (GCS ↔ Pixhawk)
- Telemetry cable (Pixhawk TELEM2 ↔ Camera)

**Connections:**
1. Connect Pixhawk to computer via USB
2. Connect Sentera camera to Pixhawk TELEM2 port
3. Power on Pixhawk
4. Wait for GPS lock (flashing green LED)

### Starting SKEYE

**Quick Start:**
```bash
start_gcs_hardware.bat
```

**Manual Start:**
```bash
# Terminal 1: Backend
python src/flight-system/v2/run_gcs.py

# Terminal 2: Frontend
cd src/flight-system/v2
flutter run -d windows
```

**Connection:**
- Backend auto-detects COM port (or set `GCS_SERIAL=COM4`)
- Frontend connects to `ws://localhost:8765`
- Wait for "Connected: sys=1, comp=1" message

### UI Overview

**Top Bar:**
- Connection status (green = connected)
- Flight mode indicator
- Battery voltage
- GPS status

**Map:**
- Vehicle position (indigo airplane icon)
- Waypoints (orange markers)
- Survey polygon (blue outline)
- Survey grid (green lines)

**Control Panel (Right Side):**
- ARM/DISARM button
- Flight mode selector
- Mission toggle
- Survey toggle
- Upload/Start/Clear buttons

---

## Flight Modes

### Mode Descriptions

**STABILIZE**
- Manual flight with self-leveling
- Default mode on startup
- Safe for beginners

**GUIDED**
- Computer-controlled flight
- Required for GOTO commands
- Used for single waypoint navigation

**AUTO**
- Mission execution mode
- Follows uploaded waypoints
- Required for survey missions

**LOITER**
- Hold position
- GPS-stabilized hover
- Good for testing

**RTL (Return to Launch)**
- Automatic return home
- Climbs to RTL altitude
- Lands at launch point

**LAND**
- Immediate landing at current position

### Changing Modes

**Via UI:**
1. Select mode from dropdown
2. Click mode name to activate
3. Wait for confirmation in status bar

**Safety Rules:**
- Cannot ARM in AUTO mode
- Must ARM in STABILIZE or GUIDED first
- RTL available from any mode

---

## Manual Mission Planning

### Creating a Mission

1. Click **Mission** toggle (disables Survey mode)
2. Click map to add waypoints (orange markers)
3. Waypoints numbered in order
4. Click **Upload** to send to vehicle

**Default Waypoint Settings:**
- Altitude: 20m AGL
- Speed: Vehicle default
- Acceptance radius: 2m

### Executing a Mission

1. Upload waypoints
2. System auto-inserts TAKEOFF command
3. ARM vehicle (must be in GUIDED or STABILIZE)
4. Click **Start** to begin mission
5. Vehicle switches to AUTO mode
6. Watch progress in UI and Mission Planner

### Manual GOTO

1. Set mode to GUIDED
2. ARM vehicle
3. Click map location (not in Mission/Survey mode)
4. Vehicle flies to clicked position at 20m altitude

---

## Survey Mode

### Quick Start

1. Click **Survey** button (blue)
2. Click map to define polygon (min 3 points)
3. Click **Generate Grid**
4. Click **Upload**
5. ARM → **Start** mission

### Survey Configuration

Edit `lib/main.dart` lines 90-95:

```dart
double surveyAltitude = 50.0;        // meters AGL
double surveySpeed = 5.0;            // m/s
double surveyFrontOverlap = 75.0;    // percent
double surveySideOverlap = 75.0;     // percent
double surveyGridAngle = 0.0;        // degrees (0=N-S, 90=E-W)
```

### Camera Specifications

**Sentera Double 4K (Default):**
- Sensor: 6.3mm × 4.7mm (1/2.3" Sony IMX377)
- Resolution: 4000 × 3000 px (12.3 MP)
- HFOV: 60°
- Focal length: 5.4mm
- Trigger: MAVLink distance-based

**GSD Examples:**
- 30m altitude: ~1.05 cm/pixel
- 50m altitude: ~1.75 cm/pixel (default)
- 60m altitude: ~2.10 cm/pixel

### Overlap Recommendations

**Front Overlap (Direction of Flight):**
- Minimum: 60-70% (fast coverage)
- **Recommended: 75%** (balanced)
- High detail: 85-90% (slow, expensive)

**Side Overlap (Between Transects):**
- Minimum: 50-60% (fast coverage)
- **Recommended: 75%** (balanced)
- High detail: 80-85% (slow, expensive)

### Altitude Selection

**General Mapping:** 50-60m
- GSD: 1.75 cm/px
- Good balance of detail and coverage

**Crop Inspection:** 30-40m
- GSD: 1.05 cm/px
- High detail for plant health

**Large Area Survey:** 80-100m
- GSD: 2.80 cm/px
- Fast coverage, lower detail

**Legal Limit:** 122m (400 ft) AGL

### Grid Angle

**0° (Default):** North-South flight lines
- Good for rectangular fields
- Follows typical field orientation

**90°:** East-West flight lines
- Alternative for different shapes
- Consider wind direction

**Custom Angle:**
- Align with long axis of field
- Minimize turnarounds
- Optimize for wind (headwind on long legs)

### Survey Statistics

After generation, check backend logs:

```
INFO:GCS:✓ Survey generated: 45 waypoints
INFO:GCS:  Photos: 120
INFO:GCS:  Distance: 850.5m
INFO:GCS:  Flight time: 2.8 min
INFO:GCS:  Coverage: 2.3 acres
INFO:GCS:  GSD: 1.75 cm/px
```

**Understanding Stats:**
- **Photos:** Estimated images (distance / trigger_distance)
- **Distance:** Survey grid only (excludes climb/RTL)
- **Flight Time:** Grid only (add 2-3 min for full mission)
- **GSD:** Ground resolution in cm/pixel

### Example Workflows

**Small Field (50m × 50m):**
- Altitude: 40m
- 4 polygon points
- ~8 transects, ~35 photos
- ~1.5 minutes flight time
- Perfect for orthomosaic

**Large Field (200m × 100m):**
- Altitude: 60m
- 4-6 polygon points
- ~18 transects, ~180 photos
- ~5 minutes flight time
- Good for crop analysis

**Irregular Shape:**
- Use 8+ polygon points
- Fit boundary carefully
- System handles complex intersections
- Optimizes coverage automatically

---

## SITL Testing

### What is SITL?

Software-In-The-Loop simulation:
- Test missions without drone
- Safe environment
- ArduCopter simulator
- Full MAVLink protocol

### 5-Minute SITL Setup

**1. Start Mission Planner Simulator:**
1. Open Mission Planner
2. Click **Simulation** tab
3. Select **Multirotor** → **QuadCopter**
4. Click **Start Simulation**
5. Wait for "Ardupilot on TCP" message

**2. Start SKEYE:**
```bash
# Terminal 1
start_gcs_sitl.bat

# Terminal 2
cd src\flight-system\v2
flutter run -d windows
```

**3. Test Survey:**
1. Enable Survey mode
2. Draw 4-point polygon
3. Generate grid
4. Upload mission
5. Watch in Mission Planner!

### SITL Testing Checklist

**Basic Connectivity:**
- [ ] SITL starts without errors
- [ ] GCS shows "Connected: sys=1, comp=1"
- [ ] Flutter UI displays telemetry
- [ ] GPS shows "3D Fix"
- [ ] No timeout errors

**Flight Controls:**
- [ ] Mode changes work
- [ ] ARM/DISARM works
- [ ] GOTO command works (GUIDED mode)
- [ ] Speed commands work

**Survey Planning:**
- [ ] Can draw polygon
- [ ] Grid generates correctly
- [ ] Transects display on map
- [ ] Upload succeeds
- [ ] Mission runs in AUTO mode

### Switching Back to Hardware

```bash
# Stop SITL
# Close Mission Planner simulator

# Start hardware mode
start_gcs_hardware.bat
```

---

## Troubleshooting

### Connection Issues

**"No heartbeat received"**
- Check USB cable connected
- Check Pixhawk powered on
- Check correct COM port (Device Manager)
- Try: `set GCS_SERIAL=COM4` (your port)

**"Connection refused"**
- Check backend running: `netstat -an | findstr 8765`
- Kill old process: `taskkill /F /PID <pid>`
- Restart backend

**"Cannot find serial port"**
- Auto-detection failed
- Set manually: `set GCS_SERIAL=COM4`
- Check Windows Device Manager

### UI Issues

**No telemetry updating**
- Check backend connected to vehicle
- Check WebSocket connection (should see green indicator)
- Refresh Flutter app

**Map not loading**
- Check internet connection (map tiles)
- Map tiles load on demand
- Zoom/pan to trigger tile load

**Waypoints not appearing**
- Check Mission/Survey mode enabled
- Upload mission first
- Check logs for errors

### Flight Issues

**Cannot ARM**
- Check GPS lock (need 3D fix)
- Check battery voltage (min 10.5V for 3S)
- Check pre-arm checks in Mission Planner
- Not in AUTO mode (ARM in GUIDED/STABILIZE)

**Mission won't start**
- Must ARM first
- Upload mission first
- Check vehicle in AUTO mode
- Check TAKEOFF command exists

**Survey grid has gaps**
- Overlap too low (increase to 75%)
- Altitude too high (decrease altitude)
- Check camera specs correct

**Too many waypoints**
- Altitude too low (increase altitude)
- Area too large (split into multiple surveys)
- Overlap too high (decrease slightly)

### Survey Generation Issues

**"Survey requires at least 3 polygon points"**
- Need minimum 3 points
- Click map to add more points

**Grid doesn't cover polygon**
- Bug fixed (see survey_planner.py updates)
- Regenerate grid
- Check grid angle setting

**Camera not triggering**
- Check TELEM2 connection to camera
- Verify camera MAVLink config
- Check CAM_TRIGG_DIST in mission (item #1)
- Check camera trigger parameter in Mission Planner

### SITL Issues

**"Port 5760 already in use"**
- Close Mission Planner SITL
- Restart simulator

**No GPS fix in SITL**
- Wait 10-20 seconds after SITL starts
- GPS initializes slowly

**SITL freezes**
- Restart Mission Planner
- Restart SITL simulator

---

## Best Practices

### Pre-Flight

1. Check weather (wind < 15 mph)
2. Check battery charge (> 80%)
3. Check GPS lock (wait for 3D fix)
4. Test ARM/DISARM on ground
5. Verify mission in Mission Planner
6. Check camera connection
7. Do range check (walk away with RC)

### Survey Mission

1. Use SITL to test mission first
2. Start with higher altitude (safer)
3. Monitor battery during flight
4. Watch for RTL on low battery
5. Keep visual line of sight
6. Have RC controller ready for manual control

### After Flight

1. Download photos from camera
2. Check photo count vs estimate
3. Review mission logs
4. Note any issues for next flight
5. Charge batteries

---

## Advanced Features

### Custom Connection

```bash
# Serial
set GCS_SERIAL=COM4
set GCS_BAUD=57600

# TCP
set GCS_SERIAL=tcp:192.168.1.100:5760

# UDP
set GCS_SERIAL=udp:192.168.1.100:14550
```

### WebSocket Configuration

```bash
set GCS_WS_HOST=0.0.0.0  # Listen on all interfaces
set GCS_WS_PORT=8765     # Custom port
```

### Adding Custom Cameras

Edit `src/flight-system/v2/run_gcs.py` line 503:

```python
camera = CameraSpec(
    name="Your Camera",
    sensor_width_mm=13.2,      # Sensor width
    sensor_height_mm=8.8,       # Sensor height
    image_width_px=5472,        # Image width
    image_height_px=3648,       # Image height
    focal_length_mm=8.8,        # Focal length
    min_trigger_interval_s=2.0  # Min time between photos
)
```

---

## Quick Reference

### Keyboard Shortcuts

None currently implemented (future feature)

### UI Controls

**Mission Mode:**
- Click map → Add waypoint
- Upload → Send to vehicle
- Start → Begin mission (ARM + AUTO)
- Clear → Delete all waypoints

**Survey Mode:**
- Click map → Add polygon point
- Generate → Create survey grid
- Upload → Send to vehicle
- Start → Begin mission (ARM + AUTO)
- Clear → Delete polygon and grid

### Flight Mode Quick Reference

| Mode | Purpose | When to Use |
|------|---------|-------------|
| STABILIZE | Self-leveling manual | Default, safe |
| GUIDED | Computer control | GOTO commands |
| AUTO | Mission execution | Survey missions |
| LOITER | Hold position | Testing, pause |
| RTL | Return home | Emergency, end flight |
| LAND | Land now | Emergency landing |

---

**Last Updated:** November 19, 2025
