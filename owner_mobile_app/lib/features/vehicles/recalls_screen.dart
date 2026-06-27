import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import '../../core/api/api_client.dart';
import '../../core/api/api_endpoints.dart';

class RecallsScreen extends StatefulWidget {
  const RecallsScreen({super.key});

  @override
  State<RecallsScreen> createState() => _RecallsScreenState();
}

class _RecallsScreenState extends State<RecallsScreen> {
  List<dynamic> _recalls = [];
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
      final res = await ApiClient.instance.dio.get(ApiEndpoints.ownerRecalls);
      setState(() {
        _recalls = (res.data['recalls'] as List?) ?? [];
        _loading = false;
      });
    } on DioException catch (e) {
      setState(() {
        _error = e.response?.data?['error'] ?? 'Failed to load recalls';
        _loading = false;
      });
    } catch (_) {
      setState(() { _error = 'Failed to load recalls'; _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Safety Recalls'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 48, color: Colors.red.shade300),
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 16),
            TextButton(onPressed: _load, child: const Text('Retry')),
          ],
        ),
      );
    }
    if (_recalls.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.check_circle_outline, size: 64,
                color: Colors.green.shade300),
            const SizedBox(height: 16),
            const Text('No Active Recalls',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            Text('Your vehicles have no open safety recalls.',
                style: TextStyle(color: Colors.grey.shade600, fontSize: 14),
                textAlign: TextAlign.center),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _recalls.length,
        itemBuilder: (context, i) => _RecallCard(recall: _recalls[i]),
      ),
    );
  }
}

class _RecallCard extends StatelessWidget {
  final Map<String, dynamic> recall;
  const _RecallCard({required this.recall});

  @override
  Widget build(BuildContext context) {
    final myAffected = (recall['my_affected_vins'] as List?)?.cast<String>() ?? [];
    final myServiced = (recall['my_serviced_vins'] as List?)?.cast<String>() ?? [];
    final unserviced = myAffected.where((v) => !myServiced.contains(v)).toList();
    final isFullyServiced = unserviced.isEmpty && myAffected.isNotEmpty;

    final statusColor = isFullyServiced ? Colors.green : Colors.orange;
    final muted = Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6);

    return Card(
      margin: const EdgeInsets.only(bottom: 14),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: statusColor.withValues(alpha: 0.4), width: 1.5),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  isFullyServiced ? Icons.check_circle : Icons.warning_amber_rounded,
                  color: statusColor,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    recall['title'] ?? 'Recall Notice',
                    style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              recall['description'] ?? '',
              style: TextStyle(fontSize: 13, color: muted),
            ),
            const SizedBox(height: 12),
            if (unserviced.isNotEmpty) ...[
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.orange.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.orange.withValues(alpha: 0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Service Required for:',
                      style: TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 12,
                          color: Colors.orange),
                    ),
                    const SizedBox(height: 4),
                    ...unserviced.map((v) => Text(
                          v,
                          style: TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 12,
                              letterSpacing: 0.5,
                              color: Colors.orange.withValues(alpha: 0.9)),
                        )),
                    const SizedBox(height: 8),
                    Text(
                      'Please visit an authorised service centre to have the recall service performed.',
                      style: TextStyle(fontSize: 12, color: Colors.orange.withValues(alpha: 0.85)),
                    ),
                  ],
                ),
              ),
            ] else if (myServiced.isNotEmpty) ...[
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.green.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.green.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.check_circle, color: Colors.green, size: 16),
                    const SizedBox(width: 6),
                    Text(
                      'Recall service completed for your vehicle(s)',
                      style: TextStyle(fontSize: 12, color: Colors.green.withValues(alpha: 0.9)),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 8),
            if (recall['vin_range_start'] != null && recall['vin_range_end'] != null) ...[
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
                ),
                child: Row(
                  children: [
                    Icon(Icons.linear_scale, size: 13, color: muted),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'Affected range: ${recall['vin_range_start']} – ${recall['vin_range_end']}',
                        style: TextStyle(
                          fontSize: 11,
                          fontFamily: 'monospace',
                          color: muted,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 6),
            ],
            Text(
              'Issued by ${recall['issued_by'] ?? 'Manufacturer'}',
              style: TextStyle(fontSize: 11, color: muted),
            ),
          ],
        ),
      ),
    );
  }
}
