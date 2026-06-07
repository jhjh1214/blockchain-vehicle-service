import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../api/api_client.dart';
import '../api/api_endpoints.dart';
import '../../features/notifications/notifications_provider.dart';
import '../../features/services/services_provider.dart';

/// Handles FCM token registration with the backend and stores received messages locally.
///
/// Requires a valid google-services.json in android/app/ and a Firebase project.
/// If Firebase is not configured, all methods are no-ops.
class PushNotificationService {
  static final PushNotificationService _instance = PushNotificationService._();
  PushNotificationService._();
  static PushNotificationService get instance => _instance;

  bool _listenersSetup = false;
  NotificationsProvider? _store;
  ServicesProvider? _services;
  GoRouter? _router;

  void attachStore(NotificationsProvider store) {
    _store = store;
  }

  void attachServices(ServicesProvider services) {
    _services = services;
  }

  void attachRouter(GoRouter router) {
    _router = router;
  }

  Future<void> init() async {
    try {
      final messaging = FirebaseMessaging.instance;

      if (!_listenersSetup) {
        _listenersSetup = true;
        final settings = await messaging.requestPermission(
          alert: true,
          badge: true,
          sound: true,
        );
        if (settings.authorizationStatus != AuthorizationStatus.authorized) return;

        messaging.onTokenRefresh.listen(_registerToken);
        FirebaseMessaging.onMessage.listen(_onForegroundMessage);

        final initial = await messaging.getInitialMessage();
        if (initial != null) _handleTap(initial);

        FirebaseMessaging.onMessageOpenedApp.listen(_handleTap);
      }

      // Always re-register token — called after login so the user is authenticated
      final token = await messaging.getToken();
      if (token != null) await _registerToken(token);
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
    const serviceTypes = {
      'pending_service', 'dispute_filed', 'rebuttal_submitted',
      'dispute_message', 'dispute_resolved', 'service_completed',
    };
    if (serviceTypes.contains(message.data['type'])) {
      _services?.loadPending();
    }
  }

  void _handleTap(RemoteMessage message) {
    final router = _router;
    if (router == null) return;
    final type = message.data['type'] ?? '';
    final vin = message.data['vin'] ?? '';
    switch (type) {
      case 'pending_service':
      case 'dispute_filed':
      case 'rebuttal_submitted':
      case 'dispute_message':
        router.go('/services/pending');
      case 'dispute_resolved':
      case 'service_completed':
        router.go('/services/history');
      case 'warranty_claim':
        router.go('/warranties');
      case 'recall':
        router.go('/vehicles/recalls');
      case 'warranty_void':
      case 'warranty_void_resolved':
        router.go('/services/void-requests');
      default:
        if (vin.isNotEmpty) {
          router.go('/vehicles/$vin');
        } else {
          router.go('/notifications');
        }
    }
  }
}
