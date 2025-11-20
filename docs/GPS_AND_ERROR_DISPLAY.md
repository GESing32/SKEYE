# GPS Satellite Count and Error Display System

## Overview
Enhanced diagnostics and safety monitoring for SKEYE GCS with GPS satellite tracking and prominent error/warning display.

## Quick Summary

**Three-Layer Error/Warning System**:
1. **Status Bar** - GPS status with satellite count (always visible)
2. **Error Banner** - Shows most critical message below status bar (dismissible)
3. **Messages Button** - 🔔 Icon in app bar with badge - click to see full log (persistent)

## Features Added

### 1. GPS Satellite Count Display
**Location**: Status bar (top of screen)

**Display Format**:
- **3D Fix or better**: `GPS: 3D Fix (12 sats)` - **GREEN**
- **2D Fix**: `GPS: 2D Fix` - **ORANGE**
- **No Fix**: `GPS: No Fix` - **RED**
- **No Data**: `GPS: NO DATA` - **RED**

**Fix Types**:
- `No GPS` (0) - GPS hardware not detected
- `No Fix` (1) - GPS detected but no satellite lock
- `2D Fix` (2) - Latitude/longitude only (no altitude)
- `3D Fix` (3) - Full position fix ✓ **Required for flight**
- `DGPS` (4) - Differential GPS (enhanced accuracy)
- `RTK Float` (5) - RTK floating ambiguity
- `RTK Fixed` (6) - RTK fixed ambiguity (cm-level accuracy)

### 2. Error/Warning Banner
**Location**: Below status bar, above map

**Severity Levels**:
1. **CRITICAL** (Red, dark) - Flight safety risk
   - EKF failures during flight
   - Attitude estimation unavailable
   - Emergency messages from ArduPilot

2. **ERROR** (Red) - Operation failures
   - Command failures (ARM, mode change, etc.)
   - Mission upload errors
   - Communication errors

3. **WARNING** (Orange) - Issues requiring attention
   - GPS degraded to 2D fix
   - EKF using constant position mode
   - Pre-arm check failures

4. **INFO** (Blue) - Informational messages
   - System status updates

**Features**:
- Auto-prioritizes most severe message
- Shows "+N more" if multiple messages
- Click ✕ to dismiss all messages
- Auto-appears when new messages arrive

### 3. Messages Log Button
**Location**: App bar (top-right corner)

**Continuous Error/Warning Log**:
- 🔔 Bell icon (`notification_important`) with colored badge
- Badge shows message count (e.g., "5")
- Badge color matches highest severity:
  - **Dark Red** - Critical messages present
  - **Red** - Errors present
  - **Orange** - Warnings present
  - **Blue** - Info messages only
- Click to open full message history dialog

**Message Log Dialog**:
- Shows last **50 messages** in chronological order (newest first)
- Each message card displays:
  - Icon and severity color-coding
  - Full message text
  - Timestamp (e.g., "3s ago", "5m ago", "2h ago")
  - Severity label (CRITICAL, ERROR, WARNING, INFO)
- **Clear All** button to reset entire log
- Scrollable list for reviewing message history

**Why This Is Useful**:
- Review all errors that occurred during flight session
- Check message history after dismissing banner
- Monitor patterns (e.g., repeated GPS loss, intermittent EKF warnings)
- Take screenshots for troubleshooting/bug reports
- Always visible even when banner is dismissed
- Persistent log survives banner dismissals

### 4. Safety Monitoring

#### GPS Status
- Tracks satellite count in real-time
- Alerts when fix degrades from 3D → 2D
- Position marker only shows with valid GPS fix (not 0,0)

#### EKF (Extended Kalman Filter) Monitoring
- **Attitude estimate** - Critical for stabilization
- **Horizontal velocity** - Critical for position hold
- **Constant position mode** - Indicates poor GPS quality

#### ArduPilot Messages
- Pre-arm failure messages (e.g., "PreArm: GPS not healthy")
- Mode change failures
- Battery warnings
- Calibration errors

#### Command Acknowledgments
- Tracks success/failure of all commands
- Shows specific failure reasons:
  - "Temporarily rejected" - Try again
  - "Denied" - Not allowed in current state
  - "Unsupported" - Feature not available
  - "Failed" - Execution error

## Backend Changes

### Added Message Types (`gcs_core.py`)
```python
RELAY_TYPES = {
    ...
    "GPS_RAW_INT",      # Satellite count + fix type
    "STATUSTEXT",       # ArduPilot text messages
    "COMMAND_ACK",      # Command success/failure
    "EKF_STATUS_REPORT", # EKF health monitoring
}
```

## Common Scenarios

### Scenario 1: No Drone Icon Shows
**Status Bar**: `GPS: NO DATA` (red)
**Console**: No GPS messages
**Cause**: Backend not receiving GPS data
**Fix**: Check GPS connection to Pixhawk GPS1/GPS2 port

### Scenario 2: Drone Icon Missing (Hardware Mode)
**Status Bar**: `GPS: No Fix` (red)
**Console**: `⚠️ GPS Position: NO FIX (lat=0, lon=0)`
**Cause**: GPS doesn't have satellite lock
**Fix**:
1. Go outdoors with clear sky view
2. Wait 1-3 minutes for GPS lock
3. Watch satellite count increase: 0 → 4 → 8 → 12+
4. When status shows `3D Fix`, drone icon appears

### Scenario 3: Pre-Arm Check Failure
**Banner**: ⚠️ `PreArm: GPS not healthy` (warning)
**Fix**: Wait for GPS fix (3D, 6+ satellites recommended)

### Scenario 4: EKF Error During Flight
**Banner**: ⚠️ `EKF: Attitude estimate unavailable!` (critical)
**Action**: Land immediately - flight control compromised

### Scenario 5: Command Rejected
**Banner**: `Command failed: ARM/DISARM (Denied)` (error)
**Cause**: Pre-arm checks not passed
**Fix**: Check other messages for specific pre-arm failures

## Testing Checklist

### SITL Mode (Mission Planner)
- [x] GPS shows `3D Fix (10+ sats)` immediately
- [x] Drone icon visible on map
- [x] Position updates in status bar
- [x] No warning banners (unless intentional)

### Hardware Mode (Real Pixhawk)
- [x] GPS starts as `NO DATA` or `No Fix`
- [x] Satellite count increases: 0 → 4 → 8 → 12+
- [x] Status changes: `No Fix` → `2D Fix` → `3D Fix`
- [x] Drone icon appears when `3D Fix` acquired
- [x] Pre-arm failures show in banner
- [x] Mode change errors displayed
- [x] Battery warnings visible

## Tips

1. **Minimum GPS Requirements**:
   - **6+ satellites** for reliable 3D fix
   - **10+ satellites** recommended for flight
   - **RTK** for precision applications (survey, inspection)

2. **Indoor Testing**:
   - Use SITL mode - real GPS won't work indoors
   - Hardware GPS will show `No Fix` indefinitely

3. **GPS Lock Time**:
   - **Cold start**: 30-90 seconds (first power-on)
   - **Warm start**: 10-30 seconds (recent lock)
   - **Hot start**: 1-5 seconds (within minutes of last lock)

4. **Error Banner Management**:
   - Click ✕ to clear messages after reviewing
   - Messages auto-prioritize by severity
   - Only most important message shown at once

## Debugging

Enable verbose logging in Flutter DevTools console to see:
- `📍 GPS Position: lat=X, lon=Y, alt=Z` - Valid position updates
- `⚠️ GPS lost fix` - Position degraded to invalid
- `STATUSTEXT: [message]` - All ArduPilot messages (including info)
- `System message [severity]: [text]` - All system messages

## Related Files

- `lib/main.dart` - Flutter UI with GPS display and error banner
- `src/flight-system/v2/gcs_core.py` - Backend message relay configuration
- `src/flight-system/v2/run_gcs.py` - WebSocket server and telemetry handling
