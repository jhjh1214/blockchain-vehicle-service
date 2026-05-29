import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:open_file/open_file.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'vehicles_provider.dart';
import '../../core/models/vehicle.dart';
import '../../core/api/api_client.dart';
import '../../core/api/api_endpoints.dart';
import '../../shared/theme/app_theme.dart';

class VehicleDetailScreen extends StatefulWidget {
  final String vin;
  const VehicleDetailScreen({super.key, required this.vin});

  @override
  State<VehicleDetailScreen> createState() => _VehicleDetailScreenState();
}

class _VehicleDetailScreenState extends State<VehicleDetailScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  Vehicle? _vehicle;
  Map<String, dynamic>? _warranty;
  Map<String, dynamic>? _eligibility;
  bool _loading = true;
  bool _exporting = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _exportPdf() async {
    setState(() => _exporting = true);
    try {
      final bytes = await ApiClient.instance.downloadBytes(
        ApiEndpoints.vehicleExport(widget.vin),
      );
      if (!mounted) return;
      final dir = await getTemporaryDirectory();
      if (!mounted) return;
      final file = File('${dir.path}/VehicleChain_${widget.vin}.pdf');
      await file.writeAsBytes(bytes);
      if (!mounted) return;
      await OpenFile.open(file.path);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to generate PDF report')),
        );
      }
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  Future<void> _loadData() async {
    final provider = context.read<VehiclesProvider>();
    final results = await Future.wait([
      provider.getVehicle(widget.vin),
      provider.checkWarranty(widget.vin),
      provider.checkEligibility(widget.vin),
    ]);
    if (mounted) {
      setState(() {
        _vehicle = results[0] as Vehicle?;
        _warranty = results[1] as Map<String, dynamic>?;
        _eligibility = results[2] as Map<String, dynamic>?;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_vehicle?.displayName ?? widget.vin),
        actions: [
          PopupMenuButton<String>(
            onSelected: (v) {
              if (v == 'transfer') context.push('/vehicles/transfer/${widget.vin}');
              if (v == 'warranty') context.push('/warranties/submit/${widget.vin}');
            },
            itemBuilder: (_) => [
              const PopupMenuItem(
                  value: 'warranty',
                  child: ListTile(
                      leading: Icon(Icons.shield),
                      title: Text('Submit Warranty Claim'),
                      contentPadding: EdgeInsets.zero)),
              const PopupMenuItem(
                  value: 'transfer',
                  child: ListTile(
                      leading: Icon(Icons.swap_horiz),
                      title: Text('Transfer Ownership'),
                      contentPadding: EdgeInsets.zero)),
            ],
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Details'),
            Tab(text: 'Warranty'),
          ],
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _vehicle == null
              ? const Center(child: Text('Vehicle not found'))
              : TabBarView(
                  controller: _tabController,
                  children: [
                    _buildDetails(),
                    _buildWarranty(),
                  ],
                ),
    );
  }

  Widget _buildDetails() {
    final v = _vehicle!;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _InfoCard(title: 'Vehicle Information', items: {
          'VIN': v.vin,
          'Make': v.make,
          'Model': v.model,
          'Year': v.year?.toString() ?? '-',
          'Verified Services': '${v.serviceCount} records on-chain',
        }),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: v.vin));
              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                content: Text('VIN copied to clipboard'),
                duration: Duration(seconds: 2),
              ));
            },
            icon: const Icon(Icons.copy, size: 15),
            label: const Text('Copy VIN'),
            style: TextButton.styleFrom(
                foregroundColor: Colors.grey,
                padding: const EdgeInsets.symmetric(horizontal: 4)),
          ),
        ),
        _InfoCard(title: 'Ownership', items: {
          'Status': v.registrationStatus ?? '-',
          'Owner Address': () {
                final addr = v.ownerAddress;
                if (addr == null || addr.isEmpty) return '-';
                if (addr.length <= 14) return addr;
                return '${addr.substring(0, 8)}...${addr.substring(addr.length - 6)}';
              }(),
        }),
        const SizedBox(height: 16),
        OutlinedButton.icon(
          onPressed: () => context.go('/services/history'),
          icon: const Icon(Icons.history),
          label: const Text('View Service History'),
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: _exporting ? null : _exportPdf,
          icon: _exporting
              ? const SizedBox(
                  width: 18, height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.picture_as_pdf_outlined),
          label: Text(_exporting ? 'Generating PDF…' : 'Export History PDF'),
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: () => context.push('/vehicles/transfer/${v.vin}'),
          icon: const Icon(Icons.swap_horiz),
          label: const Text('Transfer Ownership'),
        ),
      ],
    );
  }

  Widget _buildWarranty() {
    if (_warranty == null) {
      return const Center(child: Text('Could not load warranty info'));
    }
    final isValid = _warranty!['valid'] as bool? ?? false;
    final expiry = _warranty!['warranty_expiry'] as int? ?? 0;
    final expiryDate = expiry > 0
        ? DateFormat('dd MMM yyyy').format(
            DateTime.fromMillisecondsSinceEpoch(expiry * 1000))
        : 'N/A';

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                Icon(
                  isValid ? Icons.verified_user : Icons.shield_outlined,
                  size: 56,
                  color: isValid ? AppColors.success : Colors.grey,
                ),
                const SizedBox(height: 12),
                Text(
                  isValid ? 'Warranty Active' : 'Warranty Expired',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: isValid ? AppColors.success : Colors.grey,
                  ),
                ),
                const SizedBox(height: 8),
                Text('Expires: $expiryDate',
                    style: const TextStyle(fontSize: 14, color: Colors.grey)),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        _buildEligibilityChecklist(),
        if (isValid) ...[
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: () =>
                context.push('/warranties/submit/${widget.vin}'),
            icon: const Icon(Icons.assignment),
            label: const Text('Submit Warranty Claim'),
          ),
        ],
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: () => context.push('/warranties'),
          icon: const Icon(Icons.list),
          label: const Text('View All My Claims'),
        ),
      ],
    );
  }

  Widget _buildEligibilityChecklist() {
    if (_eligibility == null) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(14),
          child: Row(children: [
            Icon(Icons.info_outline, size: 16, color: Colors.grey),
            SizedBox(width: 8),
            Text('Eligibility check unavailable',
                style: TextStyle(fontSize: 13, color: Colors.grey)),
          ]),
        ),
      );
    }
    final warrantyValid = _eligibility!['valid'] as bool? ?? false;
    final hasHistory = _eligibility!['service_history_maintained'] as bool? ?? false;
    final serviceCount = _eligibility!['service_record_count'] as int? ?? 0;
    final eligible = _eligibility!['eligible_to_claim'] as bool? ?? false;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(eligible ? Icons.checklist_rounded : Icons.checklist_outlined,
                  size: 18, color: eligible ? AppColors.success : Colors.amber),
              const SizedBox(width: 6),
              Text('Warranty Eligibility Checklist',
                  style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                      color: eligible ? AppColors.success : Colors.amber)),
            ]),
            const Divider(height: 16),
            _checkItem('Warranty within validity period', warrantyValid),
            _checkItem(
                'Service history maintained ($serviceCount record${serviceCount == 1 ? '' : 's'})',
                hasHistory),
          ],
        ),
      ),
    );
  }

  Widget _checkItem(String label, bool passed) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        Icon(
          passed ? Icons.check_circle_outline : Icons.cancel_outlined,
          size: 16,
          color: passed ? AppColors.success : Colors.redAccent,
        ),
        const SizedBox(width: 8),
        Expanded(
            child: Text(label,
                style: TextStyle(
                    fontSize: 13,
                    color: passed
                        ? const Color(0xFF374151)
                        : Colors.redAccent))),
      ]),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final String title;
  final Map<String, String> items;

  const _InfoCard({required this.title, required this.items});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title,
                style: const TextStyle(
                    fontWeight: FontWeight.bold, fontSize: 14)),
            const Divider(height: 20),
            ...items.entries.map((e) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 120,
                        child: Text(e.key,
                            style: const TextStyle(
                                color: Colors.grey, fontSize: 13)),
                      ),
                      Expanded(
                        child: Text(e.value,
                            style: const TextStyle(
                                fontWeight: FontWeight.w500, fontSize: 13)),
                      ),
                    ],
                  ),
                )),
          ],
        ),
      ),
    );
  }
}
