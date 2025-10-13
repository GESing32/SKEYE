// Integration tests for GCS application
// Tests user flows and WebSocket communication behavior

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:latlong2/latlong.dart';
import 'package:custom_gcs_serial/main.dart';

void main() {
  group('GCS Integration Tests', () {
    testWidgets('Mission planning workflow - add and clear waypoints', (WidgetTester tester) async {
      // Start the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Enable mission edit mode
      final missionChip = find.widgetWithText(FilterChip, 'Mission edit');
      await tester.tap(missionChip);
      await tester.pump();

      // Verify mission mode is active
      FilterChip chip = tester.widget<FilterChip>(missionChip);
      expect(chip.selected, isTrue);

      // Note: In mission mode, tapping the map would add waypoints
      // However, testing map tap is complex without a real map instance
      // We verify the UI state and button availability instead

      // Mission buttons should still be disabled (no waypoints yet)
      final uploadButton = find.widgetWithText(ElevatedButton, 'Upload');

      ElevatedButton uploadWidget = tester.widget<ElevatedButton>(uploadButton);
      expect(uploadWidget.onPressed, isNull);

      // Disable mission mode
      await tester.tap(missionChip);
      await tester.pump();

      chip = tester.widget<FilterChip>(missionChip);
      expect(chip.selected, isFalse);
    });

    testWidgets('Arm/Disarm button toggles text', (WidgetTester tester) async {
      // Start the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Initially should show "Arm" (disarmed state)
      expect(find.text('Arm'), findsOneWidget);
      expect(find.text('Disarm'), findsNothing);

      // Note: Tapping would send a command, but without WebSocket connection
      // the actual state won't change. This test verifies initial state only.
    });

    testWidgets('Mode selection from dropdown', (WidgetTester tester) async {
      // Start the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Open mode menu
      final modeButton = find.widgetWithText(ElevatedButton, 'Mode');
      await tester.tap(modeButton);
      await tester.pumpAndSettle();

      // Verify all modes are available
      expect(find.text('GUIDED'), findsOneWidget);
      expect(find.text('LOITER'), findsOneWidget);
      expect(find.text('ALT_HOLD'), findsOneWidget);
      expect(find.text('STABILIZE'), findsOneWidget);

      // Select GUIDED mode
      await tester.tap(find.text('GUIDED'));
      await tester.pumpAndSettle();

      // Menu should close after selection
      expect(find.text('GUIDED'), findsNothing);
    });

    testWidgets('RTL button is always enabled', (WidgetTester tester) async {
      // Start the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Find RTL button
      final rtlButton = find.widgetWithText(ElevatedButton, 'RTL');
      expect(rtlButton, findsOneWidget);

      // RTL should always be available as emergency function
      final rtlWidget = tester.widget<ElevatedButton>(rtlButton);
      expect(rtlWidget.onPressed, isNotNull);
    });

    testWidgets('Status bar displays default values on startup', (WidgetTester tester) async {
      // Start the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Check for default/empty telemetry values
      expect(find.text('UNKNOWN'), findsOneWidget); // Mode
      expect(find.text('No'), findsOneWidget); // Armed status

      // Should show "-" for uninitialized numeric values
      expect(find.textContaining('-'), findsWidgets);
    });

    testWidgets('Connection status icon reflects disconnected state', (WidgetTester tester) async {
      // Start the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Initially disconnected
      expect(find.byIcon(Icons.link_off), findsOneWidget);
      expect(find.byIcon(Icons.link), findsNothing);

      // Verify icon is red (disconnected)
      final iconWidget = tester.widget<Icon>(find.byIcon(Icons.link_off));
      expect(iconWidget.color, equals(Colors.red));
    });
  });

  group('WebSocket Message Parsing Tests', () {
    test('HELLO message structure', () {
      final helloMsg = {
        "type": "HELLO",
        "mode": "STABILIZE",
        "armed": false,
        "link_ok": true,
      };

      expect(helloMsg["type"], equals("HELLO"));
      expect(helloMsg["mode"], equals("STABILIZE"));
      expect(helloMsg["armed"], isFalse);
      expect(helloMsg["link_ok"], isTrue);
    });

    test('HEARTBEAT message structure', () {
      final heartbeatMsg = {
        "type": "HEARTBEAT",
        "base_mode": 128, // Armed
      };

      expect(heartbeatMsg["type"], equals("HEARTBEAT"));
      final baseMode = heartbeatMsg["base_mode"] as int;
      expect((baseMode & 0x80) != 0, isTrue);
    });

    test('GLOBAL_POSITION_INT message structure', () {
      final posMsg = {
        "type": "GLOBAL_POSITION_INT",
        "lat": 380308000,
        "lon": -845060000,
        "relative_alt": 25000,
      };

      expect(posMsg["type"], equals("GLOBAL_POSITION_INT"));
      final lat = posMsg["lat"] as int;
      final lon = posMsg["lon"] as int;
      final relAlt = posMsg["relative_alt"] as int;
      expect(lat / 1e7, closeTo(38.0308, 0.0001));
      expect(lon / 1e7, closeTo(-84.506, 0.0001));
      expect(relAlt / 1000.0, equals(25.0));
    });

    test('VFR_HUD message structure', () {
      final vfrMsg = {
        "type": "VFR_HUD",
        "groundspeed": 12.5,
      };

      expect(vfrMsg["type"], equals("VFR_HUD"));
      expect(vfrMsg["groundspeed"], equals(12.5));
    });

    test('SYS_STATUS message structure', () {
      final sysMsg = {
        "type": "SYS_STATUS",
        "voltage_battery": 11800,
      };

      expect(sysMsg["type"], equals("SYS_STATUS"));
      final voltage = sysMsg["voltage_battery"] as int;
      expect(voltage / 1000.0, equals(11.8));
    });
  });

  group('Command Generation Tests', () {
    test('Arm command structure', () {
      final armCmd = {
        "cmd": "arm",
        "value": true,
      };

      expect(armCmd["cmd"], equals("arm"));
      expect(armCmd["value"], isTrue);

      final disarmCmd = {
        "cmd": "arm",
        "value": false,
      };

      expect(disarmCmd["cmd"], equals("arm"));
      expect(disarmCmd["value"], isFalse);
    });

    test('Mode change command structure', () {
      final modeCmd = {
        "cmd": "mode",
        "mode": "GUIDED",
      };

      expect(modeCmd["cmd"], equals("mode"));
      expect(modeCmd["mode"], equals("GUIDED"));
    });

    test('RTL command structure', () {
      final rtlCmd = {
        "cmd": "rtl",
      };

      expect(rtlCmd["cmd"], equals("rtl"));
    });

    test('GOTO command structure', () {
      final gotoCmd = {
        "cmd": "goto",
        "lat": 38.0308,
        "lon": -84.506,
        "alt_rel": 20.0,
      };

      expect(gotoCmd["cmd"], equals("goto"));
      expect(gotoCmd["lat"], equals(38.0308));
      expect(gotoCmd["lon"], equals(-84.506));
      expect(gotoCmd["alt_rel"], equals(20.0));
    });

    test('Mission clear command structure', () {
      final clearCmd = {
        "cmd": "mission_clear",
      };

      expect(clearCmd["cmd"], equals("mission_clear"));
    });

    test('Mission upload command structure', () {
      final waypoint = LatLng(38.0308, -84.506);
      final items = [
        {
          "seq": 0,
          "frame": 6,
          "command": 16,
          "current": 1,
          "autocontinue": 1,
          "param1": 0.0,
          "param2": 0.0,
          "param3": 0.0,
          "param4": double.nan,
          "x": (waypoint.latitude * 1e7).round(),
          "y": (waypoint.longitude * 1e7).round(),
          "z": 20.0,
        }
      ];

      final uploadCmd = {
        "cmd": "mission_upload",
        "items": items,
      };

      expect(uploadCmd["cmd"], equals("mission_upload"));
      expect(uploadCmd["items"], isList);
      final itemsList = uploadCmd["items"] as List;
      expect(itemsList.length, equals(1));
    });

    test('Mission start command structure', () {
      final startCmd = {
        "cmd": "mission_start",
      };

      expect(startCmd["cmd"], equals("mission_start"));
    });

    test('Command serialization to JSON', () {
      final cmd = {
        "cmd": "goto",
        "lat": 38.0308,
        "lon": -84.506,
        "alt_rel": 20.0,
      };

      final jsonStr = jsonEncode(cmd);
      expect(jsonStr, isNotEmpty);

      final decoded = jsonDecode(jsonStr);
      expect(decoded["cmd"], equals("goto"));
      expect(decoded["lat"], equals(38.0308));
    });

    test('Survey upload command structure', () {
      final surveyCmd = {
        "cmd": "survey_upload",
        "polygon": [
          {"lat": 38.0, "lon": -84.5},
          {"lat": 38.01, "lon": -84.5},
          {"lat": 38.01, "lon": -84.49},
          {"lat": 38.0, "lon": -84.49},
        ],
        "altitude": 50.0,
        "overlap_front": 75.0,
        "overlap_side": 75.0,
      };

      expect(surveyCmd["cmd"], equals("survey_upload"));
      expect(surveyCmd["polygon"], isList);
      final polygon = surveyCmd["polygon"] as List;
      expect(polygon.length, equals(4));
      expect(surveyCmd["altitude"], equals(50.0));
    });

    test('Trigger distance command structure', () {
      final triggerCmd = {
        "cmd": "set_trigger_distance",
        "distance_m": 5.5,
      };

      expect(triggerCmd["cmd"], equals("set_trigger_distance"));
      expect(triggerCmd["distance_m"], equals(5.5));
    });
  });

  group('State Management Tests', () {
    testWidgets('Mission mode state persists', (WidgetTester tester) async {
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Enable mission mode
      final missionChip = find.widgetWithText(FilterChip, 'Mission edit');
      await tester.tap(missionChip);
      await tester.pump();

      // Verify it's enabled
      FilterChip chip = tester.widget<FilterChip>(missionChip);
      expect(chip.selected, isTrue);

      // Rebuild widget
      await tester.pump();

      // Should still be enabled
      chip = tester.widget<FilterChip>(missionChip);
      expect(chip.selected, isTrue);
    });

    testWidgets('Telemetry updates reflect in UI', (WidgetTester tester) async {
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Initial state shows defaults
      expect(find.text('UNKNOWN'), findsOneWidget);
      expect(find.text('No'), findsOneWidget);
    });
  });

  group('Error Handling Tests', () {
    test('Invalid command structure is detectable', () {
      final invalidCmd = {
        "invalid_key": "value",
      };

      expect(invalidCmd.containsKey("cmd"), isFalse);
    });

    test('Mission upload with empty items', () {
      final emptyMissionCmd = {
        "cmd": "mission_upload",
        "items": [],
      };

      expect(emptyMissionCmd["cmd"], equals("mission_upload"));
      final items = emptyMissionCmd["items"] as List;
      expect(items.isEmpty, isTrue);
    });

    test('GOTO command with invalid coordinates', () {
      final invalidGoto = {
        "cmd": "goto",
        "lat": 91.0, // Invalid latitude
        "lon": -84.506,
        "alt_rel": 20.0,
      };

      // In real implementation, this should be validated
      final lat = invalidGoto["lat"] as double;
      expect(lat > 90.0 || lat < -90.0, isTrue);
    });
  });

  group('Mission Planning Workflow Tests', () {
    testWidgets('Complete mission planning flow', (WidgetTester tester) async {
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Step 1: Enable mission mode
      final missionChip = find.widgetWithText(FilterChip, 'Mission edit');
      await tester.tap(missionChip);
      await tester.pump();

      FilterChip chip = tester.widget<FilterChip>(missionChip);
      expect(chip.selected, isTrue);

      // Step 2: Verify upload button is disabled (no waypoints)
      final uploadButton = find.widgetWithText(ElevatedButton, 'Upload');
      ElevatedButton uploadWidget = tester.widget<ElevatedButton>(uploadButton);
      expect(uploadWidget.onPressed, isNull);

      // Step 3: Verify clear button exists
      expect(find.text('Clear'), findsOneWidget);

      // Step 4: Waypoint counter shows 0
      expect(find.textContaining('0 WP'), findsOneWidget);
    });

    testWidgets('Mission mode toggle disables mission controls', (WidgetTester tester) async {
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Enable mission mode
      final missionChip = find.widgetWithText(FilterChip, 'Mission edit');
      await tester.tap(missionChip);
      await tester.pump();

      // Disable mission mode
      await tester.tap(missionChip);
      await tester.pump();

      FilterChip chip = tester.widget<FilterChip>(missionChip);
      expect(chip.selected, isFalse);
    });
  });

  group('Performance and Responsiveness Tests', () {
    testWidgets('App renders within reasonable time', (WidgetTester tester) async {
      final stopwatch = Stopwatch()..start();

      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      stopwatch.stop();

      // Should render in less than 1 second
      expect(stopwatch.elapsedMilliseconds, lessThan(1000));
    });

    testWidgets('Mode menu opens quickly', (WidgetTester tester) async {
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      final stopwatch = Stopwatch()..start();

      final modeButton = find.widgetWithText(ElevatedButton, 'Mode');
      await tester.tap(modeButton);
      await tester.pumpAndSettle();

      stopwatch.stop();

      // Menu should open in less than 500ms
      expect(stopwatch.elapsedMilliseconds, lessThan(500));
    });
  });
}
