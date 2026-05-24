import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'vehicles_provider.dart';
import '../../shared/widgets/empty_state.dart';
import '../../shared/widgets/error_view.dart';
import '../../shared/theme/app_theme.dart';

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
          return Card(
            child: ListTile(
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              leading: Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.directions_car, color: AppColors.primary),
              ),
              title: Text(v.displayName,
                  style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text('VIN: ${v.vin}',
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
              trailing: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Icon(
                    v.warrantyValid ? Icons.verified : Icons.shield_outlined,
                    color: v.warrantyValid ? AppColors.success : Colors.grey,
                    size: 20,
                  ),
                  Text(
                    v.warrantyValid ? 'Warranty' : 'No warranty',
                    style: TextStyle(
                      fontSize: 11,
                      color: v.warrantyValid ? AppColors.success : Colors.grey,
                    ),
                  ),
                ],
              ),
              onTap: () => context.push('/vehicles/${v.vin}'),
            ),
          );
        },
      ),
    );
  }
}
