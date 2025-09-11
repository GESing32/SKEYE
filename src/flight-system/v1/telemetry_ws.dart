import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class TelemetryStream {
  final WebSocketChannel channel;
  TelemetryStream(String wsUrl) : channel = WebSocketChannel.connect(Uri.parse(wsUrl));

  Stream<Map<String, dynamic>> get stream => channel.stream.map((e) => jsonDecode(e as String));
  void dispose() => channel.sink.close();
}
