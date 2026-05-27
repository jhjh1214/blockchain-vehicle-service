class ServiceRecord {
  final String vin;
  final int recordIndex;
  final String serviceType;
  final String serviceDate;
  final int? mileage;
  final String? partsReplaced;
  final String? technicianName;
  final String? serviceNotes;
  final String status;
  final String? disputeReason;
  final String submittedBy;
  final String? serviceCenterName;
  final String? metadataHash;
  final List<String> photos;

  const ServiceRecord({
    required this.vin,
    required this.recordIndex,
    required this.serviceType,
    required this.serviceDate,
    this.mileage,
    this.partsReplaced,
    this.technicianName,
    this.serviceNotes,
    required this.status,
    this.disputeReason,
    required this.submittedBy,
    this.serviceCenterName,
    this.metadataHash,
    this.photos = const [],
  });

  factory ServiceRecord.fromJson(Map<String, dynamic> j) => ServiceRecord(
        vin: j['vin'] ?? '',
        recordIndex: (j['record_index'] ?? j['index'] ?? 0) as int,
        serviceType: j['service_type'] ?? '',
        serviceDate: j['service_date'] ?? '',
        mileage: j['mileage'] as int?,
        partsReplaced: j['parts_replaced'],
        technicianName: j['technician_name'],
        serviceNotes: j['service_notes'],
        status: j['status'] ?? '',
        disputeReason: j['dispute_reason'],
        submittedBy: j['submitted_by'] ?? '',
        serviceCenterName: j['service_center_name'],
        metadataHash: j['metadata_hash'],
        photos: (j['photos'] as List?)?.map((e) => e.toString()).toList() ?? [],
      );

  bool get isPending => status == 'pending';
  bool get isVerified => status == 'verified';
  bool get isDisputed => status == 'disputed';
}
