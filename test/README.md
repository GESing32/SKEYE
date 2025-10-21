# SKEYE Flight System - Test Suite

Comprehensive test suite for the SKEYE flight system, including unit tests, widget tests, integration tests, and SITL testing for both Python backend and Flutter/Dart frontend.

## Overview

The test suite is organized into four main categories:

1. **Unit Tests** - Test individual components and functions in isolation
2. **Widget Tests** - Test Flutter UI components and interactions
3. **Integration Tests** - Test complete workflows and system integration
4. **SITL Tests** - Test with Software In The Loop simulation (see [SITL Testing](#sitl-testing))

## Directory Structure

```
test/
├── README.md                              # This file
├── conftest.py                            # Shared pytest fixtures
├── widget_test.dart                       # Flutter widget tests
├── unit/                                  # Unit tests
│   ├── telemetry_test.dart               # Dart telemetry unit tests
│   ├── test_geometry_utils.py            # Python geometry tests (unittest)
│   ├── test_gcs_core.py                  # Python GCS tests (unittest)
│   ├── test_survey_planner.py            # Python survey tests (unittest)
│   ├── pytest_test_geometry_utils.py     # Python geometry tests (pytest)
│   ├── pytest_test_gcs_core.py           # Python GCS tests (pytest)
│   └── pytest_test_survey_planner.py     # Python survey tests (pytest)
└── integration/                           # Integration tests
    └── gcs_integration_test.dart         # GCS workflow integration tests
```

## SITL Testing

### Quick Start SITL Testing

SKEYE supports **Software In The Loop (SITL)** testing for safe testing without real hardware.

**5-Minute Quick Start:**
```bash
# 1. Start Mission Planner simulator (GUI: Simulation → Start Simulation)
# 2. Start SKEYE GCS in SITL mode
start_gcs_sitl.bat

# 3. Start Flutter UI
cd src\flight-system\v2
flutter run -d windows
```

**For detailed SITL setup and troubleshooting:**
- Quick Start: [../docs/SITL_QUICKSTART.md](../docs/SITL_QUICKSTART.md)
- Complete Guide: [../docs/SITL_TESTING_GUIDE.md](../docs/SITL_TESTING_GUIDE.md)
- Testing Guide: [../docs/TESTING_GUIDE.md](../docs/TESTING_GUIDE.md)
- Test Results: [../docs/TEST_RESULTS.md](../docs/TEST_RESULTS.md)

### SITL Test Scenarios

#### Basic Connection Test
```bash
# Start Mission Planner SITL
# (Launch Mission Planner → Simulation → Multirotor → Start Simulation)

# Connect SKEYE (in command prompt)
set GCS_SERIAL=tcp:127.0.0.1:5760
python src\flight-system\v2\run_gcs.py

# Expected: "Connected: sys=1, comp=1, mode=STABILIZE"
```

#### Survey Planning Test with SITL
1. Start Mission Planner SITL simulator
2. Start SKEYE GCS backend
3. Start Flutter UI
4. Draw polygon on map
5. Generate survey mission
6. Upload to SITL
7. Arm and switch to AUTO mode
8. Verify mission execution in SITL (watch in Mission Planner map)

#### Automated SITL Test Script
```python
# test/sitl/test_sitl_connection.py (create this)
import pytest
from pymavlink import mavutil

def test_sitl_connection():
    """Test connection to SITL simulator."""
    conn = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
    msg = conn.wait_heartbeat(timeout=10)
    assert msg is not None, "No heartbeat from SITL"
    assert msg.get_type() == 'HEARTBEAT'
```

## Running Tests

### Python Tests (unittest - Legacy)

Run all Python unit tests from project root:
```bash
python run_python_tests.py
```

Or run with unittest directly:
```bash
python -m unittest discover -s test/unit -p "test_*.py" -v
```

Run individual test files:
```bash
cd test/unit
python test_geometry_utils.py
python test_gcs_core.py
python test_survey_planner.py
```

### Python Tests (pytest - Recommended)

**Installation:**
```bash
# Minimum required
pip install pytest pytest-cov pytest-mock

# Full test suite (recommended)
pip install -r requirements-test.txt
```

**Run all pytest tests:**
```bash
pytest                                    # All tests with pytest discovery
pytest test/unit/                         # All unit tests
pytest test/unit/pytest_test_*.py         # Only pytest-style tests
```

**Common pytest commands:**
```bash
# Verbose output with test details
pytest -v

# Run only fast unit tests
pytest -m unit

# Run all tests except slow ones
pytest -m "not slow"

# Run specific test category
pytest -m geometry                        # Geometry tests only
pytest -m mavlink                         # MAVLink tests only
pytest -m survey                          # Survey planning tests only

# Run tests matching pattern
pytest -k "haversine"                     # Tests with "haversine" in name
pytest -k "gsd or trigger"                # Multiple patterns

# Run specific file
pytest test/unit/pytest_test_geometry_utils.py

# Run specific test
pytest test/unit/pytest_test_geometry_utils.py::test_haversine_distance_known_points

# Run with coverage report
pytest --cov=src/flight-system/v2 --cov-report=html
pytest --cov=src/flight-system/v2 --cov-report=term-missing

# Run in parallel (faster, requires pytest-xdist)
pytest -n auto                            # Use all CPU cores
pytest -n 4                               # Use 4 workers

# Run last failed tests only
pytest --lf

# Stop on first failure
pytest -x

# Generate HTML report (requires pytest-html)
pytest --html=report.html --self-contained-html
```

**pytest Benefits:**
- 30-40% less boilerplate code
- Natural Python assertions (`assert` instead of `self.assertEqual`)
- Better error messages with detailed context
- Powerful parametrization for testing multiple scenarios
- Parallel test execution for faster runs
- Rich plugin ecosystem
- Backward compatible (can run unittest tests)

### Flutter/Dart Tests

Run all Flutter tests:
```bash
flutter test
```

Run specific test file:
```bash
flutter test test/widget_test.dart
flutter test test/unit/telemetry_test.dart
flutter test test/integration/gcs_integration_test.dart
```

Run with coverage:
```bash
flutter test --coverage
```

View coverage report (requires lcov):
```bash
genhtml coverage/lcov.info -o coverage/html
```

## Test Categories

### 1. Python Unit Tests

#### test_geometry_utils.py
Tests geodetic calculations and coordinate transformations:
- `TestLatLon` - LatLon dataclass functionality
- `TestLocalCoord` - Local coordinate system
- `TestGeodeticUtils` - Haversine distance, bearing, destination point calculations
- `TestPolygonUtils` - Polygon operations (area, centroid, rotation, intersections)

**Coverage:**
- Geodetic calculations (Haversine, bearing, destination point)
- Coordinate transformations (geographic ↔ local)
- Polygon operations (area, bounding box, rotation)
- Line segment intersections

#### test_gcs_core.py
Tests MAVLink communication and command generation:
- `TestMavSerialCore` - MAVLink connection and state management
- `TestRelayTypes` - Message type constants
- Command generation (arm/disarm, mode change, GOTO, RTL)
- Heartbeat processing
- Link status monitoring

**Coverage:**
- MAVLink message processing
- Command generation (arm, mode, GOTO, speed, camera)
- Connection state management
- Heartbeat timeout handling

#### test_survey_planner.py
Tests survey planning and mission generation:
- `TestCameraSpec` - Camera specifications and presets
- `TestSurveyConfig` - Survey configuration parameters
- `TestSurveyPlanner` - GSD calculation, trigger distance, transect spacing
- Mission generation from polygon areas

**Coverage:**
- GSD (Ground Sample Distance) calculations
- Camera trigger distance calculations
- Transect spacing for grid patterns
- Complete survey workflow

### 2. Flutter Widget Tests (widget_test.dart)

Tests the GCS UI components:
- App initialization and structure
- Button presence and state
- Telemetry display
- Mission mode controls
- Connection indicators
- Mode menu functionality

**Test Groups:**
- `GcsApp Widget Tests` - Core UI structure and components

**Coverage:** 15+ widget tests covering all major UI elements

### 3. Dart Unit Tests (unit/telemetry_test.dart)

Tests Dart business logic and data models:
- Telemetry data structure
- MAVLink message parsing
- Coordinate conversions
- Mission waypoint generation
- Data validation and edge cases

**Test Groups:**
- `Telemetry Class Tests` - Telemetry object state management
- `Message Parsing Logic Tests` - MAVLink data conversion
- `Mission Waypoint Generation Tests` - Mission item structure
- `Telemetry Data Validation Tests` - Range and validity checks
- `Edge Cases and Error Handling` - Boundary conditions

**Coverage:** 40+ unit tests

### 4. Integration Tests (integration/gcs_integration_test.dart)

Tests complete user workflows and system integration:
- Mission planning workflow
- Command generation and serialization
- State management
- Error handling
- Performance benchmarks

**Test Groups:**
- `GCS Integration Tests` - User interaction flows
- `WebSocket Message Parsing Tests` - Message structure validation
- `Command Generation Tests` - All command types
- `State Management Tests` - UI state persistence
- `Error Handling Tests` - Invalid input handling
- `Mission Planning Workflow Tests` - Complete mission workflows
- `Performance and Responsiveness Tests` - UI performance

**Coverage:** 30+ integration tests

## Test Coverage Goals

### Python Backend
- **Geometry Utils:** >95% coverage
- **GCS Core:** >80% coverage (mocking MAVLink)
- **Survey Planner:** >90% coverage

### Flutter/Dart Frontend
- **Widget Tests:** All major UI components
- **Unit Tests:** >90% coverage of business logic
- **Integration Tests:** All critical user workflows

## Writing New Tests

### Python Unit Tests (unittest - Legacy)

Follow the existing pattern:

```python
import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "flight-system" / "v2"))

from your_module import YourClass

class TestYourClass(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.instance = YourClass()

    def test_something(self):
        """Test a specific behavior."""
        result = self.instance.some_method()
        self.assertEqual(result, expected_value)

if __name__ == '__main__':
    unittest.main(verbosity=2)
```

### Python Unit Tests (pytest - Recommended for New Tests)

Pytest style is more concise and Pythonic:

```python
import pytest
import sys
from pathlib import Path

# Add src to path (or use pytest.ini pythonpath)
v2_path = Path(__file__).parent.parent.parent / "src" / "flight-system" / "v2"
sys.path.insert(0, str(v2_path))

from your_module import YourClass


# Fixtures (replaces setUp/tearDown)
@pytest.fixture
def instance():
    """Create YourClass instance for testing."""
    return YourClass()


# Simple test with fixture injection
def test_something(instance):
    """Test a specific behavior."""
    result = instance.some_method()
    assert result == expected_value


# Parametrized test (test multiple scenarios)
@pytest.mark.parametrize("input_val,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiple_scenarios(instance, input_val, expected):
    """Test with multiple input/output pairs."""
    result = instance.double(input_val)
    assert result == expected


# Using markers for categorization
@pytest.mark.unit
@pytest.mark.geometry
def test_coordinate_conversion(instance):
    """Test coordinate conversion (marked as unit and geometry test)."""
    result = instance.convert_coords(38.0, -84.5)
    assert result is not None
```

### Flutter Widget Tests

```dart
testWidgets('Description of what you are testing', (WidgetTester tester) async {
  // Build the widget
  await tester.pumpWidget(const YourWidget());
  await tester.pump();

  // Perform actions
  await tester.tap(find.text('Button'));
  await tester.pump();

  // Verify results
  expect(find.text('Expected Result'), findsOneWidget);
});
```

### Dart Unit Tests

```dart
test('Description of the test', () {
  // Arrange
  final instance = YourClass();

  // Act
  final result = instance.someMethod();

  // Assert
  expect(result, equals(expectedValue));
});
```

## Continuous Integration

Tests should be run:
- Before every commit
- In CI/CD pipeline
- Before merging pull requests

## Test Data

### Test Coordinates
- **UK Campus (Lexington, KY):** 38.0336°N, 84.5037°W
- **Test square area:** ~1km² around UK campus
- **Altitude:** Typically 50m for survey tests

### Camera Specifications
- **Sentera Double 4K Wide:** 8mm lens, 3840×2160
- **Sentera Double 4K Narrow:** 25mm lens, 3840×2160

## Troubleshooting

### Flutter Tests Fail to Find Widgets

Ensure you're using `pumpWidget` and `pump`:
```dart
await tester.pumpWidget(const MyApp());
await tester.pump();
```

### Mock MAVLink Connection Errors

Tests use mocked connections. Ensure `@patch` decorators are applied correctly:
```python
@patch('gcs_core.mavutil.mavlink_connection')
def test_something(self, mock_connection):
    # Your test code
```

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain >85% coverage
4. Update this README if adding new test categories

## unittest vs pytest Comparison

### Migration Strategy

1. **Phase 1 (Immediate):** Run existing unittest tests with pytest
   ```bash
   pytest test/unit/test_*.py
   ```

2. **Phase 2 (Optional):** Write new tests in pytest style
   - Use `pytest_test_*.py` naming for new tests
   - Leverage fixtures from [conftest.py](conftest.py)

3. **Phase 3 (Optional):** Gradually convert old tests
   - Keep both versions during transition
   - No rush - unittest tests work fine with pytest

### When to Use Each

**Use unittest when:**
- No external dependencies allowed
- Team prefers traditional xUnit style
- Simple testing needs only

**Use pytest when:**
- Starting new tests (recommended)
- Need parametrization
- Want better error messages
- Need parallel execution
- Want extensive plugin ecosystem

## Resources

### Python Testing
- [pytest Documentation](https://docs.pytest.org/)
- [pytest vs unittest Guide](https://docs.pytest.org/en/stable/how-to/unittest.html)
- [Python unittest Documentation](https://docs.python.org/3/library/unittest.html)
- [pytest Plugin List](https://docs.pytest.org/en/latest/reference/plugin_list.html)

### Flutter/Dart Testing
- [Flutter Testing Guide](https://docs.flutter.dev/testing)

### MAVLink
- [MAVLink Protocol](https://mavlink.io/en/)
- [PyMAVLink Documentation](https://mavlink.io/en/mavgen_python/)
