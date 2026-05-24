import 'package:flutter_test/flutter_test.dart';
import 'package:owner_mobile_app/core/models/service_record.dart';

void main() {
  group('ServiceRecord.fromJson', () {
    final baseJson = {
      'vin': '1HGBH41JXMN109186',
      'record_index': 0,
      'service_type': 'Oil Change',
      'service_date': '2024-01-15',
      'status': 'pending',
      'submitted_by': '0xSERVICE',
    };

    test('parses required fields', () {
      final r = ServiceRecord.fromJson(baseJson);
      expect(r.vin, '1HGBH41JXMN109186');
      expect(r.recordIndex, 0);
      expect(r.serviceType, 'Oil Change');
      expect(r.serviceDate, '2024-01-15');
      expect(r.status, 'pending');
      expect(r.submittedBy, '0xSERVICE');
    });

    test('parses optional fields', () {
      final json = {
        ...baseJson,
        'mileage': 50000,
        'parts_replaced': 'Oil filter',
        'technician_name': 'Ali',
        'service_notes': 'Standard change',
        'dispute_reason': null,
      };
      final r = ServiceRecord.fromJson(json);
      expect(r.mileage, 50000);
      expect(r.partsReplaced, 'Oil filter');
      expect(r.technicianName, 'Ali');
      expect(r.serviceNotes, 'Standard change');
      expect(r.disputeReason, isNull);
    });

    test('accepts index field as fallback for record_index', () {
      final json = {...baseJson}..remove('record_index');
      json['index'] = 3;
      expect(ServiceRecord.fromJson(json).recordIndex, 3);
    });

    group('status helpers', () {
      test('isPending', () {
        expect(ServiceRecord.fromJson({...baseJson, 'status': 'pending'}).isPending, isTrue);
        expect(ServiceRecord.fromJson({...baseJson, 'status': 'verified'}).isPending, isFalse);
      });

      test('isVerified', () {
        expect(ServiceRecord.fromJson({...baseJson, 'status': 'verified'}).isVerified, isTrue);
        expect(ServiceRecord.fromJson({...baseJson, 'status': 'pending'}).isVerified, isFalse);
      });

      test('isDisputed', () {
        expect(ServiceRecord.fromJson({...baseJson, 'status': 'disputed'}).isDisputed, isTrue);
        expect(ServiceRecord.fromJson({...baseJson, 'status': 'verified'}).isDisputed, isFalse);
      });
    });
  });
}
