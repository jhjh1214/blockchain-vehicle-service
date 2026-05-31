import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'notifications_provider.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<NotificationsProvider>().markAllRead();
    });
  }

  IconData _iconFor(Map<String, String> data) {
    switch (data['type']) {
      case 'pending_service':
        return Icons.build_outlined;
      case 'warranty_claim':
        return Icons.shield_outlined;
      case 'dispute_resolved':
        return Icons.gavel_outlined;
      default:
        return Icons.notifications_outlined;
    }
  }

  Color _colorFor(Map<String, String> data) {
    switch (data['type']) {
      case 'pending_service':
        return Colors.orange;
      case 'warranty_claim':
        return Colors.blue;
      case 'dispute_resolved':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<NotificationsProvider>();
    final items = provider.items;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          if (items.isNotEmpty)
            TextButton(
              onPressed: () async {
                final ok = await showDialog<bool>(
                  context: context,
                  builder: (_) => AlertDialog(
                    title: const Text('Clear all notifications?'),
                    actions: [
                      TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
                      TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Clear')),
                    ],
                  ),
                );
                if (ok == true && context.mounted) {
                  await context.read<NotificationsProvider>().clear();
                }
              },
              child: const Text('Clear all'),
            ),
        ],
      ),
      body: items.isEmpty
          ? Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.notifications_none, size: 64, color: Colors.grey[400]),
                  const SizedBox(height: 12),
                  Text('No notifications yet', style: TextStyle(color: Colors.grey[500])),
                ],
              ),
            )
          : ListView.separated(
              itemCount: items.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, i) {
                final n = items[i];
                final color = _colorFor(n.data);
                return ListTile(
                  leading: CircleAvatar(
                    backgroundColor: color.withAlpha(30),
                    child: Icon(_iconFor(n.data), color: color, size: 20),
                  ),
                  title: Text(n.title,
                      style: TextStyle(
                        fontWeight: n.read ? FontWeight.normal : FontWeight.bold,
                        fontSize: 14,
                      )),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(n.body, style: const TextStyle(fontSize: 13)),
                      const SizedBox(height: 2),
                      Text(
                        DateFormat('d MMM yyyy, h:mm a').format(n.receivedAt.toLocal()),
                        style: TextStyle(fontSize: 11, color: Colors.grey[500]),
                      ),
                    ],
                  ),
                  isThreeLine: true,
                );
              },
            ),
    );
  }
}
