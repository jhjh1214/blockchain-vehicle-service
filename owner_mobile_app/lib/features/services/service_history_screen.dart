import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'services_provider.dart';
import '../../core/api/api_client.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/models/service_record.dart';
import '../../shared/widgets/empty_state.dart';
import '../../shared/widgets/error_view.dart';

class ServiceHistoryScreen extends StatefulWidget {
  const ServiceHistoryScreen({super.key});

  @override
  State<ServiceHistoryScreen> createState() => _ServiceHistoryScreenState();
}

class _ServiceHistoryScreenState extends State<ServiceHistoryScreen> {
  String _statusFilter = 'all';

  static const _filterLabels = {
    'all': 'All',
    'verified': 'Verified',
    'disputed': 'Disputed',
  };

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
        title: 'No service history yet',
        subtitle: 'Once a service centre submits a record and you verify or dispute it, it will appear here.',
      );
    }

    final filtered = _statusFilter == 'all'
        ? provider.history
        : provider.history.where((r) => r.status == _statusFilter).toList();

    return Column(
      children: [
        _FilterChips(
          selected: _statusFilter,
          labels: _filterLabels,
          onSelected: (v) => setState(() => _statusFilter = v),
        ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: () => context.read<ServicesProvider>().loadHistory(),
            child: filtered.isEmpty
                ? ListView(
                    children: const [
                      Padding(
                        padding: EdgeInsets.all(40),
                        child: Center(child: Text('No records match this filter.')),
                      )
                    ],
                  )
                : ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
                    itemCount: filtered.length,
                    itemBuilder: (context, i) => _TimelineItem(
                      record: filtered[i],
                      isLast: i == filtered.length - 1,
                    ),
                  ),
          ),
        ),
      ],
    );
  }
}

class _FilterChips extends StatelessWidget {
  final String selected;
  final Map<String, String> labels;
  final ValueChanged<String> onSelected;

  const _FilterChips({
    required this.selected,
    required this.labels,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Container(
      height: 48,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: labels.entries.map((entry) {
          final isSelected = selected == entry.key;
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: Semantics(
              label: '${entry.value} filter',
              selected: isSelected,
              child: FilterChip(
                label: Text(entry.value),
                selected: isSelected,
                onSelected: (_) => onSelected(entry.key),
                selectedColor: colorScheme.primaryContainer,
                checkmarkColor: colorScheme.onPrimaryContainer,
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _TimelineItem extends StatefulWidget {
  final ServiceRecord record;
  final bool isLast;

  const _TimelineItem({required this.record, required this.isLast});

  @override
  State<_TimelineItem> createState() => _TimelineItemState();
}

class _TimelineItemState extends State<_TimelineItem> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final color = _statusColor(widget.record.status);
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Timeline column: icon + vertical connector
          SizedBox(
            width: 44,
            child: Column(
              children: [
                _IconNode(
                  serviceType: widget.record.serviceType,
                  color: color,
                ),
                if (!widget.isLast)
                  Expanded(
                    child: Container(
                      width: 2,
                      color: Theme.of(context).dividerColor,
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          // Card content
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: widget.isLast ? 0 : 16),
              child: _RecordCard(
                record: widget.record,
                expanded: _expanded,
                onToggle: () => setState(() => _expanded = !_expanded),
                statusColor: color,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'verified':
        return const Color(0xFF1D9E75);
      case 'disputed':
        return Colors.red.shade600;
      default:
        return Colors.orange.shade600;
    }
  }
}

class _IconNode extends StatelessWidget {
  final String serviceType;
  final Color color;

  const _IconNode({required this.serviceType, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        shape: BoxShape.circle,
        border: Border.all(color: color.withOpacity(0.35), width: 1.5),
      ),
      child: Icon(_iconForType(serviceType), color: color, size: 20),
    );
  }

  IconData _iconForType(String type) {
    final t = type.toLowerCase();
    if (t.contains('oil')) return Icons.opacity;
    if (t.contains('tire') || t.contains('tyre') || t.contains('wheel')) {
      return Icons.tire_repair;
    }
    if (t.contains('brake')) return Icons.do_disturb_on;
    if (t.contains('battery')) return Icons.battery_charging_full;
    if (t.contains('ac') || t.contains('air') || t.contains('cool')) {
      return Icons.ac_unit;
    }
    if (t.contains('inspect') || t.contains('check')) {
      return Icons.fact_check_outlined;
    }
    if (t.contains('wash') || t.contains('clean')) return Icons.local_car_wash;
    if (t.contains('transmiss') || t.contains('gear')) return Icons.settings;
    if (t.contains('engine') || t.contains('motor')) return Icons.speed;
    return Icons.build_outlined;
  }
}

class _RecordCard extends StatelessWidget {
  final ServiceRecord record;
  final bool expanded;
  final VoidCallback onToggle;
  final Color statusColor;

  const _RecordCard({
    required this.record,
    required this.expanded,
    required this.onToggle,
    required this.statusColor,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 1,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(color: Theme.of(context).dividerColor),
      ),
      child: Column(
        children: [
          // Header row — always visible
          InkWell(
            onTap: onToggle,
            borderRadius: BorderRadius.circular(10),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          record.serviceType,
                          style: const TextStyle(
                              fontWeight: FontWeight.w600, fontSize: 14),
                        ),
                        const SizedBox(height: 3),
                        Row(
                          children: [
                            const Icon(Icons.calendar_today_outlined,
                                size: 12, color: Colors.grey),
                            const SizedBox(width: 4),
                            Text(
                              record.serviceDate,
                              style: const TextStyle(
                                  fontSize: 12, color: Colors.grey),
                            ),
                            if (record.mileage != null) ...[
                              const SizedBox(width: 10),
                              const Icon(Icons.speed_outlined,
                                  size: 12, color: Colors.grey),
                              const SizedBox(width: 4),
                              Text(
                                '${record.mileage} km',
                                style: const TextStyle(
                                    fontSize: 12, color: Colors.grey),
                              ),
                            ],
                          ],
                        ),
                      ],
                    ),
                  ),
                  _StatusChip(status: record.status, color: statusColor),
                  const SizedBox(width: 4),
                  AnimatedRotation(
                    turns: expanded ? 0.5 : 0,
                    duration: const Duration(milliseconds: 180),
                    child: const Icon(Icons.keyboard_arrow_down,
                        color: Colors.grey),
                  ),
                ],
              ),
            ),
          ),
          // Expanded details
          AnimatedCrossFade(
            duration: const Duration(milliseconds: 200),
            crossFadeState:
                expanded ? CrossFadeState.showSecond : CrossFadeState.showFirst,
            firstChild: const SizedBox.shrink(),
            secondChild: _DetailsPanel(record: record),
          ),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final String status;
  final Color color;

  const _StatusChip({required this.status, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(99),
      ),
      child: Text(
        status[0].toUpperCase() + status.substring(1),
        style: TextStyle(
            fontSize: 11, color: color, fontWeight: FontWeight.w600),
      ),
    );
  }
}

class _DetailsPanel extends StatelessWidget {
  final ServiceRecord record;
  const _DetailsPanel({required this.record});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(10)),
        border: Border(top: BorderSide(color: Theme.of(context).dividerColor)),
      ),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (record.vin.isNotEmpty)
            _row('VIN', record.vin),
          if (record.serviceCenterName != null)
            _row(
              'Service centre',
              record.isIndependentSC
                  ? '${record.serviceCenterName!} (Independent Workshop)'
                  : record.serviceCenterName!,
              valueColor: record.isIndependentSC ? Colors.orange.shade700 : null,
            ),
          if (record.technicianName != null)
            _row('Technician', record.technicianName!),
          if (record.partsReplaced != null && record.partsReplaced!.isNotEmpty)
            _row('Parts replaced', record.partsReplaced!),
          if (record.serviceNotes != null && record.serviceNotes!.isNotEmpty)
            _row('Notes', record.serviceNotes!),
          if (record.disputeReason != null)
            _row('Dispute reason', record.disputeReason!,
                valueColor: Colors.red.shade700),
          if (record.isIndependentSC && record.serviceCenterId != null) ...[
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => _reportWorkshop(context, record),
              icon: const Icon(Icons.flag_outlined, size: 16, color: Colors.red),
              label: const Text('Report this Workshop', style: TextStyle(color: Colors.red)),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: Colors.red),
                minimumSize: const Size(double.infinity, 36),
              ),
            ),
          ],
          if (record.isDisputed) ...[
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => context.push(
                '/services/dispute-chat/${record.vin}/${record.recordIndex}'
                '?type=${Uri.encodeComponent(record.serviceType)}',
              ),
              icon: const Icon(Icons.chat_bubble_outline, size: 16),
              label: const Text('View Dispute Thread'),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size(double.infinity, 36),
              ),
            ),
          ],
          if (record.isVerified && record.metadataHash != null) ...[
            const SizedBox(height: 8),
            const Divider(height: 1),
            const SizedBox(height: 8),
            _HashRow(hash: record.metadataHash!),
          ],
          const SizedBox(height: 6),
          Text(
            'Record #${record.recordIndex}',
            style: TextStyle(
                fontSize: 11,
                color: Colors.grey.shade500,
                fontFamily: 'monospace'),
          ),
        ],
      ),
    );
  }

  Future<void> _reportWorkshop(BuildContext context, ServiceRecord record) async {
    final reasons = ['spam', 'fake_service', 'harassment', 'other'];
    String selectedCategory = 'spam';
    final controller = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Report Independent Workshop'),
        content: StatefulBuilder(
          builder: (ctx2, setState) => Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Category:', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
              const SizedBox(height: 6),
              DropdownButton<String>(
                value: selectedCategory,
                isExpanded: true,
                items: reasons.map((r) => DropdownMenuItem(value: r, child: Text(r.replaceAll('_', ' ')))).toList(),
                onChanged: (v) => setState(() => selectedCategory = v!),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: controller,
                maxLines: 3,
                decoration: const InputDecoration(hintText: 'Describe the issue…', border: OutlineInputBorder()),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Submit Report')),
        ],
      ),
    );
    if (confirmed != true || controller.text.trim().isEmpty || !context.mounted) return;
    try {
      await ApiClient.instance.dio.post(ApiEndpoints.reportUser, data: {
        'reported_user_id': record.serviceCenterId,
        'reason': controller.text.trim(),
        'category': selectedCategory,
        'vin': record.vin,
      });
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Report submitted. Our team will review it.'), backgroundColor: Colors.green),
        );
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to submit report'), backgroundColor: Colors.red),
        );
      }
    }
  }

  Widget _row(String label, String value, {Color? valueColor}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
                width: 110,
                child: Text(label,
                    style: const TextStyle(color: Colors.grey, fontSize: 13))),
            Expanded(
                child: Text(value,
                    style: TextStyle(fontSize: 13, color: valueColor))),
          ],
        ),
      );
}

class _HashRow extends StatelessWidget {
  final String hash;
  const _HashRow({required this.hash});

  @override
  Widget build(BuildContext context) {
    final short = '${hash.substring(0, 10)}…${hash.substring(hash.length - 8)}';
    return Row(
      children: [
        const Icon(Icons.verified_outlined, size: 13, color: Color(0xFF1D9E75)),
        const SizedBox(width: 5),
        Expanded(
          child: Text(
            'Hash: $short',
            style: const TextStyle(
                fontSize: 11,
                fontFamily: 'monospace',
                color: Color(0xFF1D9E75)),
          ),
        ),
        GestureDetector(
          onTap: () {
            Clipboard.setData(ClipboardData(text: hash));
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                  content: Text('Hash copied to clipboard'),
                  duration: Duration(seconds: 2)),
            );
          },
          child: const Icon(Icons.copy_outlined, size: 14, color: Colors.grey),
        ),
      ],
    );
  }
}
