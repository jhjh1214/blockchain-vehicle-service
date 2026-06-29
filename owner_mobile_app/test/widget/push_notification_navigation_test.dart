import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:owner_mobile_app/core/services/push_notification_service.dart';

Widget _buildTestApp(GoRouter router) => MaterialApp.router(routerConfig: router);

void main() {
  group('PushNotificationService.navigateForData', () {
    testWidgets(
        'pushes onto the existing stack instead of replacing it, so back '
        'returns to the previous screen instead of exiting the app',
        (tester) async {
      final router = GoRouter(
        initialLocation: '/home',
        routes: [
          GoRoute(path: '/home', builder: (_, __) => const Scaffold(body: Text('Home'))),
          GoRoute(path: '/warranties', builder: (_, __) => const Scaffold(body: Text('Warranties'))),
        ],
      );
      await tester.pumpWidget(_buildTestApp(router));
      await tester.pumpAndSettle();

      PushNotificationService.navigateForData(router, {'type': 'warranty_claim'});
      await tester.pumpAndSettle();

      expect(find.text('Warranties'), findsOneWidget);
      // go() collapses the stack to just the target location, leaving
      // nothing to pop to — a real push keeps /home underneath it.
      expect(router.routerDelegate.currentConfiguration.matches.length, greaterThan(1));
      expect(router.canPop(), isTrue);
    });

    testWidgets('routes dispute_message with vin+recordIndex to the dispute chat',
        (tester) async {
      final router = GoRouter(
        initialLocation: '/home',
        routes: [
          GoRoute(path: '/home', builder: (_, __) => const Scaffold(body: Text('Home'))),
          GoRoute(
            path: '/services/dispute-chat/:vin/:recordIndex',
            builder: (_, state) =>
                Scaffold(body: Text('Chat ${state.pathParameters['vin']}')),
          ),
        ],
      );
      await tester.pumpWidget(_buildTestApp(router));
      await tester.pumpAndSettle();

      PushNotificationService.navigateForData(
          router, {'type': 'dispute_message', 'vin': 'ABC123', 'record_index': '2'});
      await tester.pumpAndSettle();

      expect(find.text('Chat ABC123'), findsOneWidget);
      expect(router.canPop(), isTrue);
    });

    testWidgets('dispute_message without vin/recordIndex falls back to pending services',
        (tester) async {
      final router = GoRouter(
        initialLocation: '/home',
        routes: [
          GoRoute(path: '/home', builder: (_, __) => const Scaffold(body: Text('Home'))),
          GoRoute(path: '/services/pending', builder: (_, __) => const Scaffold(body: Text('Pending'))),
        ],
      );
      await tester.pumpWidget(_buildTestApp(router));
      await tester.pumpAndSettle();

      PushNotificationService.navigateForData(router, {'type': 'dispute_message'});
      await tester.pumpAndSettle();

      expect(find.text('Pending'), findsOneWidget);
      expect(router.canPop(), isTrue);
    });

    testWidgets('unknown type with a vin falls back to vehicle detail', (tester) async {
      final router = GoRouter(
        initialLocation: '/home',
        routes: [
          GoRoute(path: '/home', builder: (_, __) => const Scaffold(body: Text('Home'))),
          GoRoute(
            path: '/vehicles/:vin',
            builder: (_, state) =>
                Scaffold(body: Text('Vehicle ${state.pathParameters['vin']}')),
          ),
        ],
      );
      await tester.pumpWidget(_buildTestApp(router));
      await tester.pumpAndSettle();

      PushNotificationService.navigateForData(router, {'type': 'something_else', 'vin': 'XYZ789'});
      await tester.pumpAndSettle();

      expect(find.text('Vehicle XYZ789'), findsOneWidget);
      expect(router.canPop(), isTrue);
    });
  });
}
