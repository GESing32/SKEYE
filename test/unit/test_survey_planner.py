"""
Unit tests for survey_planner module - FIXED for correct GSD values.
Tests now expect proper GSD calculations without the /1000 bug.
"""

import unittest
import math
import sys
from pathlib import Path

# Add v2 directory to path
v2_path = Path(__file__).parent.parent.parent / "src" / "flight-system" / "v2"
sys.path.insert(0, str(v2_path))

from survey_planner import (  # type: ignore
    CameraSpec, SurveyConfig, SurveyPlanner,
    EntryPoint, TriggerMode
)
from geometry_utils import LatLon, PolygonUtils  # type: ignore


class TestCameraSpec(unittest.TestCase):
    """Tests for CameraSpec dataclass and presets."""

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
    """Tests for SurveyPlanner class - FIXED expectations."""

    def setUp(self):
        """Set up test fixtures."""
        self.camera = CameraSpec.sentera_double_4k_wide()
        self.planner = SurveyPlanner(self.camera)

    def test_initialization(self):
        """Test SurveyPlanner initialization."""
        self.assertEqual(self.planner.camera, self.camera)

    def test_gsd_realistic_values(self):
        """
        Test GSD calculation produces CORRECT realistic values.
        
        Expected values (FIXED - removed /1000 bug):
        - At 30m: 0.00875 m/px = 0.875 cm/px
        - At 50m: 0.014583 m/px = 1.458 cm/px
        - At 90m: 0.02625 m/px = 2.625 cm/px
        """
        test_cases = [
            (30.0, 0.875),   # 30m: 0.875 cm/px (CORRECT)
            (50.0, 1.458),   # 50m: 1.458 cm/px (CORRECT)
            (90.0, 2.625),   # 90m: 2.625 cm/px (CORRECT)
        ]

        print("\n" + "="*70)
        print("GSD Analysis - FIXED VALUES")
        print("="*70)

        for altitude, expected_gsd_cm in test_cases:
            with self.subTest(altitude=altitude):
                gsd_cm = self.planner.calculate_gsd(altitude_m=altitude, camera_angle_deg=90.0)

                # Verify GSD matches expected (in cm/px)
                self.assertAlmostEqual(gsd_cm, expected_gsd_cm, places=3)

                # Calculate footprint
                footprint_width = (gsd_cm / 100.0) * self.camera.image_width_px
                footprint_height = (gsd_cm / 100.0) * self.camera.image_height_px

                print(f"\nAltitude: {altitude}m")
                print(f"  GSD: {gsd_cm:.3f} cm/px (CORRECT)")
                print(f"  Footprint: {footprint_width:.1f}m × {footprint_height:.1f}m")

        print("="*70)

    def test_calculate_gsd_nadir(self):
        """Test GSD calculation for nadir - FIXED expectation."""
        gsd_cm = self.planner.calculate_gsd(altitude_m=50.0, camera_angle_deg=90.0)

        # FIXED: Expect 1.458 cm/px, NOT 0.00001458 m/px
        # GSD = (6.3mm * 50m * 1000) / (5.4mm * 4000px) / 10 = 1.458 cm/px
        self.assertGreater(gsd_cm, 0.0)
        self.assertAlmostEqual(gsd_cm, 1.458, places=3)

    def test_calculate_gsd_higher_altitude(self):
        """Test GSD increases with altitude."""
        gsd_50m = self.planner.calculate_gsd(altitude_m=50.0)
        gsd_100m = self.planner.calculate_gsd(altitude_m=100.0)

        # GSD should double when altitude doubles
        self.assertAlmostEqual(gsd_100m, gsd_50m * 2, places=2)
        
    def test_calculate_gsd_angled_camera(self):
        """Test GSD calculation with angled camera."""
        gsd_nadir = self.planner.calculate_gsd(altitude_m=50.0, camera_angle_deg=90.0)
        gsd_angled = self.planner.calculate_gsd(altitude_m=50.0, camera_angle_deg=60.0)

        # Angled camera (60deg) should have smaller GSD than nadir due to cos factor
        # At 60deg, angle_from_nadir = 30deg, cos(30) ≈ 0.866
        self.assertLess(gsd_angled, gsd_nadir)

    def test_calculate_trigger_distance_75_overlap(self):
        """Test trigger distance - FIXED to expect realistic values."""
        trigger_dist = self.planner.calculate_trigger_distance(
            altitude_m=50.0,
            front_overlap_pct=75.0
        )

        # At 50m: GSD = 1.458 cm/px
        # Footprint height = 1.458 * 3000 = 43.74m
        # 75% overlap = 25% spacing = 10.9m
        # Should be > 5m (min from camera rate)
        self.assertGreater(trigger_dist, 5.0)
        self.assertAlmostEqual(trigger_dist, 10.9, delta=1.0)

    def test_calculate_trigger_distance_80_overlap(self):
        """Test trigger distance with 80% overlap - FIXED."""
        # At 50m altitude, different overlaps should give different results
        dist_75 = self.planner.calculate_trigger_distance(50.0, 75.0)
        dist_80 = self.planner.calculate_trigger_distance(50.0, 80.0)

        # 80% overlap should be tighter than 75%
        self.assertLess(dist_80, dist_75)
        
        # Values should be realistic (not stuck at 1m minimum)
        self.assertGreater(dist_75, 5.0)
        self.assertGreater(dist_80, 5.0)

    def test_calculate_trigger_distance_minimum(self):
        """Test trigger distance has minimum constraint."""
        # At very low altitude with high overlap, minimum kicks in
        trigger_dist = self.planner.calculate_trigger_distance(1.0, 99.0)

        # Should respect minimum from camera trigger rate
        self.assertGreaterEqual(trigger_dist, 1.0)

    def test_calculate_transect_spacing_75_overlap(self):
        """Test transect spacing - FIXED to expect realistic values."""
        spacing = self.planner.calculate_transect_spacing(
            altitude_m=50.0,
            side_overlap_pct=75.0
        )

        # At 50m: footprint width = 1.458 * 4000 = 58.3m
        # 75% overlap = 25% spacing = 14.6m
        self.assertGreater(spacing, 10.0)
        self.assertAlmostEqual(spacing, 14.6, delta=2.0)

    def test_calculate_transect_spacing_different_overlaps(self):
        """Test transect spacing with different overlaps - FIXED."""
        # At 50m altitude, different overlaps give different results
        spacing_60 = self.planner.calculate_transect_spacing(50.0, 60.0)
        spacing_80 = self.planner.calculate_transect_spacing(50.0, 80.0)

        # Lower overlap = wider spacing
        self.assertGreater(spacing_60, spacing_80)
        
        # Both should be realistic (not stuck at 0.1m minimum)
        self.assertGreater(spacing_60, 10.0)
        self.assertGreater(spacing_80, 5.0)

    def test_calculate_transect_spacing_minimum(self):
        """Test transect spacing has minimum constraint."""
        # Very low altitude should hit minimum
        spacing = self.planner.calculate_transect_spacing(0.5, 99.0)

        self.assertGreaterEqual(spacing, 0.5)

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
        """Test transect generation for simple square."""
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
    """Integration tests - FIXED expectations."""

    def test_complete_survey_workflow(self):
        """Test complete survey workflow."""
        camera = CameraSpec.sentera_double_4k_wide()
        planner = SurveyPlanner(camera)

        center = LatLon(38.0336, -84.5037)
        polygon = [
            LatLon(38.0336, -84.5037),
            LatLon(38.0346, -84.5037),
            LatLon(38.0346, -84.5027),
            LatLon(38.0336, -84.5027),
        ]

        area = PolygonUtils.calculate_area(polygon)
        self.assertGreater(area, 0)

        config = SurveyConfig(
            altitude_m=50.0,
            speed_m_s=5.0,
            front_overlap_pct=75.0,
            side_overlap_pct=75.0,
        )

        gsd_cm = planner.calculate_gsd(config.altitude_m)
        self.assertGreater(gsd_cm, 0)
        self.assertAlmostEqual(gsd_cm, 1.458, delta=0.1)

        trigger_dist = planner.calculate_trigger_distance(
            config.altitude_m, config.front_overlap_pct
        )
        self.assertGreater(trigger_dist, 5.0)

        spacing = planner.calculate_transect_spacing(
            config.altitude_m, config.side_overlap_pct
        )
        self.assertGreater(spacing, 5.0)

    def test_survey_with_narrow_camera(self):
        """Test survey with narrow camera."""
        camera = CameraSpec.sentera_double_4k_narrow()
        planner = SurveyPlanner(camera)

        # Narrow camera (30° HFOV, 11.76mm focal) should have smaller GSD
        gsd_narrow = planner.calculate_gsd(50.0)

        wide_camera = CameraSpec.sentera_double_4k_wide()
        wide_planner = SurveyPlanner(wide_camera)
        gsd_wide = wide_planner.calculate_gsd(50.0)

        # Longer focal length = smaller GSD
        self.assertLess(gsd_narrow, gsd_wide)

    def test_survey_high_overlap(self):
        """Test survey with high overlap - FIXED."""
        camera = CameraSpec.sentera_double_4k_wide()
        planner = SurveyPlanner(camera)

        config_high = SurveyConfig(altitude_m=50.0, front_overlap_pct=90.0)
        config_low = SurveyConfig(altitude_m=50.0, front_overlap_pct=70.0)

        # At 50m altitude, calculated values are realistic
        trigger_high = planner.calculate_trigger_distance(
            config_high.altitude_m, config_high.front_overlap_pct
        )
        trigger_low = planner.calculate_trigger_distance(
            config_low.altitude_m, config_low.front_overlap_pct
        )

        # Higher overlap = tighter spacing
        self.assertLess(trigger_high, trigger_low)
        
        # Both should be realistic
        self.assertGreater(trigger_high, 2.0)
        self.assertGreater(trigger_low, 5.0)


class TestCameraCalculations(unittest.TestCase):
    """Tests for camera calculations - FIXED."""

    def test_image_footprint_calculation(self):
        """Test image footprint calculation."""
        camera = CameraSpec.sentera_double_4k_wide()
        planner = SurveyPlanner(camera)

        altitude = 50.0
        gsd_cm = planner.calculate_gsd(altitude)
        gsd_m = gsd_cm / 100.0

        footprint_width = gsd_m * camera.image_width_px
        footprint_height = gsd_m * camera.image_height_px

        self.assertGreater(footprint_width, 0)
        self.assertGreater(footprint_height, 0)
        
        # At 50m: GSD ~1.458 cm, so footprint ~58m × 44m
        self.assertAlmostEqual(footprint_width, 58.3, delta=2.0)
        self.assertAlmostEqual(footprint_height, 43.7, delta=2.0)

    def test_coverage_area_per_image(self):
        """Test area covered by single image."""
        camera = CameraSpec.sentera_double_4k_wide()
        planner = SurveyPlanner(camera)

        gsd_cm = planner.calculate_gsd(50.0)
        gsd_m = gsd_cm / 100.0
        
        width = gsd_m * camera.image_width_px
        height = gsd_m * camera.image_height_px
        area = width * height

        self.assertGreater(area, 0)
        # At 50m: ~58m × 44m = ~2550 m²
        self.assertAlmostEqual(area, 2550, delta=200)


if __name__ == '__main__':
    unittest.main(verbosity=2)
