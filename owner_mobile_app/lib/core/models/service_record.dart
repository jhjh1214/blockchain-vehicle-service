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
  final int? serviceCenterId;
  final String? scBrand;
  final String? rebuttalNotes;
  final String? rebuttalSubmittedAt;
  final bool escalated;

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
    this.serviceCenterId,
    this.scBrand,
    this.rebuttalNotes,
    this.rebuttalSubmittedAt,
    this.escalated = false,
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
        serviceCenterId: j['service_center_id'] as int?,
        scBrand: j['sc_brand'],
        rebuttalNotes: j['rebuttal_notes'],
        rebuttalSubmittedAt: j['rebuttal_submitted_at'],
        escalated: j['escalated'] == true,
      );

  bool get isPending => status == 'pending';
  bool get isVerified => status == 'verified';
  bool get isDisputed => status == 'disputed';
  bool get isIndependentSC => scBrand == null;
}
