#!/usr/bin/env python3
"""
SKEYE GCS - SITL Testing Mode

Launches GCS with SITL connection (TCP/UDP instead of serial).
Supports multiple SITL backends for easy Windows testing.

Usage:
    python run_gcs_sitl.py                    # Default: Mission Planner TCP
    python run_gcs_sitl.py mission_planner    # Mission Planner simulator
    python run_gcs_sitl.py mavproxy_udp       # MAVProxy UDP output
    python run_gcs_sitl.py custom <connection_string>  # Custom connection

Examples:
    python run_gcs_sitl.py mission_planner
    python run_gcs_sitl.py custom tcp:192.168.1.100:5760
    python run_gcs_sitl.py custom udp:127.0.0.1:14550
"""

import os
import sys
import asyncio

# SITL connection presets
SITL_PRESETS = {
    "mission_planner": {
        "connection": "tcp:127.0.0.1:5760",
        "description": "Mission Planner built-in simulator (TCP)",
        "instructions": [
            "1. Launch Mission Planner",
            "2. Go to Simulation tab",
            "3. Select 'Multirotor' vehicle type",
            "4. Click 'Start Simulation'",
            "5. Wait for 'Ardupilot on TCP' message",
        ]
    },
    "mavproxy_udp": {
        "connection": "udp:127.0.0.1:14550",
        "description": "MAVProxy UDP output (standard GCS port)",
        "instructions": [
            "1. Start Mission Planner SITL (or use sim_vehicle.py from ArduPilot)",
            "2. Start MAVProxy: mavproxy.py --master=tcp:127.0.0.1:5760 --out=udp:127.0.0.1:14550",
            "3. Run this script",
        ]
    },
    "mavproxy_tcp": {
        "connection": "tcp:127.0.0.1:5760",
        "description": "Direct TCP connection to SITL",
        "instructions": [
            "1. Start Mission Planner SITL simulator",
            "2. Run this script (MAVProxy optional for monitoring)",
        ]
    },
    "udpin": {
        "connection": "udpin:0.0.0.0:14550",
        "description": "UDP input (listening mode - GCS receives from SITL)",
        "instructions": [
            "1. Start SITL with UDP output to 14550",
            "2. Configure SITL to send to this IP:14550",
            "3. Run this script",
        ]
    }
}

# Default test locations
TEST_LOCATIONS = {
    "uk_campus": (38.0336, -84.5037, 584, 353),  # UK Campus, Lexington KY
    "sf_bay": (37.7749, -122.4194, 0, 0),        # San Francisco Bay
    "london": (51.5074, -0.1278, 0, 0),          # London, UK
}


def print_banner():
    """Print startup banner."""
    print("=" * 70)
    print("  SKEYE GCS - SITL Testing Mode")
    print("  Software In The Loop testing for Windows")
    print("=" * 70)
    print()


def print_preset_info(preset_name: str):
    """Print information about selected preset."""
    if preset_name not in SITL_PRESETS:
        print(f"ERROR: Unknown preset '{preset_name}'")
        print(f"Available presets: {', '.join(SITL_PRESETS.keys())}")
        sys.exit(1)

    preset = SITL_PRESETS[preset_name]
    print(f"Preset: {preset_name}")
    print(f"Description: {preset['description']}")
    print(f"Connection: {preset['connection']}")
    print()
    print("Setup Instructions:")
    for instruction in preset['instructions']:
        print(f"  {instruction}")
    print()


def print_available_presets():
    """Print all available presets."""
    print("Available SITL Presets:")
    print("-" * 70)
    for name, preset in SITL_PRESETS.items():
        print(f"  {name:20} - {preset['description']}")
    print("-" * 70)
    print()


def get_connection_string(args):
    """Get connection string from arguments."""
    if len(args) == 0:
        # Default to Mission Planner
        return "mission_planner", SITL_PRESETS["mission_planner"]["connection"]

    preset_name = args[0]

    if preset_name == "custom":
        if len(args) < 2:
            print("ERROR: 'custom' preset requires connection string")
            print("Usage: python run_gcs_sitl.py custom <connection_string>")
            print("Example: python run_gcs_sitl.py custom tcp:192.168.1.100:5760")
            sys.exit(1)
        return "custom", args[1]

    if preset_name == "help" or preset_name == "--help" or preset_name == "-h":
        print_banner()
        print_available_presets()
        print(__doc__)
        sys.exit(0)

    if preset_name not in SITL_PRESETS:
        print(f"ERROR: Unknown preset '{preset_name}'")
        print()
        print_available_presets()
        sys.exit(1)

    return preset_name, SITL_PRESETS[preset_name]["connection"]


def main():
    """Main entry point."""
    print_banner()

    # Parse arguments
    preset_name, connection_string = get_connection_string(sys.argv[1:])

    # Print preset info (unless custom)
    if preset_name != "custom":
        print_preset_info(preset_name)
    else:
        print(f"Custom connection: {connection_string}")
        print()

    # Set environment variables for run_gcs.py
    os.environ["GCS_SERIAL"] = connection_string
    os.environ["GCS_BAUD"] = "57600"  # Standard MAVLink baud (ignored for TCP/UDP)

    print("Starting SKEYE GCS Backend...")
    print(f"  Connection: {connection_string}")
    print(f"  WebSocket: ws://localhost:8765")
    print()
    print("Press Ctrl+C to stop")
    print("-" * 70)
    print()

    # Import and run the main GCS
    try:
        from run_gcs import main as gcs_main
        asyncio.run(gcs_main())
    except KeyboardInterrupt:
        print()
        print("Shutting down SKEYE GCS...")
        print()
    except ImportError as e:
        print(f"ERROR: Failed to import run_gcs.py: {e}")
        print("Make sure you're running this script from src/flight-system/v2/")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
