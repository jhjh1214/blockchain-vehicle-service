import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class StatusBadge extends StatelessWidget {
  final String status;

  const StatusBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    final (color, label) = switch (status.toLowerCase()) {
      'pending' => (AppColors.pending, 'Pending'),
      'verified' => (AppColors.verified, 'Verified'),
      'disputed' => (AppColors.disputed, 'Disputed'),
      'approved' => (AppColors.verified, 'Approved'),
      'denied' => (AppColors.disputed, 'Denied'),
      'resolved' => (AppColors.primary, 'Resolved'),
      'active' => (AppColors.verified, 'Active'),
      'expired' => (AppColors.disputed, 'Expired'),
      _ => (Colors.grey, status),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
