import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mockito/mockito.dart';
import 'package:provider/provider.dart';
import 'package:owner_mobile_app/features/auth/auth_provider.dart';
import 'package:owner_mobile_app/features/auth/login_screen.dart';

class MockAuthProvider extends Mock implements AuthProvider {
  @override
  bool get loading => false;
  @override
  bool get isAuthenticated => false;
  @override
  String? get error => null;
}

Widget _buildTestApp(AuthProvider auth) => ChangeNotifierProvider<AuthProvider>.value(
      value: auth,
      child: MaterialApp.router(
        routerConfig: GoRouter(
          routes: [
            GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
            GoRoute(path: '/home', builder: (_, __) => const Scaffold(body: Text('Home'))),
            GoRoute(path: '/register', builder: (_, __) => const Scaffold(body: Text('Register'))),
          ],
          initialLocation: '/login',
        ),
      ),
    );

void main() {
  group('LoginScreen', () {
    testWidgets('renders email and password fields', (tester) async {
      await tester.pumpWidget(_buildTestApp(MockAuthProvider()));
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsNWidgets(2));
      expect(find.text('Email'), findsOneWidget);
      expect(find.text('Password'), findsOneWidget);
      expect(find.text('Sign In'), findsOneWidget);
    });

    testWidgets('shows validation error for empty email', (tester) async {
      await tester.pumpWidget(_buildTestApp(MockAuthProvider()));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Sign In'));
      await tester.pumpAndSettle();

      expect(find.text('Enter a valid email'), findsOneWidget);
    });

    testWidgets('shows validation error for empty password', (tester) async {
      await tester.pumpWidget(_buildTestApp(MockAuthProvider()));
      await tester.pumpAndSettle();

      await tester.enterText(
          find.byType(TextFormField).first, 'test@test.com');
      await tester.tap(find.text('Sign In'));
      await tester.pumpAndSettle();

      expect(find.text('Password required'), findsOneWidget);
    });

    testWidgets('shows validation error for invalid email format', (tester) async {
      await tester.pumpWidget(_buildTestApp(MockAuthProvider()));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextFormField).first, 'notanemail');
      await tester.tap(find.text('Sign In'));
      await tester.pumpAndSettle();

      expect(find.text('Enter a valid email'), findsOneWidget);
    });

    testWidgets('shows loading indicator when auth is loading', (tester) async {
      final auth = MockAuthProvider();
      when(auth.loading).thenReturn(true);

      await tester.pumpWidget(_buildTestApp(auth));
      await tester.pumpAndSettle();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('register link navigates to register screen', (tester) async {
      await tester.pumpWidget(_buildTestApp(MockAuthProvider()));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Register'));
      await tester.pumpAndSettle();

      expect(find.text('Register'), findsWidgets);
    });

    testWidgets('password visibility toggle works', (tester) async {
      await tester.pumpWidget(_buildTestApp(MockAuthProvider()));
      await tester.pumpAndSettle();

      // Initially obscured — visibility_off icon shown
      expect(find.byIcon(Icons.visibility_off), findsOneWidget);

      await tester.tap(find.byIcon(Icons.visibility_off));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.visibility), findsOneWidget);
    });
  });
}
