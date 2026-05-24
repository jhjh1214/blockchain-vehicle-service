import 'package:flutter_test/flutter_test.dart';
import 'package:owner_mobile_app/core/models/user.dart';

void main() {
  group('User.fromJson', () {
    test('parses all fields correctly', () {
      final json = {
        'id': 42,
        'email': 'owner@example.com',
        'name': 'John Doe',
        'role': 'OWNER',
        'phone': '+601234567890',
        'city': 'Kuala Lumpur',
        'state': 'Selangor',
        'blockchain_address': '0xABCDEF1234567890ABCDEF1234567890ABCDEF12',
      };

      final user = User.fromJson(json);

      expect(user.id, '42');
      expect(user.email, 'owner@example.com');
      expect(user.name, 'John Doe');
      expect(user.role, 'OWNER');
      expect(user.phone, '+601234567890');
      expect(user.city, 'Kuala Lumpur');
      expect(user.state, 'Selangor');
      expect(user.blockchainAddress,
          '0xABCDEF1234567890ABCDEF1234567890ABCDEF12');
    });

    test('handles missing optional fields', () {
      final json = {
        'id': 1,
        'email': 'owner@example.com',
        'name': 'Jane',
        'role': 'OWNER',
        'blockchain_address': '0x1234',
      };

      final user = User.fromJson(json);

      expect(user.phone, isNull);
      expect(user.city, isNull);
      expect(user.state, isNull);
    });

    test('converts integer id to string', () {
      final json = {
        'id': 99,
        'email': 'a@b.com',
        'name': 'A',
        'role': 'OWNER',
        'blockchain_address': '0x0',
      };
      expect(User.fromJson(json).id, '99');
    });

    test('defaults empty strings when fields are null', () {
      final json = {
        'id': 1,
        'email': null,
        'name': null,
        'role': null,
        'blockchain_address': null,
      };
      final user = User.fromJson(json);
      expect(user.email, '');
      expect(user.name, '');
      expect(user.role, '');
      expect(user.blockchainAddress, '');
    });
  });
}
