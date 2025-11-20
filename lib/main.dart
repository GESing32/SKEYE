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
  int? gpsSatellites;  // Number of GPS satellites visible
  int? gpsFixType;     // GPS fix type (0=No GPS, 1=No Fix, 2=2D, 3=3D, 4=DGPS, 5=RTK)
}

class SystemMessage {
  final String message;
  final MessageSeverity severity;
  final DateTime timestamp;

  SystemMessage(this.message, this.severity) : timestamp = DateTime.now();
}

enum MessageSeverity {
  info,
  warning,
  error,
  critical,
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

  // System messages and errors
  List<SystemMessage> systemMessages = [];
  final int maxMessages = 50;  // Keep last 50 messages for continuous log

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
        log.info("  Mode: ${msg["mode"]}, Armed: ${msg["armed"]}, Link OK: ${msg["link_ok"]}");
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

        // Only update position if valid (not 0,0 which indicates no GPS fix)
        if (lat != 0 && lon != 0) {
          log.info("📍 GPS Position: lat=${lat.toStringAsFixed(6)}, lon=${lon.toStringAsFixed(6)}, alt=${alt.toStringAsFixed(1)}m");
          setState(() {
            tel.pos = LatLng(lat, lon);
            tel.relAlt = alt;
          });
        } else {
          // Only log once when we don't have a fix (to avoid spam)
          if (tel.pos != null) {
            log.warning("⚠️ GPS lost fix - Waiting for GPS lock...");
            setState(() {
              tel.pos = null;
            });
          }
        }
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
    } else if (type == "GPS_RAW_INT") {
      if (mounted) {
        final satellites = msg["satellites_visible"] ?? 0;
        final fixType = msg["fix_type"] ?? 0;

        // Detect GPS fix degradation (transition from good to bad)
        final hadGoodFix = tel.gpsFixType != null && tel.gpsFixType! >= 3;
        final nowHasBadFix = fixType < 3;

        setState(() {
          tel.gpsSatellites = satellites;
          tel.gpsFixType = fixType;
        });

        // Log when GPS degrades from good fix to bad fix
        if (hadGoodFix && nowHasBadFix) {
          _addSystemMessage("GPS fix degraded: ${_getGpsFixTypeName(fixType)} (${satellites} sats)", MessageSeverity.warning);
        }
      }
    } else if (type == "EKF_STATUS_REPORT") {
      // EKF status flags - check for critical errors
      final flags = msg["flags"] ?? 0;

      // EKF_ATTITUDE (bit 0) - critical for flight
      if ((flags & 0x01) == 0 && tel.armed) {
        _addSystemMessage("⚠️ EKF: Attitude estimate unavailable!", MessageSeverity.critical);
      }

      // EKF_VELOCITY_HORIZ (bit 1) - critical for position hold
      if ((flags & 0x02) == 0 && tel.armed) {
        _addSystemMessage("⚠️ EKF: Horizontal velocity unavailable!", MessageSeverity.warning);
      }

      // EKF_CONST_POS_MODE (bit 3) - indicates poor GPS
      if ((flags & 0x08) != 0) {
        _addSystemMessage("EKF: Using constant position mode (poor GPS)", MessageSeverity.warning);
      }
    } else if (type == "STATUSTEXT") {
      // ArduPilot status text messages
      final text = msg["text"] ?? "";
      final severity = msg["severity"] ?? 6; // MAV_SEVERITY_INFO

      // Only show important messages (severity <= 4 is warning or higher)
      // 0=EMERGENCY, 1=ALERT, 2=CRITICAL, 3=ERROR, 4=WARNING, 5=NOTICE, 6=INFO, 7=DEBUG
      if (severity <= 4 && text.isNotEmpty) {
        final msgSeverity = severity <= 2
            ? MessageSeverity.critical
            : severity == 3
                ? MessageSeverity.error
                : MessageSeverity.warning;

        _addSystemMessage(text, msgSeverity);
      } else if (text.isNotEmpty) {
        // Log info messages but don't display
        log.info("STATUSTEXT: $text");
      }
    } else if (type == "COMMAND_ACK") {
      // Command acknowledgment - check for failures
      final command = msg["command"] ?? 0;
      final result = msg["result"] ?? 0;

      // MAV_RESULT: 0=ACCEPTED, 1=TEMPORARILY_REJECTED, 2=DENIED, 3=UNSUPPORTED, 4=FAILED
      if (result != 0) {
        final commandName = _getCommandName(command);
        final resultName = _getCommandResultName(result);
        _addSystemMessage("Command failed: $commandName ($resultName)", MessageSeverity.error);
      }
    } else if (type == "ERROR") {
      final error = msg["error"] ?? "Unknown error";
      final command = msg["command"];
      log.error("Server error: $error");
      _addSystemMessage(command != null ? "Error ($command): $error" : "Error: $error", MessageSeverity.error);
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

  void _addSystemMessage(String message, MessageSeverity severity) {
    if (!mounted) return;

    setState(() {
      systemMessages.insert(0, SystemMessage(message, severity));
      // Keep only the last N messages
      if (systemMessages.length > maxMessages) {
        systemMessages = systemMessages.sublist(0, maxMessages);
      }
    });

    log.info("System message [$severity]: $message");
  }

  String _getGpsFixTypeName(int fixType) {
    switch (fixType) {
      case 0: return "No GPS";
      case 1: return "No Fix";
      case 2: return "2D Fix";
      case 3: return "3D Fix";
      case 4: return "DGPS";
      case 5: return "RTK Float";
      case 6: return "RTK Fixed";
      default: return "Unknown";
    }
  }

  String _getCommandName(int command) {
    // Common MAVLink commands
    switch (command) {
      case 16: return "NAV_WAYPOINT";
      case 22: return "NAV_TAKEOFF";
      case 176: return "DO_SET_MODE";
      case 400: return "ARM/DISARM";
      case 84: return "NAV_GUIDED_ENABLE";
      default: return "Command $command";
    }
  }

  String _getCommandResultName(int result) {
    switch (result) {
      case 0: return "Accepted";
      case 1: return "Temporarily rejected";
      case 2: return "Denied";
      case 3: return "Unsupported";
      case 4: return "Failed";
      case 5: return "In progress";
      default: return "Result $result";
    }
  }

  Color _getHighestSeverityColor() {
    if (systemMessages.any((m) => m.severity == MessageSeverity.critical)) {
      return Colors.red.shade900;
    } else if (systemMessages.any((m) => m.severity == MessageSeverity.error)) {
      return Colors.red.shade700;
    } else if (systemMessages.any((m) => m.severity == MessageSeverity.warning)) {
      return Colors.orange.shade700;
    }
    return Colors.blue.shade700;
  }

  void _showMessagesDialog() {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          width: 600,
          height: 500,
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'System Messages',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  Row(
                    children: [
                      TextButton.icon(
                        icon: const Icon(Icons.clear_all),
                        label: const Text('Clear All'),
                        onPressed: () {
                          setState(() {
                            systemMessages.clear();
                          });
                          Navigator.pop(context);
                        },
                      ),
                      IconButton(
                        icon: const Icon(Icons.close),
                        onPressed: () => Navigator.pop(context),
                      ),
                    ],
                  ),
                ],
              ),
              const Divider(),
              if (systemMessages.isEmpty)
                const Expanded(
                  child: Center(
                    child: Text(
                      'No messages',
                      style: TextStyle(color: Colors.grey),
                    ),
                  ),
                )
              else
                Expanded(
                  child: ListView.builder(
                    itemCount: systemMessages.length,
                    itemBuilder: (context, index) {
                      final msg = systemMessages[index];
                      return _buildMessageCard(msg);
                    },
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMessageCard(SystemMessage msg) {
    Color borderColor;
    IconData icon;
    Color iconColor;

    switch (msg.severity) {
      case MessageSeverity.critical:
        borderColor = Colors.red.shade900;
        icon = Icons.error;
        iconColor = Colors.red.shade900;
        break;
      case MessageSeverity.error:
        borderColor = Colors.red.shade700;
        icon = Icons.error_outline;
        iconColor = Colors.red.shade700;
        break;
      case MessageSeverity.warning:
        borderColor = Colors.orange.shade700;
        icon = Icons.warning_amber;
        iconColor = Colors.orange.shade700;
        break;
      case MessageSeverity.info:
        borderColor = Colors.blue.shade700;
        icon = Icons.info_outline;
        iconColor = Colors.blue.shade700;
        break;
    }

    final timeAgo = _formatTimeAgo(DateTime.now().difference(msg.timestamp));

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(color: borderColor, width: 2),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: iconColor, size: 24),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    msg.message,
                    style: const TextStyle(fontSize: 14),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '$timeAgo - ${msg.severity.name.toUpperCase()}',
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.grey.shade400,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatTimeAgo(Duration duration) {
    if (duration.inSeconds < 60) {
      return '${duration.inSeconds}s ago';
    } else if (duration.inMinutes < 60) {
      return '${duration.inMinutes}m ago';
    } else {
      return '${duration.inHours}h ago';
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
          // Messages/Errors button with badge
          Stack(
            alignment: Alignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.notification_important),
                tooltip: 'System Messages',
                onPressed: _showMessagesDialog,
              ),
              if (systemMessages.isNotEmpty)
                Positioned(
                  right: 8,
                  top: 8,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      color: _getHighestSeverityColor(),
                      shape: BoxShape.circle,
                    ),
                    constraints: const BoxConstraints(
                      minWidth: 16,
                      minHeight: 16,
                    ),
                    child: Text(
                      '${systemMessages.length}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
            ],
          ),
          Icon(tel.linkOk ? Icons.link : Icons.link_off, color: tel.linkOk ? Colors.green : Colors.red),
          const SizedBox(width: 12),
        ],
      ),
      body: Column(
        children: [
          _statusBar(),
          // Error/Warning Banner
          if (systemMessages.isNotEmpty) _systemMessagesBanner(),
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
                  // Use subdomain-based load balancing for better performance
                  urlTemplate: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                  subdomains: const ['a', 'b', 'c'],
                  userAgentPackageName: 'custom_gcs_serial',
                  maxNativeZoom: 19,
                  maxZoom: 22,
                  // Reduce simultaneous tile loads to avoid overwhelming servers
                  tileDisplay: const TileDisplay.fadeIn(
                    duration: Duration(milliseconds: 200),
                  ),
                  // Show error placeholder for failed tiles
                  errorTileCallback: (tile, error, stackTrace) {
                    log.debug('Tile load error: $error');
                  },
                  tileBuilder: (context, widget, tile) {
                    return DecoratedBox(
                      decoration: BoxDecoration(
                        color: Colors.grey[300],
                      ),
                      child: widget,
                    );
                  },
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
                    // GPS status with satellite count
                    _kvColored(
                      "GPS",
                      tel.gpsFixType != null && tel.gpsFixType! >= 3
                          ? "${_getGpsFixTypeName(tel.gpsFixType!)} (${tel.gpsSatellites ?? 0} sats)"
                          : tel.gpsFixType != null
                              ? _getGpsFixTypeName(tel.gpsFixType!)
                              : "NO DATA",
                      tel.gpsFixType != null && tel.gpsFixType! >= 3
                          ? Colors.green
                          : tel.gpsFixType != null && tel.gpsFixType! >= 2
                              ? Colors.orange
                              : Colors.red,
                    ),
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

  Widget _systemMessagesBanner() {
    // Show only the most severe message
    final criticalMessages = systemMessages.where((m) => m.severity == MessageSeverity.critical).toList();
    final errorMessages = systemMessages.where((m) => m.severity == MessageSeverity.error).toList();
    final warningMessages = systemMessages.where((m) => m.severity == MessageSeverity.warning).toList();

    SystemMessage? displayMessage;
    if (criticalMessages.isNotEmpty) {
      displayMessage = criticalMessages.first;
    } else if (errorMessages.isNotEmpty) {
      displayMessage = errorMessages.first;
    } else if (warningMessages.isNotEmpty) {
      displayMessage = warningMessages.first;
    } else if (systemMessages.isNotEmpty) {
      displayMessage = systemMessages.first;
    }

    if (displayMessage == null) return const SizedBox.shrink();

    Color bgColor;
    IconData icon;
    switch (displayMessage.severity) {
      case MessageSeverity.critical:
        bgColor = Colors.red.shade900;
        icon = Icons.error;
        break;
      case MessageSeverity.error:
        bgColor = Colors.red.shade800;
        icon = Icons.error_outline;
        break;
      case MessageSeverity.warning:
        bgColor = Colors.orange.shade800;
        icon = Icons.warning_amber;
        break;
      case MessageSeverity.info:
        bgColor = Colors.blue.shade800;
        icon = Icons.info_outline;
        break;
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      color: bgColor,
      child: Row(
        children: [
          Icon(icon, color: Colors.white, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              displayMessage.message,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 13,
              ),
            ),
          ),
          if (systemMessages.length > 1)
            Text(
              "+${systemMessages.length - 1} more",
              style: const TextStyle(color: Colors.white70, fontSize: 11),
            ),
          const SizedBox(width: 8),
          IconButton(
            icon: const Icon(Icons.close, color: Colors.white, size: 18),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
            onPressed: () {
              setState(() {
                systemMessages.clear();
              });
            },
          ),
        ],
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

  Widget _kvColored(String k, String v, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text("$k: ", style: const TextStyle(fontWeight: FontWeight.bold)),
        Text(v, style: TextStyle(color: color, fontWeight: FontWeight.bold)),
      ],
    );
  }
}