import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services_provider.dart';
import '../../core/models/service_record.dart';
import '../../shared/widgets/empty_state.dart';
import '../../shared/widgets/error_view.dart';
import '../../shared/widgets/status_badge.dart';

class ServiceHistoryScreen extends StatefulWidget {
  const ServiceHistoryScreen({super.key});

  @override
  State<ServiceHistoryScreen> createState() => _ServiceHistoryScreenState();
}

class _ServiceHistoryScreenState extends State<ServiceHistoryScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ServicesProvider>().loadHistory();
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ServicesProvider>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Service History'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => context.read<ServicesProvider>().loadHistory(),
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
          onRetry: () => context.read<ServicesProvider>().loadHistory());
    }
    if (provider.history.isEmpty) {
      return const EmptyState(
        icon: Icons.history,
        title: 'No service history',
        subtitle: 'Completed service records will appear here',
      );
    }
    return RefreshIndicator(
      onRefresh: () => context.read<ServicesProvider>().loadHistory(),
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: provider.history.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (context, i) =>
            _HistoryCard(record: provider.history[i]),
      ),
    );
  }
}

class _HistoryCard extends StatelessWidget {
  final ServiceRecord record;
  const _HistoryCard({required this.record});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ExpansionTile(
        leading: const Icon(Icons.build, color: Colors.grey),
        title: Text(record.serviceType,
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(record.serviceDate,
            style: const TextStyle(fontSize: 12)),
        trailing: StatusBadge(status: record.status),
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Divider(),
                _row('VIN', record.vin),
                if (record.mileage != null)
                  _row('Mileage', '${record.mileage} km'),
                if (record.technicianName != null)
                  _row('Technician', record.technicianName!),
                if (record.partsReplaced != null &&
                    record.partsReplaced!.isNotEmpty)
                  _row('Parts replaced', record.partsReplaced!),
                if (record.serviceNotes != null &&
                    record.serviceNotes!.isNotEmpty)
                  _row('Notes', record.serviceNotes!),
                if (record.disputeReason != null)
                  _row('Dispute reason', record.disputeReason!,
                      valueColor: Colors.red),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _row(String label, String value, {Color? valueColor}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
                width: 120,
                child: Text(label,
                    style: const TextStyle(
                        color: Colors.grey, fontSize: 13))),
            Expanded(
                child: Text(value,
                    style: TextStyle(
                        fontSize: 13, color: valueColor))),
          ],
        ),
      );
}
