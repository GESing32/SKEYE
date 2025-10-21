/// Application-wide constants for SKEYE GCS
library;

import 'package:latlong2/latlong.dart';

/// Map configuration constants
class MapConstants {
  static const double defaultZoom = 13.0;
  static const double minZoom = 3.0;
  static const double maxZoom = 18.0;

  // Default center (Manila, Philippines)
  static const LatLng defaultCenter = LatLng(14.5995, 120.9842);

  // Tile server configuration
  static const String osmTileUrl = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
  static const String userAgent = 'com.skeye.gcs';
}

/// Survey planning constants
class SurveyConstants {
  // Default survey parameters
  static const double defaultAltitude = 50.0;
  static const double defaultOverlapFront = 75.0;
  static const double defaultOverlapSide = 65.0;
  static const double defaultGridAngle = 0.0;
  static const double defaultSpeed = 0.0; // 0 = vehicle default

  // Limits
  static const double minAltitude = 10.0;
  static const double maxAltitude = 150.0;
  static const double minOverlap = 50.0;
  static const double maxFrontOverlap = 90.0;
  static const double maxSideOverlap = 85.0;
  static const double minGridAngle = -90.0;
  static const double maxGridAngle = 90.0;
  static const double maxSpeed = 20.0;

  // UI dimensions
  static const double configPanelWidth = 350.0;
  static const double markerSize = 30.0;
  static const double vertexMarkerSize = 20.0;
  static const double triggerPointSize = 6.0;

  // Minimum polygon vertices
  static const int minPolygonVertices = 3;
}

/// WebSocket configuration
class WebSocketConstants {
  static const String defaultHost = 'localhost';
  static const int defaultPort = 8765;
  static const Duration reconnectDelay = Duration(seconds: 5);
  static const Duration connectionTimeout = Duration(seconds: 10);
}

/// UI Colors and styles
class UIConstants {
  // Survey colors
  static const double polygonOpacity = 0.2;
  static const double transectStrokeWidth = 2.0;
  static const double polygonStrokeWidth = 2.0;
  static const double vertexBorderWidth = 2.0;

  // Overlay padding
  static const double toolbarPadding = 16.0;
  static const double cardPadding = 16.0;
  static const double sectionSpacing = 16.0;
  static const double itemSpacing = 8.0;

  // Animation durations
  static const Duration snackBarDuration = Duration(seconds: 3);
  static const Duration errorDuration = Duration(seconds: 5);
}

/// Error messages
class ErrorMessages {
  static const String connectionError = 'Failed to connect to GCS server';
  static const String surveyGenerationError = 'Error generating survey mission';
  static const String missionUploadError = 'Error uploading mission to vehicle';
  static const String invalidPolygon = 'Please define survey area (minimum 3 points)';
  static const String invalidConfiguration = 'Invalid survey configuration';
  static const String websocketClosed = 'Connection to GCS server closed';
}

/// Success messages
class SuccessMessages {
  static const String missionGenerated = 'Survey mission generated successfully';
  static const String missionUploaded = 'Mission uploaded to vehicle';
  static const String polygonCleared = 'Survey area cleared';
}
