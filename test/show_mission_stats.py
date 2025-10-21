#!/usr/bin/env python3
"""
Display mission statistics including photo count for a sample survey.

This script generates a survey mission and displays all statistics including
the approximate number of photos that will be taken.

Usage:
    python test/show_mission_stats.py
"""

import sys
from pathlib import Path

# Add v2 directory to path
v2_path = Path(__file__).parent.parent / "src" / "flight-system" / "v2"
sys.path.insert(0, str(v2_path))

from survey_planner import SurveyPlanner, CameraSpec, SurveyConfig, TriggerMode
from geometry_utils import LatLon


def print_banner(text):
    """Print a formatted banner."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def format_stat(name, value, unit=""):
    """Format a statistic for display."""
    if isinstance(value, float):
        return f"  {name:<30} {value:>12.2f} {unit}"
    else:
        return f"  {name:<30} {value:>12} {unit}"


def main():
    # Create camera and planner
    camera = CameraSpec.sentera_double_4k_wide()
    planner = SurveyPlanner(camera)

    # Define survey area (small polygon ~100m x 100m)
    survey_polygon = [
        LatLon(38.0336, -84.5037),  # Southwest corner
        LatLon(38.0346, -84.5037),  # Northwest corner
        LatLon(38.0346, -84.5027),  # Northeast corner
        LatLon(38.0336, -84.5027),  # Southeast corner
    ]

    print_banner("SKEYE Survey Mission Statistics Calculator")

    # Test different configurations
    configs = [
        {
            "name": "Standard Survey (75% overlap)",
            "config": SurveyConfig(
                altitude_m=50.0,
                speed_m_s=5.0,
                front_overlap_pct=75.0,
                side_overlap_pct=75.0,
                grid_angle_deg=0.0,
                trigger_mode=TriggerMode.DISTANCE
            )
        },
        {
            "name": "High Overlap Survey (85% overlap)",
            "config": SurveyConfig(
                altitude_m=50.0,
                speed_m_s=5.0,
                front_overlap_pct=85.0,
                side_overlap_pct=85.0,
                grid_angle_deg=0.0,
                trigger_mode=TriggerMode.DISTANCE
            )
        },
        {
            "name": "Low Altitude (30m, 75% overlap)",
            "config": SurveyConfig(
                altitude_m=30.0,
                speed_m_s=5.0,
                front_overlap_pct=75.0,
                side_overlap_pct=75.0,
                grid_angle_deg=0.0,
                trigger_mode=TriggerMode.DISTANCE
            )
        },
        {
            "name": "High Altitude (90m, 75% overlap)",
            "config": SurveyConfig(
                altitude_m=90.0,
                speed_m_s=5.0,
                front_overlap_pct=75.0,
                side_overlap_pct=75.0,
                grid_angle_deg=0.0,
                trigger_mode=TriggerMode.DISTANCE
            )
        },
    ]

    for scenario in configs:
        print_banner(scenario["name"])
        config = scenario["config"]

        # Generate mission
        items, stats = planner.generate_mission_items(survey_polygon, config)

        # Display configuration
        print("\nCONFIGURATION:")
        print(format_stat("Altitude", config.altitude_m, "m"))
        print(format_stat("Speed", config.speed_m_s, "m/s"))
        print(format_stat("Front Overlap", config.front_overlap_pct, "%"))
        print(format_stat("Side Overlap", config.side_overlap_pct, "%"))
        print(format_stat("Grid Angle", config.grid_angle_deg, "deg"))
        print(format_stat("Camera", camera.name, ""))

        # Display mission statistics
        print("\nMISSION STATISTICS:")

        if "error" in stats:
            print(f"  ERROR: {stats['error']}")
            continue

        print(format_stat("Waypoint Count", stats.get("waypoint_count", 0), "waypoints"))
        print(format_stat(">>> PHOTO COUNT <<<", stats.get("photo_count", 0), "photos"))
        print(format_stat("Transect Count", stats.get("transect_count", 0), "lines"))
        print(format_stat("Flight Distance", stats.get("flight_distance_m", 0), "m"))
        print(format_stat("Flight Time", stats.get("flight_time_min", 0), "min"))
        print(format_stat("Coverage Area", stats.get("coverage_area_m2", 0), "m^2"))
        print(format_stat("GSD (Ground Sample Distance)", stats.get("gsd_cm_px", 0), "cm/px"))
        print(format_stat("Trigger Distance", stats.get("trigger_distance_m", 0), "m"))

        # Calculate efficiency metrics
        if stats.get("photo_count", 0) > 0 and stats.get("coverage_area_m2", 0) > 0:
            area_per_photo = stats["coverage_area_m2"] / stats["photo_count"]
            photos_per_min = stats["photo_count"] / stats["flight_time_min"] if stats["flight_time_min"] > 0 else 0

            print("\nEFFICIENCY METRICS:")
            print(format_stat("Area per Photo", area_per_photo, "m^2/photo"))
            print(format_stat("Photo Rate", photos_per_min, "photos/min"))

            # Estimate storage (assuming 5MB per photo for 4K images)
            storage_mb = stats["photo_count"] * 5
            storage_gb = storage_mb / 1024
            print(format_stat("Est. Storage (5MB/photo)", storage_gb, "GB"))

    # Summary
    print_banner("COMPARISON SUMMARY")
    print("\nKEY INSIGHTS:")
    print("  * Higher overlap = More photos needed")
    print("  * Lower altitude = Smaller trigger distance = More photos")
    print("  * Photo count directly affects:")
    print("    - Flight time")
    print("    - Storage requirements")
    print("    - Processing time")
    print("    - Image quality/coverage")

    print("\n" + "=" * 70)
    print("  Analysis complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
