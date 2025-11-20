import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

void main() {
  runApp(const GcsApp());
}

class GcsApp extends StatelessWidget {
  const GcsApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Custom GCS (Serial)',
      theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
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
  const GcsHome({super.key});
  @override
  State<GcsHome> createState() => _GcsHomeState();
}

class _GcsHomeState extends State<GcsHome> {
  final _mapController = MapController();
  Telemetry tel = Telemetry();
  WebSocketChannel? channel;
  StreamSubscription? sub;

  // Change to your RPi or host IP/name
  String wsUrl = "ws://localhost:8765";

  List<LatLng> mission = [];
  bool missionMode = false;

  LatLng defaultCenter = const LatLng(38.0308, -84.506);
  LatLng get mapCenter => tel.pos ?? defaultCenter;

  @override
  void initState() {
    super.initState();
    _connect();
  }

  @override
  void dispose() {
    sub?.cancel();
    channel?.sink.close();
    super.dispose();
  }

  void _connect() {
    channel = WebSocketChannel.connect(Uri.parse(wsUrl));
    sub = channel!.stream.listen((event) {
      final msg = jsonDecode(event);
      final type = msg["type"];

      if (type == "HELLO") {
        setState(() {
          tel.mode = msg["mode"] ?? "UNKNOWN";
          tel.armed = msg["armed"] ?? false;
          tel.linkOk = msg["link_ok"] ?? false;
        });
        return;
      }

      if (type == "HEARTBEAT") {
        setState(() {
          tel.armed = ((msg["base_mode"] ?? 0) & 0x80) != 0;
          tel.linkOk = true;
          // Server already computed mode string; keep last known for display
        });
      } else if (type == "GLOBAL_POSITION_INT") {
        setState(() {
          tel.pos = LatLng((msg["lat"] ?? 0) / 1e7, (msg["lon"] ?? 0) / 1e7);
          tel.relAlt = (msg["relative_alt"] ?? 0) / 1000.0;
        });
      } else if (type == "VFR_HUD") {
        setState(() {
          tel.groundSpeed = (msg["groundspeed"] ?? 0.0) * 1.0;
        });
      } else if (type == "SYS_STATUS") {
        final vbat = (msg["voltage_battery"] ?? 0) / 1000.0;
        setState(() {
          tel.voltage = vbat > 0 ? vbat : null;
        });
      } else if (type == "ERROR") {
        // Optionally show a snackbar
      }
    }, onDone: () {
      setState(() => tel.linkOk = false);
      _reconnect();
    }, onError: (e) {
      setState(() => tel.linkOk = false);
      _reconnect();
    });
  }

  void _reconnect() {
    Future.delayed(const Duration(seconds: 2), _connect);
  }

  void _send(Map<String, dynamic> cmd) {
    if (channel == null) return;
    channel!.sink.add(jsonEncode(cmd));
  }

  void _armToggle() => _send({"cmd": "arm", "value": !tel.armed});
  void _setMode(String m) => _send({"cmd": "mode", "mode": m});
  void _rtl() => _send({"cmd": "rtl"});

  void _goto(LatLng p) {
    _setMode("GUIDED");
    _send({"cmd": "goto", "lat": p.latitude, "lon": p.longitude, "alt_rel": 20.0});
  }

  void _missionToggle() => setState(() => missionMode = !missionMode);
  void _missionClear() {
    setState(() => mission.clear());
    _send({"cmd": "mission_clear"});
  }

  void _missionUpload() {
    if (mission.isEmpty) return;
    final items = <Map<String, dynamic>>[];
    for (int i = 0; i < mission.length; i++) {
      final p = mission[i];
      items.add({
        "seq": i,
        "frame": 6, // MAV_FRAME_GLOBAL_RELATIVE_ALT_INT
        "command": 16, // MAV_CMD_NAV_WAYPOINT
        "current": i == 0 ? 1 : 0,
        "autocontinue": 1,
        "param1": 0.0, // hold
        "param2": 0.0, // accept radius
        "param3": 0.0, // pass through
        "param4": 0.0, // yaw (0 = use default)
        "x": (p.latitude * 1e7).round(),
        "y": (p.longitude * 1e7).round(),
        "z": 20.0, // rel alt m
      });
    }
    _send({"cmd": "mission_upload", "items": items});
  }

  void _missionStart() => _send({"cmd": "mission_start"});

  @override
  Widget build(BuildContext context) {
    final markers = <Marker>[
      if (tel.pos != null)
        Marker(
          width: 42,
          height: 42,
          point: tel.pos!,
          child: const Icon(Icons.airplanemode_active, color: Colors.indigo, size: 34),
        ),
    ];

    // Only create polyline if mission has waypoints to avoid empty bounds assertion
    final polylines = mission.isNotEmpty
        ? [Polyline(points: mission, strokeWidth: 3, color: Colors.orangeAccent)]
        : <Polyline>[];

    return Scaffold(
      appBar: AppBar(
        title: const Text('SKEYE GCS'),
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
                  if (missionMode) {
                    setState(() => mission.add(latlng));
                  } else {
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
                    debugPrint('Tile load error: $error');
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
      color: Colors.grey.shade100,
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
          color: Colors.grey.shade50,
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
                  FilterChip(
                    selected: missionMode,
                    onSelected: (v) => _missionToggle(),
                    label: const Text("Mission edit"),
                    selectedColor: Colors.orange.shade100,
                  ),
                  const SizedBox(width: 6),
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
                  if (missionMode)
                    Text("${mission.length} WP", style: const TextStyle(fontWeight: FontWeight.bold)),
                  if (missionMode) const SizedBox(width: 6),
                  TextButton(
                    onPressed: mission.isNotEmpty ? _missionClear : null,
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
                  FilterChip(
                    selected: missionMode,
                    onSelected: (v) => _missionToggle(),
                    label: const Text("Mission edit"),
                    selectedColor: Colors.orange.shade100,
                  ),
                  const SizedBox(width: 8),
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
                  if (missionMode)
                    Text("${mission.length} WP", style: const TextStyle(fontWeight: FontWeight.bold)),
                  if (missionMode) const SizedBox(width: 8),
                  TextButton(
                    onPressed: mission.isNotEmpty ? _missionClear : null,
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