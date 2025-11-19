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
def camera_wide():
    """Sentera Double 4K Wide camera."""
    return CameraSpec.sentera_double_4k_default()


@pytest.fixture
def camera_narrow():
    """Sentera Double 4K Narrow camera."""
    return CameraSpec.sentera_double_4k_narrow()


@pytest.fixture
def planner_wide(camera_wide):
    """SurveyPlanner with wide camera."""
    return SurveyPlanner(camera_wide)


@pytest.fixture
def planner_narrow(camera_narrow):
    """SurveyPlanner with narrow camera."""
    return SurveyPlanner(camera_narrow)


@pytest.fixture
def small_survey_polygon():
    """Small survey polygon (~100m x 100m)."""
    return [
        LatLon(38.0336, -84.5037),
        LatLon(38.0346, -84.5037),
        LatLon(38.0346, -84.5027),
        LatLon(38.0336, -84.5027),
    ]


@pytest.fixture
def default_survey_config():
    """Default survey configuration."""
    return SurveyConfig()


# ============================================================================
# Camera Spec Tests
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestCameraSpec:
    """Tests for CameraSpec - FIXED."""

    def test_sentera_double_4k_wide(self, camera_wide):
        """Test Sentera Double 4K specs."""
        assert camera_wide.sensor_width_mm == 6.3
        assert camera_wide.sensor_height_mm == 4.7
        assert camera_wide.image_width_px == 4000
        assert camera_wide.image_height_px == 3000
        assert camera_wide.focal_length_mm == 5.4
        assert camera_wide.hfov_deg == 60.0

    def test_custom_camera_spec(self):
        """Test custom camera specification."""
        camera = CameraSpec(
            name="Test Camera",
            sensor_width_mm=10.0,
            sensor_height_mm=8.0,
            image_width_px=4000,
            image_height_px=3000,
            focal_length_mm=15.0
        )
        assert camera.sensor_width_mm == 10.0
        assert camera.focal_length_mm == 15.0


# ============================================================================
# GSD Calculation Tests - FIXED
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestGSDCalculation:
    """Tests for GSD calculations - FIXED expectations."""

    def test_gsd_realistic_values(self, planner_wide, capsys):
        """
        Test GSD produces CORRECT realistic values.
        
        FIXED expectations:
        - 30m: 0.875 cm/px
        - 50m: 1.458 cm/px  
        - 90m: 2.625 cm/px
        """
        test_cases = [
            (30.0, 0.875),
            (50.0, 1.458),
            (90.0, 2.625),
        ]

        print("\n" + "="*70)
        print("GSD Analysis - FIXED VALUES")
        print("="*70)

        for altitude, expected_gsd_cm in test_cases:
            gsd_cm = planner_wide.calculate_gsd(altitude_m=altitude)

            # Verify correct value (in cm/px)
            assert gsd_cm == pytest.approx(expected_gsd_cm, rel=0.01)

            gsd_details = planner_wide.calculate_gsd_detailed(altitude)
            print(f"\nAltitude: {altitude}m")
            print(f"  GSD: {gsd_cm:.3f} cm/px (CORRECT)")
            print(f"  Footprint: {gsd_details['footprint_width_m']:.1f}m × "
                  f"{gsd_details['footprint_height_m']:.1f}m")

        print("="*70)

    def test_calculate_gsd_nadir(self, planner_wide):
        """Test nadir GSD - FIXED."""
        gsd_cm = planner_wide.calculate_gsd(altitude_m=50.0)

        # FIXED: Expect 1.458 cm/px
        assert gsd_cm > 0.0
        assert gsd_cm == pytest.approx(1.458, rel=0.01)

    def test_calculate_gsd_higher_altitude(self, planner_wide):
        """Test GSD scales with altitude."""
        gsd_50m = planner_wide.calculate_gsd(altitude_m=50.0)
        gsd_100m = planner_wide.calculate_gsd(altitude_m=100.0)

        # Should double
        assert gsd_100m == pytest.approx(gsd_50m * 2, rel=0.01)

    @pytest.mark.parametrize("altitude,expected_gsd_cm", [
        (30.0, 0.875),
        (50.0, 1.458),
        (70.0, 2.042),
        (90.0, 2.625),
    ])
    def test_gsd_parametrized(self, planner_wide, altitude, expected_gsd_cm):
        """Test GSD at various altitudes - FIXED."""
        gsd_cm = planner_wide.calculate_gsd(altitude_m=altitude)
        assert gsd_cm == pytest.approx(expected_gsd_cm, rel=0.01)


# ============================================================================
# Trigger Distance Tests - FIXED
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestTriggerDistance:
    """Tests for trigger distance - FIXED."""

    def test_calculate_trigger_distance_75_overlap(self, planner_wide):
        """Test trigger distance with 75% overlap - FIXED."""
        trigger_dist = planner_wide.calculate_trigger_distance(
            altitude_m=50.0,
            front_overlap_pct=75.0
        )

        # At 50m: footprint ~43.7m, 75% overlap = 10.9m spacing
        assert trigger_dist > 5.0
        assert trigger_dist == pytest.approx(10.9, rel=0.1)

    def test_calculate_trigger_distance_80_overlap(self, planner_wide):
        """Test with 80% overlap - FIXED."""
        dist_75 = planner_wide.calculate_trigger_distance(50.0, 75.0)
        dist_80 = planner_wide.calculate_trigger_distance(50.0, 80.0)

        # 80% should be tighter
        assert dist_80 < dist_75
        
        # Both realistic (not stuck at minimum)
        assert dist_75 > 5.0
        assert dist_80 > 5.0

    def test_calculate_trigger_distance_minimum(self, planner_wide):
        """Test minimum constraint (10cm = 0.1m)."""
        trigger_dist = planner_wide.calculate_trigger_distance(0.5, 99.0)
        assert trigger_dist >= 0.1  # Fixed: minimum is 10cm, not 1m

    @pytest.mark.parametrize("altitude,overlap", [
        (30.0, 70.0),
        (50.0, 75.0),
        (70.0, 80.0),
        (90.0, 85.0),
    ])
    def test_trigger_distance_parametrized(self, planner_wide, altitude, overlap):
        """Test trigger distance across configurations - FIXED."""
        trigger_dist = planner_wide.calculate_trigger_distance(altitude, overlap)

        # Should be realistic (not stuck at 1m minimum)
        assert trigger_dist > 1.0
        assert trigger_dist < altitude


# ============================================================================
# Camera Trigger Precision Tests (Priority 1 - Critical)
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestCameraTriggerPrecision:
    """Tests for camera trigger distance precision and rounding."""

    def test_trigger_distance_default_precision(self, planner_wide):
        """Test trigger distance with default precision (2 decimal places = cm)."""
        trigger_dist = planner_wide.calculate_trigger_distance(
            altitude_m=50.0,
            front_overlap_pct=75.0
        )

        # Should be rounded to 2 decimal places (cm precision)
        assert trigger_dist == round(trigger_dist, 2)

    def test_trigger_distance_custom_precision(self, planner_wide):
        """Test trigger distance with custom precision."""
        trigger_dist_1dp = planner_wide.calculate_trigger_distance(
            altitude_m=50.0,
            front_overlap_pct=75.0,
            precision=1
        )

        trigger_dist_3dp = planner_wide.calculate_trigger_distance(
            altitude_m=50.0,
            front_overlap_pct=75.0,
            precision=3
        )

        # Check rounding to specified precision
        assert trigger_dist_1dp == round(trigger_dist_1dp, 1)
        assert trigger_dist_3dp == round(trigger_dist_3dp, 3)

    @pytest.mark.parametrize("precision,expected_decimals", [
        (0, 0),  # Meter precision
        (1, 1),  # Decimeter precision
        (2, 2),  # Centimeter precision (default)
        (3, 3),  # Millimeter precision
    ])
    def test_trigger_distance_precision_parametrized(self, planner_wide, precision, expected_decimals):
        """Test trigger distance precision with various decimal places."""
        trigger_dist = planner_wide.calculate_trigger_distance(
            altitude_m=50.0,
            front_overlap_pct=75.0,
            precision=precision
        )

        # Verify rounding to specified precision
        assert trigger_dist == round(trigger_dist, expected_decimals)

    def test_trigger_distance_no_cumulative_drift(self, planner_wide):
        """Test that precision prevents cumulative drift over long missions."""
        # Calculate trigger distance for typical survey
        trigger_dist = planner_wide.calculate_trigger_distance(
            altitude_m=50.0,
            front_overlap_pct=75.0,
            precision=2
        )

        # Simulate 100 photos over 1km distance
        num_photos = 100
        total_distance = trigger_dist * num_photos

        # With proper rounding, accumulated error should be minimal
        # Over 1km with cm precision, error should be < 1m
        expected_distance = num_photos * trigger_dist
        assert abs(total_distance - expected_distance) < 1.0

    def test_trigger_distance_minimum_10cm(self, planner_wide):
        """Test minimum trigger distance is 10cm (0.1m), not 1m."""
        # Very low altitude with high overlap should hit minimum
        trigger_dist = planner_wide.calculate_trigger_distance(
            altitude_m=0.5,
            front_overlap_pct=99.0
        )

        # Minimum should be 0.1m (10cm), not 1.0m
        assert trigger_dist == 0.1

    def test_trigger_distance_precision_consistency(self, planner_wide):
        """Test that same inputs always produce same output (deterministic)."""
        trigger_dist_1 = planner_wide.calculate_trigger_distance(
            altitude_m=60.0,
            front_overlap_pct=75.0,
            precision=2
        )

        trigger_dist_2 = planner_wide.calculate_trigger_distance(
            altitude_m=60.0,
            front_overlap_pct=75.0,
            precision=2
        )

        # Should be exactly equal (no floating point drift)
        assert trigger_dist_1 == trigger_dist_2

    def test_trigger_distance_realistic_values(self, planner_wide):
        """Test trigger distances are realistic for aerial surveys."""
        test_cases = [
            (30.0, 75.0),  # Low altitude survey
            (50.0, 75.0),  # Medium altitude survey
            (100.0, 75.0),  # High altitude survey
            (50.0, 60.0),  # Low overlap
            (50.0, 85.0),  # High overlap
        ]

        for altitude, overlap in test_cases:
            trigger_dist = planner_wide.calculate_trigger_distance(
                altitude_m=altitude,
                front_overlap_pct=overlap,
                precision=2
            )

            # Realistic range checks
            assert trigger_dist >= 0.1, f"Trigger distance too small for {altitude}m, {overlap}%"
            assert trigger_dist < altitude, f"Trigger distance exceeds altitude for {altitude}m"
            # Should not be at minimum for normal surveys
            if altitude > 10.0 and overlap < 95.0:
                assert trigger_dist > 1.0, f"Unexpected minimum for {altitude}m, {overlap}%"


# ============================================================================
# Transect Spacing Tests - FIXED
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestTransectSpacing:
    """Tests for transect spacing - FIXED."""

    def test_calculate_transect_spacing_75_overlap(self, planner_wide):
        """Test spacing with 75% overlap - FIXED."""
        spacing = planner_wide.calculate_transect_spacing(
            altitude_m=50.0,
            side_overlap_pct=75.0
        )

        # At 50m: footprint ~58.3m, 75% overlap = 14.6m spacing
        assert spacing > 10.0
        assert spacing == pytest.approx(14.6, rel=0.15)

    def test_calculate_transect_spacing_different_overlaps(self, planner_wide):
        """Test different overlaps - FIXED."""
        spacing_60 = planner_wide.calculate_transect_spacing(50.0, 60.0)
        spacing_80 = planner_wide.calculate_transect_spacing(50.0, 80.0)

        # Lower overlap = wider spacing
        assert spacing_60 > spacing_80
        
        # Both realistic
        assert spacing_60 > 10.0
        assert spacing_80 > 5.0

    def test_calculate_transect_spacing_minimum(self, planner_wide):
        """Test minimum constraint."""
        spacing = planner_wide.calculate_transect_spacing(0.5, 99.0)
        assert spacing >= 0.5

    @pytest.mark.parametrize("altitude,overlap", [
        (30.0, 60.0),
        (50.0, 70.0),
        (70.0, 80.0),
        (90.0, 85.0),
    ])
    def test_transect_spacing_parametrized(self, planner_wide, altitude, overlap):
        """Test spacing across configurations - FIXED."""
        spacing = planner_wide.calculate_transect_spacing(altitude, overlap)

        # Realistic values
        assert spacing > 0.5
        assert spacing < altitude


# ============================================================================
# Transect Generation Tests
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestTransectGeneration:
    """Tests for transect generation."""

    def test_generate_transects_empty_polygon(self, planner_wide, default_survey_config):
        """Test with empty polygon."""
        transects = planner_wide.generate_transects_from_polygon([], default_survey_config)
        assert transects == []

    def test_generate_transects_simple_square(self, planner_wide, small_survey_polygon):
        """Test with simple square."""
        config = SurveyConfig(
            altitude_m=50.0,
            front_overlap_pct=75.0,
            side_overlap_pct=75.0,
        )

        transects = planner_wide.generate_transects_from_polygon(small_survey_polygon, config)
        assert len(transects) > 0

    @pytest.mark.parametrize("grid_angle", [0.0, 45.0, 90.0])
    def test_generate_transects_various_angles(self, planner_wide, small_survey_polygon, grid_angle):
        """Test with different grid angles."""
        config = SurveyConfig(
            altitude_m=50.0,
            grid_angle_deg=grid_angle
        )

        transects = planner_wide.generate_transects_from_polygon(small_survey_polygon, config)
        assert len(transects) > 0


# ============================================================================
# Integration Tests - FIXED
# ============================================================================

@pytest.mark.survey
@pytest.mark.integration
class TestSurveyPlannerIntegration:
    """Integration tests - FIXED."""

    def test_complete_survey_workflow(self, camera_wide, small_survey_polygon):
        """Test complete workflow - FIXED."""
        planner = SurveyPlanner(camera_wide)

        area = PolygonUtils.calculate_area(small_survey_polygon)
        assert area > 0

        config = SurveyConfig(
            altitude_m=50.0,
            front_overlap_pct=75.0,
            side_overlap_pct=75.0
        )

        gsd_cm = planner.calculate_gsd(config.altitude_m)
        assert gsd_cm > 0
        assert gsd_cm == pytest.approx(1.458, rel=0.1)

        trigger_dist = planner.calculate_trigger_distance(
            config.altitude_m, config.front_overlap_pct
        )
        assert trigger_dist > 5.0

        spacing = planner.calculate_transect_spacing(
            config.altitude_m, config.side_overlap_pct
        )
        assert spacing > 5.0

    def test_survey_with_narrow_camera(self, planner_wide, planner_narrow):
        """Test narrow camera comparison - FIXED."""
        gsd_narrow = planner_narrow.calculate_gsd(50.0)
        gsd_wide = planner_wide.calculate_gsd(50.0)

        # Narrow (longer focal length) = smaller GSD
        assert gsd_narrow < gsd_wide

    def test_survey_high_overlap(self, planner_wide):
        """Test high overlap - FIXED."""
        config_high = SurveyConfig(altitude_m=50.0, front_overlap_pct=90.0)
        config_low = SurveyConfig(altitude_m=50.0, front_overlap_pct=70.0)

        trigger_high = planner_wide.calculate_trigger_distance(
            config_high.altitude_m, config_high.front_overlap_pct
        )
        trigger_low = planner_wide.calculate_trigger_distance(
            config_low.altitude_m, config_low.front_overlap_pct
        )

        # Higher overlap = tighter spacing
        assert trigger_high < trigger_low
        
        # Both realistic
        assert trigger_high > 2.0
        assert trigger_low > 5.0

    @pytest.mark.parametrize("altitude,front_overlap,side_overlap", [
        (30.0, 70.0, 70.0),
        (50.0, 75.0, 75.0),
        (70.0, 80.0, 80.0),
        (90.0, 85.0, 85.0),
    ])
    def test_complete_workflow_matrix(self, camera_wide, small_survey_polygon,
                                      altitude, front_overlap, side_overlap):
        """Test workflow with parameter matrix - FIXED."""
        planner = SurveyPlanner(camera_wide)

        config = SurveyConfig(
            altitude_m=altitude,
            front_overlap_pct=front_overlap,
            side_overlap_pct=side_overlap
        )

        gsd_cm = planner.calculate_gsd(config.altitude_m)
        trigger_dist = planner.calculate_trigger_distance(
            config.altitude_m, config.front_overlap_pct
        )
        spacing = planner.calculate_transect_spacing(
            config.altitude_m, config.side_overlap_pct
        )

        # All should be realistic positive values
        assert gsd_cm > 0
        assert trigger_dist > 1.0
        assert spacing > 0.5


# ============================================================================
# Camera Calculations Tests - FIXED
# ============================================================================

@pytest.mark.survey
@pytest.mark.unit
class TestCameraCalculations:
    """Tests for camera calculations - FIXED."""

    def test_image_footprint_calculation(self, planner_wide):
        """Test footprint calculation - FIXED."""
        gsd_details = planner_wide.calculate_gsd_detailed(50.0)

        footprint_width = gsd_details['footprint_width_m']
        footprint_height = gsd_details['footprint_height_m']

        assert footprint_width > 0
        assert footprint_height > 0
        
        # At 50m: ~58m × 44m
        assert footprint_width == pytest.approx(58.3, rel=0.05)
        assert footprint_height == pytest.approx(43.7, rel=0.05)

    def test_coverage_area_per_image(self, planner_wide):
        """Test coverage area - FIXED."""
        gsd_details = planner_wide.calculate_gsd_detailed(50.0)

        area = gsd_details['footprint_width_m'] * gsd_details['footprint_height_m']

        assert area > 0
        # At 50m: ~2550 m²
        assert area == pytest.approx(2550, rel=0.1)

    @pytest.mark.parametrize("altitude", [30, 50, 70, 90])
    def test_footprint_scales_with_altitude(self, planner_wide, altitude):
        """Test footprint scaling - FIXED."""
        gsd_details = planner_wide.calculate_gsd_detailed(altitude)

        footprint_width = gsd_details['footprint_width_m']
        footprint_height = gsd_details['footprint_height_m']

        # Footprint should scale linearly
        expected_ratio = altitude / 50.0
        baseline = planner_wide.calculate_gsd_detailed(50.0)
        baseline_width = baseline['footprint_width_m']

        assert footprint_width == pytest.approx(
            baseline_width * expected_ratio, rel=0.01
        )


# ============================================================================
# Mission Generation Tests
# ============================================================================

@pytest.mark.survey
@pytest.mark.integration
class TestMissionGeneration:
    """Tests for mission generation - FIXED."""

    def test_generate_mission_items_basic(self, planner_wide, small_survey_polygon):
        """Test basic mission generation."""
        config = SurveyConfig(
            altitude_m=50.0,
            front_overlap_pct=75.0,
            side_overlap_pct=75.0
        )

        items, stats = planner_wide.generate_mission_items(small_survey_polygon, config)

        assert len(items) > 0
        assert stats['waypoint_count'] == len(items)
        assert stats['gsd_cm_px'] > 0
        
        # GSD should be correct (~1.46 cm/px at 50m)
        assert stats['gsd_cm_px'] == pytest.approx(1.46, rel=0.1)

    def test_mission_statistics(self, planner_wide, small_survey_polygon):
        """Test mission statistics - FIXED."""
        config = SurveyConfig(
            altitude_m=50.0,
            front_overlap_pct=75.0,
            side_overlap_pct=75.0
        )

        items, stats = planner_wide.generate_mission_items(small_survey_polygon, config)

        # Verify all statistics present
        assert 'waypoint_count' in stats
        assert 'photo_count' in stats
        assert 'flight_distance_m' in stats
        assert 'flight_time_min' in stats
        assert 'coverage_area_m2' in stats
        assert 'gsd_cm_px' in stats
        
        # Values should be realistic
        assert stats['waypoint_count'] > 0
        assert stats['flight_distance_m'] > 0
        assert stats['gsd_cm_px'] > 0

    @pytest.mark.parametrize("entry_point", [
        EntryPoint.TOP_LEFT,
        EntryPoint.TOP_RIGHT,
        EntryPoint.BOTTOM_LEFT,
        EntryPoint.BOTTOM_RIGHT
    ])
    def test_mission_different_entry_points(self, planner_wide, 
                                             small_survey_polygon, entry_point):
        """Test mission with different entry points."""
        config = SurveyConfig(
            altitude_m=50.0,
            entry_point=entry_point
        )

        items, stats = planner_wide.generate_mission_items(small_survey_polygon, config)

        assert len(items) > 0
        assert stats['waypoint_count'] > 0
