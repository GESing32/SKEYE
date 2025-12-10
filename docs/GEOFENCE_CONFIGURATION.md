# Geofence Configuration Feature

## Overview
Comprehensive geofence (safety fence) configuration for SKEYE GCS based on ArduPilot fence parameters. Allows you to set maximum altitude, circular boundary, and safety actions.

## Accessing Geofence Panel

**Button Location**: Control panel at bottom of screen

Click **"Geofence"** button (🏗️ fence icon) to show/hide the fence configuration panel.

- Button turns **orange** when panel is open
- Panel appears as overlay on right side of map
- Scrollable panel for all fence options

## Fence Parameters

### 1. **Enable Geofence** (`FENCE_ENABLE`)
Toggle to enable/disable the entire fence system.

- **ON**: Fence is active, violations trigger action
- **OFF**: Fence disabled, no restrictions

### 2. **Fence Types** (`FENCE_TYPE` - Bitfield)
Select which fence types to use (can combine multiple):

| Type | Description | Use Case |
|------|-------------|----------|
| **Max Altitude** | Ceiling altitude limit | Prevent flying too high |
| **Circle Radius** | Cylindrical boundary | Keep drone within range |
| **Polygon** | Custom boundary shape | Complex operational areas |
| **Min Altitude** | Floor altitude limit | Prevent flying too low |

**Example Combinations**:
- ✅ Max Altitude + Circle = Cylindrical safety zone
- ✅ Max Altitude + Min Altitude + Circle = Vertical limits within radius
- ✅ All types = Full 3D boundary

### 3. **Fence Action** (`FENCE_ACTION`)
What happens when fence is breached:

| Action | Value | Behavior |
|--------|-------|----------|
| **Report Only** | 0 | Log breach, no action |
| **RTL** | 1 | Return to launch point |
| **Land** | 2 | Land immediately at current position |
| **SmartRTL** | 3 | Return via path taken |
| **Brake** | 4 | Stop and hover |
| **SmartRTL or Land** | 5 | SmartRTL if possible, else land |

**Recommended**:
- **Testing**: Report Only
- **Production**: RTL or SmartRTL or Land

### 4. **Max Altitude** (`FENCE_ALT_MAX`)
Maximum altitude above home position.

- **Range**: 33ft - 1,640ft (10m - 500m)
- **Default**: 328ft (100m)
- **Slider + Text Input** for precise control
- Only shown if "Max Altitude" type enabled

**Example**:
- **328ft (100m)**: Typical recreational limit
- **394ft (120m)**: FAA Part 107 maximum (US)
- **400ft**: Common ATC ceiling
- **492ft (150m)**: Extended operations

### 5. **Fence Radius** (`FENCE_RADIUS`)
Horizontal distance from home position.

- **Range**: 33ft - 3,281ft (10m - 1,000m)
- **Default**: 984ft (300m)
- **Slider + Text Input** for precise control
- Only shown if "Circle Radius" type enabled

**Example**:
- **328ft (100m)**: Visual line of sight
- **984ft (300m)**: Extended VLOS operations
- **1,640ft (500m)**: Max range for most drones

### 6. **Min Altitude** (`FENCE_ALT_MIN`)
Minimum altitude above home position.

- **Range**: -328ft - 328ft (-100m - 100m)
- **Default**: -33ft (-10m)
- **Slider + Text Input** for precise control
- Only shown if "Min Altitude" type enabled
- **Negative values**: Below home position (useful for slope operations)

**Example**:
- **0ft**: No lower limit
- **-33ft (-10m)**: Allow descent below launch point
- **16ft (5m)**: Stay at least 16ft above ground

### 7. **Fence Margin** (`FENCE_MARGIN`)
Distance from fence boundary where warning triggers.

- **Range**: 3.3ft - 65.6ft (1m - 20m)
- **Default**: 6.6ft (2m)
- Gives pilot warning before actual breach
- Triggers pre-breach alerts

**Example**:
- **6.6ft (2m)**: Standard buffer
- **16.4ft (5m)**: More warning time
- **32.8ft (10m)**: Extended buffer for fast flights

## Usage Workflow

### Basic Setup

1. **Click "Geofence" button** in control panel
2. **Enable checkbox**: "Enable Geofence"
3. **Select fence types**:
   - ✅ Max Altitude
   - ✅ Circle Radius
4. **Set values**:
   - Max Altitude: 394ft (120m)
   - Fence Radius: 984ft (300m)
5. **Choose action**: "RTL (Return to Launch)"
6. **Click "Apply to Vehicle"** button

### Testing Configuration

```
Step 1: Set conservative values
  - Max Altitude: 164ft (50m)
  - Radius: 328ft (100m)
  - Action: Report Only

Step 2: Fly test pattern
  - Approach each fence boundary
  - Verify warnings appear in message log

Step 3: Upgrade to active action
  - Change action to "RTL"
  - Test fence breach behavior
```

### Production Example

**Typical Safety Configuration**:
```
Enable: ✅ ON
Types:
  ✅ Max Altitude
  ✅ Circle Radius
  ✅ Min Altitude
Max Altitude: 400ft (122m) - FAA Part 107 limit
Fence Radius: 1,640ft (500m)
Min Altitude: 16ft (5m)
Action: SmartRTL or Land
Margin: 16ft (5m)
```

## Visual Indicators

**In Future Releases** (not yet implemented):
- Circular fence rendered on map
- Altitude ceiling indicator
- Real-time distance to fence
- Warning when approaching boundary

## Safety Warnings

⚠️ **IMPORTANT SAFETY NOTES**:

1. **Always test with "Report Only"** action first
2. **Verify GPS lock** before relying on fence (3D fix, 10+ satellites)
3. **Set conservative margins** - give yourself safety buffer
4. **Check local regulations** - max altitudes vary by country
5. **Clear obstacles** - fence doesn't prevent collision with trees/buildings
6. **Battery awareness** - ensure enough battery to RTL from fence boundary

## Fence Violations

When fence is breached:

### Report Only Mode
- Message appears: `⚠️ Fence breach detected!`
- Logged to message history
- No automatic action
- Pilot must respond manually

### Active Modes (RTL, Land, etc.)
- Message appears: `⚠️ FENCE BREACH - Initiating [ACTION]`
- Mode changes automatically
- Vehicle executes safety action
- Control returns when back inside fence (RTL only)

## Troubleshooting

### Fence Not Working
- ✅ Check "Enable Geofence" is ON
- ✅ Verify at least one fence type is checked
- ✅ Ensure GPS has 3D fix (10+ satellites)
- ✅ Check EKF status (must be healthy)
- ✅ Verify parameters uploaded successfully

### Unexpected RTL
- Check if you're near fence boundary
- Review message log for fence violations
- Verify fence radius isn't too small
- Check altitude didn't exceed max

### Parameters Not Saving
- Ensure vehicle is connected
- Check message log for errors
- Try applying parameters again
- Restart GCS and vehicle if needed

## Unit Conversion

**Display Units**: All values displayed in the UI are in **feet** for ease of use with FAA regulations.

**Backend Units**: All values sent to the Pixhawk are automatically converted to **meters** (ArduPilot standard).

**Conversion**:
- 1 meter = 3.28084 feet
- 1 foot = 0.3048 meters

The UI handles all conversions automatically - you only need to work with feet.

## Backend Implementation

### MAVLink Parameters Set
```python
FENCE_ENABLE    # 0=disabled, 1=enabled
FENCE_TYPE      # Bitfield (1=alt, 2=circle, 4=polygon, 8=minAlt)
FENCE_ACTION    # 0-5 (report, RTL, land, smartRTL, brake, smartRTL or land)
FENCE_ALT_MAX   # Maximum altitude (meters - converted from feet in UI)
FENCE_ALT_MIN   # Minimum altitude (meters - converted from feet in UI)
FENCE_RADIUS    # Circular fence radius (meters - converted from feet in UI)
FENCE_MARGIN    # Distance to trigger warning (meters - converted from feet in UI)
```

### Command Format
```json
{
  "command": "set_fence_params",
  "config": {
    "enabled": true,
    "type": 3,
    "action": 1,
    "max_altitude": 120.0,
    "min_altitude": -10.0,
    "radius": 300.0,
    "margin": 2.0
  }
}
```

## ArduPilot Documentation

Full parameter reference:
https://ardupilot.org/copter/docs/parameters.html#fence-parameters

## Related Files

- **UI**: `lib/widgets/fence_config_panel.dart`
- **Integration**: `lib/main.dart` (fence state management)
- **Backend**: `src/flight-system/v2/run_gcs.py` (parameter upload)

## Future Enhancements

Planned features:
- [ ] Read current fence parameters from vehicle
- [ ] Visualize circular fence on map
- [ ] Altitude ceiling visualization
- [ ] Real-time distance to fence display
- [ ] Polygon fence drawing on map
- [ ] Import/export fence configurations
- [ ] Fence profiles (saved presets)
- [ ] Pre-flight fence check warning
