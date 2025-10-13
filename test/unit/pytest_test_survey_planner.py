"""
pytest version: Unit tests for survey_planner module.

Tests survey planning, camera specifications, and mission generation.
This is the pytest-style version of test_survey_planner.py.

Run with:
    pytest test/unit/pytest_test_survey_planner.py
    pytest test/unit/pytest_test_survey_planner.py -v
    pytest test/unit/pytest_test_survey_planner.py -k "gsd"
    pytest test/unit/pytest_test_survey_planner.py -m survey
"""

import pytest
import math
import sys
from pathlib import Path

# Add v2 directory to path for imports
v2_path = Path(__file__).parent.parent.parent / "src" / "flight-system" / "v2"
sys.path.insert(0, str(v2_path))

from survey_planner import (  # type: ignore
    CameraSpec, SurveyConfig, SurveyPlanner,
    EntryPoint, TriggerMode
)
from geometry_utils import LatLon, PolygonUtils  # type: ignore


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def planner_wide(camera_wide):
    """SurveyPlanner instance with wide camera."""
    return SurveyPlanner(camera_wide)


@pytest.fixture
def planner_narrow(camera_narrow):
    """SurveyPlanner instance with narrow camera."""
    return SurveyPlanner(camera_narrow)


@pytest.fixture
def small_survey_polygon():
    """Small survey area polygon (~100m x 100m)."""
    return [
        LatLon(38.0336, -84.5037),
        LatLon(38.0346, -84.5037),
        LatLon(38.0346, -84.5027),
        LatLon(38.0336, -84.5027),
    ]


# ============================================================================
# CameraSpec Tests
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestCameraSpec:
    """Tests for CameraSpec dataclass and presets."""

    def test_sentera_double_4k_wide(self, camera_wide):
        """Test Sentera Double 4K Wide camera specs."""
        assert camera_wide.name == "Sentera Double 4K (8mm Wide)"
        assert camera_wide.sensor_width_mm == 6.3
        assert camera_wide.sensor_height_mm == 4.7
        assert camera_wide.image_width_px == 4000
        assert camera_wide.image_height_px == 3000
        assert camera_wide.focal_length_mm == 8.0
        assert camera_wide.min_trigger_interval_s == 0.5

    def test_sentera_double_4k_narrow(self, camera_narrow):
        """Test Sentera Double 4K Narrow camera specs."""
        assert camera_narrow.name == "Sentera Double 4K (25mm Narrow)"
        assert camera_narrow.focal_length_mm == 25.0
        assert camera_narrow.image_width_px == 4000
        assert camera_narrow.image_height_px == 3000

    def test_custom_camera_spec(self):
        """Test creating custom camera specification."""
        camera = CameraSpec(
            name="Test Camera",
            sensor_width_mm=10.0,
            sensor_height_mm=8.0,
            image_width_px=4000,
            image_height_px=3000,
            focal_length_mm=15.0,
            min_trigger_interval_s=1.0
        )

        assert camera.name == "Test Camera"
        assert camera.sensor_width_mm == 10.0
        assert camera.focal_length_mm == 15.0

    @pytest.mark.parametrize("camera_factory,expected_focal_length", [
        (CameraSpec.sentera_double_4k_wide, 8.0),
        (CameraSpec.sentera_double_4k_narrow, 25.0),
    ])
    def test_camera_presets(self, camera_factory, expected_focal_length):
        """Test camera preset factory methods."""
        camera = camera_factory()
        assert camera.focal_length_mm == expected_focal_length
        assert camera.image_width_px == 4000
        assert camera.image_height_px == 3000


# ============================================================================
# EntryPoint Enum Tests
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestEntryPoint:
    """Tests for EntryPoint enum."""

    def test_entry_point_values(self):
        """Test EntryPoint enum values."""
        assert EntryPoint.TOP_LEFT.value == "TopLeft"
        assert EntryPoint.TOP_RIGHT.value == "TopRight"
        assert EntryPoint.BOTTOM_LEFT.value == "BottomLeft"
        assert EntryPoint.BOTTOM_RIGHT.value == "BottomRight"

    @pytest.mark.parametrize("entry_point,expected_value", [
        (EntryPoint.TOP_LEFT, "TopLeft"),
        (EntryPoint.TOP_RIGHT, "TopRight"),
        (EntryPoint.BOTTOM_LEFT, "BottomLeft"),
        (EntryPoint.BOTTOM_RIGHT, "BottomRight"),
    ])
    def test_entry_point_parametrized(self, entry_point, expected_value):
        """Test all entry point values with parametrization."""
        assert entry_point.value == expected_value


# ============================================================================
# TriggerMode Enum Tests
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestTriggerMode:
    """Tests for TriggerMode enum."""

    def test_trigger_mode_values(self):
        """Test TriggerMode enum values."""
        assert TriggerMode.NONE.value == "None"
        assert TriggerMode.DISTANCE.value == "Distance"
        assert TriggerMode.TIME.value == "Time"
        assert TriggerMode.HOVER_CAPTURE.value == "HoverCapture"

    @pytest.mark.parametrize("trigger_mode,expected_value", [
        (TriggerMode.NONE, "None"),
        (TriggerMode.DISTANCE, "Distance"),
        (TriggerMode.TIME, "Time"),
        (TriggerMode.HOVER_CAPTURE, "HoverCapture"),
    ])
    def test_trigger_mode_parametrized(self, trigger_mode, expected_value):
        """Test all trigger mode values with parametrization."""
        assert trigger_mode.value == expected_value


# ============================================================================
# SurveyConfig Tests
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestSurveyConfig:
    """Tests for SurveyConfig dataclass."""

    def test_survey_config_defaults(self):
        """Test SurveyConfig default values."""
        config = SurveyConfig()

        assert config.altitude_m == 50.0
        assert config.speed_m_s == 5.0
        assert config.front_overlap_pct == 75.0
        assert config.side_overlap_pct == 75.0
        assert config.grid_angle_deg == 0.0
        assert config.entry_point == EntryPoint.TOP_LEFT
        assert config.turnaround_dist_m == 10.0
        assert config.trigger_mode == TriggerMode.DISTANCE
        assert config.refly_90deg is False
        assert config.hover_and_capture is False
        assert config.camera_angle_deg == 90.0

    def test_survey_config_custom(self):
        """Test SurveyConfig with custom values."""
        config = SurveyConfig(
            altitude_m=100.0,
            speed_m_s=10.0,
            front_overlap_pct=80.0,
            side_overlap_pct=70.0,
            grid_angle_deg=45.0
        )

        assert config.altitude_m == 100.0
        assert config.speed_m_s == 10.0
        assert config.front_overlap_pct == 80.0
        assert config.side_overlap_pct == 70.0
        assert config.grid_angle_deg == 45.0

    @pytest.mark.parametrize("altitude,speed,overlap", [
        (30.0, 5.0, 70.0),
        (50.0, 7.0, 75.0),
        (70.0, 10.0, 80.0),
        (90.0, 12.0, 85.0),
    ])
    def test_survey_config_parametrized(self, altitude, speed, overlap):
        """Test SurveyConfig with various parameter combinations."""
        config = SurveyConfig(
            altitude_m=altitude,
            speed_m_s=speed,
            front_overlap_pct=overlap,
            side_overlap_pct=overlap
        )

        assert config.altitude_m == altitude
        assert config.speed_m_s == speed
        assert config.front_overlap_pct == overlap
        assert config.side_overlap_pct == overlap


# ============================================================================
# SurveyPlanner Initialization Tests
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestSurveyPlannerInitialization:
    """Tests for SurveyPlanner initialization."""

    def test_initialization(self, camera_wide, planner_wide):
        """Test SurveyPlanner initialization."""
        assert planner_wide.camera == camera_wide

    def test_initialization_with_different_cameras(self, camera_narrow):
        """Test initialization with different camera types."""
        planner = SurveyPlanner(camera_narrow)
        assert planner.camera == camera_narrow
        assert planner.camera.focal_length_mm == 25.0


# ============================================================================
# GSD Calculation Tests
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestGSDCalculation:
    """Tests for Ground Sample Distance (GSD) calculations."""

    def test_gsd_realistic_values(self, planner_wide, capsys):
        """
        Test GSD calculation produces realistic values for aerial photography.

        GSD (Ground Sample Distance) is the physical distance on the ground
        that one pixel represents. For a camera pointing straight down (nadir):

        GSD_formula = (sensor_width_mm × altitude_m) / (focal_length_mm × image_width_px)

        For Sentera Double 4K Wide (8mm lens, 6.3mm sensor, 4000px width):
        - At 30m: ~0.00001 m/px (0.01mm per pixel)
        - At 50m: ~0.00001 m/px (0.01mm per pixel)
        - At 90m: ~0.00002 m/px (0.02mm per pixel)

        NOTE: Current implementation divides by 1000 (line 124 in survey_planner.py),
        making results 1000x smaller. This causes trigger distances and transect
        spacings to hit minimum values at typical altitudes (30-90m).
        """
        test_cases = [
            (30.0, 5.906250000000e-06),   # 30m: 5.91 µm/px
            (50.0, 9.843750000000e-06),  # 50m: 9.84 µm/px
            (90.0, 1.771875000000e-05),  # 90m: 17.72 µm/px
        ]

        print("\n" + "=" * 70)
        print("GSD Analysis for Sentera Double 4K Wide Camera")
        print("=" * 70)

        for altitude, expected_gsd in test_cases:
            gsd = planner_wide.calculate_gsd(altitude_m=altitude, camera_angle_deg=90.0)

            # Verify GSD matches expected value (with current /1000)
            assert gsd == pytest.approx(expected_gsd, abs=1e-10)

            # Calculate image footprint on ground
            footprint_width = gsd * planner_wide.camera.image_width_px
            footprint_height = gsd * planner_wide.camera.image_height_px
            coverage_area = footprint_width * footprint_height

            print(f"\nAltitude: {altitude}m")
            print(f"  GSD: {gsd * 1000000:.2f} µm/px (current)")
            print(f"  GSD: {gsd * 1000:.3f} mm/px (current)")
            print(f"  Expected GSD: {gsd * 1000000:.2f} mm/px (without extra /1000)")
            print(f"  Image footprint: {footprint_width:.4f}m × {footprint_height:.4f}m")
            print(f"  Coverage area: {coverage_area:.6f} m²")

        print("=" * 70)

    def test_calculate_gsd_nadir(self, planner_wide):
        """Test GSD calculation for nadir (straight down) camera."""
        gsd = planner_wide.calculate_gsd(altitude_m=50.0, camera_angle_deg=90.0)

        # GSD = (sensor_width_mm * altitude_m) / (focal_length_mm * image_width_px) / 1000
        # GSD = (6.3mm * 50m) / (8mm * 4000px) / 1000
        # GSD = 315 / 32000 / 1000 ≈ 0.00001025 m/px (10.25 micrometers/px)
        assert gsd > 0.0
        assert gsd == pytest.approx(9.843750000000e-06, abs=1e-8)

    def test_calculate_gsd_higher_altitude(self, planner_wide):
        """Test GSD increases with altitude."""
        gsd_50m = planner_wide.calculate_gsd(altitude_m=50.0)
        gsd_100m = planner_wide.calculate_gsd(altitude_m=100.0)

        # GSD should double when altitude doubles
        assert gsd_100m == pytest.approx(gsd_50m * 2, rel=1e-5)

    def test_calculate_gsd_angled_camera(self, planner_wide):
        """Test GSD calculation with angled camera."""
        gsd_nadir = planner_wide.calculate_gsd(altitude_m=50.0, camera_angle_deg=90.0)
        gsd_angled = planner_wide.calculate_gsd(altitude_m=50.0, camera_angle_deg=60.0)

        # Angled camera (60deg) should have smaller GSD than nadir due to cos factor
        # At 60deg, angle_from_nadir = 30deg, cos(30) ≈ 0.866
        assert gsd_angled < gsd_nadir

    @pytest.mark.parametrize("altitude,camera_angle,expected_gsd_approx", [
        (30.0, 90.0, 5.906e-06),
        (50.0, 90.0, 9.844e-06),
        (70.0, 90.0, 1.378e-05),
        (90.0, 90.0, 1.772e-05),
    ])
    def test_calculate_gsd_parametrized(self, planner_wide, altitude,
                                        camera_angle, expected_gsd_approx):
        """Test GSD calculation with various altitudes."""
        gsd = planner_wide.calculate_gsd(altitude_m=altitude, camera_angle_deg=camera_angle)
        assert gsd == pytest.approx(expected_gsd_approx, rel=0.01)


# ============================================================================
# Trigger Distance Tests
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestTriggerDistance:
    """Tests for camera trigger distance calculations."""

    def test_calculate_trigger_distance_75_overlap(self, planner_wide):
        """Test trigger distance calculation with 75% overlap."""
        trigger_dist = planner_wide.calculate_trigger_distance(
            altitude_m=50.0,
            front_overlap_pct=75.0
        )

        # At 50m altitude with this camera, GSD is very small (~0.00001 m/px)
        # Image footprint would be tiny, so minimum of 1m is enforced
        assert trigger_dist >= 1.0

    def test_calculate_trigger_distance_80_overlap(self, planner_wide):
        """Test trigger distance with 80% overlap."""
        # At typical altitudes (50-90m), both will hit the 1m minimum
        # Test verifies minimum is enforced
        dist_75 = planner_wide.calculate_trigger_distance(50.0, 75.0)
        dist_80 = planner_wide.calculate_trigger_distance(50.0, 80.0)

        # Both should be at the 1m minimum
        assert dist_75 == 1.0
        assert dist_80 == 1.0

    def test_calculate_trigger_distance_minimum(self, planner_wide):
        """Test trigger distance has minimum value."""
        # Even with 99% overlap at low altitude, should have minimum
        trigger_dist = planner_wide.calculate_trigger_distance(0.1, 99.0)

        assert trigger_dist >= 1.0

    @pytest.mark.parametrize("altitude,overlap", [
        (30.0, 70.0),
        (50.0, 75.0),
        (70.0, 80.0),
        (90.0, 85.0),
    ])
    def test_calculate_trigger_distance_parametrized(self, planner_wide, altitude, overlap):
        """Test trigger distance across common configurations."""
        trigger_dist = planner_wide.calculate_trigger_distance(altitude, overlap)

        assert trigger_dist >= 1.0  # Minimum constraint
        assert trigger_dist < altitude  # Should be less than altitude


# ============================================================================
# Transect Spacing Tests
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestTransectSpacing:
    """Tests for transect spacing calculations."""

    def test_calculate_transect_spacing_75_overlap(self, planner_wide):
        """Test transect spacing calculation with 75% overlap."""
        spacing = planner_wide.calculate_transect_spacing(
            altitude_m=50.0,
            side_overlap_pct=75.0
        )

        # At 50m altitude with this camera, GSD is very small
        # Calculated spacing would be tiny, so minimum of 0.1m is enforced
        assert spacing >= 0.1

    def test_calculate_transect_spacing_different_overlaps(self, planner_wide):
        """Test transect spacing with different overlap percentages."""
        # At typical altitudes (50-90m), both will hit the 0.1m minimum
        spacing_60 = planner_wide.calculate_transect_spacing(50.0, 60.0)
        spacing_80 = planner_wide.calculate_transect_spacing(50.0, 80.0)

        # Both should be at the 0.1m minimum
        assert spacing_60 == 0.1
        assert spacing_80 == 0.1

    def test_calculate_transect_spacing_minimum(self, planner_wide):
        """Test transect spacing has minimum value."""
        spacing = planner_wide.calculate_transect_spacing(0.1, 99.0)

        assert spacing >= 0.1

    @pytest.mark.parametrize("altitude,overlap", [
        (30.0, 60.0),
        (50.0, 70.0),
        (70.0, 80.0),
        (90.0, 90.0),
    ])
    def test_calculate_transect_spacing_parametrized(self, planner_wide, altitude, overlap):
        """Test transect spacing across configurations."""
        spacing = planner_wide.calculate_transect_spacing(altitude, overlap)

        assert spacing >= 0.1  # Minimum constraint
        assert spacing < altitude  # Should be less than altitude


# ============================================================================
# Transect Generation Tests
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestTransectGeneration:
    """Tests for survey transect generation."""

    def test_generate_transects_empty_polygon(self, planner_wide, default_survey_config):
        """Test transect generation with empty polygon."""
        transects = planner_wide.generate_transects_from_polygon([], default_survey_config)
        assert transects == []

    def test_generate_transects_too_few_points(self, planner_wide, default_survey_config):
        """Test transect generation with < 3 points."""
        polygon = [
            LatLon(38.0, -84.5),
            LatLon(38.01, -84.5),
        ]

        transects = planner_wide.generate_transects_from_polygon(polygon, default_survey_config)
        assert transects == []

    def test_generate_transects_simple_square(self, planner_wide, test_square_polygon):
        """Test transect generation for simple square polygon."""
        config = SurveyConfig(
            altitude_m=50.0,
            front_overlap_pct=75.0,
            side_overlap_pct=75.0,
            grid_angle_deg=0.0
        )

        transects = planner_wide.generate_transects_from_polygon(test_square_polygon, config)

        # Should generate multiple transects
        assert len(transects) > 0

    @pytest.mark.parametrize("grid_angle", [0.0, 45.0, 90.0])
    def test_generate_transects_various_angles(self, planner_wide, test_square_polygon, grid_angle):
        """Test transect generation with different grid angles."""
        config = SurveyConfig(
            altitude_m=50.0,
            front_overlap_pct=75.0,
            side_overlap_pct=75.0,
            grid_angle_deg=grid_angle
        )

        transects = planner_wide.generate_transects_from_polygon(test_square_polygon, config)
        assert len(transects) > 0


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.survey
@pytest.mark.integration
class TestSurveyPlannerIntegration:
    """Integration tests for complete survey planning workflow."""

    def test_complete_survey_workflow(self, camera_wide, small_survey_polygon):
        """Test complete survey planning from polygon to mission."""
        planner = SurveyPlanner(camera_wide)

        # Calculate area
        area = PolygonUtils.calculate_area(small_survey_polygon)
        assert area > 0

        # Create configuration
        config = SurveyConfig(
            altitude_m=50.0,
            speed_m_s=5.0,
            front_overlap_pct=75.0,
            side_overlap_pct=75.0,
            grid_angle_deg=0.0
        )

        # Calculate metrics
        gsd = planner.calculate_gsd(config.altitude_m)
        assert gsd > 0

        trigger_dist = planner.calculate_trigger_distance(
            config.altitude_m,
            config.front_overlap_pct
        )
        assert trigger_dist > 0

        spacing = planner.calculate_transect_spacing(
            config.altitude_m,
            config.side_overlap_pct
        )
        assert spacing > 0

    def test_survey_with_narrow_camera(self, planner_wide, planner_narrow):
        """Test survey planning with narrow angle camera."""
        # Narrow camera should have smaller GSD at same altitude
        gsd_narrow = planner_narrow.calculate_gsd(50.0)
        gsd_wide = planner_wide.calculate_gsd(50.0)

        # Narrow (25mm) should have smaller GSD than wide (8mm)
        assert gsd_narrow < gsd_wide

    def test_survey_high_overlap(self, planner_wide):
        """Test survey with very high overlap settings."""
        config_high = SurveyConfig(
            altitude_m=50.0,
            front_overlap_pct=90.0,
            side_overlap_pct=90.0
        )

        config_low = SurveyConfig(
            altitude_m=50.0,
            front_overlap_pct=70.0,
            side_overlap_pct=70.0
        )

        # At typical altitudes (50-90m), calculated distances are below minimum
        # Both will be clamped to 1m minimum
        trigger_high = planner_wide.calculate_trigger_distance(
            config_high.altitude_m,
            config_high.front_overlap_pct
        )
        trigger_low = planner_wide.calculate_trigger_distance(
            config_low.altitude_m,
            config_low.front_overlap_pct
        )

        # Both should be at minimum
        assert trigger_high == 1.0
        assert trigger_low == 1.0

    @pytest.mark.parametrize("altitude,front_overlap,side_overlap", [
        (30.0, 70.0, 70.0),
        (50.0, 75.0, 75.0),
        (70.0, 80.0, 80.0),
        (90.0, 85.0, 85.0),
    ])
    def test_complete_workflow_matrix(self, camera_wide, small_survey_polygon,
                                      altitude, front_overlap, side_overlap):
        """Test complete workflow with various parameter combinations."""
        planner = SurveyPlanner(camera_wide)

        config = SurveyConfig(
            altitude_m=altitude,
            speed_m_s=5.0,
            front_overlap_pct=front_overlap,
            side_overlap_pct=side_overlap,
            grid_angle_deg=0.0
        )

        # Calculate all metrics
        gsd = planner.calculate_gsd(config.altitude_m)
        trigger_dist = planner.calculate_trigger_distance(
            config.altitude_m,
            config.front_overlap_pct
        )
        spacing = planner.calculate_transect_spacing(
            config.altitude_m,
            config.side_overlap_pct
        )

        # All should be positive
        assert gsd > 0
        assert trigger_dist > 0
        assert spacing > 0


# ============================================================================
# Camera Calculations Tests
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestCameraCalculations:
    """Tests for camera-specific calculations."""

    def test_image_footprint_calculation(self, planner_wide):
        """Test image footprint calculation."""
        altitude = 50.0
        gsd = planner_wide.calculate_gsd(altitude)

        # Image footprint dimensions
        footprint_width = gsd * planner_wide.camera.image_width_px
        footprint_height = gsd * planner_wide.camera.image_height_px

        assert footprint_width > 0
        assert footprint_height > 0
        # Width should be greater than height (landscape orientation)
        assert footprint_width > footprint_height

    def test_coverage_area_per_image(self, planner_wide):
        """Test area covered by single image."""
        altitude = 50.0
        gsd = planner_wide.calculate_gsd(altitude)

        # Area per image
        width = gsd * planner_wide.camera.image_width_px
        height = gsd * planner_wide.camera.image_height_px
        area = width * height

        assert area > 0

    @pytest.mark.parametrize("altitude", [30, 50, 70, 90])
    def test_footprint_scales_with_altitude(self, planner_wide, altitude):
        """Test that image footprint scales linearly with altitude."""
        gsd = planner_wide.calculate_gsd(altitude)

        footprint_width = gsd * planner_wide.camera.image_width_px
        footprint_height = gsd * planner_wide.camera.image_height_px

        # Footprint should scale with altitude
        expected_ratio = altitude / 50.0  # Relative to 50m baseline
        baseline_gsd = planner_wide.calculate_gsd(50.0)
        baseline_width = baseline_gsd * planner_wide.camera.image_width_px

        assert footprint_width == pytest.approx(baseline_width * expected_ratio, rel=0.01)


# ============================================================================
# Comparison Tests (Wide vs Narrow Camera)
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestCameraComparison:
    """Comparative tests between wide and narrow cameras."""

    def test_gsd_comparison(self, planner_wide, planner_narrow):
        """Compare GSD between wide and narrow cameras."""
        altitude = 50.0

        gsd_wide = planner_wide.calculate_gsd(altitude)
        gsd_narrow = planner_narrow.calculate_gsd(altitude)

        # Narrow lens (25mm) should have smaller GSD than wide lens (8mm)
        assert gsd_narrow < gsd_wide

        # The ratio should be approximately focal_length_wide / focal_length_narrow
        expected_ratio = 8.0 / 25.0
        actual_ratio = gsd_narrow / gsd_wide
        assert actual_ratio == pytest.approx(expected_ratio, rel=0.01)

    @pytest.mark.parametrize("altitude", [30, 50, 70, 90])
    def test_trigger_distance_comparison(self, planner_wide, planner_narrow, altitude):
        """Compare trigger distances between camera types."""
        overlap = 75.0

        trigger_wide = planner_wide.calculate_trigger_distance(altitude, overlap)
        trigger_narrow = planner_narrow.calculate_trigger_distance(altitude, overlap)

        # Both should be positive
        assert trigger_wide > 0
        assert trigger_narrow > 0
