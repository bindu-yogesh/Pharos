
import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import 'auth_service.dart';

class NotificationService {
  NotificationService._();

  static const String _vapidKey =
      'BLFtZPoIz0OIYa6wvRqxtZMuadZSyMfW-P0rr9fBMFmc9Lp2Efo-m1u2NqqSeI3dMagWEtzCbDggLOfeniNFYwE';

  static Future<String> enableNotifications() async {
    if (!kIsWeb) {
      throw Exception(
        'Notifications are currently configured for Chrome web.',
      );
    }

    if (!AuthService.isLoggedIn) {
      throw Exception('Please log in before enabling notifications.');
    }

    final messaging = FirebaseMessaging.instance;

    final permission = await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    if (permission.authorizationStatus ==
        AuthorizationStatus.denied) {
      return 'Notification permission was denied. Enable it in Chrome site settings.';
    }

    final token = await messaging
        .getToken(vapidKey: _vapidKey)
        .timeout(const Duration(seconds: 30));

    if (token == null || token.isEmpty) {
      throw Exception('Firebase returned an empty FCM registration token.');
    }

    final response = await http
        .post(
          Uri.parse('${ApiConfig.baseUrl}/devices'),
          headers: AuthService.authenticatedHeaders,
          body: jsonEncode({'token': token}),
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode != 200) {
      throw Exception(
        'Device registration failed (HTTP ${response.statusCode}).',
      );
    }

    return 'Notifications enabled successfully!';
  }
}
