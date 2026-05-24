class WarrantyClaim {
  final String vin;
  final int claimIndex;
  final String issueDescription;
  final String status;
  final String? denialReason;
  final int submittedAt;

  const WarrantyClaim({
    required this.vin,
    required this.claimIndex,
    required this.issueDescription,
    required this.status,
    this.denialReason,
    required this.submittedAt,
  });

  factory WarrantyClaim.fromJson(Map<String, dynamic> j) => WarrantyClaim(
        vin: j['vin'] ?? '',
        claimIndex: (j['claim_index'] ?? j['index'] ?? 0) as int,
        issueDescription: j['issue_description'] ?? '',
        status: j['status'] ?? '',
        denialReason: j['denial_reason'],
        submittedAt: (j['submitted_at'] ?? 0) as int,
      );

  bool get isPending => status == 'pending';
  bool get isApproved => status == 'approved';
  bool get isDenied => status == 'denied';
}
