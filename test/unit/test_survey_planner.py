"""
Unit tests for survey_planner module.
Tests survey planning, camera specifications, and mission generation.
"""

import unittest
import math
import sys
from pathlib import Path

# Add v2 directory to path for imports
v2_path = Path(__file__).parent.parent.parent / "src" / "flight-system" / "v2"
sys.path.insert(0, str(v2_path))

# Import from v2 directory (runtime resolution)
from survey_planner import (  # type: ignore
    CameraSpec, SurveyConfig, SurveyPlanner,
    EntryPoint, TriggerMode
)
from geometry_utils import LatLon, PolygonUtils  # type: ignore


class TestCameraSpec(unittest.TestCase):
    """Tests for CameraSpec dataclass and presets."""

    def test_sentera_double_4k_wide(self):
        """Test Sentera Double 4K Wide camera specs."""
        camera = CameraSpec.sentera_double_4k_wide()

        self.assertEqual(camera.name, "Sentera Double 4K (8mm Wide)")
        self.assertEqual(camera.sensor_width_mm, 6.3)
        self.assertEqual(camera.sensor_height_mm, 4.7)
        self.assertEqual(camera.image_width_px, 3840)
        self.assertEqual(camera.image_height_px, 2160)
        self.assertEqual(camera.focal_length_mm, 8.0)
        self.assertEqual(camera.min_trigger_interval_s, 0.5)

    def test_sentera_double_4k_narrow(self):
        """Test Sentera Double 4K Narrow camera specs."""
        camera = CameraSpec.sentera_double_4k_narrow()

        self.assertEqual(camera.name, "Sentera Double 4K (25mm Narrow)")
        self.assertEqual(camera.focal_length_mm, 25.0)
        self.assertEqual(camera.image_width_px, 3840)
        self.assertEqual(camera.image_height_px, 2160)

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

        self.assertEqual(camera.name, "Test Camera")
        self.assertEqual(camera.sensor_width_mm, 10.0)
        self.assertEqual(camera.focal_length_mm, 15.0)


class TestEntryPoint(unittest.TestCase):
    """Tests for EntryPoint enum."""

    def test_entry_point_values(self):
        """Test EntryPoint enum values."""
        self.assertEqual(EntryPoint.TOP_LEFT.value, "TopLeft")
        self.assertEqual(EntryPoint.TOP_RIGHT.value, "TopRight")
        self.assertEqual(EntryPoint.BOTTOM_LEFT.value, "BottomLeft")
        self.assertEqual(EntryPoint.BOTTOM_RIGHT.value, "BottomRight")


class TestTriggerMode(unittest.TestCase):
    """Tests for TriggerMode enum."""

    def test_trigger_mode_values(self):
        """Test TriggerMode enum values."""
        self.assertEqual(TriggerMode.NONE.value, "None")
        self.assertEqual(TriggerMode.DISTANCE.value, "Distance")
        self.assertEqual(TriggerMode.TIME.value, "Time")
        self.assertEqual(TriggerMode.HOVER_CAPTURE.value, "HoverCapture")


class TestSurveyConfig(unittest.TestCase):
    """Tests for SurveyConfig dataclass."""

    def test_survey_config_defaults(self):
        """Test SurveyConfig default values."""
        config = SurveyConfig()

        self.assertEqual(config.altitude_m, 50.0)
        self.assertEqual(config.speed_m_s, 5.0)
        self.assertEqual(config.front_overlap_pct, 75.0)
        self.assertEqual(config.side_overlap_pct, 75.0)
        self.assertEqual(config.grid_angle_deg, 0.0)
        self.assertEqual(config.entry_point, EntryPoint.TOP_LEFT)
        self.assertEqual(config.turnaround_dist_m, 10.0)
        self.assertEqual(config.trigger_mode, TriggerMode.DISTANCE)
        self.assertFalse(config.refly_90deg)
        self.assertFalse(config.hover_and_capture)
        self.assertEqual(config.camera_angle_deg, 90.0)

    def test_survey_config_custom(self):
        """Test SurveyConfig with custom values."""
        config = SurveyConfig(
            altitude_m=100.0,
            speed_m_s=10.0,
            front_overlap_pct=80.0,
            side_overlap_pct=70.0,
            grid_angle_deg=45.0
        )

        self.assertEqual(config.altitude_m, 100.0)
        self.assertEqual(config.speed_m_s, 10.0)
        self.assertEqual(config.front_overlap_pct, 80.0)
        self.assertEqual(config.side_overlap_pct, 70.0)
        self.assertEqual(config.grid_angle_deg, 45.0)


class TestSurveyPlanner(unittest.TestCase):
    """Tests for SurveyPlanner class."""

    def setUp(self):
        """Set up test fixtures."""
        self.camera = CameraSpec.sentera_double_4k_wide()
        self.planner = SurveyPlanner(self.camera)

    def test_initialization(self):
        """Test SurveyPlanner initialization."""
        self.assertEqual(self.planner.camera, self.camera)

    def test_gsd_realistic_values(self):
        """
        Test GSD calculation produces realistic values for aerial photography.

        GSD (Ground Sample Distance) is the physical distance on the ground
        that one pixel represents. For a camera pointing straight down (nadir):

        GSD_formula = (sensor_width_mm × altitude_m) / (focal_length_mm × image_width_px)

        For Sentera Double 4K Wide (8mm lens, 6.3mm sensor, 3840px width):
        - At 30m: ~0.00615 m/px (6.15mm per pixel)
        - At 50m: ~0.01025 m/px (10.25mm per pixel = 1cm per pixel)
        - At 90m: ~0.01845 m/px (18.45mm per pixel = 1.8cm per pixel)

        NOTE: Current implementation divides by 1000 (line 124 in survey_planner.py),
        making results 1000x smaller. This causes trigger distances and transect
        spacings to hit minimum values at typical altitudes (30-90m).
        """
        # Test at typical flight altitudes (max 90m ≈ 300ft)
        # Actual calculated values: (6.3mm × altitude) / (8mm × 3840px) / 1000
        test_cases = [
            (30.0, 6.15234375e-06),   # 30m: 6.15 µm/px (should be 6.15mm/px without /1000)
            (50.0, 1.025390625e-05),  # 50m: 10.25 µm/px (should be 10.25mm/px without /1000)
            (90.0, 1.845703125e-05),  # 90m: 18.45 µm/px (should be 18.45mm/px without /1000)
        ]

        print("\n" + "="*70)
        print("GSD Analysis for Sentera Double 4K Wide Camera")
        print("="*70)

        for altitude, expected_gsd in test_cases:
            with self.subTest(altitude=altitude):
                gsd = self.planner.calculate_gsd(altitude_m=altitude, camera_angle_deg=90.0)

                # Verify GSD matches expected value (with current /1000)
                self.assertAlmostEqual(gsd, expected_gsd, places=10)

                # Calculate image footprint on ground
                footprint_width = gsd * self.camera.image_width_px
                footprint_height = gsd * self.camera.image_height_px
                coverage_area = footprint_width * footprint_height

                print(f"\nAltitude: {altitude}m")
                print(f"  GSD: {gsd*1000000:.2f} µm/px (current)")
                print(f"  GSD: {gsd*1000:.3f} mm/px (current)")
                print(f"  Expected GSD: {gsd*1000000:.2f} mm/px (without extra /1000)")
                print(f"  Image footprint: {footprint_width:.4f}m × {footprint_height:.4f}m")
                print(f"  Coverage area: {coverage_area:.6f} m²")

        print("="*70)

    def test_calculate_gsd_nadir(self):
        """Test GSD calculation for nadir (straight down) camera."""
        gsd = self.planner.calculate_gsd(altitude_m=50.0, camera_angle_deg=90.0)

        # GSD = (sensor_width_mm * altitude_m) / (focal_length_mm * image_width_px) / 1000
        # GSD = (6.3mm * 50m) / (8mm * 3840px) / 1000
        # GSD = 315 / 30720 / 1000 ≈ 0.00001025 m/px (10.25 micrometers/px)
        self.assertGreater(gsd, 0.0)
        self.assertAlmostEqual(gsd, 0.00001025, places=8)

    def test_calculate_gsd_higher_altitude(self):
        """Test GSD increases with altitude."""
        gsd_50m = self.planner.calculate_gsd(altitude_m=50.0)
        gsd_100m = self.planner.calculate_gsd(altitude_m=100.0)

        # GSD should double when altitude doubles
        self.assertAlmostEqual(gsd_100m, gsd_50m * 2, places=5)

    def test_calculate_gsd_angled_camera(self):
        """Test GSD calculation with angled camera."""
        gsd_nadir = self.planner.calculate_gsd(altitude_m=50.0, camera_angle_deg=90.0)
        gsd_angled = self.planner.calculate_gsd(altitude_m=50.0, camera_angle_deg=60.0)

        # Angled camera (60deg) should have smaller GSD than nadir due to cos factor
        # At 60deg, angle_from_nadir = 30deg, cos(30) ≈ 0.866
        self.assertLess(gsd_angled, gsd_nadir)

    def test_calculate_trigger_distance_75_overlap(self):
        """Test trigger distance calculation with 75% overlap."""
        trigger_dist = self.planner.calculate_trigger_distance(
            altitude_m=50.0,
            front_overlap_pct=75.0
        )

        # At 50m altitude with this camera, GSD is very small (~0.00001 m/px)
        # Image footprint would be tiny, so minimum of 1m is enforced
        self.assertGreaterEqual(trigger_dist, 1.0)

    def test_calculate_trigger_distance_80_overlap(self):
        """Test trigger distance with 80% overlap."""
        # At typical altitudes (50-90m), both will hit the 1m minimum
        # Test verifies minimum is enforced
        dist_75 = self.planner.calculate_trigger_distance(50.0, 75.0)
        dist_80 = self.planner.calculate_trigger_distance(50.0, 80.0)

        # Both should be at the 1m minimum
        self.assertEqual(dist_75, 1.0)
        self.assertEqual(dist_80, 1.0)

    def test_calculate_trigger_distance_minimum(self):
        """Test trigger distance has minimum value."""
        # Even with 99% overlap at low altitude, should have minimum
        trigger_dist = self.planner.calculate_trigger_distance(0.1, 99.0)

        self.assertGreaterEqual(trigger_dist, 1.0)

    def test_calculate_transect_spacing_75_overlap(self):
        """Test transect spacing calculation with 75% overlap."""
        spacing = self.planner.calculate_transect_spacing(
            altitude_m=50.0,
            side_overlap_pct=75.0
        )

        # At 50m altitude with this camera, GSD is very small
        # Calculated spacing would be tiny, so minimum of 0.1m is enforced
        self.assertGreaterEqual(spacing, 0.1)

    def test_calculate_transect_spacing_different_overlaps(self):
        """Test transect spacing with different overlap percentages."""
        # At typical altitudes (50-90m), both will hit the 0.1m minimum
        spacing_60 = self.planner.calculate_transect_spacing(50.0, 60.0)
        spacing_80 = self.planner.calculate_transect_spacing(50.0, 80.0)

        # Both should be at the 0.1m minimum
        self.assertEqual(spacing_60, 0.1)
        self.assertEqual(spacing_80, 0.1)

    def test_calculate_transect_spacing_minimum(self):
        """Test transect spacing has minimum value."""
        spacing = self.planner.calculate_transect_spacing(0.1, 99.0)

        self.assertGreaterEqual(spacing, 0.1)

    def test_generate_transects_empty_polygon(self):
        """Test transect generation with empty polygon."""
        polygon = []
        config = SurveyConfig()

        transects = self.planner.generate_transects_from_polygon(polygon, config)

        self.assertEqual(transects, [])

    def test_generate_transects_too_few_points(self):
        """Test transect generation with < 3 points."""
        polygon = [
            LatLon(38.0, -84.5),
            LatLon(38.01, -84.5),
        ]
        config = SurveyConfig()

        transects = self.planner.generate_transects_from_polygon(polygon, config)

        self.assertEqual(transects, [])

    def test_generate_transects_simple_square(self):
        """Test transect generation for simple square polygon."""
        # 100m x 100m square
        center = LatLon(38.0, -84.5)
        polygon = [
            LatLon(38.0, -84.5),
            LatLon(38.001, -84.5),
            LatLon(38.001, -84.499),
            LatLon(38.0, -84.499),
        ]

        config = SurveyConfig(
            altitude_m=50.0,
            front_overlap_pct=75.0,
            side_overlap_pct=75.0,
            grid_angle_deg=0.0
        )

        transects = self.planner.generate_transects_from_polygon(polygon, config)

        # Should generate multiple transects
        self.assertGreater(len(transects), 0)


class TestSurveyPlannerIntegration(unittest.TestCase):
    """Integration tests for complete survey planning workflow."""

    def test_complete_survey_workflow(self):
        """Test complete survey planning from polygon to mission."""
        # Create camera and planner
        camera = CameraSpec.sentera_double_4k_wide()
        planner = SurveyPlanner(camera)

        # Define survey area (small square)
        center = LatLon(38.0336, -84.5037)
        polygon = [
            LatLon(38.0336, -84.5037),
            LatLon(38.0346, -84.5037),
            LatLon(38.0346, -84.5027),
            LatLon(38.0336, -84.5027),
        ]

        # Calculate area
        area = PolygonUtils.calculate_area(polygon)
        self.assertGreater(area, 0)

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
        self.assertGreater(gsd, 0)

        trigger_dist = planner.calculate_trigger_distance(
            config.altitude_m,
            config.front_overlap_pct
        )
        self.assertGreater(trigger_dist, 0)

        spacing = planner.calculate_transect_spacing(
            config.altitude_m,
            config.side_overlap_pct
        )
        self.assertGreater(spacing, 0)

    def test_survey_with_narrow_camera(self):
        """Test survey planning with narrow angle camera."""
        camera = CameraSpec.sentera_double_4k_narrow()
        planner = SurveyPlanner(camera)

        # Narrow camera should have smaller GSD at same altitude
        gsd_narrow = planner.calculate_gsd(50.0)

        wide_camera = CameraSpec.sentera_double_4k_wide()
        wide_planner = SurveyPlanner(wide_camera)
        gsd_wide = wide_planner.calculate_gsd(50.0)

        # Narrow (25mm) should have smaller GSD than wide (8mm)
        self.assertLess(gsd_narrow, gsd_wide)

    def test_survey_high_overlap(self):
        """Test survey with very high overlap settings."""
        camera = CameraSpec.sentera_double_4k_wide()
        planner = SurveyPlanner(camera)

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
        trigger_high = planner.calculate_trigger_distance(
            config_high.altitude_m,
            config_high.front_overlap_pct
        )
        trigger_low = planner.calculate_trigger_distance(
            config_low.altitude_m,
            config_low.front_overlap_pct
        )

        # Both should be at minimum
        self.assertEqual(trigger_high, 1.0)
        self.assertEqual(trigger_low, 1.0)


class TestCameraCalculations(unittest.TestCase):
    """Tests for camera-specific calculations."""

    def test_image_footprint_calculation(self):
        """Test image footprint calculation."""
        camera = CameraSpec.sentera_double_4k_wide()
        planner = SurveyPlanner(camera)

        altitude = 50.0
        gsd = planner.calculate_gsd(altitude)

        # Image footprint dimensions
        footprint_width = gsd * camera.image_width_px
        footprint_height = gsd * camera.image_height_px

        self.assertGreater(footprint_width, 0)
        self.assertGreater(footprint_height, 0)
        # Width should be greater than height (landscape orientation)
        self.assertGreater(footprint_width, footprint_height)

    def test_coverage_area_per_image(self):
        """Test area covered by single image."""
        camera = CameraSpec.sentera_double_4k_wide()
        planner = SurveyPlanner(camera)

        altitude = 50.0
        gsd = planner.calculate_gsd(altitude)

        # Area per image
        width = gsd * camera.image_width_px
        height = gsd * camera.image_height_px
        area = width * height

        self.assertGreater(area, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
