# SKEYE Flight System v2

Professional drone ground control station with QGC-style survey planning for the Sentera Double 4K camera.

## Quick Start

```bash
# 1. Hardware Setup (2 minutes)
Connect Sentera Double 4K to Pixhawk 6x TELEM2 port

# 2. Configure Pixhawk (2 minutes)
# IMPORTANT: Sentera requires MAVLink 1 at 115200 baud
param set SERIAL2_PROTOCOL 1    # MAVLink 1 (NOT 2!)
param set SERIAL2_BAUD 115      # 115200 (NOT 57!)
param set CAM1_TYPE 1
param set SR2_EXTRA1 10
param set SR2_EXTRA3 2
param set SR2_POSITION 4
reboot

# 3. Run GCS
python run_gcs.py           # Backend server
flutter run -d windows      # UI application
```

## Features

✅ **QGC-Style Survey Planning**
- Polygon-based area definition
- Automatic grid generation with optimal entry points
- Camera overlap calculations (75% front, 65% side)
- Distance-based trigger commands

✅ **Sentera Double 4K Integration**
- 8mm wide lens (default) - Best for mapping
- 25mm narrow lens (optional) - Best for inspection
- MAVLink camera control via TELEM2
- GPS-tagged 4K imagery

✅ **Real-Time Control**
- WebSocket telemetry streaming
- Interactive mission planning
- Live mission statistics
- Vehicle state monitoring

## System Requirements

**Hardware:**
- Pixhawk 6x flight controller
- Sentera Double 4K camera (Model 27060)
- Computer with USB port

**Software:**
- Python 3.9+
- Flutter 3.33+
- ArduPilot firmware

## Project Structure

```
src/flight-system/v2/
├── gcs_core.py              # MAVLink communication
├── geometry_utils.py        # Geodetic calculations
├── survey_planner.py        # Survey mission generator
├── run_gcs.py              # WebSocket GCS server
├── lib/                    # Flutter application
│   ├── models/            # Data models
│   ├── widgets/           # UI components
│   ├── screens/           # Application screens
│   └── constants/         # Configuration
└── docs/
    └── DOCUMENTATION.md   # Complete guide
```

## Documentation

📖 **Complete Documentation:** See [../../docs/](../../docs/) folder

Key guides:
- **[Complete User Guide](../../docs/DOCUMENTATION.md)** - Hardware setup, survey planning, troubleshooting
- **[Architecture Overview](../../docs/ARCHITECTURE.md)** - System design and technical details
- **[SITL Testing](../../docs/SITL_QUICKSTART.md)** - Safe testing without hardware
- **[Testing Guide](../../docs/TESTING_GUIDE.md)** - Running tests and coverage

## Camera Specifications

**Sentera Double 4K (8mm Wide) - Default**
- Resolution: 3840 × 2160 (4K)
- Sensor: 6.3mm × 4.7mm (1/2.3")
- GSD @ 50m: 0.98 cm/pixel
- Footprint @ 50m: 39m × 29m
- Best for: General mapping, large areas

**Sentera Double 4K (25mm Narrow) - Optional**
- Resolution: 3840 × 2160 (4K)
- Sensor: 6.3mm × 4.7mm (1/2.3")
- GSD @ 50m: 0.51 cm/pixel
- Footprint @ 50m: 13m × 9m
- Best for: Inspection, detail work

## Example Mission

```python
from survey_planner import SurveyPlanner, CameraSpec

# Use Sentera camera
camera = CameraSpec.sentera_double_4k_wide()
planner = SurveyPlanner(camera)

# Generate survey
result = planner.generate_survey(
    polygon=[(14.5995, 120.9842), ...],
    altitude_rel=50.0,
    overlap_front=75.0,
    overlap_side=65.0,
)

# Upload to vehicle
core.mission_upload_begin(result["mission_items"])
```

## Development

```bash
# Install Python dependencies
pip install pymavlink websockets

# Install Flutter dependencies
flutter pub get

# Run tests
python -m pytest tests/
flutter test

# Start development
python run_gcs.py           # Terminal 1
flutter run -d chrome       # Terminal 2 (web dev)
```

## License

SKEYE - University of Kentucky ECE Department Senior Design Project

## Support

- **Documentation:** See [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)
- **Sentera Support:** https://support.sentera.com/
- **ArduPilot Docs:** https://ardupilot.org/

---

**Version:** 2.0.0
**Status:** Production Ready ✅
**Last Updated:** October 2, 2025
