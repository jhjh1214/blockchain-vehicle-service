import 'package:flutter_test/flutter_test.dart';
import 'package:owner_mobile_app/core/models/vehicle.dart';

void main() {
  group('Vehicle.fromJson', () {
    test('parses full vehicle correctly', () {
      final json = {
        'vin': '1HGBH41JXMN109186',
        'make': 'Honda',
        'model': 'Civic',
        'year': 2022,
        'owner_address': '0xABC123',
        'registration_status': 'claimed',
        'warranty_expiry': 1999999999,
        'warranty_valid': true,
      };

      final v = Vehicle.fromJson(json);

      expect(v.vin, '1HGBH41JXMN109186');
      expect(v.make, 'Honda');
      expect(v.model, 'Civic');
      expect(v.year, 2022);
      expect(v.ownerAddress, '0xABC123');
      expect(v.registrationStatus, 'claimed');
      expect(v.warrantyExpiry, 1999999999);
      expect(v.warrantyValid, isTrue);
    });

    test('handles missing optional fields', () {
      final json = {
        'vin': '1HGBH41JXMN109186',
        'make': 'Toyota',
        'model': 'Camry',
      };

      final v = Vehicle.fromJson(json);

      expect(v.year, isNull);
      expect(v.ownerAddress, isNull);
      expect(v.warrantyValid, isFalse);
    });

    test('displayName formats correctly with year', () {
      final v = Vehicle.fromJson(
          {'vin': 'X', 'make': 'BMW', 'model': '3 Series', 'year': 2023});
      expect(v.displayName, '2023 BMW 3 Series');
    });

    test('displayName with null year omits year', () {
      final v = Vehicle.fromJson({'vin': 'X', 'make': 'BMW', 'model': 'X5'});
      expect(v.displayName, 'BMW X5');
    });

    test('warrantyValid defaults to false', () {
      final v = Vehicle.fromJson({'vin': 'X', 'make': 'A', 'model': 'B'});
      expect(v.warrantyValid, isFalse);
    });
  });
}
