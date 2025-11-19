# SKEYE Developer Guide

Development, testing, and extending SKEYE GCS.

---

## Table of Contents

1. [Development Setup](#development-setup)
2. [Running Tests](#running-tests)
3. [Code Structure](#code-structure)
4. [Extending SKEYE](#extending-skeye)
5. [Testing Strategy](#testing-strategy)
6. [Contributing](#contributing)

---

## Development Setup

### Prerequisites

**Python:**
- Python 3.9+
- pip package manager

**Flutter:**
- Flutter SDK 3.0+
- Windows/Linux/macOS

**Optional:**
- Mission Planner (SITL testing)
- MAVProxy (advanced testing)
- VS Code with Python/Flutter extensions

### Initial Setup

```bash
# Clone repository
git clone <repo-url>
cd SKEYE

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install Python dependencies
pip install -r requirements-test.txt
pip install pymavlink websockets geographiclib

# Install Flutter dependencies
cd src/flight-system/v2
flutter pub get
```

### IDE Configuration

**VS Code Python:**
1. Press `Ctrl+Shift+P`
2. "Python: Select Interpreter"
3. Choose `.venv\Scripts\python.exe`

**VS Code Flutter:**
1. Install Flutter extension
2. Press `Ctrl+Shift+P`
3. "Flutter: Select Device"
4. Choose "Windows (desktop)"

---

## Running Tests

### Python Unit Tests

**Quick Run:**
```bash
# Activate venv first
.venv\Scripts\activate

# Run all tests
pytest test/unit/ -v

# Run with coverage
pytest test/unit/ --cov=src/flight-system/v2 --cov-report=html

# Open coverage report
# Browser → htmlcov/index.html
```

**Specific Tests:**
```bash
# Single file
pytest test/unit/pytest_test_gcs_core.py -v

# Single class
pytest test/unit/pytest_test_gcs_core.py::TestErrorHandling -v

# Single test
pytest test/unit/pytest_test_gcs_core.py::TestErrorHandling::test_timeout -v
```

**Useful Options:**
```bash
-v              # Verbose output
-vv             # Very verbose
-x              # Stop on first failure
--lf            # Run last failed
-n auto         # Run in parallel (requires pytest-xdist)
--collect-only  # List tests without running
```

### Flutter Tests

```bash
cd src/flight-system/v2

# Run all tests
flutter test

# Run with coverage
flutter test --coverage

# Specific test file
flutter test test/widget_test.dart
```

### Test Coverage

**Current Status:**
- Python: 65% coverage (300+ tests)
- Key modules: 80%+ coverage
- Target: Maintain > 60%

**Generate Reports:**
```bash
# Python HTML report
pytest test/unit/ --cov=src/flight-system/v2 --cov-report=html

# Python terminal report with missing lines
pytest test/unit/ --cov=src/flight-system/v2 --cov-report=term-missing

# Flutter coverage
flutter test --coverage
genhtml coverage/lcov.info -o coverage/html  # Requires lcov
```

---

## Code Structure

### Python Backend

```
src/flight-system/v2/
├── gcs_core.py              # MAVLink communication
│   └── MavSerialCore        # Main MAVLink class
│
├── geometry_utils.py        # Geodetic calculations
│   ├── LatLon               # Geographic coordinates
│   ├── LocalCoord           # Local NE coordinates
│   ├── GeodeticUtils        # Distance/bearing calculations
│   └── PolygonUtils         # Polygon operations
│
├── survey_planner.py        # Survey mission generation
│   ├── CameraSpec           # Camera specifications
│   ├── SurveyConfig         # Survey parameters
│   └── SurveyPlanner        # Mission generator
│
└── run_gcs.py               # WebSocket server
    ├── WebSocketHub         # Message broadcasting
    └── handle_client()      # Command routing
```

### Flutter Frontend

```
lib/
├── main.dart                # Main app
│   ├── MyApp                # Root widget
│   └── CustomGCSSerial      # Main screen
│
├── constants/
│   └── app_constants.dart   # Configuration
│
└── models/
    ├── camera_config.dart   # Camera specs
    └── survey_config.dart   # Survey models
```

### Test Structure

```
test/
├── unit/                                  # Python unit tests
│   ├── pytest_test_gcs_core.py           # MAVLink tests
│   ├── pytest_test_geometry_utils.py     # Geodetic tests
│   ├── pytest_test_survey_planner.py     # Survey tests
│   └── pytest_test_websocket_handler.py  # WebSocket tests
│
├── integration/                           # Integration tests
│   ├── test_sitl_automated.py            # SITL automated tests
│   └── test_websocket_stress.py          # WebSocket stress tests
│
└── widget_test.dart                       # Flutter widget tests
```

---

## Extending SKEYE

### Adding a New Flight Mode

**Backend (gcs_core.py):**
```python
# In MavSerialCore class
def set_custom_mode(self, param1, param2):
    """Your custom mode."""
    msg = self.mav.command_long_encode(
        self.target_system,
        self.target_component,
        mavutil.mavlink.MAV_CMD_YOUR_COMMAND,
        0,  # confirmation
        param1, param2, 0, 0, 0, 0, 0
    )
    self.mav.send(msg)
```

**WebSocket Handler (run_gcs.py):**
```python
# In handle_client() function
elif command == "custom_mode":
    param1 = data.get('param1', 0)
    param2 = data.get('param2', 0)
    gcs.set_custom_mode(param1, param2)
    response = {
        "type": "ACK",
        "command": "custom_mode",
        "success": True
    }
```

**Frontend (main.dart):**
```dart
void sendCustomMode() async {
  final message = {
    'command': 'custom_mode',
    'param1': 100.0,
    'param2': 200.0,
  };
  channel.sink.add(json.encode(message));
}

// Add button to UI
ElevatedButton(
  onPressed: sendCustomMode,
  child: Text('Custom Mode'),
)
```

### Adding a New Camera

**survey_planner.py:**
```python
@staticmethod
def your_camera_name() -> 'CameraSpec':
    """Your camera description."""
    return CameraSpec(
        name="Your Camera Name",
        sensor_width_mm=13.2,      # 1" sensor example
        sensor_height_mm=8.8,
        image_width_px=5472,       # 20MP example
        image_height_px=3648,
        focal_length_mm=8.8,       # 24mm equiv example
        min_trigger_interval_s=2.0,
        hfov_deg=73.7             # Optional, for reference
    )
```

**run_gcs.py (line ~503):**
```python
# Change camera
camera = CameraSpec.your_camera_name()
```

### Adding a New Survey Parameter

**1. Backend Model (survey_planner.py):**
```python
@dataclass
class SurveyConfig:
    # Existing params...
    your_param: float = 10.0  # Add here
```

**2. Survey Generation (survey_planner.py):**
```python
def generate_transects_from_polygon(self, polygon, config):
    # Use config.your_param in calculations
    value = config.your_param * 2
```

**3. WebSocket Handler (run_gcs.py):**
```python
# In "generate_survey" handler
your_param = data.get('your_param', 10.0)

config = SurveyConfig(
    # Existing params...
    your_param=your_param
)
```

**4. Frontend UI (main.dart):**
```dart
double yourParam = 10.0;  // Add state variable

// Add slider
Slider(
  value: yourParam,
  min: 0,
  max: 100,
  onChanged: (value) {
    setState(() => yourParam = value);
  },
)

// Include in survey command
final message = {
  'command': 'generate_survey',
  'polygon': surveyPolygonPoints,
  'your_param': yourParam,
};
```

### Adding a New Telemetry Message

**1. Enable Relay (gcs_core.py):**
```python
RELAY_TYPES = [
    'HEARTBEAT',
    'GPS_RAW_INT',
    'YOUR_MESSAGE_TYPE',  # Add here
]
```

**2. Frontend Handler (main.dart):**
```dart
void _handleWebSocketMessage(dynamic message) {
  final data = json.decode(message);
  final type = data['type'];

  if (type == 'YOUR_MESSAGE_TYPE') {
    setState(() {
      // Update UI with message data
      yourValue = data['your_field'];
    });
  }
}
```

---

## Testing Strategy

### Test Levels

**1. Unit Tests (Python):**
- Test individual functions
- Mock MAVLink/serial/WebSocket
- Fast execution (< 1 second total)
- 300+ tests

**2. Integration Tests (Python):**
- Test component interaction
- SITL simulation
- WebSocket stress testing
- Slower (requires SITL)

**3. Widget Tests (Flutter):**
- Test UI components
- Mock WebSocket
- Fast execution

**4. SITL Testing:**
- End-to-end validation
- Real ArduCopter SITL
- Full mission simulation

### Writing Unit Tests

**Example Test (pytest):**
```python
import pytest
from src.flight_system.v2.geometry_utils import GeodeticUtils, LatLon

def test_geodesic_distance():
    """Test distance calculation."""
    p1 = LatLon(38.0336, -84.5037)
    p2 = LatLon(38.0346, -84.5027)

    dist = GeodeticUtils.geodesic_distance(p1, p2)

    assert 1000 < dist < 2000  # Expected ~1.5km
    assert isinstance(dist, float)

@pytest.mark.parametrize("alt,expected_gsd", [
    (30, 1.05),
    (50, 1.75),
    (60, 2.10),
])
def test_gsd_calculation(alt, expected_gsd):
    """Test GSD at different altitudes."""
    from survey_planner import SurveyPlanner, CameraSpec

    camera = CameraSpec.sentera_double_4k_default()
    planner = SurveyPlanner(camera)

    gsd = planner.calculate_gsd(alt)

    assert abs(gsd - expected_gsd) < 0.1  # Within 0.1 cm/px
```

### Mocking MAVLink

**Example:**
```python
def test_arm_command(mocker):
    """Test ARM command."""
    # Mock serial connection
    mock_connection = mocker.MagicMock()
    mocker.patch('pymavlink.mavutil.mavlink_connection',
                 return_value=mock_connection)

    # Create GCS instance
    gcs = MavSerialCore('COM4', 57600)

    # Call function
    gcs.arm()

    # Verify MAVLink command sent
    mock_connection.mav.command_long_send.assert_called_once()
```

### SITL Integration Testing

**Manual SITL Test:**
```bash
# Terminal 1: Start SITL
# Mission Planner → Simulation → Start

# Terminal 2: Start GCS
start_gcs_sitl.bat

# Terminal 3: Run integration tests
pytest test/integration/test_sitl_automated.py --sitl -v
```

**Automated SITL Test:**
```python
@pytest.mark.skipif(not SITL_AVAILABLE, reason="SITL not available")
def test_survey_upload_sitl():
    """Test survey upload to SITL."""
    # Connect to SITL
    gcs = MavSerialCore('tcp:127.0.0.1:5760', 57600)
    gcs.wait_heartbeat()

    # Generate survey
    polygon = [...]
    planner = SurveyPlanner(camera)
    items, stats = planner.generate_mission_items(polygon, config)

    # Upload mission
    gcs.mission_upload_begin(items)

    # Verify mission count
    assert gcs.waypoint_count() == len(items)
```

---

## Development Workflow

### Daily Workflow

```bash
# 1. Activate venv
.venv\Scripts\activate

# 2. Pull latest changes
git pull

# 3. Install any new dependencies
pip install -r requirements-test.txt

# 4. Make code changes
# ... edit files ...

# 5. Run tests
pytest test/unit/ -v

# 6. Check coverage
pytest test/unit/ --cov=src/flight-system/v2 --cov-report=term

# 7. Format code (optional)
black src/flight-system/v2/  # Python
dart format lib/             # Dart

# 8. Commit changes
git add .
git commit -m "Your message"

# 9. Before pushing - run full test suite
pytest test/unit/ test/integration/ -v
flutter test
```

### Pre-Commit Checklist

- [ ] All unit tests pass
- [ ] No decrease in code coverage
- [ ] Code follows style guide (PEP 8, Dart style)
- [ ] New features have tests
- [ ] Documentation updated
- [ ] SITL tested (if applicable)

### Debugging

**Python Backend:**
```python
# Add logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use print
print(f"DEBUG: value = {value}")

# Or use debugger
import pdb; pdb.set_trace()
```

**VS Code Debugging:**
1. Set breakpoint (F9)
2. Run → Start Debugging (F5)
3. Select "Python: Current File"

**Flutter Debugging:**
```bash
# Run with debug output
flutter run -d windows --verbose

# Or use VS Code
# Set breakpoint → F5
```

---

## Code Quality

### Style Guidelines

**Python (PEP 8):**
- 4 spaces indentation
- Max line length: 100 characters
- Use type hints
- Docstrings for all public functions

**Dart/Flutter:**
- 2 spaces indentation
- Follow Dart style guide
- Use `const` where possible

### Type Hints

**Always use type hints:**
```python
def calculate_distance(p1: LatLon, p2: LatLon) -> float:
    """Calculate distance between two points."""
    return GeodeticUtils.geodesic_distance(p1, p2)

def process_data(values: List[float]) -> Dict[str, Any]:
    """Process data and return statistics."""
    return {"mean": sum(values) / len(values)}
```

### Documentation

**Python Docstrings:**
```python
def generate_survey(polygon: List[LatLon], config: SurveyConfig) -> List[Dict]:
    """
    Generate survey mission from polygon.

    Args:
        polygon: List of polygon vertices (min 3 points)
        config: Survey configuration parameters

    Returns:
        List of MAVLink mission items

    Raises:
        ValueError: If polygon has < 3 points
    """
    pass
```

---

## Performance Optimization

### Profiling

**Python:**
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here
planner.generate_transects_from_polygon(polygon, config)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Top 10 functions
```

**Flutter:**
```bash
flutter run --profile
# Use DevTools profiler
```

### Common Optimizations

**Async I/O (already implemented):**
```python
# Non-blocking serial reads
async def telemetry_loop(gcs, hub):
    loop = asyncio.get_event_loop()
    while True:
        msg = await loop.run_in_executor(None, gcs.recv_match_cached)
        await hub.broadcast(msg)
```

**Minimize Computations:**
- Cache repeated calculations
- Use numpy for bulk operations (if needed)
- Avoid nested loops where possible

---

## Troubleshooting Development Issues

### Tests Fail After Git Pull

```bash
# Update dependencies
pip install -r requirements-test.txt

# Clear pytest cache
pytest --cache-clear

# Re-run tests
pytest test/unit/ -v
```

### Import Errors

```bash
# Check virtual environment active
which python  # Should show .venv path

# Reinstall packages
pip install --force-reinstall pymavlink websockets
```

### Coverage Report Missing

```bash
# Generate coverage
pytest test/unit/ --cov=src/flight-system/v2 --cov-report=html

# Check htmlcov/ folder created
ls htmlcov/

# Open in browser
start htmlcov/index.html  # Windows
open htmlcov/index.html   # Mac
```

---

## Quick Reference

### Common Commands

```bash
# Python tests
pytest test/unit/ -v
pytest test/unit/ --cov=src/flight-system/v2 --cov-report=html

# Flutter tests
flutter test
flutter test --coverage

# Run specific test
pytest test/unit/pytest_test_gcs_core.py::TestArming::test_arm_success -v

# SITL testing
start_gcs_sitl.bat

# Code formatting
black src/flight-system/v2/
dart format lib/
```

### File Locations

**Source Code:**
- `src/flight-system/v2/*.py` - Python backend
- `src/flight-system/v2/lib/*.dart` - Flutter frontend

**Tests:**
- `test/unit/pytest_test_*.py` - Python unit tests
- `test/integration/test_*.py` - Integration tests
- `test/widget_test.dart` - Flutter tests

**Docs:**
- `docs/README.md` - Main documentation
- `docs/SYSTEM_GUIDE.md` - Architecture
- `docs/USER_GUIDE.md` - User guide
- `docs/DEVELOPER_GUIDE.md` - This file

---

## Getting Help

**Documentation:**
- System architecture: [SYSTEM_GUIDE.md](SYSTEM_GUIDE.md)
- Operations: [USER_GUIDE.md](USER_GUIDE.md)
- Main README: [README.md](README.md)

**External Resources:**
- [pytest documentation](https://docs.pytest.org/)
- [pymavlink documentation](https://mavlink.io/en/mavgen_python/)
- [Flutter testing](https://docs.flutter.dev/testing)
- [ArduPilot SITL](https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html)

---

**Last Updated:** November 19, 2025
