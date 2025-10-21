# QGroundControl-style Survey Mission Planner
# Implements advanced survey planning with camera triggers, grid optimization,
# and polygon-based area coverage

import math
from typing import List, Dict, Any, Tuple, Optional
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


class SurveyPlanner:
    """
    Advanced survey mission planner based on QGroundControl algorithms.
    Generates optimized grid patterns for aerial photography.
    """

    def __init__(self, camera: CameraSpec):
        self.camera = camera

    def calculate_gsd(self, altitude_m: float, camera_angle_deg: float = 90.0) -> float:
        """
        Calculate Ground Sample Distance (GSD) in meters per pixel.

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

        gsd = (
            (self.camera.sensor_width_mm * altitude_m * angle_factor) /
            (focal_length * self.camera.image_width_px)
        )

        return gsd / 1000.0  # Convert mm to meters

    def calculate_trigger_distance(
        self,
        altitude_m: float,
        front_overlap_pct: float,
        camera_angle_deg: float = 90.0
    ) -> float:
        """
        Calculate camera trigger distance for desired overlap.

        Args:
            altitude_m: Flight altitude
            front_overlap_pct: Front overlap percentage (0-100)
            camera_angle_deg: Camera angle

        Returns:
            Trigger distance in meters
        """
        gsd = self.calculate_gsd(altitude_m, camera_angle_deg)
        image_footprint_length = gsd * self.camera.image_height_px
        overlap_fraction = front_overlap_pct / 100.0

        # Distance between photo centers
        trigger_dist = image_footprint_length * (1.0 - overlap_fraction)

        return max(trigger_dist, 1)  # Minimum 10cm

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
        gsd = self.calculate_gsd(altitude_m, camera_angle_deg)
        image_footprint_width = gsd * self.camera.image_width_px
        overlap_fraction = side_overlap_pct / 100.0

        spacing = image_footprint_width * (1.0 - overlap_fraction)

        return max(spacing, 0.1)  # Minimum 10cm

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
            # Primarily North-South lines
            survey_width = max_east - min_east
            num_transects = int(survey_width / spacing) + 2
            baseline_north = (max_north + min_north) / 2

            for i in range(num_transects):
                offset = (i - num_transects / 2) * spacing

                # Line perpendicular to grid angle
                line_start = LocalCoord(
                    baseline_north - 1000,  # Extend beyond polygon
                    min_east + offset
                )
                line_end = LocalCoord(
                    baseline_north + 1000,
                    min_east + offset
                )

                # Rotate line by grid angle
                if config.grid_angle_deg != 0:
                    line_start = self._rotate_point(line_start, LocalCoord(baseline_north, min_east + offset), angle_rad)
                    line_end = self._rotate_point(line_end, LocalCoord(baseline_north, min_east + offset), angle_rad)

                # Find intersections with polygon
                intersections = PolygonUtils.polygon_line_intersections(
                    local_polygon, line_start, line_end
                )

                if len(intersections) >= 2:
                    # Sort by distance along line
                    intersections.sort(key=lambda p: p.north)
                    transects_local.append(intersections)

        else:
            # Primarily East-West lines
            survey_height = max_north - min_north
            num_transects = int(survey_height / spacing) + 2
            baseline_east = (max_east + min_east) / 2

            for i in range(num_transects):
                offset = (i - num_transects / 2) * spacing

                line_start = LocalCoord(
                    min_north + offset,
                    baseline_east - 1000
                )
                line_end = LocalCoord(
                    min_north + offset,
                    baseline_east + 1000
                )

                # Rotate if needed
                if config.grid_angle_deg != 0:
                    line_start = self._rotate_point(line_start, LocalCoord(min_north + offset, baseline_east), angle_rad)
                    line_end = self._rotate_point(line_end, LocalCoord(min_north + offset, baseline_east), angle_rad)

                intersections = PolygonUtils.polygon_line_intersections(
                    local_polygon, line_start, line_end
                )

                if len(intersections) >= 2:
                    intersections.sort(key=lambda p: p.east)
                    transects_local.append(intersections)

        # Optimize transect order based on entry point
        transects_local = self._optimize_transect_order(transects_local, config.entry_point)

        # Add turnaround points
        transects_local = self._add_turnaround_points(transects_local, config.turnaround_dist_m)

        # Convert back to geographic coordinates
        transects_geo = []
        for transect in transects_local:
            transect_geo = GeodeticUtils.to_geographic_coords(transect, centroid)
            transects_geo.append(transect_geo)

        return transects_geo

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
                    "param4": float("nan"),  # Yaw
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
                    dist = GeodeticUtils.haversine_distance(transect[i-1], coord)
                    total_distance += dist

                    # Estimate photo count for distance mode
                    if config.trigger_mode == TriggerMode.DISTANCE and trigger_dist > 0:
                        photo_count += int(dist / trigger_dist)

                seq += 1

        # Calculate statistics
        flight_time_min = (total_distance / config.speed_m_s) / 60.0
        coverage_area = PolygonUtils.calculate_area(polygon)

        statistics = {
            "waypoint_count": len(mission_items),
            "photo_count": photo_count,
            "flight_distance_m": round(total_distance, 1),
            "flight_time_min": round(flight_time_min, 1),
            "coverage_area_m2": round(coverage_area, 1),
            "transect_count": len(transects),
            "trigger_distance_m": round(trigger_dist, 2),
            "gsd_cm_px": round(self.calculate_gsd(config.altitude_m) * 100, 2),
        }

        return (mission_items, statistics)


def test_survey_planner():
    """Test survey planner with sample polygon."""
    # Create survey area (100m x 100m square near UK campus)
    uk_center = LatLon(38.0336, -84.5037)
    survey_area = [
        GeodeticUtils.destination_point(uk_center, 80, 315),  # NW
        GeodeticUtils.destination_point(uk_center, 80, 45),   # NE
        GeodeticUtils.destination_point(uk_center, 80, 135),  # SE
        GeodeticUtils.destination_point(uk_center, 80, 225),  # SW
    ]

    # Configure survey
    camera = CameraSpec.sentera_double_4k_wide()
    config = SurveyConfig(
        altitude_m=80,
        speed_m_s=8,
        front_overlap_pct=75,
        side_overlap_pct=75,
        grid_angle_deg=0,
        entry_point=EntryPoint.TOP_LEFT,
        turnaround_dist_m=10,
    )

    # Generate mission
    planner = SurveyPlanner(camera)
    items, stats = planner.generate_mission_items(survey_area, config)

    print(f"\n=== Survey Mission Generated ===")
    print(f"Camera: {camera.name}")
    print(f"Altitude: {config.altitude_m}m")
    print(f"Waypoints: {stats['waypoint_count']}")
    print(f"Photos: {stats['photo_count']}")
    print(f"Distance: {stats['flight_distance_m']}m")
    print(f"Flight time: {stats['flight_time_min']} min")
    print(f"Coverage: {stats['coverage_area_m2']} m²")
    print(f"GSD: {stats['gsd_cm_px']} cm/px")
    print(f"Trigger distance: {stats['trigger_distance_m']}m")


if __name__ == "__main__":
    test_survey_planner()
