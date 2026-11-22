import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import 'auth_service.dart';

class TripApiService {
  static Future<Map<String, dynamic>> startTrip({
    required Map<String, dynamic> routeJson,
  }) async {
    if (!AuthService.isLoggedIn) {
      throw Exception('Please log in before starting a trip.');
    }

    final response = await http
        .post(
          Uri.parse('${ApiConfig.baseUrl}/trips/start'),
          headers: AuthService.authenticatedHeaders,
          body: jsonEncode({'route_json': routeJson}),
        )
        .timeout(const Duration(seconds: 30));

    return _handleResponse(response, [200, 201]);
  }

  static Future<Map<String, dynamic>> updateLocation({
    required int tripId,
    required double latitude,
    required double longitude,
  }) async {
    if (!AuthService.isLoggedIn) {
      throw Exception('Please log in before updating trip location.');
    }

    final response = await http
        .post(
          Uri.parse('${ApiConfig.baseUrl}/trips/$tripId/location'),
          headers: AuthService.authenticatedHeaders,
          body: jsonEncode({
            'latitude': latitude,
            'longitude': longitude,
          }),
        )
        .timeout(const Duration(seconds: 30));

    return _handleResponse(response, [200]);
  }

  static Future<Map<String, dynamic>> endTrip({
    required int tripId,
  }) async {
    if (!AuthService.isLoggedIn) {
      throw Exception('Please log in before ending a trip.');
    }

    final response = await http
        .post(
          Uri.parse('${ApiConfig.baseUrl}/trips/$tripId/end'),
          headers: AuthService.authenticatedHeaders,
          body: jsonEncode({'status': 'ended'}),
        )
        .timeout(const Duration(seconds: 30));

    return _handleResponse(response, [200]);
  }

  static Map<String, dynamic> _handleResponse(
    http.Response response,
    List<int> successCodes,
  ) {
    if (response.statusCode == 401) {
      AuthService.handleUnauthorized();
      throw Exception('Session expired. Please log in again.');
    }

    if (!successCodes.contains(response.statusCode)) {
      throw Exception(
        'Trip API failed (${response.statusCode}): ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body);

    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('Invalid Trip API response.');
    }

    return decoded;
  }
}
