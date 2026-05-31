import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'services_provider.dart';
import '../../core/models/service_record.dart';
import '../../core/api/api_client.dart';
import '../../shared/widgets/empty_state.dart';
import '../../shared/widgets/error_view.dart';

class PendingServicesScreen extends StatefulWidget {
  const PendingServicesScreen({super.key});

  @override
  State<PendingServicesScreen> createState() => _PendingServicesScreenState();
}

class _PendingServicesScreenState extends State<PendingServicesScreen> {
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ServicesProvider>().loadPending();
    });
    _refreshTimer = Timer.periodic(const Duration(seconds: 60), (_) {
      if (mounted) context.read<ServicesProvider>().loadPending();
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _verify(ServiceRecord record) async {
    final confirm = await _showDialog(
      'Verify Service',
      'Confirm that this service was performed correctly?',
      confirmLabel: 'Verify',
      confirmColor: Colors.green,
    );
    if (!confirm || !mounted) return;
    final result = await context
        .read<ServicesProvider>()
        .verifyService(record.vin, record.recordIndex);
    if (!mounted) return;
    if (result.isSuccess) {
      _showTxSnackBar('Service verified', result.txHash, Colors.green);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(result.error!),
        backgroundColor: Colors.red,
      ));
    }
  }

  Future<void> _dispute(ServiceRecord record) async {
    final reason = await _showDisputeDialog();
    if (reason == null || !mounted) return;
    final result = await context
        .read<ServicesProvider>()
        .disputeService(record.vin, record.recordIndex, reason);
    if (!mounted) return;
    if (result.isSuccess) {
      _showTxSnackBar('Service disputed', result.txHash, Colors.orange);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(result.error!),
        backgroundColor: Colors.red,
      ));
    }
  }

  void _showTxSnackBar(String message, String? txHash, Color color) {
    final short = txHash != null && txHash.length > 14
        ? '${txHash.substring(0, 8)}…${txHash.substring(txHash.length - 6)}'
        : txHash;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(message),
          if (short != null)
            Text('TX: $short',
                style: const TextStyle(
                    fontSize: 11, fontFamily: 'monospace', color: Colors.white70)),
        ],
      ),
      backgroundColor: color,
      duration: const Duration(seconds: 5),
    ));
  }

  Future<bool> _showDialog(String title, String content,
      {required String confirmLabel, Color? confirmColor}) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: Text(content),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: confirmColor),
            child: Text(confirmLabel),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  Future<String?> _showDisputeDialog() async {
    final ctrl = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Dispute Service'),
        content: TextField(
          controller: ctrl,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Reason for dispute',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel')),
          TextButton(
            onPressed: () {
              if (ctrl.text.trim().isNotEmpty) {
                Navigator.pop(ctx, ctrl.text.trim());
              }
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Dispute'),
          ),
        ],
      ),
    );
    ctrl.dispose();
    return result;
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ServicesProvider>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Pending Services'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => context.read<ServicesProvider>().loadPending(),
          ),
        ],
      ),
      body: _buildBody(provider),
    );
  }

  Widget _buildBody(ServicesProvider provider) {
    if (provider.loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.error != null) {
      return ErrorView(
          message: provider.error!,
          onRetry: () => context.read<ServicesProvider>().loadPending());
    }
    if (provider.pending.isEmpty) {
      return const EmptyState(
        icon: Icons.check_circle_outline,
        title: 'Nothing to review',
        subtitle: 'You\'re all caught up. When a service centre logs a new service record for your vehicle, it will appear here for your approval.',
      );
    }
    return RefreshIndicator(
      onRefresh: () => context.read<ServicesProvider>().loadPending(),
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: provider.pending.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (context, i) => _ServiceCard(
          record: provider.pending[i],
          onVerify: () => _verify(provider.pending[i]),
          onDispute: () => _dispute(provider.pending[i]),
        ),
      ),
    );
  }
}

class _ServiceCard extends StatelessWidget {
  final ServiceRecord record;
  final VoidCallback onVerify;
  final VoidCallback onDispute;

  const _ServiceCard({
    required this.record,
    required this.onVerify,
    required this.onDispute,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.build_outlined, size: 20, color: Colors.grey),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(record.serviceType,
                      style: const TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 15)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            _row('VIN', record.vin),
            if (record.serviceCenterName != null)
              _row('Service Centre', record.serviceCenterName!),
            _row('Date', record.serviceDate),
            if (record.mileage != null)
              _row('Mileage', '${record.mileage} km'),
            if (record.technicianName != null)
              _row('Technician', record.technicianName!),
            if (record.partsReplaced != null &&
                record.partsReplaced!.isNotEmpty)
              _row('Parts', record.partsReplaced!),
            if (record.serviceNotes != null &&
                record.serviceNotes!.isNotEmpty)
              _row('Notes', record.serviceNotes!),
            if (record.photos.isNotEmpty) ...[
              const SizedBox(height: 10),
              const Text('Photos',
                  style: TextStyle(fontSize: 12, color: Colors.grey)),
              const SizedBox(height: 6),
              SizedBox(
                height: 80,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: record.photos.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (ctx, i) {
                    final url = '${ApiClient.baseUrl}/upload/files/${record.photos[i]}';
                    return GestureDetector(
                      onTap: () => _showPhotoDialog(ctx, url),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: Image.network(
                          url,
                          width: 80,
                          height: 80,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => Container(
                            width: 80,
                            height: 80,
                            color: Colors.grey.shade200,
                            child: const Icon(Icons.broken_image,
                                color: Colors.grey),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
            if (record.metadataHash != null &&
                record.metadataHash!.isNotEmpty) ...[
              const SizedBox(height: 4),
              Theme(
                data: Theme.of(context)
                    .copyWith(dividerColor: Colors.transparent),
                child: ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  childrenPadding: const EdgeInsets.only(bottom: 4),
                  title: const Text('Technical Details',
                      style: TextStyle(fontSize: 12, color: Colors.grey)),
                  children: [
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('SHA-256 METADATA HASH',
                              style: TextStyle(
                                  fontSize: 10,
                                  color: Colors.grey,
                                  letterSpacing: 0.6)),
                          const SizedBox(height: 6),
                          Text(
                            record.metadataHash!,
                            style: const TextStyle(
                                fontFamily: 'monospace', fontSize: 11),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: onDispute,
                    icon: const Icon(Icons.flag_outlined, color: Colors.red),
                    label: const Text('Dispute',
                        style: TextStyle(color: Colors.red)),
                    style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: Colors.red)),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: onVerify,
                    icon: const Icon(Icons.check),
                    label: const Text('Verify'),
                    style: FilledButton.styleFrom(
                        backgroundColor: Colors.green),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => context.push(
                '/services/dispute-chat/${record.vin}/${record.recordIndex}'
                '?type=${Uri.encodeComponent(record.serviceType)}',
              ),
              icon: const Icon(Icons.chat_bubble_outline, size: 16),
              label: const Text('Dispute Thread'),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size(double.infinity, 36),
              ),
            ),
          ],
        ),
      ),
    );
  }

  static void _showPhotoDialog(BuildContext context, String url) {
    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        child: Stack(
          children: [
            InteractiveViewer(
              child: Image.network(url, fit: BoxFit.contain),
            ),
            Positioned(
              top: 4,
              right: 4,
              child: IconButton(
                icon: const Icon(Icons.close, color: Colors.white),
                onPressed: () => Navigator.pop(ctx),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _row(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
                width: 90,
                child: Text(label,
                    style: const TextStyle(
                        color: Colors.grey, fontSize: 13))),
            Expanded(
                child: Text(value,
                    style: const TextStyle(fontSize: 13))),
          ],
        ),
      );
}
