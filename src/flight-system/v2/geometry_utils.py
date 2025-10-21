# Geodetic and geometric utilities for survey planning
# Based on QGroundControl coordinate transformation algorithms

import math
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class LatLon:
    """Geographic coordinate in degrees."""
    lat: float  # Latitude in degrees
    lon: float  # Longitude in degrees

    def to_tuple(self) -> Tuple[float, float]:
        return (self.lat, self.lon)


@dataclass
class LocalCoord:
    """Local coordinate in meters (North-East frame)."""
    north: float  # North distance in meters
    east: float  # East distance in meters


class GeodeticUtils:
    """Geodetic calculations for survey planning."""

    # WGS84 ellipsoid constants
    EARTH_RADIUS_M = 6371000.0  # Mean radius in meters
    EARTH_EQUATORIAL_RADIUS = 6378137.0  # Equatorial radius (a)
    EARTH_POLAR_RADIUS = 6356752.3142  # Polar radius (b)
    EARTH_FLATTENING = (EARTH_EQUATORIAL_RADIUS - EARTH_POLAR_RADIUS) / EARTH_EQUATORIAL_RADIUS

    @staticmethod
    def haversine_distance(coord1: LatLon, coord2: LatLon) -> float:
        """
        Calculate distance between two coordinates using Haversine formula.
        Accurate for small distances (<100km).

        Returns:
            Distance in meters
        """
        lat1, lon1 = math.radians(coord1.lat), math.radians(coord1.lon)
        lat2, lon2 = math.radians(coord2.lat), math.radians(coord2.lon)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        return GeodeticUtils.EARTH_RADIUS_M * c

    @staticmethod
    def bearing(coord1: LatLon, coord2: LatLon) -> float:
        """
        Calculate initial bearing from coord1 to coord2.

        Returns:
            Bearing in degrees (0-360, where 0=North, 90=East)
        """
        lat1, lon1 = math.radians(coord1.lat), math.radians(coord1.lon)
        lat2, lon2 = math.radians(coord2.lat), math.radians(coord2.lon)

        dlon = lon2 - lon1

        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)

        return (bearing_deg + 360) % 360

    @staticmethod
    def destination_point(coord: LatLon, distance_m: float, bearing_deg: float) -> LatLon:
        """
        Calculate destination point given distance and bearing.

        Args:
            coord: Starting coordinate
            distance_m: Distance in meters
            bearing_deg: Bearing in degrees (0=North, 90=East)

        Returns:
            Destination coordinate
        """
        lat1 = math.radians(coord.lat)
        lon1 = math.radians(coord.lon)
        bearing = math.radians(bearing_deg)

        angular_distance = distance_m / GeodeticUtils.EARTH_RADIUS_M

        lat2 = math.asin(
            math.sin(lat1) * math.cos(angular_distance) +
            math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
        )

        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
            math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2)
        )

        return LatLon(math.degrees(lat2), math.degrees(lon2))

    @staticmethod
    def to_local_coords(coords: List[LatLon], origin: LatLon) -> List[LocalCoord]:
        """
        Convert geographic coordinates to local NE coordinates.
        Uses simple equirectangular projection (good for small areas).

        Args:
            coords: List of geographic coordinates
            origin: Origin point for local frame

        Returns:
            List of local coordinates in meters
        """
        origin_lat_rad = math.radians(origin.lat)

        local_coords = []
        for coord in coords:
            dlat = coord.lat - origin.lat
            dlon = coord.lon - origin.lon

            # Convert to meters
            north = dlat * 111320.0  # 1 degree latitude ≈ 111.32 km
            east = dlon * 111320.0 * math.cos(origin_lat_rad)

            local_coords.append(LocalCoord(north, east))

        return local_coords

    @staticmethod
    def to_geographic_coords(local_coords: List[LocalCoord], origin: LatLon) -> List[LatLon]:
        """
        Convert local NE coordinates back to geographic coordinates.

        Args:
            local_coords: List of local coordinates in meters
            origin: Origin point for local frame

        Returns:
            List of geographic coordinates
        """
        origin_lat_rad = math.radians(origin.lat)

        geo_coords = []
        for local in local_coords:
            dlat = local.north / 111320.0
            dlon = local.east / (111320.0 * math.cos(origin_lat_rad))

            geo_coords.append(LatLon(origin.lat + dlat, origin.lon + dlon))

        return geo_coords


class PolygonUtils:
    """Polygon operations for survey area definition."""

    @staticmethod
    def calculate_bounding_box(polygon: List[LatLon]) -> Tuple[LatLon, LatLon]:
        """
        Calculate bounding box of polygon.

        Returns:
            (min_corner, max_corner) where min has min lat/lon, max has max lat/lon
        """
        lats = [p.lat for p in polygon]
        lons = [p.lon for p in polygon]

        min_corner = LatLon(min(lats), min(lons))
        max_corner = LatLon(max(lats), max(lons))

        return (min_corner, max_corner)

    @staticmethod
    def calculate_centroid(polygon: List[LatLon]) -> LatLon:
        """Calculate centroid of polygon."""
        if not polygon:
            return LatLon(0, 0)

        lat_sum = sum(p.lat for p in polygon)
        lon_sum = sum(p.lon for p in polygon)

        return LatLon(lat_sum / len(polygon), lon_sum / len(polygon))

    @staticmethod
    def calculate_area(polygon: List[LatLon]) -> float:
        """
        Calculate area of polygon in square meters.
        Uses shoelace formula in local coordinates.
        """
        if len(polygon) < 3:
            return 0.0

        # Convert to local coordinates
        centroid = PolygonUtils.calculate_centroid(polygon)
        local_coords = GeodeticUtils.to_local_coords(polygon, centroid)

        # Shoelace formula
        area = 0.0
        n = len(local_coords)
        for i in range(n):
            j = (i + 1) % n
            area += local_coords[i].east * local_coords[j].north
            area -= local_coords[j].east * local_coords[i].north

        return abs(area) / 2.0

    @staticmethod
    def rotate_polygon(polygon: List[LatLon], angle_deg: float, center: Optional[LatLon] = None) -> List[LatLon]:
        """
        Rotate polygon around center point.

        Args:
            polygon: Polygon vertices
            angle_deg: Rotation angle in degrees (positive = counter-clockwise)
            center: Rotation center (default: polygon centroid)

        Returns:
            Rotated polygon
        """
        if center is None:
            center = PolygonUtils.calculate_centroid(polygon)

        # Convert to local coordinates
        local_coords = GeodeticUtils.to_local_coords(polygon, center)

        # Rotate
        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        rotated_local = []
        for coord in local_coords:
            rotated_north = coord.north * cos_a - coord.east * sin_a
            rotated_east = coord.north * sin_a + coord.east * cos_a
            rotated_local.append(LocalCoord(rotated_north, rotated_east))

        # Convert back to geographic
        return GeodeticUtils.to_geographic_coords(rotated_local, center)

    @staticmethod
    def line_segment_intersection(
        p1: LocalCoord, p2: LocalCoord,
        p3: LocalCoord, p4: LocalCoord
    ) -> Optional[LocalCoord]:
        """
        Find intersection point of two line segments.

        Args:
            p1, p2: First line segment endpoints
            p3, p4: Second line segment endpoints

        Returns:
            Intersection point or None if no intersection
        """
        x1, y1 = p1.east, p1.north
        x2, y2 = p2.east, p2.north
        x3, y3 = p3.east, p3.north
        x4, y4 = p4.east, p4.north

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

        if abs(denom) < 1e-10:
            return None  # Parallel or coincident

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        if 0 <= t <= 1 and 0 <= u <= 1:
            # Intersection exists
            int_x = x1 + t * (x2 - x1)
            int_y = y1 + t * (y2 - y1)
            return LocalCoord(int_y, int_x)

        return None

    @staticmethod
    def polygon_line_intersections(
        polygon: List[LocalCoord],
        line_start: LocalCoord,
        line_end: LocalCoord
    ) -> List[LocalCoord]:
        """
        Find all intersection points between polygon and line segment.

        Returns:
            List of intersection points (may be empty)
        """
        intersections = []

        n = len(polygon)
        for i in range(n):
            j = (i + 1) % n
            intersection = PolygonUtils.line_segment_intersection(
                polygon[i], polygon[j],
                line_start, line_end
            )
            if intersection:
                intersections.append(intersection)

        return intersections


def test_geodetic_utils():
    """Test geodetic utility functions."""
    # Test coordinates (Lexington, KY area)
    uk_campus = LatLon(38.0336, -84.5037)
    rupp_arena = LatLon(38.0489, -84.4958)

    # Test distance
    dist = GeodeticUtils.haversine_distance(uk_campus, rupp_arena)
    print(f"Distance UK to Rupp: {dist:.1f} meters")

    # Test bearing
    bearing = GeodeticUtils.bearing(uk_campus, rupp_arena)
    print(f"Bearing UK to Rupp: {bearing:.1f} degrees")

    # Test destination
    dest = GeodeticUtils.destination_point(uk_campus, 1000, 45)
    print(f"1km NE of UK: {dest.lat:.6f}, {dest.lon:.6f}")

    # Test polygon area
    square = [
        LatLon(38.0336, -84.5037),
        LatLon(38.0346, -84.5037),
        LatLon(38.0346, -84.5027),
        LatLon(38.0336, -84.5027),
    ]
    area = PolygonUtils.calculate_area(square)
    print(f"Square area: {area:.0f} m²")


if __name__ == "__main__":
    test_geodetic_utils()
