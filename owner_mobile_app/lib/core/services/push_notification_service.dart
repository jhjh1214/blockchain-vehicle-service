import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:dio/dio.dart';
import '../api/api_client.dart';
import '../api/api_endpoints.dart';
import '../../features/notifications/notifications_provider.dart';

/// Handles FCM token registration with the backend and stores received messages locally.
///
/// Requires a valid google-services.json in android/app/ and a Firebase project.
/// If Firebase is not configured, all methods are no-ops.
class PushNotificationService {
  static final PushNotificationService _instance = PushNotificationService._();
  PushNotificationService._();
  static PushNotificationService get instance => _instance;

  bool _initialized = false;
  NotificationsProvider? _store;

  void attachStore(NotificationsProvider store) {
    _store = store;
  }

  Future<void> init() async {
    if (_initialized) return;
    _initialized = true;
    try {
      final messaging = FirebaseMessaging.instance;
      final settings = await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );
      if (settings.authorizationStatus != AuthorizationStatus.authorized) return;

      final token = await messaging.getToken();
      if (token != null) {
        await _registerToken(token);
      }

      FirebaseMessaging.instance.onTokenRefresh.listen(_registerToken);
      FirebaseMessaging.onMessage.listen(_onForegroundMessage);
    } catch (_) {
      // Firebase not configured — push notifications unavailable
    }
  }

  Future<void> _registerToken(String token) async {
    try {
      await ApiClient.instance.dio.post(
        ApiEndpoints.deviceToken,
        data: {'token': token, 'platform': 'android'},
      );
    } on DioException catch (_) {}
  }

  void _onForegroundMessage(RemoteMessage message) {
    final title = message.notification?.title ?? message.data['title'] ?? '';
    final body = message.notification?.body ?? message.data['body'] ?? '';
    if (title.isEmpty && body.isEmpty) return;
    _store?.add(
      title,
      body,
      Map<String, String>.from(message.data.map((k, v) => MapEntry(k, v.toString()))),
    );
  }
}
