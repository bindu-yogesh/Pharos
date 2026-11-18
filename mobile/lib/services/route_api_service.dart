
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/route_response.dart';

class RouteApiService {
  static const String baseUrl = 'http://127.0.0.1:8001';

  // Stores the latest route response for other screens.
  static final ValueNotifier<RouteCollectionResponse?> latestRoute =
      ValueNotifier<RouteCollectionResponse?>(null);

  static Future<RouteCollectionResponse> calculateRoute({
    required double originLatitude,
    required double originLongitude,
    required double destinationLatitude,
    required double destinationLongitude,
  }) async {
    final url = Uri.parse('$baseUrl/route');

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

    final response = await http
        .post(
          url,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(requestBody),
        )
        .timeout(const Duration(seconds: 60));

    if (response.statusCode == 200) {
      final Map<String, dynamic> data =
          jsonDecode(response.body) as Map<String, dynamic>;

      final result = RouteCollectionResponse.fromJson(data);

      // Make the response available to the Live Map screen.
      latestRoute.value = result;

      return result;
    }

    throw Exception(
      'Route API failed (${response.statusCode}): ${response.body}',
    );
  }
}
