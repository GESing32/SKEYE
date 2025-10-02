/// Camera configuration for survey planning
/// Sentera Double 4K camera specifications
class CameraConfig {
  final String name;
  final double sensorWidth; // mm
  final double sensorHeight; // mm
  final double focalLength; // mm
  final int imageWidth; // pixels
  final int imageHeight; // pixels

  const CameraConfig({
    required this.name,
    required this.sensorWidth,
    required this.sensorHeight,
    required this.focalLength,
    required this.imageWidth,
    required this.imageHeight,
  });

  /// Sentera Double 4K Camera - 8mm Wide Lens (DEFAULT)
  /// Connected via MAVLink TELEM2 on Pixhawk 6x
  /// Model: 27060 Double 4K
  /// Best for: General mapping, large area coverage
  static const senteraDouble4kWide = CameraConfig(
    name: 'Sentera Double 4K (8mm Wide)',
    sensorWidth: 6.3,      // 1/2.3" sensor
    sensorHeight: 4.7,
    focalLength: 8.0,      // Wide angle lens
    imageWidth: 3840,      // 4K resolution
    imageHeight: 2160,
  );

  /// Sentera Double 4K Camera - 25mm Narrow Lens (OPTIONAL)
  /// Connected via MAVLink TELEM2 on Pixhawk 6x
  /// Model: 27060 Double 4K
  /// Best for: High-resolution inspection, detail work
  static const senteraDouble4kNarrow = CameraConfig(
    name: 'Sentera Double 4K (25mm Narrow)',
    sensorWidth: 6.3,      // 1/2.3" sensor
    sensorHeight: 4.7,
    focalLength: 25.0,     // Narrow angle lens
    imageWidth: 3840,      // 4K resolution
    imageHeight: 2160,
  );

  /// Default camera preset (8mm wide lens)
  static const defaultCamera = senteraDouble4kWide;

  /// Available camera presets (only Sentera cameras)
  static const List<CameraConfig> presets = [
    senteraDouble4kWide,
    senteraDouble4kNarrow,
  ];

  /// Calculate Ground Sample Distance (cm/pixel) at given altitude
  double calculateGSD(double altitudeMeters) {
    return (sensorWidth * altitudeMeters * 100.0) / (focalLength * imageWidth);
  }

  /// Calculate footprint dimensions (meters) at given altitude
  Map<String, double> calculateFootprint(double altitudeMeters) {
    final width = (sensorWidth * altitudeMeters) / focalLength;
    final height = (sensorHeight * altitudeMeters) / focalLength;
    return {'width': width, 'height': height};
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'sensor_width': sensorWidth,
      'sensor_height': sensorHeight,
      'focal_length': focalLength,
      'image_width': imageWidth,
      'image_height': imageHeight,
    };
  }

  factory CameraConfig.fromJson(Map<String, dynamic> json) {
    return CameraConfig(
      name: json['name'] as String,
      sensorWidth: (json['sensor_width'] as num).toDouble(),
      sensorHeight: (json['sensor_height'] as num).toDouble(),
      focalLength: (json['focal_length'] as num).toDouble(),
      imageWidth: json['image_width'] as int,
      imageHeight: json['image_height'] as int,
    );
  }

  CameraConfig copyWith({
    String? name,
    double? sensorWidth,
    double? sensorHeight,
    double? focalLength,
    int? imageWidth,
    int? imageHeight,
  }) {
    return CameraConfig(
      name: name ?? this.name,
      sensorWidth: sensorWidth ?? this.sensorWidth,
      sensorHeight: sensorHeight ?? this.sensorHeight,
      focalLength: focalLength ?? this.focalLength,
      imageWidth: imageWidth ?? this.imageWidth,
      imageHeight: imageHeight ?? this.imageHeight,
    );
  }

  @override
  String toString() => name;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is CameraConfig &&
          runtimeType == other.runtimeType &&
          name == other.name &&
          sensorWidth == other.sensorWidth &&
          sensorHeight == other.sensorHeight &&
          focalLength == other.focalLength &&
          imageWidth == other.imageWidth &&
          imageHeight == other.imageHeight;

  @override
  int get hashCode =>
      name.hashCode ^
      sensorWidth.hashCode ^
      sensorHeight.hashCode ^
      focalLength.hashCode ^
      imageWidth.hashCode ^
      imageHeight.hashCode;
}
