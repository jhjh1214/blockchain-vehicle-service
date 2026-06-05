import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import '../../core/api/api_client.dart';
import '../../core/api/api_endpoints.dart';

class VoidRequestsScreen extends StatefulWidget {
  const VoidRequestsScreen({super.key});

  @override
  State<VoidRequestsScreen> createState() => _VoidRequestsScreenState();
}

class _VoidRequestsScreenState extends State<VoidRequestsScreen> {
  List<dynamic> _requests = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final res = await ApiClient.instance.dio.get(ApiEndpoints.ownerVoidRequests);
      setState(() {
        _requests = (res.data['requests'] as List?) ?? [];
        _loading = false;
      });
    } on DioException catch (e) {
      setState(() { _error = e.response?.data?['error'] ?? 'Failed to load'; _loading = false; });
    } catch (_) {
      setState(() { _error = 'Failed to load'; _loading = false; });
    }
  }

  Future<void> _dispute(int id) async {
    final controller = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Dispute Warranty Void Request'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Explain why you believe this warranty void request is incorrect:',
              style: TextStyle(fontSize: 13),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              maxLines: 4,
              decoration: const InputDecoration(
                hintText: 'e.g. Vehicle was only serviced at authorised centres…',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Submit Dispute'),
          ),
        ],
      ),
    );
    if (confirmed != true || controller.text.trim().isEmpty || !mounted) return;
    try {
      await ApiClient.instance.dio.post(ApiEndpoints.voidRequestDispute(id), data: {
        'reason': controller.text.trim(),
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Dispute submitted. The manufacturer will review your case.'), backgroundColor: Colors.green),
        );
        _load();
      }
    } on DioException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.response?.data?['error'] ?? 'Failed to submit dispute'), backgroundColor: Colors.red),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Warranty Void Requests'),
        actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _load)],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Text(_error!, style: const TextStyle(color: Colors.red)));
    if (_requests.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.verified_user, size: 64, color: Colors.green),
            SizedBox(height: 12),
            Text('No warranty void requests', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            SizedBox(height: 6),
            Text('Your warranties are in good standing.', style: TextStyle(color: Colors.grey)),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _requests.length,
        itemBuilder: (context, i) => _buildCard(_requests[i]),
      ),
    );
  }

  Widget _buildCard(Map<String, dynamic> r) {
    final status = r['status'] as String? ?? 'pending';
    final statusColor = {
      'pending': Colors.orange,
      'disputed': Colors.blue,
      'approved': Colors.red,
      'denied': Colors.green,
    }[status] ?? Colors.grey;

    final statusLabel = {
      'pending': 'Pending Review',
      'disputed': 'Disputed — Under Review',
      'approved': 'Warranty Voided',
      'denied': 'Request Denied — Warranty Valid',
    }[status] ?? status;

    return Card(
      margin: const EdgeInsets.only(bottom: 14),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: statusColor.withOpacity(0.4), width: 1.5),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    r['vin'] ?? '',
                    style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w700, fontSize: 14, letterSpacing: 0.5),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(color: statusColor.withOpacity(0.12), borderRadius: BorderRadius.circular(20)),
                  child: Text(statusLabel, style: TextStyle(fontSize: 11, color: statusColor, fontWeight: FontWeight.w600)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text('Requested by: ${r['sc_name'] ?? r['sc_email'] ?? 'Service Centre'}',
                style: const TextStyle(fontSize: 13, color: Colors.grey)),
            const SizedBox(height: 6),
            Text(r['reason'] ?? '', style: const TextStyle(fontSize: 13)),
            if (r['mileage_submitted'] != null && r['last_authorized_mileage'] != null) ...[
              const SizedBox(height: 6),
              Text(
                'Mileage gap: ${(r['mileage_submitted'] - r['last_authorized_mileage']).toString()} km',
                style: TextStyle(fontSize: 12, color: Colors.orange.shade700, fontWeight: FontWeight.w500),
              ),
            ],
            if (r['manufacturer_notes'] != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text('Manufacturer note: ${r['manufacturer_notes']}', style: const TextStyle(fontSize: 12)),
              ),
            ],
            if (r['owner_dispute_reason'] != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: Colors.blue.shade50, borderRadius: BorderRadius.circular(6), border: Border.all(color: Colors.blue.shade200)),
                child: Text('Your dispute: ${r['owner_dispute_reason']}', style: TextStyle(fontSize: 12, color: Colors.blue.shade800)),
              ),
            ],
            if (status == 'pending') ...[
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () => _dispute(r['id'] as int),
                  icon: const Icon(Icons.gavel, size: 16),
                  label: const Text('Dispute This Request'),
                  style: OutlinedButton.styleFrom(foregroundColor: Colors.orange.shade700, side: BorderSide(color: Colors.orange.shade300)),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
