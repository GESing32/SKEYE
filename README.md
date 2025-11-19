# SKEYE Flight System

Professional drone ground control station with advanced survey planning capabilities for agricultural application.

**University of Kentucky ECE Department**

---

## Features

- **Survey Planning** - QGC-style polygon-based survey generation with automatic grid patterns
- **Real-Time Control** - WebSocket-based telemetry and command/control
- **Camera Integration** - Sentera Double 4K camera with MAVLink triggering
- **SITL Testing** - Software-in-the-loop simulation for safe testing
- **Geodesic Accuracy** - Survey-grade coordinate calculations using Karney's algorithms

---

## Quick Start

### SITL Testing (Recommended)

Test safely without hardware:

```bash
# 1. Start Mission Planner SITL
#    Mission Planner → Simulation → Multirotor → Start Simulation

# 2. Start SKEYE Backend
start_gcs_sitl.bat

# 3. Start Flutter UI (new terminal)
cd src\flight-system\v2
flutter run -d windows
```

### Real Hardware

```bash
# 1. Connect Pixhawk 6x via USB

# 2. Start SKEYE Backend (auto-detects COM port)
start_gcs_hardware.bat

# 3. Start Flutter UI (new terminal)
cd src\flight-system\v2
flutter run -d windows
```

---

## Documentation

Complete guides in the [`docs/`](docs/) folder:

- **[README](docs/README.md)** - Documentation overview and quick start
- **[System Guide](docs/SYSTEM_GUIDE.md)** - Architecture, data flow, and design
- **[User Guide](docs/USER_GUIDE.md)** - Operations, flight modes, and survey planning
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Development, testing, and extending

---

## Project Structure

```
SKEYE/
├── docs/                          # Documentation (4 focused guides)
│   ├── README.md                  # Documentation overview
│   ├── SYSTEM_GUIDE.md            # Architecture & design
│   ├── USER_GUIDE.md              # Operations guide
│   └── DEVELOPER_GUIDE.md         # Development guide
│
├── src/flight-system/v2/          # Core system
│   ├── gcs_core.py                # MAVLink communication (400 lines)
│   ├── geometry_utils.py          # Geodetic calculations (525 lines)
│   ├── survey_planner.py          # Survey generator (830 lines)
│   ├── run_gcs.py                 # WebSocket server (220 lines)
│   └── lib/                       # Flutter frontend (~1,300 lines)
│
├── test/                          # Test suite
│   ├── unit/                      # Python unit tests (300+ tests)
│   ├── integration/               # Integration tests
│   └── widget_test.dart           # Flutter tests
│
├── start_gcs_sitl.bat             # SITL launcher
└── start_gcs_hardware.bat         # Hardware launcher
```

**Total:** ~3,275 lines of code (lean and focused)

---

## System Requirements

### Hardware
- Pixhawk 6x flight controller
- Sentera Double 4K camera (MAVLink trigger)
- USB cable or telemetry radio
- Computer 

### Software
- Python 3.9+
- Flutter 3.0+
- QGroundControl (latest version)
- Mission Planner (SITL testing)

### Dependencies

**Python:**
```bash
pip install pymavlink websockets geographiclib
```

**Flutter:**
```bash
cd src/flight-system/v2
flutter pub get
```

---

## Development

### Running Tests

**Python (pytest):**
```bash
# Activate virtual environment
.venv\Scripts\activate

# Run all tests
pytest test/unit/ -v

# With coverage
pytest test/unit/ --cov=src/flight-system/v2 --cov-report=html
```

**Flutter:**
```bash
flutter test
flutter test --coverage
```

See [Developer Guide](docs/DEVELOPER_GUIDE.md) for complete testing instructions.

### Test Coverage

- **Python:** 65% coverage (300+ tests)
- **Integration:** SITL automated testing
- **Widget:** Flutter UI tests

---

## Key Technologies

**Backend:**
- Python 3.9+ with pymavlink
- WebSocket server (async I/O)
- Geographiclib (geodesic calculations)

**Frontend:**
- Flutter/Dart
- flutter_map (OpenStreetMap)
- WebSocket client

**Communication:**
- WebSocket: Backend ↔ Frontend
- MAVLink: Backend ↔ Pixhawk
- Serial/TCP/UDP: Connection transport

**Flight Controller:**
- ArduPilot firmware
- Pixhawk 6x hardware

---

## System Status

- **Version:** 2.0
- **Status:** Production Ready ✅
- **Backend:** ~1,975 lines (Python)
- **Frontend:** ~1,300 lines (Flutter)
- **Test Coverage:** 65% (300+ tests)
- **Last Updated:** November 19, 2025

---

## Support

**Documentation:**
- [README](docs/README.md) - Getting started
- [System Guide](docs/SYSTEM_GUIDE.md) - Architecture
- [User Guide](docs/USER_GUIDE.md) - How to operate
- [Developer Guide](docs/DEVELOPER_GUIDE.md) - How to develop

**External Resources:**
- [ArduPilot Documentation](https://ardupilot.org/)
- [MAVLink Protocol](https://mavlink.io/)
- [Flutter Documentation](https://docs.flutter.dev/)

---

## License

University of Kentucky ECE Department

---

**Ready to start?**
1. Try [SITL testing](docs/README.md#5-minute-sitl-test) first (safe simulation)
2. Read [User Guide](docs/USER_GUIDE.md) for operations
3. See [Developer Guide](docs/DEVELOPER_GUIDE.md) for development
