import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;

class RiskApiService {
  static const String baseUrl = 'http://127.0.0.1:8001';

  static final ValueNotifier<Map<String, dynamic>?> latestRisk =
      ValueNotifier<Map<String, dynamic>?>(null);

  static Future<Map<String, dynamic>> getCurrentLocationRisk({
    double? heading,
  }) async {
    // Check whether location services are enabled.
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();

    if (!serviceEnabled) {
      throw Exception('Please enable your device location service.');
    }

    // Check and request location permission.
    LocationPermission permission = await Geolocator.checkPermission();

    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      throw Exception('Location permission was not granted.');
    }

    // Get current device coordinates.
    final position = await Geolocator.getCurrentPosition();

    // Build GET /risk request.
    final queryParameters = <String, String>{
      'lat': position.latitude.toString(),
      'lon': position.longitude.toString(),
    };

    if (heading != null) {
      queryParameters['heading'] = heading.toString();
    }

    final url = Uri.parse('$baseUrl/risk')
        .replace(queryParameters: queryParameters);

    final response = await http.get(url).timeout(
          const Duration(seconds: 30),
        );

    if (response.statusCode == 200) {
      final result =
          jsonDecode(response.body) as Map<String, dynamic>;

      latestRisk.value = result;
      return result;
    }

    throw Exception(
      'Risk API failed (${response.statusCode}): ${response.body}',
    );
  }
}
