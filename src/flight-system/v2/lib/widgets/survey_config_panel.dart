import 'package:flutter/material.dart';
import '../models/camera_config.dart';
import '../models/survey_config.dart';

/// Survey configuration panel widget
/// Provides UI for configuring survey parameters matching QGC functionality
class SurveyConfigPanel extends StatefulWidget {
  final SurveyConfig config;
  final Function(SurveyConfig) onConfigChanged;
  final VoidCallback? onGenerate;
  final bool canGenerate;

  const SurveyConfigPanel({
    super.key,
    required this.config,
    required this.onConfigChanged,
    this.onGenerate,
    this.canGenerate = false,
  });

  @override
  State<SurveyConfigPanel> createState() => _SurveyConfigPanelState();
}

class _SurveyConfigPanelState extends State<SurveyConfigPanel> {
  late CameraConfig _selectedCamera;
  late double _altitude;
  late double _overlapFront;
  late double _overlapSide;
  late double _gridAngle;
  late bool _hoverAndCapture;
  late double _speed;

  @override
  void initState() {
    super.initState();
    _updateFromConfig();
  }

  @override
  void didUpdateWidget(SurveyConfigPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.config != oldWidget.config) {
      _updateFromConfig();
    }
  }

  void _updateFromConfig() {
    _selectedCamera = widget.config.camera;
    _altitude = widget.config.altitude;
    _overlapFront = widget.config.overlapFront;
    _overlapSide = widget.config.overlapSide;
    _gridAngle = widget.config.gridAngle;
    _hoverAndCapture = widget.config.hoverAndCapture;
    _speed = widget.config.speed;
  }

  void _notifyChange() {
    widget.onConfigChanged(
      widget.config.copyWith(
        camera: _selectedCamera,
        altitude: _altitude,
        overlapFront: _overlapFront,
        overlapSide: _overlapSide,
        gridAngle: _gridAngle,
        hoverAndCapture: _hoverAndCapture,
        speed: _speed,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final gsd = _selectedCamera.calculateGSD(_altitude);
    final footprint = _selectedCamera.calculateFootprint(_altitude);

    return Card(
      margin: const EdgeInsets.all(16),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Survey Configuration',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const Divider(),

            // Camera selection
            const SizedBox(height: 16),
            Text(
              'Camera',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<CameraConfig>(
              initialValue: _selectedCamera,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
              items: CameraConfig.presets.map((camera) {
                return DropdownMenuItem(
                  value: camera,
                  child: Text(camera.name),
                );
              }).toList(),
              onChanged: (camera) {
                if (camera != null) {
                  setState(() {
                    _selectedCamera = camera;
                  });
                  _notifyChange();
                }
              },
            ),

            // Camera specs display
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.grey.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Sensor: ${_selectedCamera.sensorWidth}×${_selectedCamera.sensorHeight}mm',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  Text(
                    'Resolution: ${_selectedCamera.imageWidth}×${_selectedCamera.imageHeight}px',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  Text(
                    'Focal Length: ${_selectedCamera.focalLength}mm',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),

            // Altitude
            const SizedBox(height: 16),
            Text(
              'Altitude (meters)',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: Slider(
                    value: _altitude,
                    min: 10,
                    max: 150,
                    divisions: 28,
                    label: '${_altitude.toStringAsFixed(0)}m',
                    onChanged: (value) {
                      setState(() {
                        _altitude = value;
                      });
                      _notifyChange();
                    },
                  ),
                ),
                SizedBox(
                  width: 60,
                  child: Text(
                    '${_altitude.toStringAsFixed(0)}m',
                    style: Theme.of(context).textTheme.titleMedium,
                    textAlign: TextAlign.right,
                  ),
                ),
              ],
            ),

            // GSD display
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.blue.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'GSD: ${gsd.toStringAsFixed(2)} cm/px',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  Text(
                    'Footprint: ${footprint['width']!.toStringAsFixed(1)}×${footprint['height']!.toStringAsFixed(1)}m',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),

            // Front overlap
            const SizedBox(height: 16),
            Text(
              'Front Overlap (${_overlapFront.toStringAsFixed(0)}%)',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Slider(
              value: _overlapFront,
              min: 50,
              max: 90,
              divisions: 40,
              label: '${_overlapFront.toStringAsFixed(0)}%',
              onChanged: (value) {
                setState(() {
                  _overlapFront = value;
                });
                _notifyChange();
              },
            ),

            // Side overlap
            const SizedBox(height: 8),
            Text(
              'Side Overlap (${_overlapSide.toStringAsFixed(0)}%)',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Slider(
              value: _overlapSide,
              min: 50,
              max: 85,
              divisions: 35,
              label: '${_overlapSide.toStringAsFixed(0)}%',
              onChanged: (value) {
                setState(() {
                  _overlapSide = value;
                });
                _notifyChange();
              },
            ),

            // Grid angle
            const SizedBox(height: 16),
            Text(
              'Grid Angle (${_gridAngle.toStringAsFixed(0)}°)',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Slider(
              value: _gridAngle,
              min: -90,
              max: 90,
              divisions: 36,
              label: '${_gridAngle.toStringAsFixed(0)}°',
              onChanged: (value) {
                setState(() {
                  _gridAngle = value;
                });
                _notifyChange();
              },
            ),

            // Speed
            const SizedBox(height: 16),
            Text(
              'Speed (${_speed == 0 ? 'Default' : '${_speed.toStringAsFixed(1)} m/s'})',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Slider(
              value: _speed,
              min: 0,
              max: 20,
              divisions: 40,
              label: _speed == 0 ? 'Default' : '${_speed.toStringAsFixed(1)} m/s',
              onChanged: (value) {
                setState(() {
                  _speed = value;
                });
                _notifyChange();
              },
            ),

            // Hover and capture
            const SizedBox(height: 8),
            SwitchListTile(
              title: const Text('Hover and Capture'),
              subtitle: const Text('Stop at each photo location'),
              value: _hoverAndCapture,
              onChanged: (value) {
                setState(() {
                  _hoverAndCapture = value;
                });
                _notifyChange();
              },
            ),

            // Generate button
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: widget.canGenerate ? widget.onGenerate : null,
              icon: const Icon(Icons.check),
              label: const Text('Generate Survey Mission'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.all(16),
              ),
            ),

            // Validation warning
            if (!widget.config.isValid)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'Please define survey area (minimum 3 points)',
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.error,
                    fontSize: 12,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// Compact survey statistics display
class SurveyStatsWidget extends StatelessWidget {
  final SurveyStatistics stats;

  const SurveyStatsWidget({
    super.key,
    required this.stats,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Mission Statistics',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const Divider(),
            _buildStatRow(context, 'Distance', stats.formattedDistance),
            _buildStatRow(context, 'Time', stats.formattedTime),
            _buildStatRow(context, 'Photos', '${stats.photoCount}'),
            _buildStatRow(context, 'GSD', '${stats.gsd.toStringAsFixed(2)} cm/px'),
            _buildStatRow(context, 'Area', stats.formattedArea),
          ],
        ),
      ),
    );
  }

  Widget _buildStatRow(BuildContext context, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
        ],
      ),
    );
  }
}
