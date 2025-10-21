# SKEYE Flight System

Professional drone ground control station (GCS) with QGC-style survey planning for the Sentera Double 4K camera.

**University of Kentucky ECE Department Senior Design Project**

## Features

- **Survey Planning** - QGC-style polygon-based survey generation with automatic grid patterns
- **Real-Time Control** - WebSocket-based telemetry streaming and command/control
- **Camera Integration** - Sentera Double 4K camera control via MAVLink
- **SITL Testing** - Software-in-the-loop simulation support for safe testing
- **Platform** - Windows via Flutter

## Quick Start

### SITL Testing (Recommended First Step)

Test without real hardware using Mission Planner simulator:

```bash
# 1. Start Mission Planner SITL (GUI: Simulation → Multirotor → Start Simulation)

# 2. Start SKEYE GCS
start_gcs_sitl.bat

# 3. Start Flutter UI (in another terminal)
cd src/flight-system/v2
flutter run -d windows
```

**See [SITL Quick Start Guide](docs/SITL_QUICKSTART.md) for detailed instructions.**

### Real Hardware

```bash
# 1. Connect Pixhawk 6X via USB or telemetry radio

# 2. Start SKEYE GCS (auto-detects hardware)
start_gcs_hardware.bat

# 3. Start Flutter UI (in another terminal)
cd src/flight-system/v2
flutter run -d windows
```

## Documentation

**Complete documentation available in [`docs/`](docs/) folder:**

- **[Documentation Index](docs/README.md)** - All documentation organized by topic
- **[SITL Quick Start](docs/SITL_QUICKSTART.md)** - 5-minute SITL testing setup
- **[Complete User Guide](docs/DOCUMENTATION.md)** - Hardware setup, survey planning, troubleshooting
- **[Architecture Overview](docs/ARCHITECTURE.md)** - System design and technical details
- **[SITL Testing Guide](docs/SITL_TESTING_GUIDE.md)** - Comprehensive SITL testing on Windows
- **[Testing Guide](docs/TESTING_GUIDE.md)** - Running unit and integration tests
- **[Test Results](docs/TEST_RESULTS.md)** - Current test coverage (59%, 379 tests)

## Project Structure

```
SKEYE/
├── docs/                          # All documentation
│   ├── README.md                  # Documentation index
│   ├── SITL_QUICKSTART.md         # Quick SITL setup
│   ├── DOCUMENTATION.md           # Complete user guide
│   └── ...                        # Architecture, testing guides
│
├── src/flight-system/v2/          # Core GCS system
│   ├── gcs_core.py                # MAVLink communication
│   ├── geometry_utils.py          # Geodetic calculations
│   ├── survey_planner.py          # Survey mission generator
│   ├── run_gcs.py                 # WebSocket server
│   ├── run_gcs_sitl.py            # SITL launcher
│   └── lib/                       # Flutter frontend
│
├── test/                          # Test suite
│   ├── unit/                      # Unit tests (Python + Dart)
│   ├── integration/               # Integration tests
│   └── widget_test.dart           # Widget tests
│
├── start_gcs_sitl.bat             # SITL launcher (Windows)
└── start_gcs_hardware.bat         # Hardware launcher (Windows)
```

## System Requirements

### Hardware
- Pixhawk 6X flight controller
- Sentera Double 4K camera (Model 27060)
- SiK Telemetry Radio (915MHz) or USB connection
- Windows/macOS/Linux computer

### Software
- Python 3.9 or later
- Flutter 3.33 or later
- QGroundControle latest version
- Mission Planner (for SITL testing)

### Python Dependencies
```bash
pip install pymavlink websockets
```

### Flutter Dependencies
```bash
flutter pub get
```

## Development

### Running Tests

**Python tests:**
```bash
# Using pytest (recommended)
pytest test/unit/

# Using unittest
python -m unittest discover -s test/unit -p "test_*.py"
```

**Flutter tests:**
```bash
flutter test
```

**See [Testing Guide](docs/TESTING_GUIDE.md) for detailed test instructions.**

### Project Status

- **Version**: 2.0.0
- **Status**: Production Ready ✅
- **Test Coverage**: 59% (379 tests total)
- **Last Updated**: October 20, 2025

## Key Technologies

- **Backend**: Python 3.9+ with pymavlink
- **Frontend**: Flutter/Dart
- **Communication**: WebSocket (backend ↔ frontend), MAVLink (drone ↔ backend)
- **Flight Controller**: ArduPilot firmware on Pixhawk 6X
- **Camera**: Sentera Double 4K via MAVLink

## Support

- **Documentation**: See [`docs/`](docs/) folder
- **Issues**: Check troubleshooting sections in documentation
- **SITL Testing**: See [SITL guides](docs/SITL_QUICKSTART.md) for safe testing

## License

SKEYE - University of Kentucky ECE Department Senior Design Project

---

**Ready to get started?** Begin with [SITL Quick Start](docs/SITL_QUICKSTART.md) for safe testing, then move to [Complete Documentation](docs/DOCUMENTATION.md) for real hardware setup.
