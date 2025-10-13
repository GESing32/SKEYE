// Unit tests for Telemetry class and helper functions
// Tests data models and business logic

import 'package:flutter_test/flutter_test.dart';
import 'package:latlong2/latlong.dart';
import 'package:custom_gcs_serial/main.dart';

void main() {
  group('Telemetry Class Tests', () {
    test('Telemetry initializes with default values', () {
      final telemetry = Telemetry();

      expect(telemetry.linkOk, isFalse);
      expect(telemetry.armed, isFalse);
      expect(telemetry.mode, equals('UNKNOWN'));
      expect(telemetry.pos, isNull);
      expect(telemetry.relAlt, isNull);
      expect(telemetry.groundSpeed, isNull);
      expect(telemetry.voltage, isNull);
    });

    test('Telemetry can update linkOk status', () {
      final telemetry = Telemetry();

      telemetry.linkOk = true;
      expect(telemetry.linkOk, isTrue);

      telemetry.linkOk = false;
      expect(telemetry.linkOk, isFalse);
    });

    test('Telemetry can update armed status', () {
      final telemetry = Telemetry();

      telemetry.armed = true;
      expect(telemetry.armed, isTrue);

      telemetry.armed = false;
      expect(telemetry.armed, isFalse);
    });

    test('Telemetry can update mode', () {
      final telemetry = Telemetry();

      telemetry.mode = 'GUIDED';
      expect(telemetry.mode, equals('GUIDED'));

      telemetry.mode = 'LOITER';
      expect(telemetry.mode, equals('LOITER'));
    });

    test('Telemetry can update position', () {
      final telemetry = Telemetry();
      final testPos = LatLng(38.0308, -84.506);

      telemetry.pos = testPos;
      expect(telemetry.pos, equals(testPos));
      expect(telemetry.pos!.latitude, equals(38.0308));
      expect(telemetry.pos!.longitude, equals(-84.506));
    });

    test('Telemetry can update altitude', () {
      final telemetry = Telemetry();

      telemetry.relAlt = 25.5;
      expect(telemetry.relAlt, equals(25.5));
    });

    test('Telemetry can update ground speed', () {
      final telemetry = Telemetry();

      telemetry.groundSpeed = 12.3;
      expect(telemetry.groundSpeed, equals(12.3));
    });

    test('Telemetry can update voltage', () {
      final telemetry = Telemetry();

      telemetry.voltage = 11.8;
      expect(telemetry.voltage, equals(11.8));
    });

    test('Telemetry handles null position correctly', () {
      final telemetry = Telemetry();

      expect(telemetry.pos, isNull);

      final testPos = LatLng(40.0, -75.0);
      telemetry.pos = testPos;
      expect(telemetry.pos, isNotNull);

      telemetry.pos = null;
      expect(telemetry.pos, isNull);
    });
  });

  group('Message Parsing Logic Tests', () {
    test('Armed status extracted from base_mode correctly', () {
      // base_mode with bit 7 set (0x80 = 128) means armed
      final baseMode1 = 128; // Binary: 10000000
      final armed1 = (baseMode1 & 0x80) != 0;
      expect(armed1, isTrue);

      // base_mode without bit 7 means disarmed
      final baseMode2 = 0; // Binary: 00000000
      final armed2 = (baseMode2 & 0x80) != 0;
      expect(armed2, isFalse);

      final baseMode3 = 127; // Binary: 01111111
      final armed3 = (baseMode3 & 0x80) != 0;
      expect(armed3, isFalse);
    });

    test('Latitude conversion from MAVLink format', () {
      // MAVLink sends lat/lon as int32 in degrees * 1e7
      final mavlinkLat = 380308000; // 38.0308 degrees * 1e7
      final degreesLat = mavlinkLat / 1e7;
      expect(degreesLat, closeTo(38.0308, 0.0001));
    });

    test('Longitude conversion from MAVLink format', () {
      final mavlinkLon = -845060000; // -84.506 degrees * 1e7
      final degreesLon = mavlinkLon / 1e7;
      expect(degreesLon, closeTo(-84.506, 0.0001));
    });

    test('Relative altitude conversion from millimeters', () {
      final mavlinkAlt = 25000; // 25000mm = 25m
      final metersAlt = mavlinkAlt / 1000.0;
      expect(metersAlt, equals(25.0));
    });

    test('Voltage conversion from millivolts', () {
      final mavlinkVoltage = 11800; // 11800mV = 11.8V
      final volts = mavlinkVoltage / 1000.0;
      expect(volts, equals(11.8));
    });

    test('Negative voltage should result in null', () {
      final mavlinkVoltage = 0;
      final volts = mavlinkVoltage / 1000.0;
      final result = volts > 0 ? volts : null;
      expect(result, isNull);
    });
  });

  group('Mission Waypoint Generation Tests', () {
    test('Mission item structure is correct', () {
      final waypoint = LatLng(38.0308, -84.506);
      final seq = 0;

      final item = {
        "seq": seq,
        "frame": 6, // MAV_FRAME_GLOBAL_RELATIVE_ALT_INT
        "command": 16, // MAV_CMD_NAV_WAYPOINT
        "current": seq == 0 ? 1 : 0,
        "autocontinue": 1,
        "param1": 0.0,
        "param2": 0.0,
        "param3": 0.0,
        "param4": double.nan,
        "x": (waypoint.latitude * 1e7).round(),
        "y": (waypoint.longitude * 1e7).round(),
        "z": 20.0,
      };

      expect(item["seq"], equals(0));
      expect(item["frame"], equals(6));
      expect(item["command"], equals(16));
      expect(item["current"], equals(1)); // First waypoint
      expect(item["autocontinue"], equals(1));
      expect(item["x"], equals(380308000));
      expect(item["y"], equals(-845060000));
      expect(item["z"], equals(20.0));
    });

    test('Second waypoint has current set to 0', () {
      final seq = 1;

      final item = {
        "seq": seq,
        "current": seq == 0 ? 1 : 0,
      };

      expect(item["current"], equals(0));
    });

    test('Multiple waypoints have correct sequence numbers', () {
      final waypoints = [
        LatLng(38.0, -84.5),
        LatLng(38.01, -84.5),
        LatLng(38.01, -84.49),
      ];

      final items = waypoints.asMap().entries.map((entry) {
        return {
          "seq": entry.key,
          "current": entry.key == 0 ? 1 : 0,
        };
      }).toList();

      expect(items.length, equals(3));
      expect(items[0]["seq"], equals(0));
      expect(items[1]["seq"], equals(1));
      expect(items[2]["seq"], equals(2));
      expect(items[0]["current"], equals(1));
      expect(items[1]["current"], equals(0));
      expect(items[2]["current"], equals(0));
    });

    test('Coordinate conversion maintains precision', () {
      final testCases = [
        LatLng(38.0308, -84.506),
        LatLng(0.0, 0.0),
        LatLng(-33.8688, 151.2093), // Sydney
        LatLng(51.5074, -0.1278), // London
      ];

      for (final coord in testCases) {
        final x = (coord.latitude * 1e7).round();
        final y = (coord.longitude * 1e7).round();

        final reconstructedLat = x / 1e7;
        final reconstructedLon = y / 1e7;

        expect(reconstructedLat, closeTo(coord.latitude, 0.0000001));
        expect(reconstructedLon, closeTo(coord.longitude, 0.0000001));
      }
    });
  });

  group('Telemetry Data Validation Tests', () {
    test('Position coordinates are within valid range', () {
      final telemetry = Telemetry();

      // Valid coordinates
      telemetry.pos = LatLng(38.0308, -84.506);
      expect(telemetry.pos!.latitude, greaterThanOrEqualTo(-90));
      expect(telemetry.pos!.latitude, lessThanOrEqualTo(90));
      expect(telemetry.pos!.longitude, greaterThanOrEqualTo(-180));
      expect(telemetry.pos!.longitude, lessThanOrEqualTo(180));
    });

    test('Altitude can be negative (below home)', () {
      final telemetry = Telemetry();

      telemetry.relAlt = -5.0; // Below home position
      expect(telemetry.relAlt, equals(-5.0));
    });

    test('Ground speed is non-negative', () {
      final telemetry = Telemetry();

      telemetry.groundSpeed = 0.0;
      expect(telemetry.groundSpeed, greaterThanOrEqualTo(0.0));

      telemetry.groundSpeed = 15.5;
      expect(telemetry.groundSpeed, greaterThanOrEqualTo(0.0));
    });

    test('Voltage is positive when set', () {
      final telemetry = Telemetry();

      telemetry.voltage = 11.8;
      expect(telemetry.voltage, greaterThan(0.0));
    });

    test('Mode string handles various flight modes', () {
      final telemetry = Telemetry();
      final modes = ['STABILIZE', 'GUIDED', 'LOITER', 'RTL', 'AUTO', 'ALT_HOLD'];

      for (final mode in modes) {
        telemetry.mode = mode;
        expect(telemetry.mode, equals(mode));
      }
    });
  });

  group('Edge Cases and Error Handling', () {
    test('Telemetry handles zero altitude', () {
      final telemetry = Telemetry();
      telemetry.relAlt = 0.0;
      expect(telemetry.relAlt, equals(0.0));
    });

    test('Telemetry handles extreme coordinates', () {
      final telemetry = Telemetry();

      // North pole
      telemetry.pos = LatLng(90.0, 0.0);
      expect(telemetry.pos!.latitude, equals(90.0));

      // South pole
      telemetry.pos = LatLng(-90.0, 0.0);
      expect(telemetry.pos!.latitude, equals(-90.0));

      // Date line
      telemetry.pos = LatLng(0.0, 180.0);
      expect(telemetry.pos!.longitude, equals(180.0));
    });

    test('Coordinate conversion handles boundary values', () {
      final maxLat = 90.0;
      final minLat = -90.0;
      final maxLon = 180.0;
      final minLon = -180.0;

      final maxLatInt = (maxLat * 1e7).round();
      final minLatInt = (minLat * 1e7).round();
      final maxLonInt = (maxLon * 1e7).round();
      final minLonInt = (minLon * 1e7).round();

      expect(maxLatInt / 1e7, equals(maxLat));
      expect(minLatInt / 1e7, equals(minLat));
      expect(maxLonInt / 1e7, equals(maxLon));
      expect(minLonInt / 1e7, equals(minLon));
    });

    test('Large voltage values are handled correctly', () {
      // High voltage batteries (6S = ~25V)
      final mavlinkVoltage = 25200; // 25.2V
      final volts = mavlinkVoltage / 1000.0;
      expect(volts, equals(25.2));
    });
  });
}
