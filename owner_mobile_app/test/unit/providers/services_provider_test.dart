import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:owner_mobile_app/core/api/api_client.dart';
import 'package:owner_mobile_app/core/api/api_endpoints.dart';
import 'package:owner_mobile_app/features/services/services_provider.dart';

import '../../helpers/mock_dio.dart';

void main() {
  late MockDio mockDio;
  late ServicesProvider provider;

  // Service records now identified by metadata_hash (not record_index)
  const testHash = '0xaabbccddeeff00112233445566778899aabbccddeeff00112233445566778899';
  const testVin = '1HGBH41JXMN109186';

  final pendingServiceJson = {
    'vin': testVin,
    'record_index': 0,
    'metadata_hash': testHash,
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
    'metadata_hash': '0xbbccddeeffffffffffffffffffffffffffffffffffffffffffffffffffff',
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
    test('succeeds and reloads pending', () async {
      when(mockDio.post(ApiEndpoints.ownerVerifyService,
              data: anyNamed('data')))
          .thenAnswer((_) async => mockResponse({
                'message': 'Verified',
                'transaction': {'tx_hash': '0xdeadbeef'}
              }));
      when(mockDio.get(ApiEndpoints.ownerPendingServices))
          .thenAnswer((_) async => mockResponse({'pending_services': []}));

      final result = await provider.verifyService(testVin, testHash);

      expect(result.isSuccess, isTrue);
      expect(result.error, isNull);
      expect(provider.pending, isEmpty);
    });

    test('sends metadata_hash in request body', () async {
      final capturedData = <String, dynamic>{};
      when(mockDio.post(ApiEndpoints.ownerVerifyService,
              data: anyNamed('data')))
          .thenAnswer((inv) async {
        capturedData
            .addAll(inv.namedArguments[#data] as Map<String, dynamic>);
        return mockResponse({'message': 'Verified', 'transaction': {}});
      });
      when(mockDio.get(ApiEndpoints.ownerPendingServices))
          .thenAnswer((_) async => mockResponse({'pending_services': []}));

      await provider.verifyService(testVin, testHash);

      expect(capturedData['vin'], testVin);
      expect(capturedData['metadata_hash'], testHash);
      expect(capturedData.containsKey('record_index'), isFalse);
    });

    test('returns error on failure', () async {
      when(mockDio.post(ApiEndpoints.ownerVerifyService,
              data: anyNamed('data')))
          .thenThrow(
              mockDioError({'error': 'Record not found'}, statusCode: 404));

      final result = await provider.verifyService(testVin, testHash);

      expect(result.isSuccess, isFalse);
      expect(result.error, 'Record not found');
    });
  });

  group('disputeService', () {
    test('succeeds and reloads pending', () async {
      when(mockDio.post(ApiEndpoints.ownerDisputeService,
              data: anyNamed('data')))
          .thenAnswer(
              (_) async => mockResponse({'message': 'Disputed', 'transaction': {}}));
      when(mockDio.get(ApiEndpoints.ownerPendingServices))
          .thenAnswer((_) async => mockResponse({'pending_services': []}));

      final result = await provider.disputeService(
          testVin, testHash, 'Service was not performed');

      expect(result.isSuccess, isTrue);
    });

    test('sends metadata_hash and reason in request body', () async {
      final capturedData = <String, dynamic>{};
      when(mockDio.post(ApiEndpoints.ownerDisputeService,
              data: anyNamed('data')))
          .thenAnswer((inv) async {
        capturedData
            .addAll(inv.namedArguments[#data] as Map<String, dynamic>);
        return mockResponse({'message': 'Disputed', 'transaction': {}});
      });
      when(mockDio.get(ApiEndpoints.ownerPendingServices))
          .thenAnswer((_) async => mockResponse({'pending_services': []}));

      await provider.disputeService(testVin, testHash, 'Incorrect mileage logged');

      expect(capturedData['reason'], 'Incorrect mileage logged');
      expect(capturedData['vin'], testVin);
      expect(capturedData['metadata_hash'], testHash);
      expect(capturedData.containsKey('record_index'), isFalse);
    });

    test('returns error on failure', () async {
      when(mockDio.post(ApiEndpoints.ownerDisputeService,
              data: anyNamed('data')))
          .thenThrow(mockDioError({'error': 'Cannot dispute verified record'}));

      final result = await provider.disputeService(testVin, testHash, 'reason');
      expect(result.isSuccess, isFalse);
      expect(result.error, 'Cannot dispute verified record');
    });
  });
}
