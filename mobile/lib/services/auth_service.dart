
import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';

class AuthService {
  AuthService._();

  static const FlutterSecureStorage _storage = FlutterSecureStorage();

  static const String _tokenKey = 'pharos_access_token';

  static String? _accessToken;

  // Updates all app bars when login status changes.
  static final ValueNotifier<bool> authState =
      ValueNotifier<bool>(false);

  static String? get accessToken => _accessToken;

  static bool get isLoggedIn =>
      _accessToken != null && _accessToken!.isNotEmpty;

  static Map<String, String> get authenticatedHeaders => {
        'Content-Type': 'application/json',
        if (isLoggedIn) 'Authorization': 'Bearer $_accessToken',
      };

  static Future<void> restoreSession() async {
    _accessToken = await _storage.read(key: _tokenKey);
    authState.value = isLoggedIn;
  }

  static Future<Map<String, dynamic>> register({
    required String name,
    required String email,
    required String password,
    String preferredLanguage = 'en',
  }) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/auth/register');

    try {
      final response = await http
          .post(
            url,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'name': name.trim(),
              'email': email.trim(),
              'password': password,
              'preferred_language': preferredLanguage,
            }),
          )
          .timeout(const Duration(seconds: 30));

      final data = _decodeResponse(response);

      if (response.statusCode == 201) {
        return data;
      }

      throw Exception(_errorMessage(data, response.statusCode));
    } on TimeoutException {
      throw Exception('Registration timed out. Please try again.');
    } on http.ClientException {
      throw Exception('Cannot connect to the server. Check that the backend is running.');
    }
  }

  static Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final url = Uri.parse('${ApiConfig.baseUrl}/auth/login');

    try {
      final response = await http
          .post(
            url,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'email': email.trim(),
              'password': password,
            }),
          )
          .timeout(const Duration(seconds: 30));

      final data = _decodeResponse(response);

      if (response.statusCode == 200) {
        final token = data['access_token'];

        if (token is! String || token.isEmpty) {
          throw Exception('The server did not return a valid access token.');
        }

        await _storage.write(key: _tokenKey, value: token);
        _accessToken = token;
        authState.value = true;

        return data;
      }

      throw Exception(_errorMessage(data, response.statusCode));
    } on TimeoutException {
      throw Exception('Login timed out. Please try again.');
    } on http.ClientException {
      throw Exception('Cannot connect to the server. Check that the backend is running.');
    }
  }

  static Future<void> logout() async {
    await _storage.delete(key: _tokenKey);
    _accessToken = null;
    authState.value = false;
  }

  static Future<void> handleUnauthorized() async {
    await logout();
  }

  static Map<String, dynamic> _decodeResponse(http.Response response) {
    try {
      final decoded = jsonDecode(response.body);

      if (decoded is Map<String, dynamic>) {
        return decoded;
      }

      throw const FormatException('Unexpected server response.');
    } on FormatException {
      throw Exception('The server returned an invalid response.');
    }
  }

  static String _errorMessage(
    Map<String, dynamic> data,
    int statusCode,
  ) {
    final detail = data['detail'];

    if (detail is String) {
      return detail;
    }

    if (detail is List) {
      return detail
          .map((item) => item is Map ? item['msg'] ?? item : item)
          .join(', ');
    }

    return 'Authentication failed (HTTP $statusCode).';
  }
}
