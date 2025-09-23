// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

//import 'package:custom_gcs_serial/main.dart';


class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SKEYE GCS',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        brightness: Brightness.dark, // Dark theme for better visibility
        useMaterial3: true,
      ),
      home: const GCSHomePage(),
    );
  }
}

class GCSHomePage extends StatelessWidget {
  const GCSHomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SKEYE Ground Control Station'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              // Add settings navigation here
            },
          ),
        ],
      ),
      body: const Column(
        children: [
          Expanded(
            child: Row(
              children: [
                // Main telemetry and control panel
                Expanded(
                  flex: 2,
                  child: Card(
                    margin: EdgeInsets.all(8.0),
                    child: Center(child: Text('Telemetry Panel')),
                  ),
                ),
                // Map view
                Expanded(
                  flex: 3,
                  child: Card(
                    margin: EdgeInsets.all(8.0),
                    child: Center(child: Text('Map View')),
                  ),
                ),
              ],
            ),
          ),
          // Status bar
          Card(
            margin: EdgeInsets.all(8.0),
            child: Padding(
              padding: EdgeInsets.all(8.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Connection Status'),
                  Text('Battery: --'),
                  Text('GPS: --'),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

void main() {
  testWidgets('Counter increments smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const MyApp());

    // Verify that our counter starts at 0.
    expect(find.text('0'), findsOneWidget);
    expect(find.text('1'), findsNothing);

    // Tap the '+' icon and trigger a frame.
    await tester.tap(find.byIcon(Icons.add));
    await tester.pump();

    // Verify that our counter has incremented.
    expect(find.text('0'), findsNothing);
    expect(find.text('1'), findsOneWidget);
  });
}
