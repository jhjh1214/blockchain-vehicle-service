import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'vehicles_provider.dart';
import '../../core/models/vehicle.dart';
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
  bool _loading = true;

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

  Future<void> _loadData() async {
    final provider = context.read<VehiclesProvider>();
    final results = await Future.wait([
      provider.getVehicle(widget.vin),
      provider.checkWarranty(widget.vin),
    ]);
    if (mounted) {
      setState(() {
        _vehicle = results[0] as Vehicle?;
        _warranty = results[1] as Map<String, dynamic>?;
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
        }),
        const SizedBox(height: 12),
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
