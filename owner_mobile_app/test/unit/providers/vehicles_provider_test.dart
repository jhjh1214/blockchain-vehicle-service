import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:owner_mobile_app/core/api/api_client.dart';
import 'package:owner_mobile_app/core/api/api_endpoints.dart';
import 'package:owner_mobile_app/features/vehicles/vehicles_provider.dart';

import '../../helpers/mock_dio.dart';

void main() {
  late MockDio mockDio;
  late VehiclesProvider provider;

  final vehicleJson = {
    'vin': '1HGBH41JXMN109186',
    'make': 'Honda',
    'model': 'Civic',
    'year': 2022,
    'warranty_valid': true,
  };

  setUp(() {
    mockDio = MockDio();
    ApiClient.instance.injectDio(mockDio);
    provider = VehiclesProvider();
  });

  group('loadVehicles', () {
    test('populates vehicles list on success', () async {
      when(mockDio.get(ApiEndpoints.myVehicles))
          .thenAnswer((_) async => mockResponse({'vehicles': [vehicleJson]}));

      await provider.loadVehicles();

      expect(provider.vehicles.length, 1);
      expect(provider.vehicles.first.vin, '1HGBH41JXMN109186');
      expect(provider.vehicles.first.make, 'Honda');
      expect(provider.error, isNull);
      expect(provider.loading, isFalse);
    });

    test('returns empty list when no vehicles', () async {
      when(mockDio.get(ApiEndpoints.myVehicles))
          .thenAnswer((_) async => mockResponse({'vehicles': []}));

      await provider.loadVehicles();

      expect(provider.vehicles, isEmpty);
      expect(provider.error, isNull);
    });

    test('sets error on failure', () async {
      when(mockDio.get(ApiEndpoints.myVehicles))
          .thenThrow(mockDioError({'error': 'Unauthorized'}, statusCode: 401));

      await provider.loadVehicles();

      expect(provider.vehicles, isEmpty);
      expect(provider.error, 'Unauthorized');
      expect(provider.loading, isFalse);
    });

    test('clears previous error on retry', () async {
      when(mockDio.get(ApiEndpoints.myVehicles))
          .thenThrow(mockDioError({'error': 'Network error'}));
      await provider.loadVehicles();
      expect(provider.error, isNotNull);

      when(mockDio.get(ApiEndpoints.myVehicles))
          .thenAnswer((_) async => mockResponse({'vehicles': [vehicleJson]}));
      await provider.loadVehicles();

      expect(provider.error, isNull);
      expect(provider.vehicles.length, 1);
    });
  });

  group('claimVehicle', () {
    test('returns null on success and reloads vehicles', () async {
      when(mockDio.post(ApiEndpoints.claimVehicle, data: anyNamed('data')))
          .thenAnswer((_) async => mockResponse({'message': 'Claimed'}));
      when(mockDio.get(ApiEndpoints.myVehicles))
          .thenAnswer((_) async => mockResponse({'vehicles': [vehicleJson]}));

      final error = await provider.claimVehicle('1HGBH41JXMN109186');

      expect(error, isNull);
      expect(provider.vehicles.length, 1);
    });

    test('returns error string on failure', () async {
      when(mockDio.post(ApiEndpoints.claimVehicle, data: anyNamed('data')))
          .thenThrow(mockDioError({'error': 'Vehicle already claimed'}, statusCode: 409));

      final error = await provider.claimVehicle('1HGBH41JXMN109186');

      expect(error, 'Vehicle already claimed');
    });
  });

  group('transferVehicle', () {
    test('returns null on success and reloads vehicles', () async {
      when(mockDio.post(ApiEndpoints.transferVehicle, data: anyNamed('data')))
          .thenAnswer((_) async => mockResponse({'message': 'Transferred'}));
      when(mockDio.get(ApiEndpoints.myVehicles))
          .thenAnswer((_) async => mockResponse({'vehicles': []}));

      final error = await provider.transferVehicle('1HGBH41JXMN109186', 'new@owner.com');

      expect(error, isNull);
      expect(provider.vehicles, isEmpty);
    });

    test('returns error string on not found', () async {
      when(mockDio.post(ApiEndpoints.transferVehicle, data: anyNamed('data')))
          .thenThrow(mockDioError({'error': 'Vehicle not found'}, statusCode: 404));

      final error = await provider.transferVehicle('BADVIN', 'x@x.com');
      expect(error, 'Vehicle not found');
    });
  });

  group('checkWarranty', () {
    test('returns warranty data on success', () async {
      when(mockDio.get(ApiEndpoints.warrantyCheck('1HGBH41JXMN109186')))
          .thenAnswer((_) async => mockResponse({
                'is_valid': true,
                'warranty_expiry': 1999999999,
              }));

      final result = await provider.checkWarranty('1HGBH41JXMN109186');

      expect(result, isNotNull);
      expect(result!['is_valid'], isTrue);
      expect(result['warranty_expiry'], 1999999999);
    });

    test('returns null on error', () async {
      when(mockDio.get(ApiEndpoints.warrantyCheck('BADVIN')))
          .thenThrow(mockDioError({'error': 'Not found'}, statusCode: 404));

      final result = await provider.checkWarranty('BADVIN');
      expect(result, isNull);
    });
  });
}
