import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:owner_mobile_app/core/api/api_client.dart';
import 'package:owner_mobile_app/core/api/api_endpoints.dart';
import 'package:owner_mobile_app/features/services/services_provider.dart';

import '../../helpers/mock_dio.dart';

void main() {
  late MockDio mockDio;
  late ServicesProvider provider;

  final pendingServiceJson = {
    'vin': '1HGBH41JXMN109186',
    'record_index': 0,
    'service_type': 'Oil Change',
    'service_date': '2024-01-15',
    'status': 'pending',
    'submitted_by': '0xSERVICE',
    'mileage': 50000,
    'technician_name': 'Ali',
  };

  final verifiedServiceJson = {
    ...pendingServiceJson,
    'status': 'verified',
    'record_index': 1,
  };

  setUp(() {
    mockDio = MockDio();
    ApiClient.instance.injectDio(mockDio);
    provider = ServicesProvider();
  });

  group('loadPending', () {
    test('populates pending list on success', () async {
      when(mockDio.get(ApiEndpoints.ownerPendingServices))
          .thenAnswer((_) async =>
              mockResponse({'pending_services': [pendingServiceJson]}));

      await provider.loadPending();

      expect(provider.pending.length, 1);
      expect(provider.pending.first.serviceType, 'Oil Change');
      expect(provider.pending.first.isPending, isTrue);
      expect(provider.error, isNull);
    });

    test('sets error on network failure', () async {
      when(mockDio.get(ApiEndpoints.ownerPendingServices))
          .thenThrow(mockDioError({'error': 'Server error'}, statusCode: 500));

      await provider.loadPending();

      expect(provider.pending, isEmpty);
      expect(provider.error, 'Server error');
    });

    test('handles empty list', () async {
      when(mockDio.get(ApiEndpoints.ownerPendingServices))
          .thenAnswer((_) async => mockResponse({'pending_services': []}));

      await provider.loadPending();

      expect(provider.pending, isEmpty);
      expect(provider.error, isNull);
    });
  });

  group('loadHistory', () {
    test('populates history list on success', () async {
      when(mockDio.get(ApiEndpoints.ownerServiceHistory))
          .thenAnswer((_) async =>
              mockResponse({'service_history': [verifiedServiceJson]}));

      await provider.loadHistory();

      expect(provider.history.length, 1);
      expect(provider.history.first.isVerified, isTrue);
    });

    test('sets error on failure', () async {
      when(mockDio.get(ApiEndpoints.ownerServiceHistory))
          .thenThrow(mockDioError({'error': 'Unauthorized'}));

      await provider.loadHistory();

      expect(provider.error, 'Unauthorized');
    });
  });

  group('verifyService', () {
    test('returns null on success and reloads pending', () async {
      when(mockDio.post(ApiEndpoints.ownerVerifyService, data: anyNamed('data')))
          .thenAnswer((_) async => mockResponse({'message': 'Verified'}));
      when(mockDio.get(ApiEndpoints.ownerPendingServices))
          .thenAnswer((_) async => mockResponse({'pending_services': []}));

      final error = await provider.verifyService('1HGBH41JXMN109186', 0);

      expect(error, isNull);
      expect(provider.pending, isEmpty);
    });

    test('returns error message on failure', () async {
      when(mockDio.post(ApiEndpoints.ownerVerifyService, data: anyNamed('data')))
          .thenThrow(mockDioError({'error': 'Record not found'}, statusCode: 404));

      final error = await provider.verifyService('1HGBH41JXMN109186', 99);

      expect(error, 'Record not found');
    });
  });

  group('disputeService', () {
    test('returns null on success and reloads pending', () async {
      when(mockDio.post(ApiEndpoints.ownerDisputeService, data: anyNamed('data')))
          .thenAnswer((_) async => mockResponse({'message': 'Disputed'}));
      when(mockDio.get(ApiEndpoints.ownerPendingServices))
          .thenAnswer((_) async => mockResponse({'pending_services': []}));

      final error = await provider.disputeService(
          '1HGBH41JXMN109186', 0, 'Service was not performed');

      expect(error, isNull);
    });

    test('passes reason in request body', () async {
      final capturedData = <String, dynamic>{};
      when(mockDio.post(ApiEndpoints.ownerDisputeService, data: anyNamed('data')))
          .thenAnswer((inv) async {
        capturedData.addAll(inv.namedArguments[#data] as Map<String, dynamic>);
        return mockResponse({'message': 'Disputed'});
      });
      when(mockDio.get(ApiEndpoints.ownerPendingServices))
          .thenAnswer((_) async => mockResponse({'pending_services': []}));

      await provider.disputeService('VIN123', 1, 'Incorrect mileage logged');

      expect(capturedData['reason'], 'Incorrect mileage logged');
      expect(capturedData['vin'], 'VIN123');
      expect(capturedData['record_index'], 1);
    });

    test('returns error message on failure', () async {
      when(mockDio.post(ApiEndpoints.ownerDisputeService, data: anyNamed('data')))
          .thenThrow(mockDioError({'error': 'Cannot dispute verified record'}));

      final error = await provider.disputeService('VIN', 0, 'reason');
      expect(error, 'Cannot dispute verified record');
    });
  });
}
