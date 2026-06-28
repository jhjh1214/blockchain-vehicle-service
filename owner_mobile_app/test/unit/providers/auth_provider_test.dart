import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:owner_mobile_app/core/api/api_client.dart';
import 'package:owner_mobile_app/core/api/api_endpoints.dart';
import 'package:owner_mobile_app/features/auth/auth_provider.dart';

import '../../helpers/mock_dio.dart';

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    // Stub flutter_secure_storage platform channel so unit tests don't need a real device.
    const channel = MethodChannel('plugins.it_nomads.com/flutter_secure_storage');
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (MethodCall call) async => null);
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
}
