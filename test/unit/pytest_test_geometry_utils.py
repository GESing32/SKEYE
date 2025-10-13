"""
pytest version: Unit tests for geometry_utils module.

Tests geodetic calculations, coordinate transformations, and polygon operations.
This is the pytest-style version of test_geometry_utils.py.

Run with:
    pytest test/unit/pytest_test_geometry_utils.py
    pytest test/unit/pytest_test_geometry_utils.py -v
    pytest test/unit/pytest_test_geometry_utils.py -k "haversine"
"""

import pytest
import math
import sys
from pathlib import Path

# Add v2 directory to path for imports
v2_path = Path(__file__).parent.parent.parent / "src" / "flight-system" / "v2"
sys.path.insert(0, str(v2_path))

from geometry_utils import LatLon, LocalCoord, GeodeticUtils, PolygonUtils  # type: ignore


# ============================================================================
# Fixtures (Local to this module)
# ============================================================================

@pytest.fixture
def test_square():
    """Square polygon for testing."""
    return [
        LatLon(38.0, -84.5),
        LatLon(38.01, -84.5),
        LatLon(38.01, -84.49),
        LatLon(38.0, -84.49),
    ]


# ============================================================================
# LatLon Tests
# ============================================================================

@pytest.mark.geometry
class TestLatLon:
    """Tests for LatLon dataclass."""

    def test_latlon_creation(self):
        """Test LatLon creation and attributes."""
        coord = LatLon(38.0308, -84.506)
        assert coord.lat == 38.0308
        assert coord.lon == -84.506

    def test_latlon_to_tuple(self):
        """Test LatLon to tuple conversion."""
        coord = LatLon(38.0308, -84.506)
        assert coord.to_tuple() == (38.0308, -84.506)


# ============================================================================
# LocalCoord Tests
# ============================================================================

@pytest.mark.geometry
class TestLocalCoord:
    """Tests for LocalCoord dataclass."""

    def test_localcoord_creation(self):
        """Test LocalCoord creation and attributes."""
        coord = LocalCoord(100.0, 50.0)
        assert coord.north == 100.0
        assert coord.east == 50.0


# ============================================================================
# GeodeticUtils Tests
# ============================================================================

@pytest.mark.geometry
class TestGeodeticUtils:
    """Tests for GeodeticUtils geodetic calculations."""

    def test_haversine_distance_known_points(self, uk_campus, rupp_arena):
        """Test haversine distance between known coordinates."""
        dist = GeodeticUtils.haversine_distance(uk_campus, rupp_arena)

        # Distance should be approximately 1.8 km
        assert dist > 1500
        assert dist < 2000

    def test_haversine_distance_same_point(self, uk_campus):
        """Test haversine distance for same point."""
        dist = GeodeticUtils.haversine_distance(uk_campus, uk_campus)
        assert dist == pytest.approx(0.0, abs=1e-5)

    def test_haversine_distance_equator(self):
        """Test haversine distance along equator."""
        p1 = LatLon(0.0, 0.0)
        p2 = LatLon(0.0, 1.0)
        dist = GeodeticUtils.haversine_distance(p1, p2)

        # 1 degree longitude at equator ≈ 111 km
        assert dist == pytest.approx(111195, abs=500)

    @pytest.mark.parametrize("lat1,lon1,lat2,lon2,expected_min,expected_max", [
        # Known points - UK campus to Rupp Arena
        (38.0336, -84.5037, 38.0489, -84.4958, 1500, 2000),
        # Equator
        (0.0, 0.0, 0.0, 1.0, 110700, 111700),
        # Same point
        (38.0, -84.5, 38.0, -84.5, 0, 0.1),
    ])
    def test_haversine_distance_parametrized(self, lat1, lon1, lat2, lon2,
                                              expected_min, expected_max):
        """Test haversine distance with multiple coordinate pairs."""
        p1 = LatLon(lat1, lon1)
        p2 = LatLon(lat2, lon2)
        dist = GeodeticUtils.haversine_distance(p1, p2)
        assert expected_min <= dist <= expected_max

    def test_bearing_north(self):
        """Test bearing calculation for northward direction."""
        p1 = LatLon(38.0, -84.5)
        p2 = LatLon(39.0, -84.5)
        bearing = GeodeticUtils.bearing(p1, p2)

        # Should be approximately north (0 degrees)
        assert bearing == pytest.approx(0.0, abs=1.0)

    def test_bearing_east(self):
        """Test bearing calculation for eastward direction."""
        p1 = LatLon(38.0, -84.5)
        p2 = LatLon(38.0, -83.5)
        bearing = GeodeticUtils.bearing(p1, p2)

        # Should be approximately east (90 degrees)
        assert bearing == pytest.approx(90.0, abs=1.0)

    def test_bearing_range(self, uk_campus, rupp_arena):
        """Test bearing is always in range [0, 360)."""
        bearing = GeodeticUtils.bearing(uk_campus, rupp_arena)
        assert 0.0 <= bearing < 360.0

    @pytest.mark.parametrize("lat_offset,lon_offset,expected_bearing", [
        (1.0, 0.0, 0.0),    # North
        (0.0, 1.0, 90.0),   # East
        (-1.0, 0.0, 180.0), # South
        (0.0, -1.0, 270.0), # West
    ])
    def test_bearing_cardinal_directions(self, lat_offset, lon_offset, expected_bearing):
        """Test bearing calculations for all cardinal directions."""
        p1 = LatLon(38.0, -84.5)
        p2 = LatLon(p1.lat + lat_offset, p1.lon + lon_offset)
        bearing = GeodeticUtils.bearing(p1, p2)
        assert bearing == pytest.approx(expected_bearing, abs=1.0)

    def test_destination_point_north(self):
        """Test destination point calculation - north direction."""
        start = LatLon(38.0, -84.5)
        dest = GeodeticUtils.destination_point(start, 1000, 0)  # 1km north

        # Latitude should increase
        assert dest.lat > start.lat
        # Longitude should stay approximately same
        assert dest.lon == pytest.approx(start.lon, abs=0.001)

    def test_destination_point_east(self):
        """Test destination point calculation - east direction."""
        start = LatLon(38.0, -84.5)
        dest = GeodeticUtils.destination_point(start, 1000, 90)  # 1km east

        # Latitude should stay approximately same
        assert dest.lat == pytest.approx(start.lat, abs=0.001)
        # Longitude should increase
        assert dest.lon > start.lon

    @pytest.mark.parametrize("distance,bearing", [
        (1000, 0),    # 1km North
        (1000, 90),   # 1km East
        (5000, 45),   # 5km Northeast
        (2000, 270),  # 2km West
    ])
    def test_destination_point_roundtrip(self, distance, bearing):
        """Test destination point with reverse bearing returns to start."""
        start = LatLon(38.0, -84.5)

        dest = GeodeticUtils.destination_point(start, distance, bearing)
        back = GeodeticUtils.destination_point(dest, distance, (bearing + 180) % 360)

        assert start.lat == pytest.approx(back.lat, abs=0.001)
        assert start.lon == pytest.approx(back.lon, abs=0.001)

    def test_to_local_coords_single_point(self):
        """Test conversion to local coordinates for single point."""
        origin = LatLon(38.0, -84.5)
        coords = [LatLon(38.01, -84.49)]

        local = GeodeticUtils.to_local_coords(coords, origin)

        assert len(local) == 1
        # 0.01 degrees latitude ≈ 1113 meters north
        assert local[0].north == pytest.approx(1113.2, abs=10)
        # Should be east of origin
        assert local[0].east > 0

    def test_to_local_coords_origin_is_zero(self):
        """Test that origin point converts to (0, 0)."""
        origin = LatLon(38.0, -84.5)
        coords = [origin]

        local = GeodeticUtils.to_local_coords(coords, origin)

        assert local[0].north == pytest.approx(0.0, abs=1e-5)
        assert local[0].east == pytest.approx(0.0, abs=1e-5)

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
            assert coord.lat == pytest.approx(back[i].lat, abs=1e-5)
            assert coord.lon == pytest.approx(back[i].lon, abs=1e-5)


# ============================================================================
# PolygonUtils Tests
# ============================================================================

@pytest.mark.geometry
class TestPolygonUtils:
    """Tests for PolygonUtils polygon operations."""

    def test_calculate_bounding_box_square(self, test_square):
        """Test bounding box calculation for square."""
        min_corner, max_corner = PolygonUtils.calculate_bounding_box(test_square)

        assert min_corner.lat == 38.0
        assert min_corner.lon == -84.5
        assert max_corner.lat == 38.01
        assert max_corner.lon == -84.49

    def test_calculate_bounding_box_single_point(self):
        """Test bounding box for single point."""
        point = [LatLon(38.0, -84.5)]
        min_corner, max_corner = PolygonUtils.calculate_bounding_box(point)

        assert min_corner.lat == max_corner.lat
        assert min_corner.lon == max_corner.lon

    def test_calculate_centroid_square(self, test_square):
        """Test centroid calculation for square."""
        centroid = PolygonUtils.calculate_centroid(test_square)

        # Center of square should be at (38.005, -84.495)
        assert centroid.lat == pytest.approx(38.005, abs=1e-5)
        assert centroid.lon == pytest.approx(-84.495, abs=1e-5)

    def test_calculate_centroid_empty(self):
        """Test centroid for empty polygon."""
        centroid = PolygonUtils.calculate_centroid([])
        assert centroid.lat == 0
        assert centroid.lon == 0

    def test_calculate_area_square(self, test_square):
        """Test area calculation for square polygon."""
        area = PolygonUtils.calculate_area(test_square)

        # 0.01 deg lat ≈ 1113m, 0.01 deg lon ≈ 900m at this latitude
        # Area should be approximately 1,000,000 m²
        assert 900000 < area < 1100000

    def test_calculate_area_triangle(self, test_triangle_polygon):
        """Test area calculation for triangle."""
        area = PolygonUtils.calculate_area(test_triangle_polygon)

        # Should be approximately half of square
        assert 400000 < area < 600000

    @pytest.mark.parametrize("num_points", [0, 1, 2])
    def test_calculate_area_too_few_points(self, num_points):
        """Test area calculation with < 3 points."""
        coords = [LatLon(38.0, -84.5) for _ in range(num_points)]
        area = PolygonUtils.calculate_area(coords)
        assert area == 0.0

    def test_rotate_polygon_90_degrees(self, test_square):
        """Test polygon rotation by 90 degrees."""
        rotated = PolygonUtils.rotate_polygon(test_square, 90)

        # After 90° rotation, should have same area
        original_area = PolygonUtils.calculate_area(test_square)
        rotated_area = PolygonUtils.calculate_area(rotated)
        assert original_area == pytest.approx(rotated_area, abs=1000)

    def test_rotate_polygon_360_degrees(self, test_square):
        """Test polygon rotation by 360 degrees returns to original."""
        rotated = PolygonUtils.rotate_polygon(test_square, 360)

        for i in range(len(test_square)):
            assert test_square[i].lat == pytest.approx(rotated[i].lat, abs=1e-5)
            assert test_square[i].lon == pytest.approx(rotated[i].lon, abs=1e-5)

    @pytest.mark.parametrize("rotation_angle", [0, 45, 90, 180, 270, 360])
    def test_rotate_polygon_preserves_area(self, test_square, rotation_angle):
        """Test that rotation preserves polygon area."""
        rotated = PolygonUtils.rotate_polygon(test_square, rotation_angle)

        original_area = PolygonUtils.calculate_area(test_square)
        rotated_area = PolygonUtils.calculate_area(rotated)

        assert original_area == pytest.approx(rotated_area, rel=0.01)

    def test_line_segment_intersection_crossing(self):
        """Test line segment intersection - crossing segments."""
        p1 = LocalCoord(0, 0)
        p2 = LocalCoord(10, 10)
        p3 = LocalCoord(0, 10)
        p4 = LocalCoord(10, 0)

        intersection = PolygonUtils.line_segment_intersection(p1, p2, p3, p4)

        assert intersection is not None
        # Intersection should be at (5, 5)
        assert intersection.north == pytest.approx(5, abs=1e-5)
        assert intersection.east == pytest.approx(5, abs=1e-5)

    def test_line_segment_intersection_parallel(self):
        """Test line segment intersection - parallel segments."""
        p1 = LocalCoord(0, 0)
        p2 = LocalCoord(10, 0)
        p3 = LocalCoord(0, 5)
        p4 = LocalCoord(10, 5)

        intersection = PolygonUtils.line_segment_intersection(p1, p2, p3, p4)

        assert intersection is None

    def test_line_segment_intersection_no_overlap(self):
        """Test line segment intersection - no overlap."""
        p1 = LocalCoord(0, 0)
        p2 = LocalCoord(5, 5)
        p3 = LocalCoord(10, 0)
        p4 = LocalCoord(15, 5)

        intersection = PolygonUtils.line_segment_intersection(p1, p2, p3, p4)

        assert intersection is None

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

        assert len(intersections) == 2

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

        assert len(intersections) == 0


# ============================================================================
# Geodetic Constants Tests
# ============================================================================

@pytest.mark.geometry
class TestGeodeticConstants:
    """Tests for geodetic constants."""

    def test_earth_radius_constant(self):
        """Test Earth radius constant is reasonable."""
        assert GeodeticUtils.EARTH_RADIUS_M == pytest.approx(6371000.0, abs=100000)

    def test_earth_flattening(self):
        """Test Earth flattening is calculated correctly."""
        expected_flattening = (
            GeodeticUtils.EARTH_EQUATORIAL_RADIUS - GeodeticUtils.EARTH_POLAR_RADIUS
        ) / GeodeticUtils.EARTH_EQUATORIAL_RADIUS

        assert GeodeticUtils.EARTH_FLATTENING == pytest.approx(expected_flattening, abs=1e-10)


# ============================================================================
# Performance/Stress Tests (Optional - mark as slow)
# ============================================================================

@pytest.mark.slow
@pytest.mark.geometry
class TestGeometryPerformance:
    """Performance and stress tests for geometry calculations."""

    @pytest.mark.parametrize("num_points", [10, 100, 1000])
    def test_large_polygon_area(self, num_points):
        """Test area calculation with large polygons."""
        # Create circular polygon with many points
        center = LatLon(38.0, -84.5)
        radius_deg = 0.01

        polygon = []
        for i in range(num_points):
            angle = (i / num_points) * 2 * math.pi
            lat = center.lat + radius_deg * math.cos(angle)
            lon = center.lon + radius_deg * math.sin(angle)
            polygon.append(LatLon(lat, lon))

        # Should complete without error
        area = PolygonUtils.calculate_area(polygon)
        assert area > 0

    def test_many_coordinate_conversions(self):
        """Test coordinate conversion performance with many points."""
        origin = LatLon(38.0, -84.5)

        # Generate 1000 random coordinates
        coords = [
            LatLon(38.0 + i * 0.001, -84.5 + i * 0.001)
            for i in range(1000)
        ]

        # Convert to local and back
        local = GeodeticUtils.to_local_coords(coords, origin)
        back = GeodeticUtils.to_geographic_coords(local, origin)

        # Verify roundtrip accuracy
        assert len(back) == len(coords)
        for orig, converted in zip(coords, back):
            assert orig.lat == pytest.approx(converted.lat, abs=1e-5)
            assert orig.lon == pytest.approx(converted.lon, abs=1e-5)
