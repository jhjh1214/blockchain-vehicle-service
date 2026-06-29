import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:owner_mobile_app/core/api/api_client.dart';
import 'package:owner_mobile_app/core/api/api_endpoints.dart';
import 'package:owner_mobile_app/core/storage/token_storage.dart';
import 'package:owner_mobile_app/features/auth/auth_provider.dart';

import '../../helpers/mock_dio.dart';

const _secureStorageChannel =
    MethodChannel('plugins.it_nomads.com/flutter_secure_storage');

/// Backs the secure storage channel with an in-memory map keyed by storage
/// key, so tests can seed values (e.g. a persisted access token, or the
/// biometric_enabled flag) and have TokenStorage actually read them back.
void _stubSecureStorage(Map<String, String> seed) {
  final values = Map<String, String>.from(seed);
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(_secureStorageChannel, (MethodCall call) async {
    switch (call.method) {
      case 'read':
        return values[call.arguments['key']];
      case 'write':
        values[call.arguments['key']] = call.arguments['value'];
        return null;
      case 'delete':
        values.remove(call.arguments['key']);
        return null;
      default:
        return null;
    }
  });
}

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
  });

  setUp(() {
    // Default: empty secure storage, like a fresh install. Individual tests
    // override this via _stubSecureStorage when they need specific values.
    _stubSecureStorage({});
  });

  late MockDio mockDio;
  late AuthProvider provider;

  setUp(() {
    mockDio = MockDio();
    // Inject mock Dio into ApiClient singleton for tests
    ApiClient.instance.injectDio(mockDio);
    provider = AuthProvider();
  });

  final userJson = {
    'id': 1,
    'email': 'owner@test.com',
    'name': 'Test Owner',
    'role': 'OWNER',
    'blockchain_address': '0xABC',
  };

  group('login', () {
    test('sets user and returns true on success', () async {
      when(mockDio.post(ApiEndpoints.login, data: anyNamed('data')))
          .thenAnswer((_) async => mockResponse({
                'access_token': 'access123',
                'refresh_token': 'refresh123',
                'user': userJson,
              }));

      final result = await provider.login('owner@test.com', 'password123');

      expect(result, isTrue);
      expect(provider.isAuthenticated, isTrue);
      expect(provider.user?.email, 'owner@test.com');
      expect(provider.user?.role, 'OWNER');
      expect(provider.loading, isFalse);
      expect(provider.error, isNull);
    });

    test('sets error and returns false on 401', () async {
      when(mockDio.post(ApiEndpoints.login, data: anyNamed('data')))
          .thenThrow(mockDioError({'error': 'Invalid credentials'}, statusCode: 401));

      final result = await provider.login('bad@test.com', 'wrongpass');

      expect(result, isFalse);
      expect(provider.isAuthenticated, isFalse);
      expect(provider.error, 'Invalid credentials');
      expect(provider.loading, isFalse);
    });

    test('sets loading true during request then false after', () async {
      bool wasLoading = false;
      when(mockDio.post(ApiEndpoints.login, data: anyNamed('data')))
          .thenAnswer((_) async {
        wasLoading = provider.loading;
        return mockResponse({
          'access_token': 'tok',
          'refresh_token': 'ref',
          'user': userJson,
        });
      });

      await provider.login('owner@test.com', 'pass');

      expect(wasLoading, isTrue);
      expect(provider.loading, isFalse);
    });
  });

  group('register', () {
    test('sets user and returns true on success', () async {
      when(mockDio.post(ApiEndpoints.register, data: anyNamed('data')))
          .thenAnswer((_) async => mockResponse({
                'access_token': 'access123',
                'refresh_token': 'refresh123',
                'user': userJson,
              }));

      final result = await provider.register('owner@test.com', 'Pass1234!', 'Test Owner');

      expect(result, isTrue);
      expect(provider.isAuthenticated, isTrue);
    });

    test('sets error on duplicate email', () async {
      when(mockDio.post(ApiEndpoints.register, data: anyNamed('data')))
          .thenThrow(mockDioError({'error': 'Email already registered'}, statusCode: 400));

      final result = await provider.register('dup@test.com', 'Pass1234!', 'Test');

      expect(result, isFalse);
      expect(provider.error, 'Email already registered');
    });

    test('saves credentials so a later restart can resume the session',
        () async {
      when(mockDio.post(ApiEndpoints.register, data: anyNamed('data')))
          .thenAnswer((_) async => mockResponse({
                'access_token': 'access123',
                'refresh_token': 'refresh123',
                'user': userJson,
              }));

      await provider.register('owner@test.com', 'Pass1234!', 'Test Owner');

      final creds = await TokenStorage.loadCredentials();
      expect(creds?.email, 'owner@test.com');
      expect(creds?.password, 'Pass1234!');
    });
  });

  group('logout', () {
    test('clears user on logout', () async {
      // First log in
      when(mockDio.post(ApiEndpoints.login, data: anyNamed('data')))
          .thenAnswer((_) async => mockResponse({
                'access_token': 'tok',
                'refresh_token': 'ref',
                'user': userJson,
              }));
      await provider.login('owner@test.com', 'pass');
      expect(provider.isAuthenticated, isTrue);

      when(mockDio.post(ApiEndpoints.logout, data: anyNamed('data')))
          .thenAnswer((_) async => mockResponse({'message': 'Logged out'}));

      await provider.logout();

      expect(provider.isAuthenticated, isFalse);
      expect(provider.user, isNull);
    });
  });

  group('updateProfile', () {
    test('updates user fields on success', () async {
      when(mockDio.put(ApiEndpoints.profile, data: anyNamed('data')))
          .thenAnswer((_) async => mockResponse({
                'user': {...userJson, 'name': 'New Name', 'phone': '0123456789'},
              }));

      // Manually set user first
      provider.setUserForTest(userJson);

      final result = await provider.updateProfile(name: 'New Name', phone: '0123456789');

      expect(result, isTrue);
      expect(provider.user?.name, 'New Name');
      expect(provider.user?.phone, '0123456789');
    });

    test('sets error on failure', () async {
      when(mockDio.put(ApiEndpoints.profile, data: anyNamed('data')))
          .thenThrow(mockDioError({'error': 'Update failed'}));

      provider.setUserForTest(userJson);
      final result = await provider.updateProfile(name: 'X');

      expect(result, isFalse);
      expect(provider.error, 'Update failed');
    });
  });

  group('clearError', () {
    test('clears the error field', () async {
      when(mockDio.post(ApiEndpoints.login, data: anyNamed('data')))
          .thenThrow(mockDioError({'error': 'Some error'}));
      await provider.login('x@x.com', 'pass');
      expect(provider.error, isNotNull);

      provider.clearError();
      expect(provider.error, isNull);
    });
  });

  group('tryAutoLogin', () {
    test('does nothing when no token is persisted', () async {
      await provider.tryAutoLogin();

      expect(provider.isAuthenticated, isFalse);
      verifyNever(mockDio.get(ApiEndpoints.me));
    });

    test('resumes the session when a token exists and biometric is off',
        () async {
      await TokenStorage.save('access123', 'refresh123', rememberMe: true);
      when(mockDio.get(ApiEndpoints.me))
          .thenAnswer((_) async => mockResponse(userJson));

      await provider.tryAutoLogin();

      expect(provider.isAuthenticated, isTrue);
      expect(provider.user?.email, 'owner@test.com');
    });

    test(
        'does NOT auto-resume when biometric login is enabled and a saved '
        'credential exists to unlock with — regression guard for remembered '
        'sessions silently bypassing the fingerprint gate',
        () async {
      await TokenStorage.save('access123', 'refresh123', rememberMe: true);
      await TokenStorage.setBiometricEnabled(true);
      await TokenStorage.saveCredentials('owner@test.com', 'pass');

      await provider.tryAutoLogin();

      expect(provider.isAuthenticated, isFalse);
      verifyNever(mockDio.get(ApiEndpoints.me));
    });

    test(
        'still auto-resumes when biometric is enabled but no saved credential '
        'exists — regression guard for a stale enabled flag (e.g. left over '
        'from a different account on the same device) stranding the user on '
        'a blank login screen with nothing to unlock',
        () async {
      await TokenStorage.save('access123', 'refresh123', rememberMe: true);
      await TokenStorage.setBiometricEnabled(true);
      // No saveCredentials call — simulates a stale flag with nothing paired.
      when(mockDio.get(ApiEndpoints.me))
          .thenAnswer((_) async => mockResponse(userJson));

      await provider.tryAutoLogin();

      expect(provider.isAuthenticated, isTrue);
      expect(provider.user?.email, 'owner@test.com');
    });
  });
}
