# Geodetic and geometric utilities for survey planning
# Based on QGroundControl coordinate transformation algorithms

import math
from typing import List, Tuple, Optional
from dataclasses import dataclass
import pyproj

try:
    from geographiclib.geodesic import Geodesic
    from geographiclib.polygonarea import PolygonArea
    GEOGRAPHICLIB_AVAILABLE = True
except ImportError:
    GEOGRAPHICLIB_AVAILABLE = False
    print("WARNING: geographiclib not available. Install with: pip install geographiclib")
    print("Falling back to less accurate Haversine calculations.")


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
    """
    Geodetic calculations for survey planning.
    Uses Karney's geodesic algorithms for survey-grade accuracy.
    """

    # WGS84 ellipsoid constants
    EARTH_RADIUS_M = 6371000.0  # Mean radius in meters
    EARTH_EQUATORIAL_RADIUS = 6378137.0  # Equatorial radius (a)
    EARTH_POLAR_RADIUS = 6356752.3142  # Polar radius (b)
    EARTH_FLATTENING = (EARTH_EQUATORIAL_RADIUS - EARTH_POLAR_RADIUS) / EARTH_EQUATORIAL_RADIUS

    # Initialize GeographicLib geodesic calculator
    if GEOGRAPHICLIB_AVAILABLE:
        _geod = Geodesic.WGS84
    else:
        _geod = None
    
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
    def geodesic_distance(coord1: LatLon, coord2: LatLon) -> float:
        """
        Calculate geodesic distance using Karney's algorithm.
        Accuracy: 15 nanometers (essentially exact for Earth's surface).
        
        Returns:
            Distance in meters with sub-millimeter precision
        """
        if not GEOGRAPHICLIB_AVAILABLE:
            return GeodeticUtils.haversine_distance(coord1, coord2)
        
        result = GeodeticUtils._geod.Inverse(coord1.lat, coord1.lon, coord2.lat, coord2.lon)
        return result['s12']

    @staticmethod
    def geodesic_bearing(coord1: LatLon, coord2: LatLon) -> float:
        """
        Calculate initial geodesic bearing using Karney's algorithm.
        
        Returns:
            Bearing in degrees (0-360, where 0=North, 90=East)
        """
        if not GEOGRAPHICLIB_AVAILABLE:
            return GeodeticUtils.bearing(coord1, coord2)
        
        result = GeodeticUtils._geod.Inverse(coord1.lat, coord1.lon, coord2.lat, coord2.lon)
        bearing = result['azi1']
        return (bearing + 360) % 360
    
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
    def geodesic_destination(coord: LatLon, distance_m: float, bearing_deg: float) -> LatLon:
        """
        Calculate destination point using geodesic direct problem.
        
        Args:
            coord: Starting coordinate
            distance_m: Distance in meters
            bearing_deg: Initial bearing in degrees (0=North, 90=East)
        
        Returns:
            Destination coordinate with sub-millimeter accuracy
        """
        if not GEOGRAPHICLIB_AVAILABLE:
            return GeodeticUtils.destination_point(coord, distance_m, bearing_deg)
        
        result = GeodeticUtils._geod.Direct(coord.lat, coord.lon, bearing_deg, distance_m)
        return LatLon(result['lat2'], result['lon2'])

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
        Convert geographic coordinates to local NE coordinates using geodesic method.
        More accurate than equirectangular projection, especially at high latitudes.
        
        Args:
            coords: List of geographic coordinates
            origin: Origin point for local frame
        
        Returns:
            List of local coordinates in meters with sub-cm accuracy
        """
        local_coords = []
        
        for coord in coords:
            if GEOGRAPHICLIB_AVAILABLE:
                # Use geodesic inverse to get distance and azimuth
                result = GeodeticUtils._geod.Inverse(
                    origin.lat, origin.lon,
                    coord.lat, coord.lon
                )
                distance = result['s12']
                azimuth = math.radians(result['azi1'])
                
                # Convert polar to Cartesian
                north = distance * math.cos(azimuth)
                east = distance * math.sin(azimuth)
            else:
                # Fallback to equirectangular
                dlat = coord.lat - origin.lat
                dlon = coord.lon - origin.lon
                origin_lat_rad = math.radians(origin.lat)
                
                north = dlat * 111320.0
                east = dlon * 111320.0 * math.cos(origin_lat_rad)
            
            local_coords.append(LocalCoord(north, east))
        
        return local_coords

    @staticmethod
    def to_geographic_coords(local_coords: List[LocalCoord], origin: LatLon) -> List[LatLon]:
        """
        Convert local NE coordinates back to geographic using geodesic method.
        
        Args:
            local_coords: List of local coordinates in meters
            origin: Origin point for local frame
        
        Returns:
            List of geographic coordinates
        """
        geo_coords = []
        
        for local in local_coords:
            if GEOGRAPHICLIB_AVAILABLE:
                # Convert Cartesian to polar
                distance = math.sqrt(local.north**2 + local.east**2)
                azimuth_rad = math.atan2(local.east, local.north)
                azimuth_deg = math.degrees(azimuth_rad)
                
                # Use geodesic direct
                result = GeodeticUtils._geod.Direct(
                    origin.lat, origin.lon,
                    azimuth_deg, distance
                )
                geo_coords.append(LatLon(result['lat2'], result['lon2']))
            else:
                # Fallback to equirectangular
                origin_lat_rad = math.radians(origin.lat)
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
        Calculate area of polygon using geodesic polygon area algorithm.
        Accuracy: <0.00001% error for any polygon on WGS84 ellipsoid.
        
        Returns:
            Area in square meters
        """
        if len(polygon) < 3:
            return 0.0

        if GEOGRAPHICLIB_AVAILABLE:
            # Use Karney's geodesic polygon area (exact for WGS84)
            geod = Geodesic.WGS84
            poly = PolygonArea(geod, False)
            
            for point in polygon:
                poly.AddPoint(point.lat, point.lon)
            
            # Compute returns (perimeter, area, number_of_points)
            _, area, _ = poly.Compute(False, True)
            return abs(area)
        else:
            # Fallback: Shoelace in local coordinates (less accurate)
            centroid = PolygonUtils.calculate_centroid(polygon)
            local_coords = GeodeticUtils.to_local_coords(polygon, centroid)

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
    
    @staticmethod
    def validate_edge_coverage(
        polygon: List[LocalCoord],
        transects: List[List[LocalCoord]],
        min_coverage_m: float = 5.0
    ) -> dict:
        """
        Validate that transects provide adequate edge coverage.
        
        Args:
            polygon: Survey polygon in local coordinates
            transects: List of transects (each a list of waypoints)
            min_coverage_m: Minimum distance from edge to nearest transect
        
        Returns:
            dict with 'valid', 'min_distance', 'problem_edges' keys
        """
        if not transects or not polygon:
            return {'valid': False, 'min_distance': 0, 'problem_edges': []}
        
        # Sample points along polygon edges
        edge_samples = []
        n = len(polygon)
        samples_per_edge = 10
        
        for i in range(n):
            j = (i + 1) % n
            for k in range(samples_per_edge):
                t = k / samples_per_edge
                sample = LocalCoord(
                    polygon[i].north + t * (polygon[j].north - polygon[i].north),
                    polygon[i].east + t * (polygon[j].east - polygon[i].east)
                )
                edge_samples.append((sample, i))  # Store edge index
        
        # Find minimum distance from each edge sample to any transect
        min_distances = []
        problem_edges = []
        
        for sample, edge_idx in edge_samples:
            min_dist = float('inf')
            
            for transect in transects:
                for waypoint in transect:
                    dist = math.sqrt(
                        (waypoint.north - sample.north)**2 +
                        (waypoint.east - sample.east)**2
                    )
                    min_dist = min(min_dist, dist)
            
            min_distances.append(min_dist)
            if min_dist > min_coverage_m:
                problem_edges.append(edge_idx)
        
        overall_min = min(min_distances) if min_distances else 0
        unique_problem_edges = list(set(problem_edges))
        
        return {
            'valid': len(unique_problem_edges) == 0,
            'min_distance': overall_min,
            'problem_edges': unique_problem_edges,
            'max_edge_distance': max(min_distances) if min_distances else 0
        }


def test_geodetic_utils():
    """Test geodetic utility functions."""
    # Test coordinates (Lexington, KY area)
    uk_campus = LatLon(38.0336, -84.5037)
    rupp_arena = LatLon(38.0489, -84.4958)

    # Test distance (geodesic vs haversine)
    dist_geodesic = GeodeticUtils.geodesic_distance(uk_campus, rupp_arena)
    dist_haversine = GeodeticUtils.haversine_distance(uk_campus, rupp_arena)
    print(f"Distance UK to Rupp:")
    print(f"  Geodesic: {dist_geodesic:.3f} m (survey-grade)")
    print(f"  Haversine: {dist_haversine:.3f} m (error: {abs(dist_geodesic-dist_haversine):.3f} m)")

    # Test bearing
    bearing_geodesic = GeodeticUtils.geodesic_bearing(uk_campus, rupp_arena)
    bearing_simple = GeodeticUtils.bearing(uk_campus, rupp_arena)
    print(f"\nBearing UK to Rupp:")
    print(f"  Geodesic: {bearing_geodesic:.6f}°")
    print(f"  Simple: {bearing_simple:.6f}° (error: {abs(bearing_geodesic-bearing_simple):.6f}°)")

    # Test destination
    dest_geodesic = GeodeticUtils.geodesic_destination(uk_campus, 1000, 45)
    dest_simple = GeodeticUtils.destination_point(uk_campus, 1000, 45)
    error = GeodeticUtils.geodesic_distance(dest_geodesic, dest_simple)
    print(f"\n1km NE of UK:")
    print(f"  Geodesic: {dest_geodesic.lat:.8f}, {dest_geodesic.lon:.8f}")
    print(f"  Simple: {dest_simple.lat:.8f}, {dest_simple.lon:.8f}")
    print(f"  Position error: {error:.3f} m")

    # Test polygon area (geodesic vs shoelace)
    square = [
        LatLon(38.0336, -84.5037),
        LatLon(38.0346, -84.5037),
        LatLon(38.0346, -84.5027),
        LatLon(38.0336, -84.5027),
    ]
    area = PolygonUtils.calculate_area(square)
    print(f"\nSquare area: {area:.0f} m²")
    if GEOGRAPHICLIB_AVAILABLE:
        print("  (Using geodesic polygon area - exact)")
    else:
        print("  (Using shoelace formula - approximate)")


if __name__ == "__main__":
    test_geodetic_utils()
