"""
Unit tests for geometry_utils module.
Tests geodetic calculations, coordinate transformations, and polygon operations.
"""

import unittest
import math
import sys
from pathlib import Path

# Add v2 directory to path for imports
v2_path = Path(__file__).parent.parent.parent / "src" / "flight-system" / "v2"
sys.path.insert(0, str(v2_path))

# Import from v2 directory (runtime resolution)
from geometry_utils import LatLon, LocalCoord, GeodeticUtils, PolygonUtils  # type: ignore


class TestLatLon(unittest.TestCase):
    """Tests for LatLon dataclass."""

    def test_latlon_creation(self):
        """Test LatLon creation and attributes."""
        coord = LatLon(38.0308, -84.506)
        self.assertEqual(coord.lat, 38.0308)
        self.assertEqual(coord.lon, -84.506)

    def test_latlon_to_tuple(self):
        """Test LatLon to tuple conversion."""
        coord = LatLon(38.0308, -84.506)
        self.assertEqual(coord.to_tuple(), (38.0308, -84.506))


class TestLocalCoord(unittest.TestCase):
    """Tests for LocalCoord dataclass."""

    def test_localcoord_creation(self):
        """Test LocalCoord creation and attributes."""
        coord = LocalCoord(100.0, 50.0)
        self.assertEqual(coord.north, 100.0)
        self.assertEqual(coord.east, 50.0)


class TestGeodeticUtils(unittest.TestCase):
    """Tests for GeodeticUtils geodetic calculations."""

    def setUp(self):
        """Set up test fixtures."""
        # Lexington, KY test coordinates
        self.uk_campus = LatLon(38.0336, -84.5037)
        self.rupp_arena = LatLon(38.0489, -84.4958)

    def test_haversine_distance_known_points(self):
        """Test haversine distance between known coordinates."""
        dist = GeodeticUtils.haversine_distance(self.uk_campus, self.rupp_arena)

        # Distance should be approximately 1.8 km
        self.assertGreater(dist, 1500)
        self.assertLess(dist, 2000)

    def test_haversine_distance_same_point(self):
        """Test haversine distance for same point."""
        dist = GeodeticUtils.haversine_distance(self.uk_campus, self.uk_campus)
        self.assertAlmostEqual(dist, 0.0, places=5)

    def test_haversine_distance_equator(self):
        """Test haversine distance along equator."""
        p1 = LatLon(0.0, 0.0)
        p2 = LatLon(0.0, 1.0)
        dist = GeodeticUtils.haversine_distance(p1, p2)

        # 1 degree longitude at equator ≈ 111 km
        self.assertAlmostEqual(dist, 111195, delta=500)

    def test_bearing_north(self):
        """Test bearing calculation for northward direction."""
        p1 = LatLon(38.0, -84.5)
        p2 = LatLon(39.0, -84.5)
        bearing = GeodeticUtils.bearing(p1, p2)

        # Should be approximately north (0 degrees)
        self.assertAlmostEqual(bearing, 0.0, delta=1.0)

    def test_bearing_east(self):
        """Test bearing calculation for eastward direction."""
        p1 = LatLon(38.0, -84.5)
        p2 = LatLon(38.0, -83.5)
        bearing = GeodeticUtils.bearing(p1, p2)

        # Should be approximately east (90 degrees)
        self.assertAlmostEqual(bearing, 90.0, delta=1.0)

    def test_bearing_range(self):
        """Test bearing is always in range [0, 360)."""
        bearing = GeodeticUtils.bearing(self.uk_campus, self.rupp_arena)
        self.assertGreaterEqual(bearing, 0.0)
        self.assertLess(bearing, 360.0)

    def test_destination_point_north(self):
        """Test destination point calculation - north direction."""
        start = LatLon(38.0, -84.5)
        dest = GeodeticUtils.destination_point(start, 1000, 0)  # 1km north

        # Latitude should increase
        self.assertGreater(dest.lat, start.lat)
        # Longitude should stay approximately same
        self.assertAlmostEqual(dest.lon, start.lon, delta=0.001)

    def test_destination_point_east(self):
        """Test destination point calculation - east direction."""
        start = LatLon(38.0, -84.5)
        dest = GeodeticUtils.destination_point(start, 1000, 90)  # 1km east

        # Latitude should stay approximately same
        self.assertAlmostEqual(dest.lat, start.lat, delta=0.001)
        # Longitude should increase
        self.assertGreater(dest.lon, start.lon)

    def test_destination_point_roundtrip(self):
        """Test destination point with reverse bearing returns to start."""
        start = LatLon(38.0, -84.5)
        distance = 5000
        bearing = 45

        dest = GeodeticUtils.destination_point(start, distance, bearing)
        back = GeodeticUtils.destination_point(dest, distance, (bearing + 180) % 360)

        self.assertAlmostEqual(start.lat, back.lat, delta=0.001)
        self.assertAlmostEqual(start.lon, back.lon, delta=0.001)

    def test_to_local_coords_single_point(self):
        """Test conversion to local coordinates for single point."""
        origin = LatLon(38.0, -84.5)
        coords = [LatLon(38.01, -84.49)]

        local = GeodeticUtils.to_local_coords(coords, origin)

        self.assertEqual(len(local), 1)
        # 0.01 degrees latitude ≈ 1113 meters north
        self.assertAlmostEqual(local[0].north, 1113.2, delta=10)
        # Should be east of origin
        self.assertGreater(local[0].east, 0)

    def test_to_local_coords_origin_is_zero(self):
        """Test that origin point converts to (0, 0)."""
        origin = LatLon(38.0, -84.5)
        coords = [origin]

        local = GeodeticUtils.to_local_coords(coords, origin)

        self.assertAlmostEqual(local[0].north, 0.0, places=5)
        self.assertAlmostEqual(local[0].east, 0.0, places=5)

    def test_to_geographic_coords_roundtrip(self):
        """Test conversion to local and back to geographic."""
        origin = LatLon(38.0, -84.5)
        coords = [
            LatLon(38.0, -84.5),
            LatLon(38.01, -84.49),
            LatLon(37.99, -84.51),
        ]

        local = GeodeticUtils.to_local_coords(coords, origin)
        back = GeodeticUtils.to_geographic_coords(local, origin)

        for i, coord in enumerate(coords):
            self.assertAlmostEqual(coord.lat, back[i].lat, places=5)
            self.assertAlmostEqual(coord.lon, back[i].lon, places=5)


class TestPolygonUtils(unittest.TestCase):
    """Tests for PolygonUtils polygon operations."""

    def setUp(self):
        """Set up test fixtures."""
        # Square polygon
        self.square = [
            LatLon(38.0, -84.5),
            LatLon(38.01, -84.5),
            LatLon(38.01, -84.49),
            LatLon(38.0, -84.49),
        ]

    def test_calculate_bounding_box_square(self):
        """Test bounding box calculation for square."""
        min_corner, max_corner = PolygonUtils.calculate_bounding_box(self.square)

        self.assertEqual(min_corner.lat, 38.0)
        self.assertEqual(min_corner.lon, -84.5)
        self.assertEqual(max_corner.lat, 38.01)
        self.assertEqual(max_corner.lon, -84.49)

    def test_calculate_bounding_box_single_point(self):
        """Test bounding box for single point."""
        point = [LatLon(38.0, -84.5)]
        min_corner, max_corner = PolygonUtils.calculate_bounding_box(point)

        self.assertEqual(min_corner.lat, max_corner.lat)
        self.assertEqual(min_corner.lon, max_corner.lon)

    def test_calculate_centroid_square(self):
        """Test centroid calculation for square."""
        centroid = PolygonUtils.calculate_centroid(self.square)

        # Center of square should be at (38.005, -84.495)
        self.assertAlmostEqual(centroid.lat, 38.005, places=5)
        self.assertAlmostEqual(centroid.lon, -84.495, places=5)

    def test_calculate_centroid_empty(self):
        """Test centroid for empty polygon."""
        centroid = PolygonUtils.calculate_centroid([])
        self.assertEqual(centroid.lat, 0)
        self.assertEqual(centroid.lon, 0)

    def test_calculate_area_square(self):
        """Test area calculation for square polygon."""
        area = PolygonUtils.calculate_area(self.square)

        # 0.01 deg lat ≈ 1113m, 0.01 deg lon ≈ 900m at this latitude
        # Area should be approximately 1,000,000 m²
        self.assertGreater(area, 900000)
        self.assertLess(area, 1100000)

    def test_calculate_area_triangle(self):
        """Test area calculation for triangle."""
        triangle = [
            LatLon(38.0, -84.5),
            LatLon(38.01, -84.5),
            LatLon(38.005, -84.49),
        ]
        area = PolygonUtils.calculate_area(triangle)

        # Should be approximately half of square
        self.assertGreater(area, 400000)
        self.assertLess(area, 600000)

    def test_calculate_area_too_few_points(self):
        """Test area calculation with < 3 points."""
        self.assertEqual(PolygonUtils.calculate_area([]), 0.0)
        self.assertEqual(PolygonUtils.calculate_area([LatLon(38.0, -84.5)]), 0.0)
        self.assertEqual(PolygonUtils.calculate_area([LatLon(38.0, -84.5), LatLon(38.01, -84.5)]), 0.0)

    def test_rotate_polygon_90_degrees(self):
        """Test polygon rotation by 90 degrees."""
        # Simple square at origin
        square = [
            LatLon(38.0, -84.5),
            LatLon(38.01, -84.5),
            LatLon(38.01, -84.49),
            LatLon(38.0, -84.49),
        ]

        rotated = PolygonUtils.rotate_polygon(square, 90)

        # After 90° rotation, should have same area
        original_area = PolygonUtils.calculate_area(square)
        rotated_area = PolygonUtils.calculate_area(rotated)
        self.assertAlmostEqual(original_area, rotated_area, delta=1000)

    def test_rotate_polygon_360_degrees(self):
        """Test polygon rotation by 360 degrees returns to original."""
        rotated = PolygonUtils.rotate_polygon(self.square, 360)

        for i in range(len(self.square)):
            self.assertAlmostEqual(self.square[i].lat, rotated[i].lat, places=5)
            self.assertAlmostEqual(self.square[i].lon, rotated[i].lon, places=5)

    def test_line_segment_intersection_crossing(self):
        """Test line segment intersection - crossing segments."""
        p1 = LocalCoord(0, 0)
        p2 = LocalCoord(10, 10)
        p3 = LocalCoord(0, 10)
        p4 = LocalCoord(10, 0)

        intersection = PolygonUtils.line_segment_intersection(p1, p2, p3, p4)

        self.assertIsNotNone(intersection)
        # Intersection should be at (5, 5)
        self.assertAlmostEqual(intersection.north, 5, places=5)
        self.assertAlmostEqual(intersection.east, 5, places=5)

    def test_line_segment_intersection_parallel(self):
        """Test line segment intersection - parallel segments."""
        p1 = LocalCoord(0, 0)
        p2 = LocalCoord(10, 0)
        p3 = LocalCoord(0, 5)
        p4 = LocalCoord(10, 5)

        intersection = PolygonUtils.line_segment_intersection(p1, p2, p3, p4)

        self.assertIsNone(intersection)

    def test_line_segment_intersection_no_overlap(self):
        """Test line segment intersection - no overlap."""
        p1 = LocalCoord(0, 0)
        p2 = LocalCoord(5, 5)
        p3 = LocalCoord(10, 0)
        p4 = LocalCoord(15, 5)

        intersection = PolygonUtils.line_segment_intersection(p1, p2, p3, p4)

        self.assertIsNone(intersection)

    def test_polygon_line_intersections_two_points(self):
        """Test polygon-line intersections - line crosses polygon twice."""
        # Square in local coordinates
        polygon = [
            LocalCoord(0, 0),
            LocalCoord(10, 0),
            LocalCoord(10, 10),
            LocalCoord(0, 10),
        ]

        # Horizontal line through middle
        line_start = LocalCoord(5, -5)
        line_end = LocalCoord(5, 15)

        intersections = PolygonUtils.polygon_line_intersections(polygon, line_start, line_end)

        self.assertEqual(len(intersections), 2)

    def test_polygon_line_intersections_no_hit(self):
        """Test polygon-line intersections - line misses polygon."""
        polygon = [
            LocalCoord(0, 0),
            LocalCoord(10, 0),
            LocalCoord(10, 10),
            LocalCoord(0, 10),
        ]

        # Line outside polygon
        line_start = LocalCoord(20, 0)
        line_end = LocalCoord(20, 10)

        intersections = PolygonUtils.polygon_line_intersections(polygon, line_start, line_end)

        self.assertEqual(len(intersections), 0)


class TestGeodeticConstants(unittest.TestCase):
    """Tests for geodetic constants."""

    def test_earth_radius_constant(self):
        """Test Earth radius constant is reasonable."""
        self.assertAlmostEqual(GeodeticUtils.EARTH_RADIUS_M, 6371000.0, delta=100000)

    def test_earth_flattening(self):
        """Test Earth flattening is calculated correctly."""
        expected_flattening = (
            GeodeticUtils.EARTH_EQUATORIAL_RADIUS - GeodeticUtils.EARTH_POLAR_RADIUS
        ) / GeodeticUtils.EARTH_EQUATORIAL_RADIUS

        self.assertAlmostEqual(GeodeticUtils.EARTH_FLATTENING, expected_flattening, places=10)


if __name__ == '__main__':
    unittest.main(verbosity=2)
