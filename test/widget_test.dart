// Basic Flutter widget tests for GCS application
// Tests the main app structure and initial rendering

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:custom_gcs_serial/main.dart';

void main() {
  group('GcsApp Widget Tests', () {
    testWidgets('App loads with correct title', (WidgetTester tester) async {
      // Build the GCS app
      await tester.pumpWidget(const GcsApp());

      // Verify app title is present in AppBar
      expect(find.text('Custom GCS (Serial)'), findsOneWidget);
    });

    testWidgets('App shows disconnected link icon initially', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Should show link_off icon when not connected
      expect(find.byIcon(Icons.link_off), findsOneWidget);
    });

    testWidgets('Control buttons are present', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Verify main control buttons exist
      expect(find.text('Arm'), findsOneWidget);
      expect(find.text('RTL'), findsOneWidget);
      expect(find.text('Mission edit'), findsOneWidget);
    });

    testWidgets('Status bar shows telemetry fields', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Verify telemetry fields are displayed
      expect(find.textContaining('Mode:'), findsOneWidget);
      expect(find.textContaining('Armed:'), findsOneWidget);
      expect(find.textContaining('Lat:'), findsOneWidget);
      expect(find.textContaining('Lon:'), findsOneWidget);
      expect(find.textContaining('Alt rel'), findsOneWidget);
      expect(find.textContaining('GS'), findsOneWidget);
      expect(find.textContaining('VBat'), findsOneWidget);
    });

    testWidgets('Mission control buttons are initially disabled', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Find upload and start buttons
      final uploadButton = find.widgetWithText(ElevatedButton, 'Upload');
      final startButton = find.widgetWithText(ElevatedButton, 'Start');

      expect(uploadButton, findsOneWidget);
      expect(startButton, findsOneWidget);

      // Verify buttons are disabled (onPressed is null)
      final uploadWidget = tester.widget<ElevatedButton>(uploadButton);
      final startWidget = tester.widget<ElevatedButton>(startButton);

      expect(uploadWidget.onPressed, isNull);
      expect(startWidget.onPressed, isNull);
    });

    testWidgets('Mission edit toggle works', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Find and tap mission edit chip
      final missionChip = find.widgetWithText(FilterChip, 'Mission edit');
      expect(missionChip, findsOneWidget);

      // Initially not selected
      FilterChip chip = tester.widget<FilterChip>(missionChip);
      expect(chip.selected, isFalse);

      // Tap to enable mission mode
      await tester.tap(missionChip);
      await tester.pump();

      // Should now be selected
      chip = tester.widget<FilterChip>(missionChip);
      expect(chip.selected, isTrue);
    });

    testWidgets('Mode menu button exists and opens popup', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Find mode button
      final modeButton = find.widgetWithText(ElevatedButton, 'Mode');
      expect(modeButton, findsOneWidget);

      // Tap to open popup menu
      await tester.tap(modeButton);
      await tester.pumpAndSettle();

      // Verify mode options are shown
      expect(find.text('GUIDED'), findsOneWidget);
      expect(find.text('LOITER'), findsOneWidget);
      expect(find.text('ALT_HOLD'), findsOneWidget);
      expect(find.text('STABILIZE'), findsOneWidget);
    });

    testWidgets('Connection indicator is visible', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Verify connection status icon is visible (starts disconnected)
      expect(find.byIcon(Icons.link_off), findsOneWidget);

      // Find the icon widget
      final iconWidget = tester.widget<Icon>(find.byIcon(Icons.link_off));
      expect(iconWidget.color, equals(Colors.red));
    });

    testWidgets('Clear waypoints button exists in mission mode', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Enable mission edit mode
      final missionChip = find.widgetWithText(FilterChip, 'Mission edit');
      await tester.tap(missionChip);
      await tester.pump();

      // Verify Clear button is present
      expect(find.text('Clear'), findsOneWidget);
    });

    testWidgets('Waypoint counter displays initially zero', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Enable mission edit mode
      final missionChip = find.widgetWithText(FilterChip, 'Mission edit');
      await tester.tap(missionChip);
      await tester.pump();

      // Verify waypoint counter shows 0
      expect(find.textContaining('0 WP'), findsOneWidget);
    });

    testWidgets('All flight control buttons are enabled', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Find control buttons
      final armButton = find.widgetWithText(ElevatedButton, 'Arm');
      final rtlButton = find.widgetWithText(ElevatedButton, 'RTL');
      final modeButton = find.widgetWithText(ElevatedButton, 'Mode');

      // Verify all buttons exist
      expect(armButton, findsOneWidget);
      expect(rtlButton, findsOneWidget);
      expect(modeButton, findsOneWidget);

      // Verify buttons are enabled
      final armWidget = tester.widget<ElevatedButton>(armButton);
      final rtlWidget = tester.widget<ElevatedButton>(rtlButton);
      final modeWidget = tester.widget<ElevatedButton>(modeButton);

      expect(armWidget.onPressed, isNotNull);
      expect(rtlWidget.onPressed, isNotNull);
      expect(modeWidget.onPressed, isNotNull);
    });

    testWidgets('Status bar has all telemetry indicators', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Verify all telemetry indicators are present
      final indicators = [
        'Mode:',
        'Armed:',
        'Lat:',
        'Lon:',
        'Alt rel',
        'GS',
        'VBat',
      ];

      for (final indicator in indicators) {
        expect(find.textContaining(indicator), findsOneWidget);
      }
    });

    testWidgets('Altitude indicator displays meters unit', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Verify altitude has meters unit
      expect(find.textContaining('Alt rel'), findsOneWidget);
      expect(find.textContaining('m'), findsWidgets);
    });

    testWidgets('Speed indicator displays m/s unit', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Verify speed has m/s unit
      expect(find.textContaining('GS'), findsOneWidget);
      expect(find.textContaining('m/s'), findsWidgets);
    });

    testWidgets('Battery indicator displays voltage unit', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const GcsApp());
      await tester.pump();

      // Verify battery has voltage unit
      expect(find.textContaining('VBat'), findsOneWidget);
      expect(find.textContaining('V'), findsWidgets);
    });
  });
}
