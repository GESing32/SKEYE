# SKEYE Ground Control Station

Professional drone ground control station with advanced survey planning capabilities.

**Version:** 2.0
**Status:** Production Ready

---

## Quick Start

### Run SKEYE GCS

**SITL Testing (Simulation):**
```bash
start_gcs_sitl.bat
```

**Real Hardware:**
```bash
start_gcs_hardware.bat
```

### Manual Start

```bash
# Backend
python src/flight-system/v2/run_gcs.py

# Frontend (new terminal)
cd src/flight-system/v2
flutter run -d windows
```

---

## What is SKEYE?

SKEYE is a lightweight, professional ground control station designed for autonomous drone operations with a focus on aerial survey missions.

**Key Features:**
- Real-time MAVLink telemetry and control
- QGC-style survey mission planning
- Interactive polygon-based survey areas
- Automatic camera trigger calculations
- WebSocket-based Flutter UI
- Support for Sentera Double 4K camera
- SITL simulation support

**Hardware:**
- Flight Controller: Pixhawk 6x
- Camera: Sentera Double 4K (MAVLink triggered)
- Connection: USB serial (57600 baud)

---

## Documentation

### Core Guides

- **[System Guide](SYSTEM_GUIDE.md)** - Architecture, data flow, and system design
- **[User Guide](USER_GUIDE.md)** - Operating the GCS, flight modes, survey planning
- **[Developer Guide](DEVELOPER_GUIDE.md)** - Development, testing, and extending

### Quick References

**Connection Strings:**
- Hardware: `COM4` (Windows) or `/dev/ttyUSB0` (Linux)
- SITL TCP: `tcp:127.0.0.1:5760`
- SITL UDP: `udp:127.0.0.1:14550`

**Environment Variables:**
- `GCS_SERIAL` - Connection string (default: auto-detect)
- `GCS_BAUD` - Baud rate (default: 57600)
- `GCS_WS_PORT` - WebSocket port (default: 8765)

---

## Project Structure

```
SKEYE/
├── docs/                           # Documentation (this folder)
│   ├── README.md                   # This file
│   ├── SYSTEM_GUIDE.md             # Architecture and design
│   ├── USER_GUIDE.md               # Operations guide
│   └── DEVELOPER_GUIDE.md          # Development guide
│
├── src/flight-system/v2/           # Core system
│   ├── gcs_core.py                 # MAVLink communication
│   ├── geometry_utils.py           # Geodetic calculations
│   ├── survey_planner.py           # Survey mission generator
│   ├── run_gcs.py                  # WebSocket GCS server
│   └── lib/                        # Flutter frontend
│
├── test/                           # Test suite
│   ├── unit/                       # Unit tests
│   └── integration/                # Integration tests
│
├── start_gcs_sitl.bat              # SITL launcher
└── start_gcs_hardware.bat          # Hardware launcher
```

---

## 5-Minute SITL Test

### Start SITL Simulator

1. Open Mission Planner
2. Click **Simulation** tab
3. Select **Multirotor** → **QuadCopter**
4. Click **Start Simulation**

### Start SKEYE

```bash
# Terminal 1: Backend
start_gcs_sitl.bat

# Terminal 2: Frontend
cd src\flight-system\v2
flutter run -d windows
```

### Test Survey Mode

1. Click **Survey** button
2. Click map 4 times to define area
3. Click **Generate Grid**
4. Click **Upload**
5. Watch mission in Mission Planner!

Full guide: [User Guide - SITL Testing](USER_GUIDE.md#sitl-testing)

---

## System Requirements

**Python Backend:**
- Python 3.9+
- pymavlink >= 2.4.0
- websockets >= 10.0
- geographiclib (optional, for geodesic calculations)

**Flutter Frontend:**
- Flutter 3.0+
- Windows/Linux/macOS

**Optional:**
- Mission Planner (SITL testing)
- MAVProxy (advanced testing)

---

## Support

**Documentation:**
- System architecture → [SYSTEM_GUIDE.md](SYSTEM_GUIDE.md)
- How to operate → [USER_GUIDE.md](USER_GUIDE.md)
- How to develop → [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)

**External Resources:**
- [ArduPilot Documentation](https://ardupilot.org/)
- [MAVLink Protocol](https://mavlink.io/)
- [Flutter Documentation](https://docs.flutter.dev/)

---

## License

University of Kentucky ECE Department

---

**Last Updated:** November 19, 2025
