# SKEYE Documentation

Complete documentation for the SKEYE Flight System - professional drone ground control station with survey planning capabilities.

## Quick Start

- **[SITL Quick Start](SITL_QUICKSTART.md)** - Get SITL testing working in 5 minutes on Windows
- **[Flight System v2 README](../src/flight-system/v2/README.md)** - Quick start for running SKEYE GCS

## Core Documentation

### User Guides

- **[Complete Documentation](DOCUMENTATION.md)** - Comprehensive user guide covering:
  - Hardware setup and wiring diagrams
  - Software configuration
  - Survey planning tutorial
  - Camera specifications
  - Troubleshooting guide
  - API reference

### Architecture & Design

- **[Architecture Overview](ARCHITECTURE.md)** - System design and technical details:
  - Component architecture (Python backend + Flutter frontend)
  - Data flow diagrams
  - Performance metrics
  - Code organization
  - Maintenance guide

### Testing

- **[SITL Testing Guide](SITL_TESTING_GUIDE.md)** - Complete Windows SITL testing guide:
  - Mission Planner simulator setup
  - MAVProxy configuration
  - Connection methods (TCP/UDP)
  - Testing workflows
  - Troubleshooting

- **[Testing Guide](TESTING_GUIDE.md)** - Test environment setup:
  - Virtual environment configuration
  - Running pytest and unittest
  - Common test issues
  - Coverage reporting

- **[Test Results](TEST_RESULTS.md)** - Current test coverage and results:
  - 59% Python code coverage
  - 379 total tests (unit + integration + widget)
  - Module-by-module breakdown

- **[System Integration Tests](SYSTEM_INTEGRATION_TESTS.md)** - Integration test specifications:
  - Communication flow analysis
  - Test suite definitions
  - Performance benchmarks

- **[Test Suite README](../test/README.md)** - Test organization and running tests

## Documentation by Topic

### Getting Started
1. Read [SITL Quick Start](SITL_QUICKSTART.md) for safe testing without hardware
2. Read [Flight System v2 README](../src/flight-system/v2/README.md) for basic setup
3. Read [Complete Documentation](DOCUMENTATION.md) for detailed hardware setup

### Development
1. Read [Architecture Overview](ARCHITECTURE.md) to understand system design
2. Read [Testing Guide](TESTING_GUIDE.md) to set up test environment
3. Read [System Integration Tests](SYSTEM_INTEGRATION_TESTS.md) for integration test specs

### Operations
1. Use [SITL Testing Guide](SITL_TESTING_GUIDE.md) for mission validation before flight
2. Use [Complete Documentation](DOCUMENTATION.md) for field operations
3. Refer to [Troubleshooting Section](DOCUMENTATION.md#troubleshooting) for issues

## Project Structure

```
SKEYE/
├── docs/                                  # All documentation (THIS FOLDER)
│   ├── README.md                          # This file - documentation index
│   ├── ARCHITECTURE.md                    # System architecture
│   ├── DOCUMENTATION.md                   # Complete user guide
│   ├── SITL_QUICKSTART.md                 # 5-minute SITL setup
│   ├── SITL_TESTING_GUIDE.md              # Complete SITL guide
│   ├── TESTING_GUIDE.md                   # Test environment setup
│   ├── TEST_RESULTS.md                    # Test coverage results
│   └── SYSTEM_INTEGRATION_TESTS.md        # Integration test specs
│
├── src/flight-system/v2/                  # Core SKEYE system
│   ├── README.md                          # Quick start guide
│   ├── gcs_core.py                        # MAVLink communication
│   ├── geometry_utils.py                  # Geodetic calculations
│   ├── survey_planner.py                  # Survey mission generator
│   ├── run_gcs.py                         # WebSocket GCS server
│   ├── run_gcs_sitl.py                    # SITL launcher
│   └── lib/                               # Flutter frontend
│
├── test/                                  # Test suite
│   ├── README.md                          # Test suite overview
│   ├── conftest.py                        # Pytest configuration
│   ├── unit/                              # Unit tests (Python + Dart)
│   ├── integration/                       # Integration tests
│   └── widget_test.dart                   # Flutter widget tests
│
├── start_gcs_sitl.bat                     # Windows launcher - SITL mode
├── start_gcs_hardware.bat                 # Windows launcher - Hardware mode
└── README.md                              # Project README
```

## Quick Reference

### Running SKEYE

**SITL Testing (Simulation):**
```bash
start_gcs_sitl.bat
```

**Real Hardware:**
```bash
start_gcs_hardware.bat
```

**Manual Start:**
```bash
# Backend
python src/flight-system/v2/run_gcs.py

# Frontend
cd src/flight-system/v2
flutter run -d windows
```

### Connection Configuration

**Environment Variables:**
- `GCS_SERIAL` - Connection string (e.g., COM4, tcp:127.0.0.1:5760, udp:127.0.0.1:14550)
- `GCS_BAUD` - Baud rate (default: 57600)
- `GCS_WS_HOST` - WebSocket host (default: 0.0.0.0)
- `GCS_WS_PORT` - WebSocket port (default: 8765)

**Common Connection Strings:**
- Serial: `COM4` (Windows), `/dev/ttyUSB0` (Linux)
- SITL TCP: `tcp:127.0.0.1:5760`
- SITL UDP: `udp:127.0.0.1:14550`

## Support & Resources

### External Documentation
- [ArduPilot Documentation](https://ardupilot.org/)
- [Mission Planner Guide](https://ardupilot.org/planner/)
- [MAVLink Protocol](https://mavlink.io/en/)
- [pymavlink Documentation](https://mavlink.io/en/mavgen_python/)
- [Flutter Documentation](https://docs.flutter.dev/)

### Project Information
- **Project**: SKEYE Flight System
- **Institution**: University of Kentucky ECE Department
- **Version**: 2.0.0
- **Last Updated**: October 20, 2025

---

**For questions or issues**, refer to the appropriate documentation section above or check the troubleshooting guides in each document.
