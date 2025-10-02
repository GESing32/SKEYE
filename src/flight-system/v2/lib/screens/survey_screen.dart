import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../models/survey_config.dart';
import '../widgets/survey_config_panel.dart';

/// Survey planning screen with QGC-style functionality
/// Integrates polygon editor, config panel, and mission generation
class SurveyScreen extends StatefulWidget {
  final WebSocketChannel? channel;
  final LatLng? initialCenter;

  const SurveyScreen({
    super.key,
    this.channel,
    this.initialCenter,
  });

  @override
  State<SurveyScreen> createState() => _SurveyScreenState();
}

class _SurveyScreenState extends State<SurveyScreen> {
  final MapController _mapController = MapController();
  List<LatLng> _polygon = [];
  SurveyConfig _config = const SurveyConfig(
    polygon: [],
  );
  SurveyResult? _result;
  bool _isGenerating = false;
  bool _showConfig = true;

  @override
  void initState() {
    super.initState();
    _setupWebSocketListener();
  }

  void _setupWebSocketListener() {
    widget.channel?.stream.listen(
      (message) {
        try {
          final data = jsonDecode(message);
          if (data['type'] == 'SURVEY_RESULT') {
            setState(() {
              _result = SurveyResult.fromJson(data);
              _isGenerating = false;
            });
            _showResultDialog();
          }
        } catch (e) {
          setState(() {
            _isGenerating = false;
          });
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Error parsing survey result: $e')),
            );
          }
        }
      },
      onError: (error) {
        setState(() {
          _isGenerating = false;
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Connection error: $error'),
              backgroundColor: Colors.red,
              duration: const Duration(seconds: 5),
            ),
          );
        }
      },
      onDone: () {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Connection closed'),
              duration: Duration(seconds: 3),
            ),
          );
        }
      },
    );
  }

  void _onPolygonChanged(List<LatLng> polygon) {
    setState(() {
      _polygon = polygon;
      _config = _config.copyWith(polygon: polygon);
    });
  }

  void _onConfigChanged(SurveyConfig config) {
    setState(() {
      _config = config;
    });
  }

  Future<void> _generateSurvey() async {
    if (!_config.isValid) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Invalid survey configuration')),
      );
      return;
    }

    setState(() {
      _isGenerating = true;
    });

    try {
      final command = {
        'cmd': 'survey_plan',
        'polygon': _polygon.map((p) => {'lat': p.latitude, 'lon': p.longitude}).toList(),
        'camera': _config.camera.toJson(),
        'altitude': _config.altitude,
        'overlap_front': _config.overlapFront,
        'overlap_side': _config.overlapSide,
        'grid_angle': _config.gridAngle,
        'hover_and_capture': _config.hoverAndCapture,
      };

      widget.channel?.sink.add(jsonEncode(command));
    } catch (e) {
      setState(() {
        _isGenerating = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error generating survey: $e')),
        );
      }
    }
  }

  void _showResultDialog() {
    if (_result == null) return;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Survey Mission Generated'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Mission Items: ${_result!.missionItems.length}'),
              Text('Distance: ${_result!.statistics.formattedDistance}'),
              Text('Time: ${_result!.statistics.formattedTime}'),
              Text('Photos: ${_result!.statistics.photoCount}'),
              Text('GSD: ${_result!.statistics.gsd.toStringAsFixed(2)} cm/px'),
              Text('Area: ${_result!.statistics.formattedArea}'),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _uploadMission();
            },
            child: const Text('Upload Mission'),
          ),
        ],
      ),
    );
  }

  Future<void> _uploadMission() async {
    if (_result == null) return;

    try {
      final command = {
        'cmd': 'mission_upload',
        'items': _result!.missionItems,
      };
      widget.channel?.sink.add(jsonEncode(command));

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Mission uploaded to vehicle')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error uploading mission: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Survey Planning'),
        actions: [
          IconButton(
            icon: Icon(_showConfig ? Icons.map : Icons.settings),
            tooltip: _showConfig ? 'Show Map' : 'Show Config',
            onPressed: () {
              setState(() {
                _showConfig = !_showConfig;
              });
            },
          ),
          if (_polygon.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.delete_outline),
              tooltip: 'Clear polygon',
              onPressed: () {
                setState(() {
                  _polygon.clear();
                  _config = _config.copyWith(polygon: []);
                  _result = null;
                });
              },
            ),
        ],
      ),
      body: _isGenerating
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Generating survey mission...'),
                ],
              ),
            )
          : Row(
              children: [
                // Map view
                Expanded(
                  flex: 2,
                  child: FlutterMap(
                    mapController: _mapController,
                    options: MapOptions(
                      initialCenter: widget.initialCenter ?? LatLng(14.5995, 120.9842), // Manila default
                      initialZoom: 13.0,
                      onTap: (tapPosition, latLng) {
                        if (!_showConfig) {
                          _onPolygonChanged([..._polygon, latLng]);
                        }
                      },
                    ),
                    children: [
                      TileLayer(
                        urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                        userAgentPackageName: 'com.skeye.gcs',
                      ),
                      // Polygon editor
                      if (!_showConfig)
                        PolygonLayer(
                          polygons: [
                            if (_polygon.isNotEmpty)
                              Polygon(
                                points: _polygon,
                                color: Colors.blue.withValues(alpha: 0.2),
                                borderColor: Colors.blue,
                                borderStrokeWidth: 2.0,
                              ),
                          ],
                        ),
                      // Vertex markers
                      if (!_showConfig && _polygon.isNotEmpty)
                        MarkerLayer(
                          markers: _polygon.asMap().entries.map((entry) {
                            final index = entry.key;
                            final point = entry.value;
                            return Marker(
                              point: point,
                              width: 30,
                              height: 30,
                              child: Container(
                                decoration: BoxDecoration(
                                  color: Colors.red,
                                  shape: BoxShape.circle,
                                  border: Border.all(color: Colors.white, width: 2),
                                ),
                                child: Center(
                                  child: Text(
                                    '${index + 1}',
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 12,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ),
                            );
                          }).toList(),
                        ),
                      // Survey transects
                      if (_result != null)
                        PolylineLayer(
                          polylines: _result!.transects.map((transect) {
                            return Polyline(
                              points: transect,
                              color: Colors.green,
                              strokeWidth: 2.0,
                            );
                          }).toList(),
                        ),
                      // Trigger points
                      if (_result != null)
                        MarkerLayer(
                          markers: _result!.transects.expand((transect) {
                            return transect.map((point) => Marker(
                              point: point,
                              width: 6,
                              height: 6,
                              child: Container(
                                decoration: const BoxDecoration(
                                  color: Colors.orange,
                                  shape: BoxShape.circle,
                                ),
                              ),
                            ));
                          }).toList(),
                        ),
                    ],
                  ),
                ),

                // Config panel
                if (_showConfig)
                  SizedBox(
                    width: 350,
                    child: Column(
                      children: [
                        Expanded(
                          child: SurveyConfigPanel(
                            config: _config,
                            onConfigChanged: _onConfigChanged,
                            onGenerate: _generateSurvey,
                            canGenerate: _config.isValid && !_isGenerating,
                          ),
                        ),
                        if (_result != null)
                          SurveyStatsWidget(stats: _result!.statistics),
                      ],
                    ),
                  ),
              ],
            ),
      floatingActionButton: !_showConfig && _polygon.isNotEmpty
          ? FloatingActionButton(
              onPressed: () {
                setState(() {
                  _polygon.removeLast();
                  _config = _config.copyWith(polygon: _polygon);
                });
              },
              child: const Icon(Icons.undo),
            )
          : null,
    );
  }

  @override
  void dispose() {
    _mapController.dispose();
    super.dispose();
  }
}
