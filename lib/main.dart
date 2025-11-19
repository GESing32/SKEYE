import 'dart:async';
import 'dart:convert';
import 'dart:developer' as developer;
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

// Logging utility similar to Python's logging module
class Logger {
  final String name;

  Logger(this.name);

  void debug(String message) {
    developer.log(message, name: name, level: 500);
  }

  void info(String message) {
    developer.log(message, name: name, level: 800);
  }

  void warning(String message) {
    developer.log(message, name: name, level: 900);
  }

  void error(String message, {Object? error, StackTrace? stackTrace}) {
    developer.log(
      message,
      name: name,
      level: 1000,
      error: error,
      stackTrace: stackTrace,
    );
  }
}

final log = Logger('GCS');

void main() {
  runApp(const GcsApp());
}

class GcsApp extends StatelessWidget {
  const GcsApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SKEYE Ground Control Station',
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: Colors.black,
        colorScheme: const ColorScheme.dark(
          surface: Colors.black,
          primary: Colors.white,
          onPrimary: Colors.black,
          secondary: Color(0xFF424242),
          onSecondary: Colors.white,
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.black,
          foregroundColor: Colors.white,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF424242),  // Dark gray
            foregroundColor: Colors.white,
            side: const BorderSide(color: Colors.white70, width: 1),
          ),
        ),
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            foregroundColor: Colors.white,
          ),
        ),
        chipTheme: ChipThemeData(
          backgroundColor: const Color(0xFF424242),
          selectedColor: const Color(0xFF616161),
          labelStyle: const TextStyle(color: Colors.white),
          side: const BorderSide(color: Colors.white70, width: 1),
        ),
        textTheme: const TextTheme(
          bodyMedium: TextStyle(color: Colors.white),
          bodyLarge: TextStyle(color: Colors.white),
          bodySmall: TextStyle(color: Colors.white),
        ),
        inputDecorationTheme: const InputDecorationTheme(
          labelStyle: TextStyle(color: Colors.white70),
          enabledBorder: OutlineInputBorder(
            borderSide: BorderSide(color: Colors.white70),
          ),
          focusedBorder: OutlineInputBorder(
            borderSide: BorderSide(color: Colors.white),
          ),
        ),
      ),
      home: const GcsHome(),
    );
  }
}

class Telemetry {
  bool linkOk = false;
  bool armed = false;
  String mode = "UNKNOWN";
  LatLng? pos;
  double? relAlt;
  double? groundSpeed;
  double? voltage;
}

class GcsHome extends StatefulWidget {
  final bool enableWebSocket;
  const GcsHome({super.key, this.enableWebSocket = true});
  @override
  State<GcsHome> createState() => _GcsHomeState();
}

class _GcsHomeState extends State<GcsHome> {
  final _mapController = MapController();
  Telemetry tel = Telemetry();
  WebSocketChannel? channel;
  StreamSubscription? sub;
  Timer? _reconnectTimer;

  String wsUrl = "ws://localhost:8765";

  List<LatLng> mission = [];
  bool missionMode = false;
  bool surveyMode = false;  // Survey polygon mode
  List<LatLng> surveyPolygon = [];  // Survey boundary polygon
  List<LatLng> surveyWaypoints = [];  // Generated survey grid waypoints
  List<Map<String, dynamic>>? surveyMissionItems;  // Raw mission items from survey generation

  double takeoffAltitude = 20.0;  // Default takeoff altitude in meters

  // Survey configuration
  double surveyAltitude = 50.0;  // Survey altitude in meters
  double surveySpeed = 6.0;  // Survey speed in m/s
  double surveyFrontOverlap = 75.0;  // Front overlap percentage
  double surveySideOverlap = 75.0;  // Side overlap percentage
  double surveyGridAngle = 0.0;  // Grid angle in degrees (0 = N-S, 90 = E-W)

  LatLng defaultCenter = const LatLng(38.0308, -84.506);
  LatLng get mapCenter => tel.pos ?? defaultCenter;

  @override
  void initState() {
    super.initState();
    if (widget.enableWebSocket) {
      _connect();
    }
  }

  @override
  void dispose() {
    _reconnectTimer?.cancel();
    sub?.cancel();
    channel?.sink.close();
    super.dispose();
  }

  void _connect() {
    log.info("Connecting to WebSocket: $wsUrl");
    channel = WebSocketChannel.connect(Uri.parse(wsUrl));
    sub = channel!.stream.listen((event) {
      final msg = jsonDecode(event);
      final type = msg["type"];

      if (type == "HELLO") {
        log.info("Received HELLO from server");
        if (mounted) {
          setState(() {
            tel.mode = msg["mode"] ?? "UNKNOWN";
            tel.armed = msg["armed"] ?? false;
            tel.linkOk = msg["link_ok"] ?? false;
          });
        }
        return;
      }

      if (type == "STATE_UPDATE") {
        if (mounted) {
          setState(() {
            if (msg.containsKey("mode")) {
              tel.mode = msg["mode"];
            }
            if (msg.containsKey("armed")) {
              tel.armed = msg["armed"];
            }
          });
        }
        return;
      }

      if (type == "TELEMETRY_BATCH") {
        // Handle batched messages
        final messages = msg["messages"] as List<dynamic>?;
        if (messages != null) {
          for (final batchedMsg in messages) {
            _processTelemetryMessage(batchedMsg as Map<String, dynamic>);
          }
        }
        return;
      }

      // Process individual telemetry message
      _processTelemetryMessage(msg);
    }, onDone: () {
      log.warning("WebSocket connection closed, attempting reconnect");
      if (mounted) {
        setState(() => tel.linkOk = false);
        _reconnect();
      }
    }, onError: (e) {
      log.error("WebSocket error", error: e);
      if (mounted) {
        setState(() => tel.linkOk = false);
        _reconnect();
      }
    });
  }

  void _processTelemetryMessage(Map<String, dynamic> msg) {
    final type = msg["type"];

    if (type == "HEARTBEAT") {
      if (mounted) {
        final baseMode = msg["base_mode"] ?? 0;
        final newArmedState = (baseMode & 0x80) != 0;

        // Log armed state changes for debugging
        if (newArmedState != tel.armed) {
          log.info("Armed state changed: ${tel.armed} -> $newArmedState (base_mode=$baseMode)");
        }

        setState(() {
          tel.armed = newArmedState;
          tel.linkOk = true;
          // Server already computed mode string; keep last known for display
        });
      }
    } else if (type == "GLOBAL_POSITION_INT") {
      if (mounted) {
        final lat = (msg["lat"] ?? 0) / 1e7;
        final lon = (msg["lon"] ?? 0) / 1e7;
        final alt = (msg["relative_alt"] ?? 0) / 1000.0;

        // Debug: Log position updates (remove after debugging)
        print("📍 Position: lat=${lat.toStringAsFixed(6)}, lon=${lon.toStringAsFixed(6)}, alt=${alt.toStringAsFixed(1)}m");

        setState(() {
          tel.pos = LatLng(lat, lon);
          tel.relAlt = alt;
        });
      }
    } else if (type == "VFR_HUD") {
      if (mounted) {
        setState(() {
          tel.groundSpeed = (msg["groundspeed"] ?? 0.0) * 1.0;
        });
      }
    } else if (type == "SYS_STATUS") {
      final vbat = (msg["voltage_battery"] ?? 0) / 1000.0;
      if (mounted) {
        setState(() {
          tel.voltage = vbat > 0 ? vbat : null;
        });
      }
    } else if (type == "ERROR") {
      // Optionally show a snackbar
      final error = msg["error"] ?? "Unknown error";
      log.error("Server error: $error");
    } else if (type == "SURVEY_GENERATED") {
      // Handle generated survey mission
      log.info("Survey generated successfully");
      final missionItems = msg["mission_items"] as List<dynamic>?;
      final stats = msg["statistics"] as Map<String, dynamic>?;

      if (missionItems != null && mounted) {
        // Store raw mission items with correct altitudes
        surveyMissionItems = missionItems.cast<Map<String, dynamic>>();

        // Convert mission items to waypoints for display
        List<LatLng> waypoints = [];
        for (var item in missionItems) {
          // Skip camera trigger commands (command != 16)
          if (item["command"] == 16) {  // NAV_WAYPOINT
            final lat = (item["x"] as int) / 1e7;
            final lon = (item["y"] as int) / 1e7;
            waypoints.add(LatLng(lat, lon));
          }
        }

        setState(() {
          surveyWaypoints = waypoints;
          mission = waypoints;  // Also set as current mission for upload
        });

        if (stats != null) {
          log.info("Survey stats: ${stats['waypoint_count']} waypoints, "
              "${stats['photo_count']} photos, "
              "${stats['flight_distance_m']}m, "
              "${stats['flight_time_min']} min");
        }
      }
    }
  }

  void _reconnect() {
    _reconnectTimer?.cancel();
    log.info("Scheduling reconnection in 2 seconds");
    _reconnectTimer = Timer(const Duration(seconds: 2), () {
      if (mounted) {
        _connect();
      }
    });
  }

  void _send(Map<String, dynamic> cmd) {
  if (channel == null) return;
  channel!.sink.add(jsonEncode(cmd));
  log.debug("Sent command: $cmd");
  }

  void _armToggle() {
    if (tel.armed) {
      // Currently armed, send disarm command
      _send({
        "command": "disarm",
      });
    } else {
      // Currently disarmed, send arm command
      _send({
        "command": "arm",
        "force": true,
      });
    }
  }

  void _setMode(String m) {
    _send({
      "command": "set_mode",  // Changed from "cmd" to "command"
      "mode": m,
    });
  }

  void _rtl() {
    _setMode("RTL");  // Just set mode to RTL
  }

  void _takeoff() {
    _send({
      "command": "takeoff",
      "alt": takeoffAltitude,
    });
  }

  void _goto(LatLng p) {
    _setMode("GUIDED");
    Future.delayed(const Duration(milliseconds: 500), () {
      _send({
        "command": "goto",
        "lat": p.latitude,
        "lon": p.longitude,
        "alt": 20.0,  // Changed from alt_rel
      });
    });
  }

  void _missionClear() {
    setState(() => mission.clear());
    _send({"command": "mission_clear"});
  }

  void _missionUpload() {
    if (mission.isEmpty) return;

    final items = <Map<String, dynamic>>[];

    // Use raw survey mission items if available (from survey generation)
    if (surveyMissionItems != null && surveyMissionItems!.isNotEmpty) {
      // Survey already generated complete mission items with correct altitudes
      items.addAll(surveyMissionItems!);
      log.info("Uploading survey mission: ${items.length} items (${mission.length} waypoints)");
    } else {
      // Manual mission mode - create waypoints with default altitude
      for (int i = 0; i < mission.length; i++) {
        final p = mission[i];
        items.add({
          "frame": 3,  // MAV_FRAME_GLOBAL_RELATIVE_ALT
          "command": 16,  // MAV_CMD_NAV_WAYPOINT
          "current": i == 0 ? 1 : 0,
          "autocontinue": 1,
          "param1": 0.0,
          "param2": 0.0,
          "param3": 0.0,
          "param4": 0.0,
          "x": p.latitude,   // Use float, not int!
          "y": p.longitude,  // Use float, not int!
          "z": 20.0,
        });
      }
      log.info("Uploading manual mission: ${items.length} waypoints");
    }

    _send({
      "command": "mission_upload",
      "mission_items": items,
      "alt": surveyMissionItems != null ? surveyAltitude : takeoffAltitude,  // Pass altitude for TAKEOFF
    });
  }

  void _missionStart() {
    _send({"command": "mission_start"});
    log.info("Mission start command sent");
  }

  void _missionToggle() => setState(() {
    missionMode = !missionMode;
    if (missionMode && surveyMode) {
      // Disable survey mode when entering mission mode
      surveyMode = false;
    }
  });

  void _surveyToggle() => setState(() {
    surveyMode = !surveyMode;
    if (surveyMode) {
      // Disable mission mode when entering survey mode
      missionMode = false;
      // Clear previous survey data
      surveyPolygon.clear();
      surveyWaypoints.clear();
    }
  });

  void _generateSurvey() {
    if (surveyPolygon.length < 3) {
      log.warning("Survey requires at least 3 polygon points");
      return;
    }

    log.info("Generating survey for ${surveyPolygon.length} polygon points");
    _send({
      "command": "generate_survey",
      "polygon": surveyPolygon.map((p) => {"lat": p.latitude, "lon": p.longitude}).toList(),
      "altitude": surveyAltitude,
      "speed": surveySpeed,
      "front_overlap": surveyFrontOverlap,
      "side_overlap": surveySideOverlap,
      "grid_angle": surveyGridAngle,
      "turnaround_dist": 10.0,
    });
  }

  void _surveyClear() {
    setState(() {
      surveyPolygon.clear();
      surveyWaypoints.clear();
      surveyMissionItems = null;
      mission.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    final markers = <Marker>[
      if (tel.pos != null)
        Marker(
          width: 42,
          height: 42,
          point: tel.pos!,
          child: const Icon(Icons.airplanemode_active_rounded, color: Colors.indigo, size: 34),
        ),
    ];

    // Build polylines for mission, survey polygon, and survey waypoints
    final polylines = <Polyline>[];

    // Mission waypoints (orange)
    if (mission.isNotEmpty) {
      polylines.add(Polyline(points: mission, strokeWidth: 3, color: Colors.orangeAccent));
    }

    // Survey polygon boundary (blue, closed)
    if (surveyPolygon.isNotEmpty) {
      final closedPolygon = [...surveyPolygon, surveyPolygon.first];
      polylines.add(Polyline(points: closedPolygon, strokeWidth: 2, color: Colors.blue));
    }

    // Generated survey waypoints (green)
    if (surveyWaypoints.isNotEmpty) {
      polylines.add(Polyline(points: surveyWaypoints, strokeWidth: 2, color: Colors.green));
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('SKEYE Ground Control Station'),
        actions: [
          Icon(tel.linkOk ? Icons.link : Icons.link_off, color: tel.linkOk ? Colors.green : Colors.red),
          const SizedBox(width: 12),
        ],
      ),
      body: Column(
        children: [
          _statusBar(),
          Expanded(
            child: FlutterMap(
              mapController: _mapController,
              options: MapOptions(
                initialCenter: mapCenter,
                initialZoom: 14,
                onTap: (tapPos, latlng) {
                  print("🗺️ Map tapped: missionMode=$missionMode, surveyMode=$surveyMode");
                  print("   Position: lat=${latlng.latitude.toStringAsFixed(6)}, lon=${latlng.longitude.toStringAsFixed(6)}");

                  if (missionMode) {
                    print("   → Adding waypoint to mission (now ${mission.length + 1} WP)");
                    setState(() => mission.add(latlng));
                  } else if (surveyMode) {
                    print("   → Adding point to survey polygon (now ${surveyPolygon.length + 1} pts)");
                    setState(() => surveyPolygon.add(latlng));
                  } else {
                    print("   → Sending GOTO command");
                    _goto(latlng);
                  }
                },
              ),
              children: [
                TileLayer(
                  urlTemplate: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                  userAgentPackageName: 'custom_gcs_serial',
                ),
                PolylineLayer(polylines: polylines),
                MarkerLayer(markers: markers),
              ],
            ),
          ),
          _controls(),
        ],
      ),
    );
  }

  Widget _statusBar() {
    return Container(
      color: const Color.fromARGB(255, 0, 0, 0),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: LayoutBuilder(
        builder: (context, constraints) {
          return SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: ConstrainedBox(
              constraints: BoxConstraints(minWidth: constraints.maxWidth),
              child: IntrinsicHeight(
                child: Wrap(
                  spacing: 24,
                  runSpacing: 8,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    _kv("Mode", tel.mode),
                    _kv("Armed", tel.armed ? "Yes" : "No"),
                    _kv("Lat", tel.pos?.latitude.toStringAsFixed(6) ?? "-"),
                    _kv("Lon", tel.pos?.longitude.toStringAsFixed(6) ?? "-"),
                    _kv("Alt rel (m)", tel.relAlt?.toStringAsFixed(1) ?? "-"),
                    _kv("GS (m/s)", tel.groundSpeed?.toStringAsFixed(1) ?? "-"),
                    _kv("VBat (V)", tel.voltage?.toStringAsFixed(2) ?? "-"),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _controls() {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isNarrow = constraints.maxWidth < 900;

        return Container(
          padding: const EdgeInsets.all(12),
          color: const Color.fromARGB(255, 0, 0, 0),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                // Compact style for narrow screens
                if (isNarrow) ...[
                  ElevatedButton(
                    onPressed: _armToggle,
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(tel.armed ? Icons.lock_open : Icons.lock, size: 18),
                        const SizedBox(width: 4),
                        Text(tel.armed ? "Disarm" : "Arm"),
                      ],
                    ),
                  ),
                  const SizedBox(width: 6),
                  _modeMenu(),
                  const SizedBox(width: 6),
                  ElevatedButton(
                    onPressed: _rtl,
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.undo, size: 18),
                        SizedBox(width: 4),
                        Text("RTL"),
                      ],
                    ),
                  ),
                  const SizedBox(width: 6),
                  ElevatedButton(
                    onPressed: tel.armed ? _takeoff : null,
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      backgroundColor: tel.armed ? Colors.green : null,
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.flight_takeoff, size: 18),
                        const SizedBox(width: 4),
                        Text("T/O ${takeoffAltitude.toStringAsFixed(0)}m"),
                      ],
                    ),
                  ),
                  const SizedBox(width: 6),
                  FilterChip(
                    selected: missionMode,
                    onSelected: (v) => _missionToggle(),
                    label: const Text("Mission"),
                    selectedColor: Colors.orange.shade100,
                  ),
                  const SizedBox(width: 6),
                  FilterChip(
                    selected: surveyMode,
                    onSelected: (v) => _surveyToggle(),
                    label: const Text("Survey"),
                    selectedColor: Colors.blue.shade100,
                  ),
                  const SizedBox(width: 6),
                  if (surveyMode && surveyPolygon.length >= 3)
                    ElevatedButton(
                      onPressed: _generateSurvey,
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                        backgroundColor: Colors.green,
                      ),
                      child: const Text("Generate"),
                    ),
                  if (surveyMode && surveyPolygon.length >= 3) const SizedBox(width: 6),
                  if (!surveyMode) ...[
                    ElevatedButton(
                      onPressed: mission.isNotEmpty ? _missionUpload : null,
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                      ),
                      child: const Text("Upload"),
                    ),
                    const SizedBox(width: 6),
                    ElevatedButton(
                      onPressed: mission.isNotEmpty ? _missionStart : null,
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                      ),
                      child: const Text("Start"),
                    ),
                    const SizedBox(width: 6),
                  ],
                  if (missionMode)
                    Text("${mission.length} WP", style: const TextStyle(fontWeight: FontWeight.bold)),
                  if (surveyMode)
                    Text("${surveyPolygon.length} pts", style: const TextStyle(fontWeight: FontWeight.bold)),
                  if (missionMode || surveyMode) const SizedBox(width: 6),
                  TextButton(
                    onPressed: (mission.isNotEmpty || surveyPolygon.isNotEmpty)
                        ? (surveyMode ? _surveyClear : _missionClear)
                        : null,
                    child: const Text("Clear"),
                  ),
                ] else ...[
                  // Full style for wider screens
                  ElevatedButton.icon(
                    onPressed: _armToggle,
                    icon: Icon(tel.armed ? Icons.lock_open : Icons.lock),
                    label: Text(tel.armed ? "Disarm" : "Arm"),
                  ),
                  const SizedBox(width: 8),
                  _modeMenu(),
                  const SizedBox(width: 8),
                  ElevatedButton.icon(
                    onPressed: _rtl,
                    icon: const Icon(Icons.undo),
                    label: const Text("RTL"),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton.icon(
                    onPressed: tel.armed ? _takeoff : null,
                    icon: const Icon(Icons.flight_takeoff),
                    label: Text("Takeoff ${takeoffAltitude.toStringAsFixed(0)}m"),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: tel.armed ? Colors.green : null,
                    ),
                  ),
                  const SizedBox(width: 8),
                  SizedBox(
                    width: 80,
                    child: TextField(
                      decoration: const InputDecoration(
                        labelText: 'Alt (m)',
                        isDense: true,
                        contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                      ),
                      keyboardType: TextInputType.number,
                      controller: TextEditingController(text: takeoffAltitude.toStringAsFixed(0)),
                      onChanged: (value) {
                        final alt = double.tryParse(value);
                        if (alt != null && alt > 0 && alt <= 120) {
                          setState(() => takeoffAltitude = alt);
                        }
                      },
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilterChip(
                    selected: missionMode,
                    onSelected: (v) => _missionToggle(),
                    label: const Text("Mission"),
                    selectedColor: Colors.orange.shade100,
                  ),
                  const SizedBox(width: 8),
                  FilterChip(
                    selected: surveyMode,
                    onSelected: (v) => _surveyToggle(),
                    label: const Text("Survey"),
                    selectedColor: Colors.blue.shade100,
                  ),
                  const SizedBox(width: 8),
                  if (surveyMode && surveyPolygon.length >= 3)
                    ElevatedButton(
                      onPressed: _generateSurvey,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                      ),
                      child: const Text("Generate Grid"),
                    ),
                  if (surveyMode && surveyPolygon.length >= 3) const SizedBox(width: 8),
                  if (!surveyMode) ...[
                    ElevatedButton(
                      onPressed: mission.isNotEmpty ? _missionUpload : null,
                      child: const Text("Upload"),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      onPressed: mission.isNotEmpty ? _missionStart : null,
                      child: const Text("Start"),
                    ),
                    const SizedBox(width: 8),
                  ],
                  if (missionMode)
                    Text("${mission.length} WP", style: const TextStyle(fontWeight: FontWeight.bold)),
                  if (surveyMode)
                    Text("${surveyPolygon.length} polygon points", style: const TextStyle(fontWeight: FontWeight.bold)),
                  if (missionMode || surveyMode) const SizedBox(width: 8),
                  TextButton(
                    onPressed: (mission.isNotEmpty || surveyPolygon.isNotEmpty)
                        ? (surveyMode ? _surveyClear : _missionClear)
                        : null,
                    child: const Text("Clear"),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _modeMenu() {
    return ElevatedButton(
      onPressed: () {
        // Show mode selection menu
        showMenu<String>(
          context: context,
          position: const RelativeRect.fromLTRB(100, 100, 0, 0),
          items: const [
            PopupMenuItem(value: "GUIDED", child: Text("GUIDED")),
            PopupMenuItem(value: "LOITER", child: Text("LOITER")),
            PopupMenuItem(value: "ALT_HOLD", child: Text("ALT_HOLD")),
            PopupMenuItem(value: "STABILIZE", child: Text("STABILIZE")),
          ],
        ).then((value) {
          if (value != null) {
            _setMode(value);
          }
        });
      },
      child: const Text("Mode"),
    );
  }

  Widget _kv(String k, String v) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text("$k: ", style: const TextStyle(fontWeight: FontWeight.bold)),
        Text(v),
      ],
    );
  }
}