import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'vehicles_provider.dart';
import '../services/services_provider.dart';
import '../../shared/widgets/empty_state.dart';
import '../../shared/widgets/error_view.dart';
import '../../shared/theme/app_theme.dart';
import '../../core/models/vehicle.dart';

class VehiclesScreen extends StatefulWidget {
  const VehiclesScreen({super.key});

  @override
  State<VehiclesScreen> createState() => _VehiclesScreenState();
}

class _VehiclesScreenState extends State<VehiclesScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<VehiclesProvider>().loadVehicles();
      final sp = context.read<ServicesProvider>();
      if (sp.pending.isEmpty) sp.loadPending();
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<VehiclesProvider>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Vehicles'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => context.read<VehiclesProvider>().loadVehicles(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/vehicles/claim'),
        icon: const Icon(Icons.add),
        label: const Text('Claim Vehicle'),
      ),
      body: _buildBody(provider),
    );
  }

  Widget _buildBody(VehiclesProvider provider) {
    final servicesProvider = context.watch<ServicesProvider>();
    if (provider.loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.error != null) {
      return ErrorView(
          message: provider.error!,
          onRetry: () => context.read<VehiclesProvider>().loadVehicles());
    }
    if (provider.vehicles.isEmpty) {
      return EmptyState(
        icon: Icons.directions_car_outlined,
        title: 'No vehicles yet',
        subtitle: 'Claim your vehicle using its VIN number',
        action: FilledButton.icon(
          onPressed: () => context.push('/vehicles/claim'),
          icon: const Icon(Icons.add),
          label: const Text('Claim Vehicle'),
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: () => context.read<VehiclesProvider>().loadVehicles(),
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: provider.vehicles.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (context, i) {
          final v = provider.vehicles[i];
          final pendingCount = servicesProvider.pending
              .where((r) => r.vin == v.vin)
              .length;
          return Card(
            child: ListTile(
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              leading: Stack(
                clipBehavior: Clip.none,
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: AppColors.primary.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child:
                        const Icon(Icons.directions_car, color: AppColors.primary),
                  ),
                  if (pendingCount > 0)
                    Positioned(
                      top: -4,
                      right: -4,
                      child: Container(
                        padding: const EdgeInsets.all(3),
                        decoration: const BoxDecoration(
                            color: Colors.red, shape: BoxShape.circle),
                        constraints:
                            const BoxConstraints(minWidth: 18, minHeight: 18),
                        child: Text(
                          '$pendingCount',
                          style: const TextStyle(
                              color: Colors.white,
                              fontSize: 10,
                              fontWeight: FontWeight.bold),
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ),
                ],
              ),
              title: Text(v.displayName,
                  style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text('VIN: ${v.vin}',
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
              trailing: _WarrantyBadge(vehicle: v),
              onTap: () => context.push('/vehicles/${v.vin}'),
            ),
          );
        },
      ),
    );
  }
}

class _WarrantyBadge extends StatelessWidget {
  final Vehicle vehicle;
  const _WarrantyBadge({required this.vehicle});

  @override
  Widget build(BuildContext context) {
    if (!vehicle.warrantyValid) {
      return Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: const [
          Icon(Icons.shield_outlined, color: Colors.grey, size: 20),
          Text('No warranty',
              style: TextStyle(fontSize: 11, color: Colors.grey)),
        ],
      );
    }
    final expiry = vehicle.warrantyExpiry;
    if (expiry != null) {
      final daysLeft = DateTime.fromMillisecondsSinceEpoch(expiry * 1000)
          .difference(DateTime.now())
          .inDays;
      if (daysLeft <= 30 && daysLeft >= 0) {
        return Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            const Icon(Icons.warning_amber_rounded,
                color: Colors.amber, size: 20),
            Text(
              daysLeft == 0 ? 'Expires today' : 'Expires in $daysLeft d',
              style: const TextStyle(fontSize: 11, color: Colors.amber),
            ),
          ],
        );
      }
    }
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: const [
        Icon(Icons.verified, color: AppColors.success, size: 20),
        Text('Warranty',
            style: TextStyle(fontSize: 11, color: AppColors.success)),
      ],
    );
  }
}
