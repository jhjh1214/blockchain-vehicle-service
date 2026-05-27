import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services_provider.dart';
import '../../core/models/service_record.dart';
import '../../shared/widgets/empty_state.dart';
import '../../shared/widgets/error_view.dart';

class PendingServicesScreen extends StatefulWidget {
  const PendingServicesScreen({super.key});

  @override
  State<PendingServicesScreen> createState() => _PendingServicesScreenState();
}

class _PendingServicesScreenState extends State<PendingServicesScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ServicesProvider>().loadPending();
    });
  }

  Future<void> _verify(ServiceRecord record) async {
    final confirm = await _showDialog(
      'Verify Service',
      'Confirm that this service was performed correctly?',
      confirmLabel: 'Verify',
      confirmColor: Colors.green,
    );
    if (!confirm || !mounted) return;
    final error = await context
        .read<ServicesProvider>()
        .verifyService(record.vin, record.recordIndex);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(error ?? 'Service verified'),
      backgroundColor: error != null ? Colors.red : Colors.green,
    ));
  }

  Future<void> _dispute(ServiceRecord record) async {
    final reason = await _showDisputeDialog();
    if (reason == null || !mounted) return;
    final error = await context
        .read<ServicesProvider>()
        .disputeService(record.vin, record.recordIndex, reason);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(error ?? 'Service disputed'),
      backgroundColor: error != null ? Colors.red : Colors.orange,
    ));
  }

  Future<bool> _showDialog(String title, String content,
      {required String confirmLabel, Color? confirmColor}) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(title),
        content: Text(content),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
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
      builder: (_) => AlertDialog(
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
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel')),
          TextButton(
            onPressed: () {
              if (ctrl.text.trim().isNotEmpty) {
                Navigator.pop(context, ctrl.text.trim());
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
        title: 'No pending services',
        subtitle: 'All services have been reviewed',
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
                        color: Colors.grey.shade100,
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
