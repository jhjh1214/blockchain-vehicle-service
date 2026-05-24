import 'package:flutter_test/flutter_test.dart';
import 'package:owner_mobile_app/core/models/warranty_claim.dart';

void main() {
  group('WarrantyClaim.fromJson', () {
    final baseJson = {
      'vin': '1HGBH41JXMN109186',
      'claim_index': 0,
      'issue_description': 'Engine noise at startup',
      'status': 'pending',
      'submitted_at': 1700000000,
    };

    test('parses required fields', () {
      final c = WarrantyClaim.fromJson(baseJson);
      expect(c.vin, '1HGBH41JXMN109186');
      expect(c.claimIndex, 0);
      expect(c.issueDescription, 'Engine noise at startup');
      expect(c.status, 'pending');
      expect(c.submittedAt, 1700000000);
      expect(c.denialReason, isNull);
    });

    test('parses denial reason', () {
      final json = {...baseJson, 'denial_reason': 'Not covered', 'status': 'denied'};
      final c = WarrantyClaim.fromJson(json);
      expect(c.denialReason, 'Not covered');
      expect(c.isDenied, isTrue);
    });

    test('accepts index as fallback for claim_index', () {
      final json = {...baseJson}..remove('claim_index');
      json['index'] = 5;
      expect(WarrantyClaim.fromJson(json).claimIndex, 5);
    });

    group('status helpers', () {
      test('isPending', () {
        expect(WarrantyClaim.fromJson({...baseJson, 'status': 'pending'}).isPending, isTrue);
        expect(WarrantyClaim.fromJson({...baseJson, 'status': 'approved'}).isPending, isFalse);
      });

      test('isApproved', () {
        expect(WarrantyClaim.fromJson({...baseJson, 'status': 'approved'}).isApproved, isTrue);
        expect(WarrantyClaim.fromJson({...baseJson, 'status': 'denied'}).isApproved, isFalse);
      });

      test('isDenied', () {
        expect(WarrantyClaim.fromJson({...baseJson, 'status': 'denied'}).isDenied, isTrue);
        expect(WarrantyClaim.fromJson({...baseJson, 'status': 'approved'}).isDenied, isFalse);
      });
    });
  });
}
