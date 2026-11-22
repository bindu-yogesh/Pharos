import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../models/route_response.dart';

class RouteApiService {
  static String get baseUrl => ApiConfig.baseUrl;

  static final ValueNotifier<RouteCollectionResponse?> latestRoute =
      ValueNotifier<RouteCollectionResponse?>(null);

  static Future<RouteCollectionResponse> calculateRoute({
    required double originLatitude,
    required double originLongitude,
    required double destinationLatitude,
    required double destinationLongitude,
  }) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/route');

    final requestBody = {
      'origin': {
        'latitude': originLatitude,
        'longitude': originLongitude,
      },
      'destination': {
        'latitude': destinationLatitude,
        'longitude': destinationLongitude,
      },
    };

    try {
      final response = await http
          .post(
            url,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(requestBody),
          )
          .timeout(const Duration(seconds: 180));

      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body);

        if (decoded is! Map<String, dynamic>) {
          throw const FormatException(
            'Invalid route response format from server.',
          );
        }

        final result = RouteCollectionResponse.fromJson(decoded);
        latestRoute.value = result;
        return result;
      }

      throw Exception(
        'Route API failed (${response.statusCode}): ${response.body}',
      );
    } on http.ClientException {
      throw Exception(
        'Cannot connect to the server. Check that the backend is running.',
      );
    } on FormatException {
      throw Exception('The server returned an invalid route response.');
    } on Exception catch (e) {
      if (e.toString().contains('TimeoutException')) {
        throw Exception('Route request timed out. Please try again.');
      }
      rethrow;
    }
  }
}
