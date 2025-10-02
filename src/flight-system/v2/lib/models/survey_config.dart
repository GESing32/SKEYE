import 'package:latlong2/latlong.dart';
import 'camera_config.dart';

/// Survey mission configuration
/// Contains all parameters for generating a QGC-style survey mission
class SurveyConfig {
  final List<LatLng> polygon;
  final CameraConfig camera;
  final double altitude; // meters (relative)
  final double overlapFront; // percentage (0-100)
  final double overlapSide; // percentage (0-100)
  final double gridAngle; // degrees (-90 to 90)
  final bool hoverAndCapture;
  final double speed; // m/s (optional, 0 = use vehicle default)

  const SurveyConfig({
    required this.polygon,
    this.camera = CameraConfig.defaultCamera,
    this.altitude = 50.0,
    this.overlapFront = 75.0,
    this.overlapSide = 65.0,
    this.gridAngle = 0.0,
    this.hoverAndCapture = false,
    this.speed = 0.0,
  });

  /// Validate configuration
  bool get isValid {
    return polygon.length >= 3 &&
        altitude > 0 &&
        overlapFront >= 0 &&
        overlapFront < 100 &&
        overlapSide >= 0 &&
        overlapSide < 100 &&
        gridAngle >= -90 &&
        gridAngle <= 90;
  }

  /// Get calculated GSD for this configuration
  double get gsd => camera.calculateGSD(altitude);

  /// Get camera footprint at survey altitude
  Map<String, double> get footprint => camera.calculateFootprint(altitude);

  Map<String, dynamic> toJson() {
    return {
      'polygon': polygon.map((p) => {'lat': p.latitude, 'lon': p.longitude}).toList(),
      'camera': camera.toJson(),
      'altitude': altitude,
      'overlap_front': overlapFront,
      'overlap_side': overlapSide,
      'grid_angle': gridAngle,
      'hover_and_capture': hoverAndCapture,
      'speed': speed,
    };
  }

  factory SurveyConfig.fromJson(Map<String, dynamic> json) {
    return SurveyConfig(
      polygon: (json['polygon'] as List)
          .map((p) => LatLng(p['lat'] as double, p['lon'] as double))
          .toList(),
      camera: CameraConfig.fromJson(json['camera'] as Map<String, dynamic>),
      altitude: (json['altitude'] as num).toDouble(),
      overlapFront: (json['overlap_front'] as num).toDouble(),
      overlapSide: (json['overlap_side'] as num).toDouble(),
      gridAngle: (json['grid_angle'] as num).toDouble(),
      hoverAndCapture: json['hover_and_capture'] as bool,
      speed: (json['speed'] as num?)?.toDouble() ?? 0.0,
    );
  }

  SurveyConfig copyWith({
    List<LatLng>? polygon,
    CameraConfig? camera,
    double? altitude,
    double? overlapFront,
    double? overlapSide,
    double? gridAngle,
    bool? hoverAndCapture,
    double? speed,
  }) {
    return SurveyConfig(
      polygon: polygon ?? this.polygon,
      camera: camera ?? this.camera,
      altitude: altitude ?? this.altitude,
      overlapFront: overlapFront ?? this.overlapFront,
      overlapSide: overlapSide ?? this.overlapSide,
      gridAngle: gridAngle ?? this.gridAngle,
      hoverAndCapture: hoverAndCapture ?? this.hoverAndCapture,
      speed: speed ?? this.speed,
    );
  }
}

/// Survey mission result from backend
class SurveyResult {
  final List<Map<String, dynamic>> missionItems;
  final SurveyStatistics statistics;
  final List<List<LatLng>> transects;

  const SurveyResult({
    required this.missionItems,
    required this.statistics,
    required this.transects,
  });

  factory SurveyResult.fromJson(Map<String, dynamic> json) {
    return SurveyResult(
      missionItems: (json['items'] as List).cast<Map<String, dynamic>>(),
      statistics: SurveyStatistics.fromJson(json['statistics'] as Map<String, dynamic>),
      transects: (json['transects'] as List)
          .map((t) => (t as List)
              .map((p) => LatLng(p['lat'] as double, p['lon'] as double))
              .toList())
          .toList(),
    );
  }
}

/// Survey mission statistics
class SurveyStatistics {
  final double totalDistance; // meters
  final double estimatedTime; // seconds
  final int photoCount;
  final double gsd; // cm/pixel
  final double area; // square meters
  final double coverage; // square meters

  const SurveyStatistics({
    required this.totalDistance,
    required this.estimatedTime,
    required this.photoCount,
    required this.gsd,
    required this.area,
    required this.coverage,
  });

  /// Format time as MM:SS
  String get formattedTime {
    final minutes = (estimatedTime / 60).floor();
    final seconds = (estimatedTime % 60).floor();
    return '${minutes}m ${seconds}s';
  }

  /// Format distance in km or m
  String get formattedDistance {
    if (totalDistance >= 1000) {
      return '${(totalDistance / 1000).toStringAsFixed(2)} km';
    } else {
      return '${totalDistance.toStringAsFixed(0)} m';
    }
  }

  /// Format area in ha or m²
  String get formattedArea {
    if (area >= 10000) {
      return '${(area / 10000).toStringAsFixed(2)} ha';
    } else {
      return '${area.toStringAsFixed(0)} m²';
    }
  }

  factory SurveyStatistics.fromJson(Map<String, dynamic> json) {
    return SurveyStatistics(
      totalDistance: (json['total_distance_m'] as num).toDouble(),
      estimatedTime: (json['estimated_time_s'] as num).toDouble(),
      photoCount: json['photo_count'] as int,
      gsd: (json['gsd_cm_px'] as num).toDouble(),
      area: (json['area_m2'] as num).toDouble(),
      coverage: (json['coverage_m2'] as num).toDouble(),
    );
  }
}
