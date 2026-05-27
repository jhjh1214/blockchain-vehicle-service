class Vehicle {
  final String vin;
  final String make;
  final String model;
  final int? year;
  final String? ownerAddress;
  final String? registrationStatus;
  final int? warrantyExpiry;
  final bool warrantyValid;
  final int serviceCount;

  const Vehicle({
    required this.vin,
    required this.make,
    required this.model,
    this.year,
    this.ownerAddress,
    this.registrationStatus,
    this.warrantyExpiry,
    this.warrantyValid = false,
    this.serviceCount = 0,
  });

  factory Vehicle.fromJson(Map<String, dynamic> j) {
    final owner = j['owner'] as Map<String, dynamic>?;
    return Vehicle(
      vin: j['vin'] ?? '',
      make: j['make'] ?? '',
      model: j['model'] ?? '',
      year: j['year'] as int?,
      ownerAddress: j['owner_address'] ?? owner?['address'],
      registrationStatus: j['registration_status'],
      warrantyExpiry: j['warranty_expiry'] as int?,
      warrantyValid: j['warranty_valid'] as bool? ?? false,
      serviceCount: j['service_count'] as int? ?? 0,
    );
  }

  String get displayName => '${year != null ? '$year ' : ''}$make $model'.trim();
}
