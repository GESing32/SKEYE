import 'package:http/http.dart' as http;
import 'package:http/retry.dart';

/// Custom HTTP client with timeout and retry logic for map tiles
class TileHttpClient extends http.BaseClient {
  final http.Client _inner;

  TileHttpClient() : _inner = RetryClient(
    http.Client(),
    retries: 3,
    when: (response) {
      // Retry on network errors and 5xx server errors
      return response.statusCode >= 500;
    },
    whenError: (error, stackTrace) {
      // Retry on timeout and socket exceptions
      return true;
    },
    delay: (retryCount) => Duration(milliseconds: 500 * retryCount),
  );

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    // Add 10 second timeout for tile requests
    return _inner.send(request).timeout(
      const Duration(seconds: 10),
      onTimeout: () {
        throw http.ClientException('Connection timeout', request.url);
      },
    );
  }

  @override
  void close() {
    _inner.close();
  }
}
