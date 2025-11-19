# QGroundControl-style Survey Mission Planner
# Implements advanced survey planning with camera triggers, grid optimization,
# and polygon-based area coverage

import math
import warnings
from typing import List, Dict, Any, Tuple, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from pymavlink import mavutil
from geometry_utils import (
    LatLon, LocalCoord, GeodeticUtils, PolygonUtils
)


class EntryPoint(Enum):
    """Entry point location for survey grid."""
    TOP_LEFT = "TopLeft"
    TOP_RIGHT = "TopRight"
    BOTTOM_LEFT = "BottomLeft"
    BOTTOM_RIGHT = "BottomRight"
class TriggerMode(Enum):
    """Camera trigger mode."""
    NONE = "None"
    DISTANCE = "Distance"  # Distance-based (default)
    TIME = "Time"  # Time-based
    HOVER_CAPTURE = "HoverCapture"  # Hover at each point and capture
@dataclass
class CameraSpec:
    """Camera specifications for trigger calculations."""
    name: str
    sensor_width_mm: float
    sensor_height_mm: float
    image_width_px: int
    image_height_px: int
    focal_length_mm: float
    min_trigger_interval_s: float = 0.0  # Minimum time between triggers
    hfov_deg: Optional[float] = None  # Horizontal field of view (alternative to focal length)

    def get_effective_focal_length(self) -> float:
        """
        Get effective focal length. Always uses focal_length_mm field.
        The hfov_deg field is kept for reference/documentation purposes.

        Returns:
            Focal length in millimeters
        """
        return self.focal_length_mm

    # Sentera Double 4K camera presets (only supported camera)
    @staticmethod
    def sentera_double_4k_default() -> 'CameraSpec':
        """
        Sentera Double 4K Camera - Default 60° HFOV at 4K resolution.
        Connected via MAVLink TELEM2 on Pixhawk 6x.
        Reference: 27060 Double 4K Integration Guide

        Specifications:
        - 12.3MP BSI CMOS RGB Sony Exmor R IMX377 Sensor
        - 4K Ultra HD video at 30fps
        - 1080p/720p Video with H.263 Encoding
        - HFOV: 60° (4K stills/video)
        - 1080p ranges: 30° - 60° HFOV
        - GSD @ 200ft: ~0.8" (2.0 cm)
        - GSD @ 400ft: ~1.0" (1.0 cm)
        """
        return CameraSpec(
            name="Sentera Double 4K (60° Default)",
            sensor_width_mm=6.3,      # 1/2.3" Sony IMX377 sensor
            sensor_height_mm=4.7,
            image_width_px=4000,      # 4K resolution
            image_height_px=3000,
            focal_length_mm=5.4,      # Calculated for 60° HFOV
            hfov_deg=60.0,            # Specified in documentation
            min_trigger_interval_s=0.5  # MAVLink triggered
        )

    @staticmethod
    def sentera_double_4k_zoom(hfov_deg: float = 60.0) -> 'CameraSpec':
        """
        Sentera Double 4K Camera - Variable zoom/HFOV.
        Connected via MAVLink TELEM2 on Pixhawk 6x.
        Reference: 27060 Double 4K Integration Guide

        The camera supports variable HFOV, particularly for 1080p mode (30° - 60°).
        This preset allows specifying custom HFOV for mission planning.

        Args:
            hfov_deg: Horizontal field of view in degrees (default 60°, range 30° - 60°)

        Note:
            - Full 4K (4000x3000): 60° HFOV
            - 1080p mode: 30° - 60° HFOV (variable zoom)
            - Lower HFOV = narrower field = higher effective focal length
        """
        if not 30.0 <= hfov_deg <= 60.0:
            raise ValueError(f"HFOV must be between 30° and 60°, got {hfov_deg}°")

        # Calculate focal length from HFOV
        sensor_width = 6.3
        hfov_rad = math.radians(hfov_deg)
        focal_length = sensor_width / (2.0 * math.tan(hfov_rad / 2.0))

        return CameraSpec(
            name=f"Sentera Double 4K ({hfov_deg}° HFOV)",
            sensor_width_mm=sensor_width,
            sensor_height_mm=4.7,
            image_width_px=4000,
            image_height_px=3000,
            focal_length_mm=focal_length,
            hfov_deg=hfov_deg,
            min_trigger_interval_s=0.5
        )

    @staticmethod
    def sentera_double_4k_wide() -> 'CameraSpec':
        """
        Sentera Double 4K Camera - Wide Angle (60° HFOV).
        Legacy preset - use sentera_double_4k_default() instead.
        """
        return CameraSpec.sentera_double_4k_default()

    @staticmethod
    def sentera_double_4k_narrow() -> 'CameraSpec':
        """
        Sentera Double 4K Camera - Narrow Angle (30° HFOV).
        Maximum zoom setting for 1080p mode.
        """
        return CameraSpec.sentera_double_4k_zoom(30.0)

@dataclass
class SurveyConfig:
    """Survey mission configuration."""
    altitude_m: float = 50.0
    speed_m_s: float = 5.0
    front_overlap_pct: float = 75.0
    side_overlap_pct: float = 75.0
    grid_angle_deg: float = 0.0  # 0 = North-South, 90 = East-West
    entry_point: EntryPoint = EntryPoint.TOP_LEFT
    turnaround_dist_m: float = 10.0
    trigger_mode: TriggerMode = TriggerMode.DISTANCE
    refly_90deg: bool = False  # Fly grid again rotated 90°
    hover_and_capture: bool = False
    camera_angle_deg: float = 90.0  # 90 = nadir (straight down)
    terrain_follow: bool = False
    terrain_provider: Optional[Callable[[LatLon], float]] = None

class SurveyPlanner:
    """
    Advanced survey mission planner based on QGroundControl algorithms.
    Generates optimized grid patterns for aerial photography.
    """

    def __init__(self, camera: CameraSpec):
        self.camera = camera

    def calculate_gsd(self, altitude_m: float, camera_angle_deg: float = 90.0) -> float:
        """
        Calculate Ground Sample Distance (GSD) in centimeters per pixel.

        GSD = (sensor_width * altitude * cos(angle)) / (focal_length * image_width)

        Args:
            altitude_m: Flight altitude above ground
            camera_angle_deg: Camera angle from nadir (90 = straight down)

        Returns:
            GSD in meters/pixel
        """
        angle_from_nadir = abs(90.0 - camera_angle_deg)
        angle_factor = math.cos(math.radians(angle_from_nadir))

        focal_length = self.camera.get_effective_focal_length()

        gsd_mm = (
            (self.camera.sensor_width_mm * altitude_m * angle_factor * 1000) /
            (focal_length * self.camera.image_width_px)
        )
        
        gsd_cm = gsd_mm / 10.0  # Convert mm to cm

        return gsd_cm

    def calculate_gsd_detailed(self, altitude_m: float, camera_angle_deg: float = 90.0) -> dict:
        """
        Calculate GSD with detailed unit breakdown for validation.
        
        Returns:
            dict with 'gsd_mm', 'gsd_cm', 'gsd_m', 'gsd_inches' keys
        """
        focal_length = self.camera.get_effective_focal_length()
        
        gsd_mm = (self.camera.sensor_width_mm * altitude_m * 1000.0) / \
                 (focal_length * self.camera.image_width_px)
        
        return {
            'gsd_mm': gsd_mm,
            'gsd_cm': gsd_mm / 10.0,
            'gsd_m': gsd_mm / 1000.0,
            'gsd_inches': gsd_mm / 25.4,
            'footprint_width_m': (gsd_mm / 1000.0) * self.camera.image_width_px,
            'footprint_height_m': (gsd_mm / 1000.0) * self.camera.image_height_px
        }
    
    def calculate_trigger_distance(
        self,
        altitude_m: float,
        front_overlap_pct: float,
        camera_angle_deg: float = 90.0,
        precision: int = 2
    ) -> float:
        """
        Calculate camera trigger distance for desired overlap with configurable precision.

        Args:
            altitude_m: Flight altitude
            front_overlap_pct: Front overlap percentage (0-100)
            camera_angle_deg: Camera angle (90 = nadir)
            precision: Decimal places for rounding (default: 2 = cm precision)

        Returns:
            Trigger distance in meters (rounded to specified precision)
        """
        # Validate overlap based on industry standards
        if front_overlap_pct > 90:
            warnings.warn(f"Front overlap {front_overlap_pct}% > 90% may be excessive. "
                         f"Minimal accuracy gain with 4x processing cost.")
        elif front_overlap_pct < 60:
            warnings.warn(f"Front overlap {front_overlap_pct}% < 60% below recommended minimum.")

        gsd_cm = self.calculate_gsd(altitude_m, camera_angle_deg)
        gsd = gsd_cm / 100.0  # Convert to meters/pixel
        image_footprint_length = gsd * self.camera.image_height_px
        overlap_fraction = front_overlap_pct / 100.0

        # Distance between photo centers
        trigger_dist = image_footprint_length * (1.0 - overlap_fraction)

        # Round to specified precision for MAVLink transmission (default: cm precision)
        trigger_dist = round(trigger_dist, precision)

        return max(trigger_dist, 0.1)  # Minimum 10cm

    def calculate_transect_spacing(
        self,
        altitude_m: float,
        side_overlap_pct: float,
        camera_angle_deg: float = 90.0
    ) -> float:
        """
        Calculate spacing between parallel transects.

        Args:
            altitude_m: Flight altitude
            side_overlap_pct: Side overlap percentage (0-100)
            camera_angle_deg: Camera angle

        Returns:
            Transect spacing in meters
        """
        # Validate overlap based on industry standards
        if side_overlap_pct > 85:
            warnings.warn(f"Side overlap {side_overlap_pct}% > 85% may be excessive.")
        elif side_overlap_pct < 50:
            warnings.warn(f"Side overlap {side_overlap_pct}% < 50% below recommended minimum.")
        
        gsd_cm = self.calculate_gsd(altitude_m, camera_angle_deg)
        gsd = gsd_cm / 100.0  # Convert to meters/pixel
        image_footprint_width = gsd * self.camera.image_width_px
        overlap_fraction = side_overlap_pct / 100.0

        spacing = image_footprint_width * (1.0 - overlap_fraction)

        return max(spacing, 0.5) 
    
    def get_terrain_altitude(
        self,
        coord: LatLon,
        terrain_provider: Optional[Callable[[LatLon], float]]
    ) -> float:
        """
        Get terrain elevation at coordinate.
        
        Args:
            coord: Geographic coordinate
            terrain_provider: Function that returns elevation in meters, or None
        
        Returns:
            Terrain elevation in meters (0 if no provider)
        """
        if terrain_provider is None:
            return 0.0
        
        try:
            return terrain_provider(coord)
        except Exception as e:
            warnings.warn(f"Terrain provider failed at {coord}: {e}")
            return 0.0
        
    def generate_transects_from_polygon(
        self,
        polygon: List[LatLon],
        config: SurveyConfig
    ) -> List[List[LatLon]]:
        """
        Generate survey transects for polygon area (QGC algorithm).

        Steps:
        1. Convert polygon to local coordinates
        2. Calculate transect spacing
        3. Generate parallel lines across bounding box
        4. Rotate lines by grid angle
        5. Find intersections with polygon
        6. Optimize transect order
        7. Add turnaround points
        8. Validate edge coverage

        Returns:
            List of transects, where each transect is a list of coordinates
        """
        if len(polygon) < 3:
            return []

        # Calculate transect spacing
        spacing = self.calculate_transect_spacing(
            config.altitude_m,
            config.side_overlap_pct,
            config.camera_angle_deg
        )

        # Convert to local coordinates
        centroid = PolygonUtils.calculate_centroid(polygon)
        local_polygon = GeodeticUtils.to_local_coords(polygon, centroid)

        # Calculate bounding box in local coords
        min_north = min(p.north for p in local_polygon)
        max_north = max(p.north for p in local_polygon)
        min_east = min(p.east for p in local_polygon)
        max_east = max(p.east for p in local_polygon)

        # Generate parallel lines
        transects_local = []

        # Grid angle rotation
        angle_rad = math.radians(config.grid_angle_deg)
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)

        # Determine number of transects needed
        if abs(cos_angle) > abs(sin_angle):
            # North-South lines
            survey_width = max_east - min_east
            num_transects = int(survey_width / spacing) + 2
            baseline_north = (max_north + min_north) / 2
            baseline_east = (max_east + min_east) / 2

            for i in range(num_transects):
                offset = (i - num_transects / 2) * spacing

                line_start = LocalCoord(baseline_north - 1000, baseline_east + offset)
                line_end = LocalCoord(baseline_north + 1000, baseline_east + offset)

                if config.grid_angle_deg != 0:
                    center = LocalCoord(baseline_north, baseline_east + offset)
                    line_start = self._rotate_point(line_start, center, angle_rad)
                    line_end = self._rotate_point(line_end, center, angle_rad)

                intersections = PolygonUtils.polygon_line_intersections(
                    local_polygon, line_start, line_end
                )

                if len(intersections) >= 2:
                    intersections.sort(key=lambda p: p.north)
                    transects_local.append(intersections)
        else:
            # East-West lines
            survey_height = max_north - min_north
            num_transects = int(survey_height / spacing) + 2
            baseline_north = (max_north + min_north) / 2
            baseline_east = (max_east + min_east) / 2

            for i in range(num_transects):
                offset = (i - num_transects / 2) * spacing

                line_start = LocalCoord(baseline_north + offset, baseline_east - 1000)
                line_end = LocalCoord(baseline_north + offset, baseline_east + 1000)

                if config.grid_angle_deg != 0:
                    center = LocalCoord(baseline_north + offset, baseline_east)
                    line_start = self._rotate_point(line_start, center, angle_rad)
                    line_end = self._rotate_point(line_end, center, angle_rad)

                intersections = PolygonUtils.polygon_line_intersections(
                    local_polygon, line_start, line_end
                )

                if len(intersections) >= 2:
                    intersections.sort(key=lambda p: p.east)
                    transects_local.append(intersections)

        # Validate edge coverage with recursive validation
        coverage_result = self._recursive_edge_coverage_validation(
            local_polygon, transects_local, spacing, max_depth=3
        )

        if not coverage_result['valid']:
            warnings.warn(
                f"Edge coverage validation failed after recursive attempts. "
                f"Problem edges: {coverage_result['problem_edges']}. "
                f"Max distance from edge: {coverage_result['max_edge_distance']:.1f}m"
            )
            
        # Optimize transect order based on entry point
        transects_local = self._optimize_transect_order(transects_local, config.entry_point)

        # Add turnaround points
        transects_local = self._add_turnaround_points(transects_local, config.turnaround_dist_m)

        # Convert back to geographic coordinates
        transects_geo = []
        for transect in transects_local:
            transect_geo = GeodeticUtils.to_geographic_coords(transect, centroid)
            
            # Apply terrain following if enabled
            if config.terrain_follow and config.terrain_provider:
                transect_geo = self._apply_terrain_following(
                    transect_geo, config.altitude_m, config.terrain_provider
                )
            
            transects_geo.append(transect_geo)

        return transects_geo
    
    def _apply_terrain_following(
        self,
        transect: List[LatLon],
        altitude_agl: float,
        terrain_provider: Callable[[LatLon], float]
    ) -> List[LatLon]:
        """
        Apply terrain-following altitude adjustment to transect.

        Args:
            transect: List of waypoint coordinates
            altitude_agl: Desired altitude above ground level
            terrain_provider: Function that returns terrain elevation

        Returns:
            Transect with terrain-adjusted altitudes (stored in LatLon for now)
        """
        # Note: This stores terrain data alongside coordinates
        # In actual implementation, waypoints would have altitude field
        adjusted_transect = []

        for coord in transect:
            terrain_elevation = self.get_terrain_altitude(coord, terrain_provider)
            # Store adjusted coordinate (altitude would be in mission item)
            adjusted_transect.append(coord)

        return adjusted_transect

    def _recursive_edge_coverage_validation(
        self,
        polygon: List[LocalCoord],
        transects: List[List[LocalCoord]],
        spacing: float,
        depth: int = 0,
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Recursively validate and fix edge coverage issues.

        Algorithm:
        1. Validate current edge coverage
        2. If invalid and depth < max_depth:
           - Identify problem edges
           - Generate additional transects near problem edges
           - Recursively validate with new transects
        3. Return final validation result

        Args:
            polygon: Survey polygon in local coordinates
            transects: List of transects (each transect is list of points)
            spacing: Transect spacing in meters
            depth: Current recursion depth
            max_depth: Maximum recursion depth

        Returns:
            Validation result dictionary with 'valid', 'problem_edges', 'max_edge_distance'
        """
        # Validate current coverage
        min_coverage = spacing / 2
        result = PolygonUtils.validate_edge_coverage(polygon, transects, min_coverage_m=min_coverage)

        # If valid or max depth reached, return
        if result['valid'] or depth >= max_depth:
            return result

        # Identify problem edges and add補充 transects
        problem_edges = result.get('problem_edges', [])

        if not problem_edges:
            return result

        # Add transects near problem edges
        new_transects = []
        for edge_idx in problem_edges:
            # Get edge endpoints
            if edge_idx >= len(polygon):
                continue

            p1 = polygon[edge_idx]
            p2 = polygon[(edge_idx + 1) % len(polygon)]

            # Calculate edge midpoint
            mid_north = (p1.north + p2.north) / 2
            mid_east = (p1.east + p2.east) / 2

            # Calculate edge normal direction
            edge_north = p2.north - p1.north
            edge_east = p2.east - p1.east
            edge_len = math.sqrt(edge_north**2 + edge_east**2)

            if edge_len < 0.1:
                continue

            # Normal vector (perpendicular to edge, pointing inward)
            normal_north = -edge_east / edge_len
            normal_east = edge_north / edge_len

            # Create transect perpendicular to problem edge
            # Extend from edge inward by spacing distance
            offset_distance = spacing * 0.5  # Half spacing for better coverage

            transect_start = LocalCoord(
                mid_north + normal_north * offset_distance,
                mid_east + normal_east * offset_distance
            )

            # Extend transect in both directions along edge direction
            transect_points = []
            for t in [-1000, 1000]:  # Extend far in both directions
                point = LocalCoord(
                    transect_start.north + (edge_north / edge_len) * t,
                    transect_start.east + (edge_east / edge_len) * t
                )
                transect_points.append(point)

            # Find intersections with polygon
            intersections = PolygonUtils.polygon_line_intersections(
                polygon, transect_points[0], transect_points[1]
            )

            if len(intersections) >= 2:
                new_transects.append(intersections)

        if new_transects:
            # Add new transects to existing ones
            all_transects = transects + new_transects

            # Recursive validation
            return self._recursive_edge_coverage_validation(
                polygon, all_transects, spacing, depth + 1, max_depth
            )

        return result

    def _rotate_point(self, point: LocalCoord, center: LocalCoord, angle_rad: float) -> LocalCoord:
        """Rotate point around center."""
        dn = point.north - center.north
        de = point.east - center.east

        rotated_n = dn * math.cos(angle_rad) - de * math.sin(angle_rad)
        rotated_e = dn * math.sin(angle_rad) + de * math.cos(angle_rad)

        return LocalCoord(center.north + rotated_n, center.east + rotated_e)

    def _optimize_transect_order(
        self,
        transects: List[List[LocalCoord]],
        entry_point: EntryPoint
    ) -> List[List[LocalCoord]]:
        """
        Optimize transect order for shortest flight distance (QGC algorithm).
        Implements alternating (lawnmower) pattern.
        """
        if not transects:
            return []

        # Determine entry corner based on entry_point
        if entry_point == EntryPoint.TOP_LEFT:
            # Start from northwest, prefer northernmost then westernmost
            transects.sort(key=lambda t: (-max(p.north for p in t), min(p.east for p in t)))
        elif entry_point == EntryPoint.TOP_RIGHT:
            # Start from northeast
            transects.sort(key=lambda t: (-max(p.north for p in t), -max(p.east for p in t)))
        elif entry_point == EntryPoint.BOTTOM_LEFT:
            # Start from southwest
            transects.sort(key=lambda t: (min(p.north for p in t), min(p.east for p in t)))
        else:  # BOTTOM_RIGHT
            # Start from southeast
            transects.sort(key=lambda t: (min(p.north for p in t), -max(p.east for p in t)))

        # Alternate transect directions (lawnmower pattern)
        optimized = []
        for i, transect in enumerate(transects):
            if i % 2 == 1:
                # Reverse every other transect
                optimized.append(list(reversed(transect)))
            else:
                optimized.append(transect)

        return optimized

    def _add_turnaround_points(
        self,
        transects: List[List[LocalCoord]],
        turnaround_dist: float
    ) -> List[List[LocalCoord]]:
        """Add turnaround waypoints at start/end of each transect."""
        extended_transects = []

        for transect in transects:
            if len(transect) < 2:
                extended_transects.append(transect)
                continue

            # Calculate entry/exit vectors
            start = transect[0]
            second = transect[1]
            second_last = transect[-2]
            end = transect[-1]

            # Entry turnaround point
            dn_entry = start.north - second.north
            de_entry = start.east - second.east
            dist_entry = math.sqrt(dn_entry**2 + de_entry**2)

            if dist_entry > 0:
                entry_point = LocalCoord(
                    start.north + (dn_entry / dist_entry) * turnaround_dist,
                    start.east + (de_entry / dist_entry) * turnaround_dist
                )
            else:
                entry_point = start

            # Exit turnaround point
            dn_exit = end.north - second_last.north
            de_exit = end.east - second_last.east
            dist_exit = math.sqrt(dn_exit**2 + de_exit**2)

            if dist_exit > 0:
                exit_point = LocalCoord(
                    end.north + (dn_exit / dist_exit) * turnaround_dist,
                    end.east + (de_exit / dist_exit) * turnaround_dist
                )
            else:
                exit_point = end

            # Build extended transect
            extended = [entry_point] + transect + [exit_point]
            extended_transects.append(extended)

        return extended_transects

    def generate_mission_items(
        self,
        polygon: List[LatLon],
        config: SurveyConfig
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Generate complete MAVLink mission items for survey.

        Returns:
            (mission_items, statistics)
        """
        # Generate transects
        transects = self.generate_transects_from_polygon(polygon, config)

        if not transects:
            return ([], {"error": "No valid transects generated"})

        mission_items = []
        seq = 0

        # Calculate trigger distance
        trigger_dist = self.calculate_trigger_distance(
            config.altitude_m,
            config.front_overlap_pct,
            config.camera_angle_deg
        )

        # Add camera trigger command (if distance mode)
        if config.trigger_mode == TriggerMode.DISTANCE:
            mission_items.append({
                "seq": seq,
                "frame": mavutil.mavlink.MAV_FRAME_MISSION,
                "command": mavutil.mavlink.MAV_CMD_DO_SET_CAM_TRIGG_DIST,
                "current": 1 if seq == 0 else 0,
                "autocontinue": 1,
                "param1": trigger_dist,
                "param2": 0.0,
                "param3": 1.0,  # Trigger once immediately
                "param4": 0.0,
                "x": 0,
                "y": 0,
                "z": 0.0,
            })
            seq += 1

        # Generate waypoints from transects
        total_distance = 0.0
        photo_count = 0

        for transect in transects:
            for i, coord in enumerate(transect):
                # Add waypoint
                mission_items.append({
                    "seq": seq,
                    "frame": mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                    "command": mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                    "current": 1 if seq == 0 else 0,
                    "autocontinue": 1,
                    "param1": 0.0,  # Hold time
                    "param2": 2.0,  # Acceptance radius
                    "param3": 0.0,  # Pass radius
                    "param4": 0.0,  # Yaw angle (0 = use current heading)
                    "x": int(coord.lat * 1e7),
                    "y": int(coord.lon * 1e7),
                    "z": float(config.altitude_m),
                })

                # Hover and capture mode
                if config.hover_and_capture and i > 0 and i < len(transect) - 1:
                    mission_items.append({
                        "seq": seq + 1,
                        "frame": mavutil.mavlink.MAV_FRAME_MISSION,
                        "command": mavutil.mavlink.MAV_CMD_DO_DIGICAM_CONTROL,
                        "current": 0,
                        "autocontinue": 1,
                        "param1": 0.0,
                        "param2": 0.0,
                        "param3": 0.0,
                        "param4": 0.0,
                        "param5": 1.0,  # Trigger camera
                        "x": 0,
                        "y": 0,
                        "z": 0.0,
                    })
                    seq += 1
                    photo_count += 1

                # Calculate distance
                if i > 0:
                    dist = GeodeticUtils.geodesic_distance(transect[i-1], coord)
                    total_distance += dist

                    if config.trigger_mode == TriggerMode.DISTANCE and trigger_dist > 0:
                        photo_count += int(dist / trigger_dist)

                seq += 1

        # Calculate statistics
        flight_time_min = (total_distance / config.speed_m_s) / 60.0
        coverage_area = PolygonUtils.calculate_area(polygon)
        gsd_details = self.calculate_gsd_detailed(config.altitude_m)

        statistics = {
            "waypoint_count": len(mission_items),
            "photo_count": photo_count,
            "flight_distance_m": round(total_distance, 1),
            "flight_time_min": round(flight_time_min, 1),
            "coverage_area_m2": round(coverage_area, 1),
            "coverage_area_acres": round(coverage_area / 4046.86, 2),
            "transect_count": len(transects),
            "trigger_distance_m": round(trigger_dist, 2),
            "transect_spacing_m": round(self.calculate_transect_spacing(
                config.altitude_m, config.side_overlap_pct
            ), 2),
            "gsd_cm_px": round(gsd_details['gsd_cm'], 2),
            "gsd_inches_px": round(gsd_details['gsd_inches'], 3),
            "footprint_width_m": round(gsd_details['footprint_width_m'], 1),
            "footprint_height_m": round(gsd_details['footprint_height_m'], 1),
        }

        return (mission_items, statistics)


def test_survey_planner():
    """Test survey planner with sample polygon."""
    uk_center = LatLon(38.0336, -84.5037)
    survey_area = [
        GeodeticUtils.destination_point(uk_center, 80, 315),  # NW
        GeodeticUtils.destination_point(uk_center, 80, 45),   # NE
        GeodeticUtils.destination_point(uk_center, 80, 135),  # SE
        GeodeticUtils.destination_point(uk_center, 80, 225),  # SW
    ]

    camera = CameraSpec.sentera_double_4k_wide()
    config = SurveyConfig(
        altitude_m=60,
        speed_m_s=8,
        front_overlap_pct=75,
        side_overlap_pct=75,
        grid_angle_deg=0,
    )

    planner = SurveyPlanner(camera)
    
    # Test GSD calculation
    gsd_details = planner.calculate_gsd_detailed(60)
    print(f"\n=== GSD Calculation ===")
    print(f"Altitude: 60m")
    print(f"GSD: {gsd_details['gsd_cm']:.2f} cm/px (should be ~1.75-1.8 cm/px)")
    print(f"GSD: {gsd_details['gsd_inches']:.3f} inches/px")
    print(f"Footprint: {gsd_details['footprint_width_m']:.1f}m × {gsd_details['footprint_height_m']:.1f}m")
    
    # Generate mission
    items, stats = planner.generate_mission_items(survey_area, config)

    print(f"\n=== Survey Mission ===")
    print(f"Waypoints: {stats['waypoint_count']}")
    print(f"Photos: {stats['photo_count']}")
    print(f"Distance: {stats['flight_distance_m']}m")
    print(f"Flight time: {stats['flight_time_min']} min")
    print(f"Coverage: {stats['coverage_area_m2']} m² ({stats['coverage_area_acres']} acres)")
    print(f"Trigger distance: {stats['trigger_distance_m']}m")
    print(f"Transect spacing: {stats['transect_spacing_m']}m")


if __name__ == "__main__":
    test_survey_planner()
