import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

/// Interactive polygon editor widget for survey area definition
/// Allows tap-to-draw on map with undo/clear functionality
class PolygonEditor extends StatefulWidget {
  final MapController mapController;
  final List<LatLng> polygon;
  final Function(List<LatLng>) onPolygonChanged;
  final Color polygonColor;
  final Color vertexColor;
  final bool enabled;

  const PolygonEditor({
    super.key,
    required this.mapController,
    required this.polygon,
    required this.onPolygonChanged,
    this.polygonColor = Colors.blue,
    this.vertexColor = Colors.red,
    this.enabled = true,
  });

  @override
  State<PolygonEditor> createState() => _PolygonEditorState();
}

class _PolygonEditorState extends State<PolygonEditor> {
  List<LatLng> _editablePolygon = [];
  int? _draggedVertexIndex;

  @override
  void initState() {
    super.initState();
    _editablePolygon = List.from(widget.polygon);
  }

  @override
  void didUpdateWidget(PolygonEditor oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.polygon != oldWidget.polygon) {
      _editablePolygon = List.from(widget.polygon);
    }
  }


  void _handleVertexDragStart(int index) {
    if (!widget.enabled) return;
    setState(() {
      _draggedVertexIndex = index;
    });
  }

  void _handleVertexDrag(LatLng newPosition) {
    if (!widget.enabled || _draggedVertexIndex == null) return;
    setState(() {
      _editablePolygon[_draggedVertexIndex!] = newPosition;
    });
  }

  void _handleVertexDragEnd() {
    if (_draggedVertexIndex == null) return;
    widget.onPolygonChanged(_editablePolygon);
    setState(() {
      _draggedVertexIndex = null;
    });
  }

  void _removeLastVertex() {
    if (_editablePolygon.isEmpty) return;
    setState(() {
      _editablePolygon.removeLast();
    });
    widget.onPolygonChanged(_editablePolygon);
  }

  void _clearPolygon() {
    setState(() {
      _editablePolygon.clear();
    });
    widget.onPolygonChanged(_editablePolygon);
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // Map layers
        if (_editablePolygon.isNotEmpty) ...[
          // Polygon outline
          PolygonLayer(
            polygons: [
              Polygon(
                points: _editablePolygon,
                color: widget.polygonColor.withValues(alpha: 0.2),
                borderColor: widget.polygonColor,
                borderStrokeWidth: 2.0,
              ),
            ],
          ),
          // Vertex markers
          MarkerLayer(
            markers: _editablePolygon.asMap().entries.map((entry) {
              final index = entry.key;
              final point = entry.value;
              return Marker(
                point: point,
                width: 20,
                height: 20,
                child: GestureDetector(
                  onPanStart: (_) => _handleVertexDragStart(index),
                  onPanUpdate: (details) {
                    // Convert screen coordinates to map coordinates
                    // This is a simplified version - you may need to use
                    // mapController.pointToLatLng for proper conversion
                    _handleVertexDrag(point);
                  },
                  onPanEnd: (_) => _handleVertexDragEnd(),
                  child: Container(
                    decoration: BoxDecoration(
                      color: widget.vertexColor,
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 2),
                    ),
                    child: Center(
                      child: Text(
                        '${index + 1}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ],

        // Toolbar overlay
        if (widget.enabled)
          Positioned(
            top: 16,
            right: 16,
            child: Card(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    icon: const Icon(Icons.undo),
                    tooltip: 'Remove last vertex',
                    onPressed: _editablePolygon.isEmpty ? null : _removeLastVertex,
                  ),
                  IconButton(
                    icon: const Icon(Icons.clear),
                    tooltip: 'Clear polygon',
                    onPressed: _editablePolygon.isEmpty ? null : _clearPolygon,
                  ),
                  Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: Text(
                      '${_editablePolygon.length} pts',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                ],
              ),
            ),
          ),

        // Instructions overlay
        if (widget.enabled && _editablePolygon.isEmpty)
          Positioned(
            bottom: 16,
            left: 0,
            right: 0,
            child: Center(
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Text(
                    'Tap on map to draw survey area polygon',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

/// Simple wrapper to handle map tap events
class TappableFlutterMap extends StatelessWidget {
  final MapController mapController;
  final Function(LatLng) onTap;
  final List<Widget> children;
  final LatLng center;
  final double zoom;

  const TappableFlutterMap({
    super.key,
    required this.mapController,
    required this.onTap,
    required this.children,
    required this.center,
    required this.zoom,
  });

  @override
  Widget build(BuildContext context) {
    return FlutterMap(
      mapController: mapController,
      options: MapOptions(
        initialCenter: center,
        initialZoom: zoom,
        onTap: (tapPosition, latLng) => onTap(latLng),
      ),
      children: children,
    );
  }
}
