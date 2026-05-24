import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'warranties_provider.dart';
import '../../core/models/warranty_claim.dart';
import '../../shared/widgets/empty_state.dart';
import '../../shared/widgets/error_view.dart';
import '../../shared/widgets/status_badge.dart';

class WarrantyClaimsScreen extends StatefulWidget {
  const WarrantyClaimsScreen({super.key});

  @override
  State<WarrantyClaimsScreen> createState() => _WarrantyClaimsScreenState();
}

class _WarrantyClaimsScreenState extends State<WarrantyClaimsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<WarrantiesProvider>().loadClaims();
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<WarrantiesProvider>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Warranty Claims'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => context.read<WarrantiesProvider>().loadClaims(),
          ),
        ],
      ),
      body: _buildBody(provider),
    );
  }

  Widget _buildBody(WarrantiesProvider provider) {
    if (provider.loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.error != null) {
      return ErrorView(
          message: provider.error!,
          onRetry: () => context.read<WarrantiesProvider>().loadClaims());
    }
    if (provider.claims.isEmpty) {
      return const EmptyState(
        icon: Icons.shield_outlined,
        title: 'No warranty claims',
        subtitle: 'Submit a claim from a vehicle\'s detail page',
      );
    }
    return RefreshIndicator(
      onRefresh: () => context.read<WarrantiesProvider>().loadClaims(),
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: provider.claims.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (context, i) => _ClaimCard(claim: provider.claims[i]),
      ),
    );
  }
}

class _ClaimCard extends StatelessWidget {
  final WarrantyClaim claim;
  const _ClaimCard({required this.claim});

  @override
  Widget build(BuildContext context) {
    final date = DateFormat('dd MMM yyyy').format(
        DateTime.fromMillisecondsSinceEpoch(claim.submittedAt * 1000));
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.shield_outlined, size: 20, color: Colors.grey),
                const SizedBox(width: 8),
                Expanded(
                  child: Text('VIN: ${claim.vin}',
                      style: const TextStyle(
                          fontFamily: 'monospace',
                          fontWeight: FontWeight.w600,
                          fontSize: 13)),
                ),
                StatusBadge(status: claim.status),
              ],
            ),
            const SizedBox(height: 10),
            Text(claim.issueDescription,
                style: const TextStyle(fontSize: 14)),
            const SizedBox(height: 8),
            Text('Submitted: $date',
                style:
                    const TextStyle(color: Colors.grey, fontSize: 12)),
            if (claim.denialReason != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.red.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline,
                        size: 16, color: Colors.red),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text('Denied: ${claim.denialReason}',
                          style: const TextStyle(
                              color: Colors.red, fontSize: 12)),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
