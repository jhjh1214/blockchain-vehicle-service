import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mockito/mockito.dart';
import 'package:owner_mobile_app/core/api/api_client.dart';
import 'package:owner_mobile_app/core/api/api_endpoints.dart';
import 'package:owner_mobile_app/features/warranties/warranties_provider.dart';

import '../../helpers/mock_dio.dart';

void main() {
  late MockDio mockDio;
  late WarrantiesProvider provider;

  final claimJson = {
    'vin': '1HGBH41JXMN109186',
    'claim_index': 0,
    'issue_description': 'Engine knocking noise',
    'status': 'pending',
    'submitted_at': 1700000000,
  };

  setUp(() {
    mockDio = MockDio();
    ApiClient.instance.injectDio(mockDio);
    provider = WarrantiesProvider();
  });

  group('loadClaims', () {
    test('populates claims list on success', () async {
      when(mockDio.get(ApiEndpoints.ownerClaims))
          .thenAnswer((_) async => mockResponse({'claims': [claimJson]}));

      await provider.loadClaims();

      expect(provider.claims.length, 1);
      expect(provider.claims.first.issueDescription, 'Engine knocking noise');
      expect(provider.claims.first.isPending, isTrue);
      expect(provider.error, isNull);
    });

    test('handles multiple claims with different statuses', () async {
      final approvedClaim = {...claimJson, 'claim_index': 1, 'status': 'approved'};
      final deniedClaim = {
        ...claimJson,
        'claim_index': 2,
        'status': 'denied',
        'denial_reason': 'Not covered',
      };
      when(mockDio.get(ApiEndpoints.ownerClaims)).thenAnswer((_) async =>
          mockResponse({'claims': [claimJson, approvedClaim, deniedClaim]}));

      await provider.loadClaims();

      expect(provider.claims.length, 3);
      expect(provider.claims[0].isPending, isTrue);
      expect(provider.claims[1].isApproved, isTrue);
      expect(provider.claims[2].isDenied, isTrue);
      expect(provider.claims[2].denialReason, 'Not covered');
    });

    test('sets error on failure', () async {
      when(mockDio.get(ApiEndpoints.ownerClaims))
          .thenThrow(mockDioError({'error': 'Server error'}, statusCode: 500));

      await provider.loadClaims();

      expect(provider.claims, isEmpty);
      expect(provider.error, 'Server error');
    });

    test('handles empty claims', () async {
      when(mockDio.get(ApiEndpoints.ownerClaims))
          .thenAnswer((_) async => mockResponse({'claims': []}));

      await provider.loadClaims();

      expect(provider.claims, isEmpty);
      expect(provider.error, isNull);
    });
  });

  group('submitClaim', () {
    test('returns null and reloads claims on success', () async {
      when(mockDio.post(ApiEndpoints.submitClaim, data: anyNamed('data')))
          .thenAnswer((_) async => mockResponse({'message': 'Claim submitted'}));
      when(mockDio.get(ApiEndpoints.ownerClaims))
          .thenAnswer((_) async => mockResponse({'claims': [claimJson]}));

      final error = await provider.submitClaim(
          '1HGBH41JXMN109186', 'Engine knocking noise');

      expect(error, isNull);
      expect(provider.claims.length, 1);
    });

    test('passes correct data to API', () async {
      final capturedData = <String, dynamic>{};
      when(mockDio.post(ApiEndpoints.submitClaim, data: anyNamed('data')))
          .thenAnswer((inv) async {
        capturedData.addAll(inv.namedArguments[#data] as Map<String, dynamic>);
        return mockResponse({'message': 'Claim submitted'});
      });
      when(mockDio.get(ApiEndpoints.ownerClaims))
          .thenAnswer((_) async => mockResponse({'claims': []}));

      await provider.submitClaim('1HGBH41JXMN109186', 'Brake failure');

      expect(capturedData['vin'], '1HGBH41JXMN109186');
      expect(capturedData['issue_description'], 'Brake failure');
    });

    test('returns error string on warranty expired', () async {
      when(mockDio.post(ApiEndpoints.submitClaim, data: anyNamed('data')))
          .thenThrow(mockDioError({'error': 'Warranty has expired'}, statusCode: 400));

      final error = await provider.submitClaim('1HGBH41JXMN109186', 'Issue');
      expect(error, 'Warranty has expired');
    });

    test('returns error string on duplicate claim', () async {
      when(mockDio.post(ApiEndpoints.submitClaim, data: anyNamed('data')))
          .thenThrow(mockDioError({'error': 'Pending claim already exists'}));

      final error = await provider.submitClaim('1HGBH41JXMN109186', 'Issue');
      expect(error, 'Pending claim already exists');
    });

    test('uses JSON body when no photos provided', () async {
      final capturedData = <String, dynamic>{};
      when(mockDio.post(ApiEndpoints.submitClaim, data: anyNamed('data')))
          .thenAnswer((inv) async {
        final data = inv.namedArguments[#data];
        if (data is Map<String, dynamic>) capturedData.addAll(data);
        return mockResponse({'message': 'Claim submitted'});
      });
      when(mockDio.get(ApiEndpoints.ownerClaims))
          .thenAnswer((_) async => mockResponse({'claims': []}));

      await provider.submitClaim(
        '1HGBH41JXMN109186',
        'Squeaky brakes issue',
        photos: [],
      );

      expect(capturedData['vin'], '1HGBH41JXMN109186');
      expect(capturedData['issue_description'], 'Squeaky brakes issue');
    });

    test('uses FormData when photos provided', () async {
      final tempDir = await Directory.systemTemp.createTemp('warranty_test_');
      final tempFile = File('${tempDir.path}/photo.jpg');
      await tempFile.writeAsBytes([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10]);
      final xFile = XFile(tempFile.path);

      when(mockDio.post(ApiEndpoints.submitClaim, data: anyNamed('data')))
          .thenAnswer((_) async => mockResponse({'message': 'Claim submitted'}));
      when(mockDio.get(ApiEndpoints.ownerClaims))
          .thenAnswer((_) async => mockResponse({'claims': [claimJson]}));

      final error = await provider.submitClaim(
        '1HGBH41JXMN109186',
        'Visible crack on windshield',
        photos: [xFile],
      );

      expect(error, isNull);
      verify(mockDio.post(ApiEndpoints.submitClaim, data: anyNamed('data'))).called(1);

      await tempDir.delete(recursive: true);
    });
  });
}
