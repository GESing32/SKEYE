import 'package:flutter/material.dart';

/// Fence configuration panel for setting geofence parameters
/// Based on ArduPilot FENCE_* parameters
class FenceConfigPanel extends StatefulWidget {
  final FenceConfig config;
  final Function(FenceConfig) onConfigChanged;
  final VoidCallback onApply;

  const FenceConfigPanel({
    super.key,
    required this.config,
    required this.onConfigChanged,
    required this.onApply,
  });

  @override
  State<FenceConfigPanel> createState() => _FenceConfigPanelState();
}

class _FenceConfigPanelState extends State<FenceConfigPanel> {
  late FenceConfig _config;

  @override
  void initState() {
    super.initState();
    _config = widget.config;
  }

  @override
  void didUpdateWidget(FenceConfigPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.config != oldWidget.config) {
      _config = widget.config;
    }
  }

  void _updateConfig(FenceConfig newConfig) {
    setState(() {
      _config = newConfig;
    });
    widget.onConfigChanged(newConfig);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[900],
        border: Border.all(color: Colors.white24),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Icon(Icons.fence, color: Colors.orange),
              const SizedBox(width: 8),
              const Text(
                'Geofence Configuration',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              ElevatedButton.icon(
                icon: const Icon(Icons.upload),
                label: const Text('Apply to Vehicle'),
                onPressed: widget.onApply,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange.shade800,
                ),
              ),
            ],
          ),
          const Divider(height: 24),

          // Enable/Disable Fence
          SwitchListTile(
            title: const Text('Enable Geofence'),
            subtitle: const Text('FENCE_ENABLE'),
            value: _config.enabled,
            onChanged: (value) {
              _updateConfig(_config.copyWith(enabled: value));
            },
          ),
          const SizedBox(height: 16),

          // Fence Type (bitfield)
          const Text(
            'Fence Types (FENCE_TYPE)',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          CheckboxListTile(
            title: const Text('Max Altitude'),
            subtitle: const Text('Bit 0: Altitude ceiling'),
            value: _config.hasAltitudeType,
            onChanged: (value) {
              _updateConfig(_config.copyWith(
                type: value!
                    ? _config.type | FenceType.altitude
                    : _config.type & ~FenceType.altitude,
              ));
            },
          ),
          CheckboxListTile(
            title: const Text('Circle Radius'),
            subtitle: const Text('Bit 1: Cylindrical fence'),
            value: _config.hasCircleType,
            onChanged: (value) {
              _updateConfig(_config.copyWith(
                type: value!
                    ? _config.type | FenceType.circle
                    : _config.type & ~FenceType.circle,
              ));
            },
          ),
          CheckboxListTile(
            title: const Text('Polygon'),
            subtitle: const Text('Bit 2: Inclusion/exclusion polygons'),
            value: _config.hasPolygonType,
            onChanged: (value) {
              _updateConfig(_config.copyWith(
                type: value!
                    ? _config.type | FenceType.polygon
                    : _config.type & ~FenceType.polygon,
              ));
            },
          ),
          CheckboxListTile(
            title: const Text('Min Altitude'),
            subtitle: const Text('Bit 3: Altitude floor'),
            value: _config.hasMinAltType,
            onChanged: (value) {
              _updateConfig(_config.copyWith(
                type: value!
                    ? _config.type | FenceType.minAltitude
                    : _config.type & ~FenceType.minAltitude,
              ));
            },
          ),
          const SizedBox(height: 16),

          // Fence Action
          const Text(
            'Action on Breach (FENCE_ACTION)',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<FenceAction>(
            value: _config.action,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            ),
            items: FenceAction.values.map((action) {
              return DropdownMenuItem(
                value: action,
                child: Text(action.displayName),
              );
            }).toList(),
            onChanged: (value) {
              if (value != null) {
                _updateConfig(_config.copyWith(action: value));
              }
            },
          ),
          const SizedBox(height: 16),

          // Max Altitude
          if (_config.hasAltitudeType) ...[
            const Text(
              'Max Altitude (FENCE_ALT_MAX)',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: Slider(
                    value: (_config.maxAltitude * FenceConfig.metersToFeet).clamp(33.0, 1640.0),
                    min: 33,
                    max: 1640,
                    divisions: 160,
                    label: '${(_config.maxAltitude * FenceConfig.metersToFeet).toStringAsFixed(0)}ft',
                    onChanged: (value) {
                      _updateConfig(_config.copyWith(maxAltitude: value * FenceConfig.feetToMeters));
                    },
                  ),
                ),
                SizedBox(
                  width: 90,
                  child: TextField(
                    decoration: const InputDecoration(
                      suffixText: 'ft',
                      border: OutlineInputBorder(),
                      contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                    ),
                    keyboardType: TextInputType.number,
                    controller: TextEditingController(
                      text: (_config.maxAltitude * FenceConfig.metersToFeet).toStringAsFixed(0),
                    ),
                    onSubmitted: (value) {
                      final altitudeFeet = double.tryParse(value);
                      if (altitudeFeet != null) {
                        _updateConfig(_config.copyWith(maxAltitude: altitudeFeet * FenceConfig.feetToMeters));
                      }
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
          ],

          // Fence Radius
          if (_config.hasCircleType) ...[
            const Text(
              'Fence Radius (FENCE_RADIUS)',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: Slider(
                    value: (_config.radius * FenceConfig.metersToFeet).clamp(33.0, 3281.0),
                    min: 33,
                    max: 3281,
                    divisions: 324,
                    label: '${(_config.radius * FenceConfig.metersToFeet).toStringAsFixed(0)}ft',
                    onChanged: (value) {
                      _updateConfig(_config.copyWith(radius: value * FenceConfig.feetToMeters));
                    },
                  ),
                ),
                SizedBox(
                  width: 90,
                  child: TextField(
                    decoration: const InputDecoration(
                      suffixText: 'ft',
                      border: OutlineInputBorder(),
                      contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                    ),
                    keyboardType: TextInputType.number,
                    controller: TextEditingController(
                      text: (_config.radius * FenceConfig.metersToFeet).toStringAsFixed(0),
                    ),
                    onSubmitted: (value) {
                      final radiusFeet = double.tryParse(value);
                      if (radiusFeet != null) {
                        _updateConfig(_config.copyWith(radius: radiusFeet * FenceConfig.feetToMeters));
                      }
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
          ],

          // Min Altitude
          if (_config.hasMinAltType) ...[
            const Text(
              'Min Altitude (FENCE_ALT_MIN)',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: Slider(
                    value: (_config.minAltitude * FenceConfig.metersToFeet).clamp(-328.0, 328.0),
                    min: -328,
                    max: 328,
                    divisions: 131,
                    label: '${(_config.minAltitude * FenceConfig.metersToFeet).toStringAsFixed(0)}ft',
                    onChanged: (value) {
                      _updateConfig(_config.copyWith(minAltitude: value * FenceConfig.feetToMeters));
                    },
                  ),
                ),
                SizedBox(
                  width: 90,
                  child: TextField(
                    decoration: const InputDecoration(
                      suffixText: 'ft',
                      border: OutlineInputBorder(),
                      contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                    ),
                    keyboardType: TextInputType.number,
                    controller: TextEditingController(
                      text: (_config.minAltitude * FenceConfig.metersToFeet).toStringAsFixed(0),
                    ),
                    onSubmitted: (value) {
                      final altitudeFeet = double.tryParse(value);
                      if (altitudeFeet != null) {
                        _updateConfig(_config.copyWith(minAltitude: altitudeFeet * FenceConfig.feetToMeters));
                      }
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
          ],

          // Margin
          const Text(
            'Fence Margin (FENCE_MARGIN)',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          const Text(
            'Distance from fence to trigger breach',
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Slider(
                  value: (_config.margin * FenceConfig.metersToFeet).clamp(3.3, 65.6),
                  min: 3.3,
                  max: 65.6,
                  divisions: 62,
                  label: '${(_config.margin * FenceConfig.metersToFeet).toStringAsFixed(1)}ft',
                  onChanged: (value) {
                    _updateConfig(_config.copyWith(margin: value * FenceConfig.feetToMeters));
                  },
                ),
              ),
              SizedBox(
                width: 90,
                child: TextField(
                  decoration: const InputDecoration(
                    suffixText: 'ft',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                  ),
                  keyboardType: TextInputType.number,
                  controller: TextEditingController(
                    text: (_config.margin * FenceConfig.metersToFeet).toStringAsFixed(1),
                  ),
                  onSubmitted: (value) {
                    final marginFeet = double.tryParse(value);
                    if (marginFeet != null) {
                      _updateConfig(_config.copyWith(margin: marginFeet * FenceConfig.feetToMeters));
                    }
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Fence configuration data class
class FenceConfig {
  final bool enabled;
  final int type;  // Bitfield: 0=disabled, 1=altitude, 2=circle, 4=polygon, 8=minAltitude
  final FenceAction action;
  final double maxAltitude;  // meters (stored in meters, displayed in feet)
  final double minAltitude;  // meters (stored in meters, displayed in feet)
  final double radius;  // meters (stored in meters, displayed in feet)
  final double margin;  // meters (stored in meters, displayed in feet)

  // Conversion constants
  static const double metersToFeet = 3.28084;
  static const double feetToMeters = 0.3048;

  const FenceConfig({
    this.enabled = false,
    this.type = 0,
    this.action = FenceAction.reportOnly,
    this.maxAltitude = 100.0,
    this.minAltitude = -10.0,
    this.radius = 300.0,
    this.margin = 2.0,
  });

  bool get hasAltitudeType => (type & FenceType.altitude) != 0;
  bool get hasCircleType => (type & FenceType.circle) != 0;
  bool get hasPolygonType => (type & FenceType.polygon) != 0;
  bool get hasMinAltType => (type & FenceType.minAltitude) != 0;

  FenceConfig copyWith({
    bool? enabled,
    int? type,
    FenceAction? action,
    double? maxAltitude,
    double? minAltitude,
    double? radius,
    double? margin,
  }) {
    return FenceConfig(
      enabled: enabled ?? this.enabled,
      type: type ?? this.type,
      action: action ?? this.action,
      maxAltitude: maxAltitude ?? this.maxAltitude,
      minAltitude: minAltitude ?? this.minAltitude,
      radius: radius ?? this.radius,
      margin: margin ?? this.margin,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'enabled': enabled,
      'type': type,
      'action': action.value,
      'max_altitude': maxAltitude,
      'min_altitude': minAltitude,
      'radius': radius,
      'margin': margin,
    };
  }

  factory FenceConfig.fromJson(Map<String, dynamic> json) {
    return FenceConfig(
      enabled: json['enabled'] ?? false,
      type: json['type'] ?? 0,
      action: FenceAction.fromValue(json['action'] ?? 0),
      maxAltitude: (json['max_altitude'] ?? 100.0).toDouble(),
      minAltitude: (json['min_altitude'] ?? -10.0).toDouble(),
      radius: (json['radius'] ?? 300.0).toDouble(),
      margin: (json['margin'] ?? 2.0).toDouble(),
    );
  }
}

/// Fence type bitfield values
class FenceType {
  static const int altitude = 1;      // Bit 0: Max altitude
  static const int circle = 2;        // Bit 1: Circle radius
  static const int polygon = 4;       // Bit 2: Inclusion/exclusion polygons
  static const int minAltitude = 8;   // Bit 3: Min altitude
}

/// Fence action on breach
enum FenceAction {
  reportOnly(0, 'Report Only'),
  rtl(1, 'RTL (Return to Launch)'),
  land(2, 'Land'),
  smartRtl(3, 'SmartRTL'),
  brake(4, 'Brake'),
  smartRtlOrLand(5, 'SmartRTL or Land');

  final int value;
  final String displayName;

  const FenceAction(this.value, this.displayName);

  static FenceAction fromValue(int value) {
    return FenceAction.values.firstWhere(
      (action) => action.value == value,
      orElse: () => FenceAction.reportOnly,
    );
  }
}
