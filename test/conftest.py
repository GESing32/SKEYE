"""
Shared pytest fixtures for SKEYE Flight System tests.

This module provides common fixtures used across unit and integration tests.
Fixtures are automatically discovered by pytest and can be used by any test
by including them as function parameters.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add v2 directory to path for imports
v2_path = Path(__file__).parent.parent / "src" / "flight-system" / "v2"
sys.path.insert(0, str(v2_path))

# Runtime imports (after path setup)
from geometry_utils import LatLon  # type: ignore
from survey_planner import CameraSpec, SurveyConfig  # type: ignore


# ============================================================================
# Geographic Location Fixtures
# ============================================================================

@pytest.fixture
def uk_campus():
    """University of Kentucky campus location (Lexington, KY).

    Returns:
        LatLon: Coordinates (38.0336°N, 84.5037°W)
    """
    return LatLon(38.0336, -84.5037)


@pytest.fixture
def rupp_arena():
    """Rupp Arena location (Lexington, KY).

    Returns:
        LatLon: Coordinates (38.0489°N, 84.4958°W)
    """
    return LatLon(38.0489, -84.4958)


@pytest.fixture
def test_square_polygon():
    """Standard test polygon (approximately 100m × 100m square).

    Returns:
        list[LatLon]: Four-corner polygon coordinates
    """
    return [
        LatLon(38.0, -84.5),
        LatLon(38.001, -84.5),
        LatLon(38.001, -84.499),
        LatLon(38.0, -84.499),
    ]


@pytest.fixture
def test_triangle_polygon():
    """Standard test triangle polygon.

    Returns:
        list[LatLon]: Three-corner polygon coordinates
    """
    return [
        LatLon(38.0, -84.5),
        LatLon(38.01, -84.5),
        LatLon(38.005, -84.49),
    ]


# ============================================================================
# Camera Specification Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def camera_wide():
    """Sentera Double 4K Wide camera specification (8mm lens).

    Scope: session (created once per test session for efficiency)

    Returns:
        CameraSpec: Wide angle camera specs
    """
    return CameraSpec.sentera_double_4k_wide()


@pytest.fixture(scope="session")
def camera_narrow():
    """Sentera Double 4K Narrow camera specification (25mm lens).

    Scope: session (created once per test session for efficiency)

    Returns:
        CameraSpec: Narrow angle camera specs
    """
    return CameraSpec.sentera_double_4k_narrow()


@pytest.fixture(params=[
    CameraSpec.sentera_double_4k_wide(),
    CameraSpec.sentera_double_4k_narrow(),
])
def any_camera(request):
    """Parametrized fixture providing all camera types.

    Tests using this fixture will run once for each camera type.

    Returns:
        CameraSpec: Each available camera specification
    """
    return request.param


# ============================================================================
# Survey Configuration Fixtures
# ============================================================================

@pytest.fixture
def default_survey_config():
    """Default survey configuration with standard parameters.

    Returns:
        SurveyConfig: 50m altitude, 5m/s speed, 75% overlap
    """
    return SurveyConfig(
        altitude_m=50.0,
        speed_m_s=5.0,
        front_overlap_pct=75.0,
        side_overlap_pct=75.0,
        grid_angle_deg=0.0
    )


@pytest.fixture
def high_overlap_survey_config():
    """High overlap survey configuration (90% overlap).

    Returns:
        SurveyConfig: High overlap configuration
    """
    return SurveyConfig(
        altitude_m=50.0,
        speed_m_s=5.0,
        front_overlap_pct=90.0,
        side_overlap_pct=90.0,
        grid_angle_deg=0.0
    )


@pytest.fixture
def low_overlap_survey_config():
    """Low overlap survey configuration (60% overlap).

    Returns:
        SurveyConfig: Low overlap configuration
    """
    return SurveyConfig(
        altitude_m=50.0,
        speed_m_s=5.0,
        front_overlap_pct=60.0,
        side_overlap_pct=60.0,
        grid_angle_deg=0.0
    )


# ============================================================================
# MAVLink Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_mavlink_connection(mocker):
    """Mock MAVLink connection for testing GCS core functionality.

    Provides a mocked mavutil.mavlink_connection that returns a MagicMock.

    Args:
        mocker: pytest-mock's mocker fixture

    Returns:
        MagicMock: Mocked MAVLink connection object
    """
    mock_mav = MagicMock()
    mocker.patch('gcs_core.mavutil.mavlink_connection', return_value=mock_mav)
    return mock_mav


@pytest.fixture
def mock_time_now(mocker):
    """Mock time.time() for consistent timestamp testing.

    Args:
        mocker: pytest-mock's mocker fixture

    Returns:
        MagicMock: Mocked time function (default return: 100.0)
    """
    mock_now = mocker.patch('gcs_core.now_s', return_value=100.0)
    return mock_now


# ============================================================================
# Parametrized Test Data
# ============================================================================

# Common altitude test values (meters)
COMMON_ALTITUDES = [30, 50, 70, 90]

# Common overlap percentages
COMMON_OVERLAPS = [70, 75, 80, 85, 90]

# Cardinal direction test data (direction_name, bearing_degrees)
CARDINAL_DIRECTIONS = [
    ("north", 0.0),
    ("east", 90.0),
    ("south", 180.0),
    ("west", 270.0),
]
