import 'dart:convert';
import 'package:http/http.dart' as http;

class DroneApi {
  final String baseUrl; // e.g., http://192.168.1.50:8000
  DroneApi(this.baseUrl);

  Future<Map<String, dynamic>> getTelemetry() async {
    final r = await http.get(Uri.parse('$baseUrl/telemetry'));
    return jsonDecode(r.body);
    }

  Future<void> setMode(String mode) async {
    await http.post(Uri.parse('$baseUrl/mode/$mode'));
  }

  Future<void> arm(bool arm) async {
    await http.post(Uri.parse('$baseUrl/arm/$arm'));
  }

  Future<void> guidedGoto(double lat, double lon, double alt, {double? gs}) async {
    final uri = Uri.parse('$baseUrl/guided_goto')
      .replace(queryParameters: {
        'lat': '$lat', 'lon': '$lon', 'alt': '$alt', if (gs != null) 'gs': '$gs'
      });
    await http.post(uri);
  }

  Future<void> uploadMission(List<Map<String, dynamic>> wps) async {
    await http.post(Uri.parse('$baseUrl/mission'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(wps),
    );
  }

  Future<void> cameraStart({double interval = 0, int count = 1}) async {
    await http.post(Uri.parse('$baseUrl/camera/start'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'interval': interval, 'count': count}),
    );
  }

  Future<void> cameraStop() async {
    await http.post(Uri.parse('$baseUrl/camera/stop'));
  }
}
