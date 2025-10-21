# SKEYE SITL Quick Start (Windows)

**Get SITL testing working in 5 minutes on Windows - no WSL required!**

## Prerequisites

- Windows 10/11
- Python 3.9+ installed
- Mission Planner installed ([download here](https://ardupilot.org/planner/docs/mission-planner-installation.html))
- SKEYE project cloned

## Option 1: Mission Planner Simulator (Easiest)

### Step 1: Start Mission Planner Simulator

1. Open **Mission Planner**
2. Click **Simulation** tab (top menu bar)
3. Select vehicle: **Multirotor**
4. Select model: **QuadCopter** or **X**
5. Click **Start Simulation**
6. Wait for "Ardupilot on TCP" message

### Step 2: Start SKEYE GCS Backend

Open **Command Prompt** in the SKEYE project folder:

```bash
start_gcs_sitl.bat
```

Or manually:

```bash
set GCS_SERIAL=tcp:127.0.0.1:5760
python src\flight-system\v2\run_gcs.py
```

You should see:
```
INFO:MavSerialCore:Opening MAVLink over serial tcp:127.0.0.1:5760 @ 57600 ...
INFO:MavSerialCore:Connected: sys=1, comp=1, mode=STABILIZE
```

### Step 3: Start Flutter UI

Open **another Command Prompt**:

```bash
cd src\flight-system\v2
flutter run -d windows
```

### Step 4: Test!

- Check telemetry is updating
- Try changing modes (STABILIZE → GUIDED → LOITER)
- Test arm/disarm
- Draw a survey polygon and generate mission
- Upload mission to SITL

**Done!** You're now running SKEYE with SITL.

---

## Option 2: MAVProxy Monitoring (Advanced)

### Step 1: Install MAVProxy

```bash
pip install MAVProxy
```

### Step 2: Start Mission Planner SITL

Same as Option 1:
1. Open Mission Planner
2. Go to **Simulation** tab
3. Select **Multirotor**
4. Click **Start Simulation**

### Step 3: Start MAVProxy (Optional for Monitoring)

In **Command Prompt**:

```bash
mavproxy.py --master=tcp:127.0.0.1:5760 --out=udp:127.0.0.1:14550
```

### Step 4: Start SKEYE GCS

In **another terminal**:

```bash
start_gcs_sitl.bat mavproxy_udp
```

Or manually:

```bash
set GCS_SERIAL=udp:127.0.0.1:14550
python src\flight-system\v2\run_gcs.py
```

### Step 5: Start Flutter UI

```bash
cd src\flight-system\v2
flutter run -d windows
```

---

## Switching to Real Hardware

To switch back to real Pixhawk:

```bash
start_gcs_hardware.bat
```

Or manually:

```bash
set GCS_SERIAL=COM4
python src\flight-system\v2\run_gcs.py
```

Or let it auto-detect:

```bash
python src\flight-system\v2\run_gcs.py
```

---

## Testing Checklist

### Basic Connectivity
- [ ] SITL starts without errors
- [ ] GCS connects (see "Connected: sys=1, comp=1")
- [ ] Flutter UI shows telemetry
- [ ] GPS shows "3D Fix" (wait ~10 seconds)
- [ ] Heartbeat maintained (no timeout errors)

### Flight Controls
- [ ] Mode changes work (STABILIZE, GUIDED, LOITER, AUTO, RTL)
- [ ] Arm/Disarm works
- [ ] GOTO command works (GUIDED mode)
- [ ] Speed commands work

### Survey Planning
- [ ] Can draw polygon on map
- [ ] Survey generation works
- [ ] Transect lines display
- [ ] Mission upload succeeds
- [ ] Mission runs in AUTO mode

---

## Troubleshooting

### "No heartbeat received"

**Check SITL is running:**
```bash
netstat -an | findstr "5760"
```
Should show: `TCP    127.0.0.1:5760    LISTENING`

**Fix:** Restart SITL simulator

### "Connection refused"

**Fix:** Make sure you're using `tcp:` prefix:
```bash
set GCS_SERIAL=tcp:127.0.0.1:5760
```
NOT just `127.0.0.1:5760`

### "Port 8765 already in use"

**Fix:** Kill existing GCS process:
```bash
netstat -ano | findstr "8765"
taskkill /F /PID <PID>
```

### No GPS fix in SITL

**Fix:** Wait 10-20 seconds after Mission Planner SITL starts for GPS initialization

### Flutter UI won't connect

**Fix:** Check WebSocket connection:
- GCS backend should show: `WebSocket listening on 0.0.0.0:8765`
- Flutter should connect to: `ws://localhost:8765`

---

## Complete Testing Workflow

1. **Start SITL** (Mission Planner simulator)
2. **Start GCS Backend** (`start_gcs_sitl.bat`)
3. **Start Flutter UI** (`flutter run -d windows`)
4. **Create Survey Mission** in UI
5. **Upload to SITL**
6. **Arm vehicle**
7. **Set mode to AUTO**
8. **Watch mission execute** in Mission Planner map
9. **Test with real hardware** by running `start_gcs_hardware.bat`

---

## Next Steps

- Read full guide: [SITL_TESTING_GUIDE.md](SITL_TESTING_GUIDE.md)
- Review architecture: [../src/flight-system/v2/README.md](../src/flight-system/v2/README.md)
- Run tests: [../test/README.md](../test/README.md)

---

**Questions?** See [SITL_TESTING_GUIDE.md](SITL_TESTING_GUIDE.md) for detailed troubleshooting and advanced options.
