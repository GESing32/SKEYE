"""
Performance benchmarking suite for GCS components.

Benchmarks key operations for performance regression detection:
- Survey generation time
- Mission planning performance
- WebSocket throughput
- Memory usage
- Geometry calculations

Run with:
    pytest test/performance/test_benchmarks.py -v --benchmark
    pytest test/performance/test_benchmarks.py -k "survey_generation"
    pytest test/performance/test_benchmarks.py -m benchmark

Requirements:
    pip install pytest-benchmark memory_profiler
"""

import pytest
import time
import sys
from pathlib import Path
from typing import List
import gc

# Add v2 directory to path for imports
v2_path = Path(__file__).parent.parent.parent / "src" / "flight-system" / "v2"
sys.path.insert(0, str(v2_path))


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def survey_areas():
    """Survey area test cases of varying sizes."""
    from geometry_utils import LatLon, GeodeticUtils

    center = LatLon(38.0336, -84.5037)

    return {
        "small": [  # ~100m x 100m (0.01 km²)
            GeodeticUtils.destination_point(center, 50, 315),
            GeodeticUtils.destination_point(center, 50, 45),
            GeodeticUtils.destination_point(center, 50, 135),
            GeodeticUtils.destination_point(center, 50, 225),
        ],
        "medium": [  # ~500m x 500m (0.25 km²)
            GeodeticUtils.destination_point(center, 250, 315),
            GeodeticUtils.destination_point(center, 250, 45),
            GeodeticUtils.destination_point(center, 250, 135),
            GeodeticUtils.destination_point(center, 250, 225),
        ],
        "large": [  # ~1km x 1km (1 km²)
            GeodeticUtils.destination_point(center, 500, 315),
            GeodeticUtils.destination_point(center, 500, 45),
            GeodeticUtils.destination_point(center, 500, 135),
            GeodeticUtils.destination_point(center, 500, 225),
        ],
        "xlarge": [  # ~2km x 2km (4 km²)
            GeodeticUtils.destination_point(center, 1000, 315),
            GeodeticUtils.destination_point(center, 1000, 45),
            GeodeticUtils.destination_point(center, 1000, 135),
            GeodeticUtils.destination_point(center, 1000, 225),
        ],
    }


@pytest.fixture
def camera():
    """Camera specification."""
    from survey_planner import CameraSpec
    return CameraSpec.sentera_double_4k_default()


@pytest.fixture
def survey_config():
    """Default survey configuration."""
    from survey_planner import SurveyConfig
    return SurveyConfig(
        altitude_m=50,
        speed_m_s=5,
        front_overlap_pct=75,
        side_overlap_pct=75,
    )


# ============================================================================
# Survey Generation Benchmarks
# ============================================================================

@pytest.mark.benchmark
@pytest.mark.performance
class TestSurveyGenerationPerformance:
    """Benchmarks for survey generation performance."""

    def test_small_survey_generation_time(self, survey_areas, camera, survey_config):
        """Benchmark small survey generation (0.01 km²)."""
        from survey_planner import SurveyPlanner

        planner = SurveyPlanner(camera)
        area = survey_areas["small"]

        # Warm-up
        planner.generate_mission_items(area, survey_config)

        # Benchmark
        iterations = 10
        start = time.time()

        for _ in range(iterations):
            items, stats = planner.generate_mission_items(area, survey_config)

        elapsed = time.time() - start
        avg_time = elapsed / iterations

        print(f"\nSmall survey: {avg_time*1000:.2f}ms avg")
        assert avg_time < 0.1, f"Survey generation too slow: {avg_time:.3f}s"

    def test_medium_survey_generation_time(self, survey_areas, camera, survey_config):
        """Benchmark medium survey generation (0.25 km²)."""
        from survey_planner import SurveyPlanner

        planner = SurveyPlanner(camera)
        area = survey_areas["medium"]

        iterations = 5
        start = time.time()

        for _ in range(iterations):
            items, stats = planner.generate_mission_items(area, survey_config)

        elapsed = time.time() - start
        avg_time = elapsed / iterations

        print(f"\nMedium survey: {avg_time*1000:.2f}ms avg ({stats['waypoint_count']} waypoints)")
        assert avg_time < 0.5, f"Survey generation too slow: {avg_time:.3f}s"

    def test_large_survey_generation_time(self, survey_areas, camera, survey_config):
        """Benchmark large survey generation (1 km²)."""
        from survey_planner import SurveyPlanner

        planner = SurveyPlanner(camera)
        area = survey_areas["large"]

        iterations = 3
        start = time.time()

        for _ in range(iterations):
            items, stats = planner.generate_mission_items(area, survey_config)

        elapsed = time.time() - start
        avg_time = elapsed / iterations

        print(f"\nLarge survey: {avg_time*1000:.2f}ms avg ({stats['waypoint_count']} waypoints)")
        assert avg_time < 2.0, f"Survey generation too slow: {avg_time:.3f}s"

    def test_survey_generation_scaling(self, survey_areas, camera, survey_config):
        """Test survey generation time scales approximately O(n)."""
        from survey_planner import SurveyPlanner

        planner = SurveyPlanner(camera)

        results = {}
        for size_name in ["small", "medium", "large"]:
            area = survey_areas[size_name]

            start = time.time()
            items, stats = planner.generate_mission_items(area, survey_config)
            elapsed = time.time() - start

            results[size_name] = {
                "time": elapsed,
                "waypoints": stats["waypoint_count"],
                "time_per_waypoint": elapsed / stats["waypoint_count"]
            }

            print(f"\n{size_name}: {elapsed*1000:.2f}ms, "
                  f"{stats['waypoint_count']} waypoints, "
                  f"{results[size_name]['time_per_waypoint']*1000:.3f}ms/waypoint")

        # Check scaling is approximately linear
        # Time per waypoint should not increase significantly
        small_tpw = results["small"]["time_per_waypoint"]
        large_tpw = results["large"]["time_per_waypoint"]

        # Allow 3x increase (should be much less for O(n) algorithm)
        assert large_tpw < small_tpw * 3, "Survey generation scaling is worse than O(n)"


# ============================================================================
# Geometry Calculation Benchmarks
# ============================================================================

@pytest.mark.benchmark
@pytest.mark.performance
class TestGeometryPerformance:
    """Benchmarks for geometry calculations."""

    def test_geodesic_distance_performance(self):
        """Benchmark geodesic distance calculation."""
        from geometry_utils import LatLon, GeodeticUtils

        p1 = LatLon(38.0336, -84.5037)
        p2 = LatLon(38.0446, -84.5137)

        iterations = 10000
        start = time.time()

        for _ in range(iterations):
            dist = GeodeticUtils.geodesic_distance(p1, p2)

        elapsed = time.time() - start
        avg_time = elapsed / iterations

        print(f"\nGeodesic distance: {avg_time*1e6:.2f}µs per call")
        assert avg_time < 0.001, f"Geodesic calculation too slow: {avg_time*1e6:.2f}µs"

    def test_polygon_area_calculation_performance(self):
        """Benchmark polygon area calculation."""
        from geometry_utils import LatLon, PolygonUtils, GeodeticUtils

        center = LatLon(38.0336, -84.5037)
        polygon = [
            GeodeticUtils.destination_point(center, 100, 0),
            GeodeticUtils.destination_point(center, 100, 90),
            GeodeticUtils.destination_point(center, 100, 180),
            GeodeticUtils.destination_point(center, 100, 270),
        ]

        iterations = 1000
        start = time.time()

        for _ in range(iterations):
            area = PolygonUtils.calculate_area(polygon)

        elapsed = time.time() - start
        avg_time = elapsed / iterations

        print(f"\nPolygon area: {avg_time*1e6:.2f}µs per call")
        assert avg_time < 0.01, f"Polygon area calculation too slow: {avg_time*1e6:.2f}µs"

    def test_coordinate_transformation_performance(self):
        """Benchmark coordinate transformations."""
        from geometry_utils import LatLon, GeodeticUtils

        origin = LatLon(38.0336, -84.5037)
        points = [LatLon(38.0336 + i*0.0001, -84.5037 + i*0.0001) for i in range(100)]

        iterations = 100
        start = time.time()

        for _ in range(iterations):
            local = GeodeticUtils.to_local_coords(points, origin)
            geo = GeodeticUtils.to_geographic_coords(local, origin)

        elapsed = time.time() - start
        avg_time = elapsed / iterations

        print(f"\nCoordinate transform (100 points): {avg_time*1000:.2f}ms")
        assert avg_time < 0.1, f"Coordinate transformation too slow: {avg_time*1000:.2f}ms"


# ============================================================================
# Camera Calculation Benchmarks
# ============================================================================

@pytest.mark.benchmark
@pytest.mark.performance
class TestCameraCalculationPerformance:
    """Benchmarks for camera-related calculations."""

    def test_gsd_calculation_performance(self, camera):
        """Benchmark GSD calculation."""
        from survey_planner import SurveyPlanner

        planner = SurveyPlanner(camera)

        iterations = 10000
        start = time.time()

        for _ in range(iterations):
            gsd = planner.calculate_gsd(50.0)

        elapsed = time.time() - start
        avg_time = elapsed / iterations

        print(f"\nGSD calculation: {avg_time*1e6:.2f}µs per call")
        assert avg_time < 0.0001, f"GSD calculation too slow: {avg_time*1e6:.2f}µs"

    def test_trigger_distance_calculation_performance(self, camera):
        """Benchmark trigger distance calculation."""
        from survey_planner import SurveyPlanner

        planner = SurveyPlanner(camera)

        iterations = 10000
        start = time.time()

        for _ in range(iterations):
            trigger_dist = planner.calculate_trigger_distance(50.0, 75.0)

        elapsed = time.time() - start
        avg_time = elapsed / iterations

        print(f"\nTrigger distance: {avg_time*1e6:.2f}µs per call")
        assert avg_time < 0.0001, f"Trigger distance calculation too slow: {avg_time*1e6:.2f}µs"


# ============================================================================
# Memory Usage Benchmarks
# ============================================================================

@pytest.mark.benchmark
@pytest.mark.performance
class TestMemoryUsage:
    """Benchmarks for memory usage."""

    def test_survey_generation_memory_usage(self, survey_areas, camera, survey_config):
        """Test memory usage during survey generation."""
        from survey_planner import SurveyPlanner
        import tracemalloc

        planner = SurveyPlanner(camera)
        area = survey_areas["large"]

        # Start memory tracking
        gc.collect()
        tracemalloc.start()

        # Generate survey
        items, stats = planner.generate_mission_items(area, survey_config)

        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        print(f"\nMemory: current={current/1024/1024:.2f}MB, peak={peak/1024/1024:.2f}MB")
        print(f"Generated {stats['waypoint_count']} waypoints")

        # Memory should not exceed 50MB for large survey
        assert peak < 50 * 1024 * 1024, f"Excessive memory usage: {peak/1024/1024:.2f}MB"

    def test_mission_items_memory_efficiency(self, survey_areas, camera, survey_config):
        """Test memory efficiency of mission item storage."""
        from survey_planner import SurveyPlanner
        import sys

        planner = SurveyPlanner(camera)
        area = survey_areas["xlarge"]

        items, stats = planner.generate_mission_items(area, survey_config)

        # Calculate memory per waypoint
        total_size = sys.getsizeof(items)
        for item in items:
            total_size += sys.getsizeof(item)
            for key, value in item.items():
                total_size += sys.getsizeof(key) + sys.getsizeof(value)

        size_per_waypoint = total_size / len(items)

        print(f"\nMemory per waypoint: {size_per_waypoint:.0f} bytes")
        print(f"Total waypoints: {len(items)}")
        print(f"Total size: {total_size/1024:.2f} KB")

        # Each waypoint should be < 1.5KB (includes mission_type field added in v2)
        assert size_per_waypoint < 1536, f"Mission item too large: {size_per_waypoint:.0f} bytes"


# ============================================================================
# Regression Baseline Tests
# ============================================================================

@pytest.mark.benchmark
@pytest.mark.performance
@pytest.mark.regression
class TestPerformanceRegression:
    """
    Performance regression tests with baseline comparisons.

    These tests establish baseline performance metrics and detect regressions.
    """

    BASELINE = {
        "small_survey_ms": 100,
        "medium_survey_ms": 500,
        "large_survey_ms": 2000,
        "gsd_calculation_us": 100,
        "trigger_distance_us": 100,
    }

    def test_regression_small_survey(self, survey_areas, camera, survey_config):
        """Regression test for small survey generation."""
        from survey_planner import SurveyPlanner

        planner = SurveyPlanner(camera)
        area = survey_areas["small"]

        start = time.time()
        items, stats = planner.generate_mission_items(area, survey_config)
        elapsed_ms = (time.time() - start) * 1000

        print(f"\nSmall survey: {elapsed_ms:.2f}ms (baseline: {self.BASELINE['small_survey_ms']}ms)")

        # Allow 50% overhead over baseline
        assert elapsed_ms < self.BASELINE["small_survey_ms"] * 1.5, \
            f"Performance regression detected: {elapsed_ms:.2f}ms vs {self.BASELINE['small_survey_ms']}ms baseline"

    def test_regression_medium_survey(self, survey_areas, camera, survey_config):
        """Regression test for medium survey generation."""
        from survey_planner import SurveyPlanner

        planner = SurveyPlanner(camera)
        area = survey_areas["medium"]

        start = time.time()
        items, stats = planner.generate_mission_items(area, survey_config)
        elapsed_ms = (time.time() - start) * 1000

        print(f"\nMedium survey: {elapsed_ms:.2f}ms (baseline: {self.BASELINE['medium_survey_ms']}ms)")

        # Allow 50% overhead over baseline
        assert elapsed_ms < self.BASELINE["medium_survey_ms"] * 1.5, \
            f"Performance regression detected: {elapsed_ms:.2f}ms vs {self.BASELINE['medium_survey_ms']}ms baseline"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
