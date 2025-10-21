# SKEYE SITL Testing Guide for Windows

**Software In The Loop (SITL)** testing guide for the SKEYE Flight System on Windows - no WSL or Linux required.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Windows SITL Options](#windows-sitl-options)
3. [Method 1: Mission Planner Built-in Simulator (Recommended)](#method-1-mission-planner-built-in-simulator-recommended)
4. [Method 2: MAVProxy with Mission Planner](#method-2-mavproxy-with-mission-planner)
5. [Connecting SKEYE GCS to SITL](#connecting-skeye-gcs-to-sitl)
6. [Testing Workflows](#testing-workflows)
7. [Switching Between SITL and Real Hardware](#switching-between-sitl-and-real-hardware)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### SKEYE System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    SKEYE Flight System                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐          ┌──────────────────┐        │
│  │  Flutter UI      │◄────────►│  Python Backend  │        │
│  │  (Windows App)   │          │  (run_gcs.py)    │        │
│  │                  │          │                  │        │
│  │  - Telemetry     │  WebSocket  - MAVLink Core  │        │
│  │  - Survey Plan   │  Port 8765  - Survey Plan   │        │
│  │  - Controls      │          │  - Commands      │        │
│  └──────────────────┘          └────────┬─────────┘        │
│                                         │                   │
│                              MAVLink over Serial/UDP/TCP    │
└─────────────────────────────────────────┼───────────────────┘
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    │                                           │
         ┌──────────▼──────────┐               ┌───────────────▼───────────┐
         │  REAL HARDWARE      │               │  SITL SIMULATOR           │
         │  - Pixhawk 6X       │               │  - Mission Planner        │
         │  - Serial (COM4)    │               │  - MAVProxy (optional)    │
         │  - 57600 baud       │               │  - UDP/TCP ports          │
         └─────────────────────┘               └───────────────────────────┘
```

### Current SKEYE Connection Configuration

From [gcs_core.py](../src/flight-system/v2/gcs_core.py:28-41):
- **Default Serial**: COM4 (Windows), /dev/ttyUSB0 (Linux)
- **Default Baud**: 57600 (MAVLink 2 - Pixhawk TELEM1)
- **Auto-reconnect**: Enabled
- **Connection type**: Serial via pymavlink

From [run_gcs.py](../src/flight-system/v2/run_gcs.py:380-385):
- **WebSocket Host**: 0.0.0.0 (localhost)
- **WebSocket Port**: 8765
- **Environment Variables**:
  - `GCS_SERIAL`: Serial device path (e.g., COM4, udp:127.0.0.1:14550)
  - `GCS_BAUD`: Baud rate (default 57600)
  - `GCS_WS_HOST`: WebSocket host (default 0.0.0.0)
  - `GCS_WS_PORT`: WebSocket port (default 8765)

---

## Windows SITL Options

### Option Comparison

| Method | Difficulty | Setup Time | Features | Recommended For |
|--------|-----------|------------|----------|-----------------|
| **Mission Planner Simulator** | Easy | 5 min | Full copter simulation, built-in, GUI-based | Quick testing, beginners |
| **MAVProxy with Mission Planner** | Medium | 10 min | Command-line monitoring, flexible routing | Advanced testing, debugging |
| **Cygwin Native** | Hard | 30+ min | Full ArduPilot build | Development (NOT recommended) |
| **WSL2** | Medium | 20 min | Full Linux SITL | Development (overkill for testing) |

**For SKEYE testing, we recommend Method 1.**

---

## Method 1: Mission Planner Built-in Simulator (Recommended)

### Simplest option for Windows - no additional software needed beyond Mission Planner.

### Step 1: Install Mission Planner

1. Download Mission Planner: https://ardupilot.org/planner/docs/mission-planner-installation.html
2. Install Mission Planner (latest version recommended)
3. Launch Mission Planner

### Step 2: Start the Simulator

1. In Mission Planner, go to **Simulation** tab (top menu)
2. Select vehicle type: **Multirotor** (for quadcopter)
3. Select model: **QuadCopter** or **X**
4. Click **"Start Simulation"** or **"Simulate"**
5. Wait for the simulator to start (you'll see "Ardupilot on TCP" message)

### Step 3: Note Connection Details

Mission Planner SITL creates these endpoints:

- **TCP Port 5760**: Main SITL connection (localhost)
- **UDP Port 14550**: MAVProxy output (if using MAVProxy bridge)
- **UDP Port 14551**: Additional GCS connection

### Step 4: Connect Your SKEYE GCS

Since SKEYE currently uses **serial connections**, you have two options:

#### Option A: Modify SKEYE to use TCP/UDP (Recommended)

See [Connecting SKEYE GCS to SITL](#connecting-skeye-gcs-to-sitl) section below.

#### Option B: Use com0com Virtual Serial Port Pair

1. Install com0com: https://sourceforge.net/projects/com0com/
2. Create virtual COM port pair (e.g., COM10 ↔ COM11)
3. Use MAVProxy to bridge TCP → Serial:
   ```bash
   mavproxy.py --master=tcp:127.0.0.1:5760 --out=COM10
   ```
4. Connect SKEYE to COM11

### Step 5: Verify Connection

In Mission Planner:
- You should see telemetry updating (altitude, GPS, battery)
- Map should show vehicle location
- HUD should show attitude

---

## Method 2: MAVProxy with Mission Planner

### Advanced option using MAVProxy for monitoring and debugging.

### Step 1: Install MAVProxy

```bash
# Install MAVProxy
pip install MAVProxy

# Verify installation
mavproxy.py --help
```

### Step 2: Start Mission Planner SITL

Follow the same steps as Method 1:
1. Launch Mission Planner
2. Go to **Simulation** tab
3. Select **Multirotor** vehicle type
4. Click **Start Simulation**
5. Wait for "Ardupilot on TCP" message

Mission Planner SITL will listen on **TCP port 5760**.

### Step 3: Start MAVProxy (Optional for Monitoring)

MAVProxy provides a command-line console for monitoring and debugging:

```bash
# Connect to Mission Planner SITL and output to UDP 14550
mavproxy.py --master=tcp:127.0.0.1:5760 --out=udp:127.0.0.1:14550

# Or connect directly for console-only monitoring
mavproxy.py --master=tcp:127.0.0.1:5760
```

**MAVProxy Features:**
- Real-time telemetry monitoring
- Command-line control
- Multiple GCS connections
- Message logging and analysis

### Step 4: Connect SKEYE GCS

**Option A: Direct TCP connection (recommended):**
```bash
set GCS_SERIAL=tcp:127.0.0.1:5760
python src/flight-system/v2/run_gcs.py
```

**Option B: Via MAVProxy UDP bridge:**
```bash
set GCS_SERIAL=udp:127.0.0.1:14550
python src/flight-system/v2/run_gcs.py
```

---

## Connecting SKEYE GCS to SITL

### Current SKEYE Connection Code

[gcs_core.py:28-41](../src/flight-system/v2/gcs_core.py#L28-L41):
```python
class MavSerialCore:
    def __init__(
        self,
        serial_dev: str = "COM4",  # Default serial port
        baud: int = 57600,
        heartbeat_timeout: float = 5.0,
        log_level: int = logging.INFO,
    ):
        # ...
        self.m: mavutil.mavfile = mavutil.mavlink_connection(serial_dev, baud=baud, autoreconnect=True)
```

### Option 1: Use Environment Variables (No Code Changes)

**pymavlink** already supports TCP and UDP connection strings!

```bash
# For TCP connection (Mission Planner simulator)
set GCS_SERIAL=tcp:127.0.0.1:5760
set GCS_BAUD=57600
python src/flight-system/v2/run_gcs.py

# For UDP connection (MAVProxy output)
set GCS_SERIAL=udp:127.0.0.1:14550
set GCS_BAUD=57600
python src/flight-system/v2/run_gcs.py

# For UDP input (listening mode)
set GCS_SERIAL=udpin:0.0.0.0:14550
python src/flight-system/v2/run_gcs.py
```

**This works because `mavutil.mavlink_connection()` accepts:**
- Serial: `COM4` or `/dev/ttyUSB0`
- TCP: `tcp:127.0.0.1:5760`
- UDP out: `udp:127.0.0.1:14550`
- UDP in: `udpin:0.0.0.0:14550`

### Option 2: Create SITL Connection Helper Script

Create `run_gcs_sitl.py` in `src/flight-system/v2/`:

```python
#!/usr/bin/env python3
"""
SKEYE GCS - SITL Testing Mode

Launches GCS with SITL connection (TCP/UDP instead of serial).
"""

import os
import sys

# SITL connection presets
SITL_PRESETS = {
    "mission_planner": "tcp:127.0.0.1:5760",
    "mavproxy_udp": "udp:127.0.0.1:14550",
    "mavproxy_tcp": "tcp:127.0.0.1:5760",
}

if __name__ == "__main__":
    # Select SITL preset
    preset = sys.argv[1] if len(sys.argv) > 1 else "mission_planner"

    if preset not in SITL_PRESETS:
        print(f"Unknown preset: {preset}")
        print(f"Available presets: {list(SITL_PRESETS.keys())}")
        sys.exit(1)

    # Set environment variables
    os.environ["GCS_SERIAL"] = SITL_PRESETS[preset]
    os.environ["GCS_BAUD"] = "57600"

    print(f"Starting SKEYE GCS in SITL mode...")
    print(f"Preset: {preset}")
    print(f"Connection: {SITL_PRESETS[preset]}")
    print("-" * 60)

    # Import and run the main GCS
    from run_gcs import main
    import asyncio
    asyncio.run(main())
```

**Usage:**
```bash
# Connect to Mission Planner simulator
python run_gcs_sitl.py mission_planner

# Connect to MAVProxy UDP output
python run_gcs_sitl.py mavproxy_udp

# Connect to MAVProxy TCP
python run_gcs_sitl.py mavproxy_tcp
```

### Option 3: Add Connection Mode Selector to run_gcs.py

Modify [run_gcs.py](../src/flight-system/v2/run_gcs.py) to add connection mode detection:

```python
async def main():
    # Get connection mode from environment
    connection_mode = os.environ.get("GCS_MODE", "auto")  # auto, serial, sitl_tcp, sitl_udp

    if connection_mode == "sitl_tcp":
        serial_dev = "tcp:127.0.0.1:5760"
        baud = 57600
    elif connection_mode == "sitl_udp":
        serial_dev = "udp:127.0.0.1:14550"
        baud = 57600
    else:
        # Original auto-detect behavior
        serial_dev = os.environ.get("GCS_SERIAL", None)
        baud = int(os.environ.get("GCS_BAUD", "57600"))
        # ... rest of auto-detect code
```

**Usage:**
```bash
set GCS_MODE=sitl_tcp
python run_gcs.py
```

---

## Testing Workflows

### Basic SITL Testing Workflow

1. **Start SITL Simulator**
   ```bash
   # Mission Planner (GUI)
   # Launch Mission Planner → Simulation → Start Simulation
   ```

2. **Start SKEYE Backend**
   ```bash
   cd src/flight-system/v2
   set GCS_SERIAL=tcp:127.0.0.1:5760
   python run_gcs.py
   ```

   You should see:
   ```
   INFO:MavSerialCore:Opening MAVLink over serial tcp:127.0.0.1:5760 @ 57600 ...
   INFO:MavSerialCore:Connected: sys=1, comp=1, mode=STABILIZE
   ```

3. **Start Flutter UI**
   ```bash
   cd src/flight-system/v2
   flutter run -d windows
   ```

4. **Test Basic Functions**
   - Check telemetry display (GPS, altitude, battery)
   - Test mode changes (STABILIZE → GUIDED → LOITER)
   - Test arming/disarming
   - Test GOTO commands
   - Test RTL

### Survey Planning Test Workflow

1. **Start SITL** (as above)

2. **Create Test Survey Area**
   - Use Flutter UI to draw polygon around UK Campus
   - Set altitude: 50m
   - Set camera: Sentera Double 4K Wide
   - Set overlaps: 75% front, 75% side

3. **Generate Survey Mission**
   - Click "Generate Survey"
   - Verify transect lines appear
   - Check mission statistics

4. **Upload to SITL**
   - Click "Upload Mission"
   - Verify mission uploaded successfully

5. **Run Mission in SITL**
   - Arm the vehicle
   - Set mode to AUTO
   - Watch vehicle follow survey pattern
   - Monitor in Mission Planner or QGroundControl

### Camera Trigger Testing

1. **Test distance-based triggering**:
   ```python
   # In SKEYE or via WebSocket
   {"cmd": "mission_upload", "items": [...]}  # Include DO_SET_CAM_TRIGG_DIST commands
   ```

2. **Monitor SITL output** for camera trigger events

3. **Verify trigger distance** matches calculated GSD requirements

---

## Switching Between SITL and Real Hardware

### Quick Switch Methods

#### Method 1: Environment Variables (Cleanest)

**For SITL:**
```bash
set GCS_SERIAL=tcp:127.0.0.1:5760
python run_gcs.py
```

**For Real Hardware:**
```bash
set GCS_SERIAL=COM4
python run_gcs.py
```

Or use auto-detect (no environment variable).

#### Method 2: Create Batch Scripts

Create `start_gcs_sitl.bat`:
```batch
@echo off
echo Starting SKEYE GCS in SITL mode...
set GCS_SERIAL=tcp:127.0.0.1:5760
set GCS_BAUD=57600
python src\flight-system\v2\run_gcs.py
```

Create `start_gcs_hardware.bat`:
```batch
@echo off
echo Starting SKEYE GCS in Hardware mode...
set GCS_SERIAL=COM4
set GCS_BAUD=57600
python src\flight-system\v2\run_gcs.py
```

#### Method 3: Add Command-Line Arguments

Modify [run_gcs.py](../src/flight-system/v2/run_gcs.py) to accept arguments:

```python
import argparse

async def main():
    parser = argparse.ArgumentParser(description="SKEYE GCS Server")
    parser.add_argument("--connection", default="auto", choices=["auto", "sitl", "serial"],
                        help="Connection mode: auto (detect), sitl (TCP), serial (COM port)")
    parser.add_argument("--port", default=None, help="Serial port or connection string")
    parser.add_argument("--baud", type=int, default=57600, help="Baud rate")
    args = parser.parse_args()

    if args.connection == "sitl":
        serial_dev = args.port or "tcp:127.0.0.1:5760"
    elif args.connection == "serial":
        serial_dev = args.port or "COM4"
    else:
        # Auto-detect
        serial_dev = auto_detect_serial_device()

    # ... rest of code
```

**Usage:**
```bash
# SITL mode
python run_gcs.py --connection sitl

# Serial mode with specific port
python run_gcs.py --connection serial --port COM4

# Auto-detect
python run_gcs.py --connection auto
```

---

## Troubleshooting

### Issue: SITL won't start

**Symptoms**: Mission Planner simulator fails to start or crashes

**Solutions**:
1. Check Mission Planner version (update to latest)
2. Restart Mission Planner
3. Check firewall settings (allow TCP 5760, UDP 14550)
4. Verify .NET Framework is installed (required for Mission Planner)

### Issue: SKEYE can't connect to SITL

**Symptoms**: "No heartbeat received" error

**Solutions**:
1. Verify SITL is running:
   ```bash
   netstat -an | findstr "5760"
   # Should show: TCP    127.0.0.1:5760    LISTENING
   ```

2. Check connection string:
   ```bash
   # TCP requires tcp: prefix
   set GCS_SERIAL=tcp:127.0.0.1:5760  # ✓ Correct
   set GCS_SERIAL=127.0.0.1:5760      # ✗ Wrong
   ```

3. Test with MAVProxy first:
   ```bash
   mavproxy.py --master=tcp:127.0.0.1:5760
   # Should see: Received 123 messages
   ```

4. Enable verbose logging in SKEYE:
   ```python
   # In gcs_core.py __init__
   log_level: int = logging.DEBUG  # Change from INFO to DEBUG
   ```

### Issue: Connection works but no telemetry

**Symptoms**: Connected but no position/attitude data

**Solutions**:
1. Check SITL GPS lock:
   - In Mission Planner: GPS status should be "3D Fix"
   - Wait 10-20 seconds after SITL start for GPS initialization

2. Verify MAVLink message types:
   ```python
   # In run_gcs.py, add debug logging
   log.debug(f"Received: {msg['type']}")
   ```

3. Check RELAY_TYPES in [gcs_core.py](../src/flight-system/v2/gcs_core.py:10-21)

### Issue: Mission upload fails

**Symptoms**: Mission items don't upload to SITL

**Solutions**:
1. Check mission item format (must use MISSION_ITEM_INT)
2. Verify target_system and target_component are set
3. Test with simple mission first (just 2-3 waypoints)
4. Enable mission upload logging:
   ```python
   # In gcs_core.py mission_upload_begin
   self.log.debug(f"Uploading {len(items)} mission items")
   ```

### Issue: Port already in use

**Symptoms**: "Address already in use" error on port 8765

**Solutions**:
```bash
# Find process using port 8765
netstat -ano | findstr "8765"

# Kill process by PID
taskkill /F /PID <PID>

# Or use different port
set GCS_WS_PORT=8766
```

### Issue: Virtual COM ports not working (com0com)

**Symptoms**: Can't connect via virtual COM port pair

**Solutions**:
1. Check com0com installation: Open "Setup Command Prompt" as Administrator
2. List ports: `list`
3. Verify port pair exists
4. Use signed driver version of com0com for Windows 10/11
5. Consider using TCP/UDP directly instead (easier)

---

## Testing Checklist

### Pre-Flight SITL Tests
- [ ] SITL starts without errors
- [ ] SKEYE backend connects to SITL
- [ ] Flutter UI shows telemetry
- [ ] GPS shows 3D fix
- [ ] Battery shows ~100%
- [ ] Mode changes work (STABILIZE, GUIDED, LOITER)
- [ ] Arm/Disarm works
- [ ] Heartbeat maintained (no timeouts)

### Mission Planning Tests
- [ ] Can draw polygon on map
- [ ] Survey generation succeeds
- [ ] Transect lines display correctly
- [ ] Mission statistics calculated
- [ ] GSD calculation correct
- [ ] Trigger distance calculated
- [ ] Mission upload succeeds
- [ ] Can start mission (mode AUTO)

### Flight Tests (SITL)
- [ ] Vehicle takes off in AUTO mode
- [ ] Follows survey pattern
- [ ] Camera triggers at waypoints
- [ ] Completes mission successfully
- [ ] RTL works
- [ ] Land works

### Real Hardware Tests
- [ ] Auto-detect finds Pixhawk
- [ ] Serial connection stable
- [ ] Telemetry matches SITL behavior
- [ ] All commands work as in SITL

---

## Next Steps

1. **Start with Mission Planner SITL** (easiest method)
2. **Test connection** with environment variable approach
3. **Run survey planning workflow** in SITL
4. **Validate mission execution** in simulator
5. **Switch to real hardware** and verify identical behavior

---

## Additional Resources

### ArduPilot Documentation
- [SITL Overview](https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html)
- [Mission Planner Simulation](https://ardupilot.org/planner/docs/mission-planner-simulation.html)
- [MAVLink Protocol](https://mavlink.io/en/)

### SKEYE Documentation
- [Main README](../src/flight-system/v2/README.md)
- [Complete Documentation](../src/flight-system/v2/docs/DOCUMENTATION.md)
- [Test Suite README](../test/README.md)

### Python MAVLink
- [pymavlink Documentation](https://mavlink.io/en/mavgen_python/)
- [MAVProxy Documentation](https://ardupilot.org/mavproxy/)

---

**Document Version**: 1.0
**Last Updated**: October 20, 2025
**Tested On**: Windows 10/11, Python 3.9+, ArduCopter SITL 4.x
