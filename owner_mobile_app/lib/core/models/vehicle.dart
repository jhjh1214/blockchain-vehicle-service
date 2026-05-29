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
  final String? lastServiceDate;
  final int? daysSinceService;
  final int? lastServiceMileage;

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
    this.lastServiceDate,
    this.daysSinceService,
    this.lastServiceMileage,
  });

  factory Vehicle.fromJson(Map<String, dynamic> j) {
    final owner = j['owner'] as Map<String, dynamic>?;
    final warranty = j['warranty'] as Map<String, dynamic>?;
    return Vehicle(
      vin: j['vin'] ?? '',
      make: j['make'] ?? '',
      model: j['model'] ?? '',
      year: j['year'] as int?,
      ownerAddress: j['owner_address'] ?? owner?['address'],
      registrationStatus: j['registration_status'],
      warrantyExpiry: j['warranty_expiry'] as int? ??
          (warranty?['expiry'] as int?),
      warrantyValid: j['warranty_valid'] as bool? ??
          (warranty?['is_valid'] as bool? ?? false),
      serviceCount: j['service_count'] as int? ?? 0,
      lastServiceDate: j['last_service_date'] as String?,
      daysSinceService: j['days_since_service'] as int?,
      lastServiceMileage: j['last_service_mileage'] as int?,
    );
  }

  String get displayName => '${year != null ? '$year ' : ''}$make $model'.trim();
}
