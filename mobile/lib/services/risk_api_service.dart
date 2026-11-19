import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

class RiskApiService {
  static String get baseUrl => ApiConfig.baseUrl;

  static final ValueNotifier<Map<String, dynamic>?> latestRisk =
      ValueNotifier<Map<String, dynamic>?>(null);

  static Future<Map<String, dynamic>> getCurrentLocationRisk({
    double? heading,
  }) async {
    try {
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();

      if (!serviceEnabled) {
        throw Exception('Please enable your device location service.');
      }

      LocationPermission permission = await Geolocator.checkPermission();

      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }

      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        throw Exception('Location permission was not granted.');
      }

      final position = await Geolocator.getCurrentPosition();

      final queryParameters = <String, String>{
        'lat': position.latitude.toString(),
        'lon': position.longitude.toString(),
      };

      if (heading != null) {
        queryParameters['heading'] = heading.toString();
      }

      final url = Uri.parse('${ApiConfig.baseUrl}/risk')
          .replace(queryParameters: queryParameters);

      final response = await http.get(url).timeout(
            const Duration(seconds: 30),
          );

      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body);

        if (decoded is! Map<String, dynamic>) {
          throw const FormatException(
            'Invalid risk response format from server.',
          );
        }

        latestRisk.value = decoded;
        return decoded;
      }

      throw Exception(
        'Risk API failed (${response.statusCode}): ${response.body}',
      );
    } on http.ClientException {
      throw Exception(
        'Cannot connect to the server. Check that the backend is running.',
      );
    } on FormatException {
      throw Exception('The server returned an invalid risk response.');
    } on Exception catch (e) {
      if (e.toString().contains('TimeoutException')) {
        throw Exception('Risk request timed out. Please try again.');
      }
      rethrow;
    }
  }
}
