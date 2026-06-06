import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:dio/dio.dart';
import '../auth/auth_provider.dart';
import '../../core/api/api_client.dart';
import '../../core/api/api_endpoints.dart';

class DisputeChatScreen extends StatefulWidget {
  final String vin;
  final int recordIndex;
  final String serviceType;

  const DisputeChatScreen({
    super.key,
    required this.vin,
    required this.recordIndex,
    required this.serviceType,
  });

  @override
  State<DisputeChatScreen> createState() => _DisputeChatScreenState();
}

class _DisputeChatScreenState extends State<DisputeChatScreen> {
  final _ctrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  List<Map<String, dynamic>> _messages = [];
  bool _loading = true;
  bool _sending = false;
  String? _error;
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    _loadMessages();
    _pollTimer = Timer.periodic(const Duration(seconds: 30), (_) => _loadMessages(silent: true));
  }

  @override
  void dispose() {
    _ctrl.dispose();
    _scrollCtrl.dispose();
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadMessages({bool silent = false}) async {
    if (!silent && mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final res = await ApiClient.instance.dio.get(
        ApiEndpoints.disputeMessages(widget.vin, widget.recordIndex),
      );
      final list = (res.data['messages'] as List)
          .map((m) => m as Map<String, dynamic>)
          .toList();
      if (!mounted) return;
      setState(() {
        _messages = list;
        _loading = false;
        _error = null;
      });
      _scrollToBottom();
    } on DioException catch (e) {
      if (!mounted) return;
      final msg = (e.response?.data as Map?)?['error'] as String?
          ?? 'Failed to load messages';
      setState(() {
        _loading = false;
        _error = msg;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Failed to load messages';
      });
    }
  }

  Future<void> _send() async {
    final text = _ctrl.text.trim();
    if (text.isEmpty || _sending) return;
    setState(() => _sending = true);
    _ctrl.clear();
    try {
      await ApiClient.instance.dio.post(
        ApiEndpoints.postDisputeMessage,
        data: {'vin': widget.vin, 'record_index': widget.recordIndex, 'message': text},
      );
      await _loadMessages();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to send message'), backgroundColor: Colors.red),
        );
        _ctrl.text = text;
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final myEmail = context.read<AuthProvider>().user?.email ?? '';
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.serviceType,
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
            Text('Dispute Thread · ${widget.vin}',
                style: const TextStyle(fontSize: 11, color: Colors.white70)),
          ],
        ),
      ),
      body: Column(
        children: [
          Expanded(child: _buildMessages(myEmail)),
          _buildInputBar(),
        ],
      ),
    );
  }

  Widget _buildMessages(String myEmail) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 8),
            TextButton(onPressed: _loadMessages, child: const Text('Retry')),
          ],
        ),
      );
    }
    if (_messages.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.chat_bubble_outline, size: 48, color: Colors.grey),
              SizedBox(height: 12),
              Text('No messages yet', style: TextStyle(color: Colors.grey)),
              SizedBox(height: 4),
              Text(
                'Use this thread to communicate about the dispute with the service centre.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ],
          ),
        ),
      );
    }
    return ListView.builder(
      controller: _scrollCtrl,
      padding: const EdgeInsets.all(12),
      itemCount: _messages.length,
      itemBuilder: (context, i) {
        final msg = _messages[i];
        final isMe = (msg['sender_role'] as String?) == 'OWNER';
        return _MessageBubble(
          message: msg['message'] as String? ?? '',
          senderName: isMe ? 'You' : (msg['sender_name'] as String? ?? 'Service Centre'),
          senderRole: msg['sender_role'] as String? ?? '',
          timestamp: msg['created_at'] as String?,
          isMe: isMe,
        );
      },
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        border: Border(top: BorderSide(color: Theme.of(context).dividerColor)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _ctrl,
              maxLines: 3,
              minLines: 1,
              textInputAction: TextInputAction.newline,
              decoration: InputDecoration(
                hintText: 'Type a message…',
                filled: true,
                fillColor: Theme.of(context).colorScheme.surfaceContainerHighest,
                contentPadding: const EdgeInsets.symmetric(
                    horizontal: 14, vertical: 10),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(20),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton.filled(
            onPressed: _sending ? null : _send,
            icon: _sending
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white))
                : const Icon(Icons.send),
          ),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  final String message;
  final String senderName;
  final String senderRole;
  final String? timestamp;
  final bool isMe;

  const _MessageBubble({
    required this.message,
    required this.senderName,
    required this.senderRole,
    required this.timestamp,
    required this.isMe,
  });

  @override
  Widget build(BuildContext context) {
    final time = timestamp != null
        ? DateFormat('MMM d, HH:mm').format(DateTime.parse(timestamp!).toLocal())
        : '';
    final roleColor = isMe
        ? Colors.blue.shade700
        : senderRole == 'MANUFACTURER'
            ? Colors.purple.shade700
            : Colors.teal.shade700;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment:
            isMe ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isMe) ...[
            CircleAvatar(
              radius: 14,
              backgroundColor: roleColor.withValues(alpha: 0.15),
              child: Text(
                senderName.isNotEmpty ? senderName[0].toUpperCase() : '?',
                style: TextStyle(fontSize: 12, color: roleColor),
              ),
            ),
            const SizedBox(width: 6),
          ],
          Flexible(
            child: Column(
              crossAxisAlignment:
                  isMe ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                if (!isMe)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 2, left: 4),
                    child: Text(
                      senderName,
                      style: TextStyle(
                          fontSize: 11,
                          color: roleColor,
                          fontWeight: FontWeight.w600),
                    ),
                  ),
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: isMe
                        ? Theme.of(context).colorScheme.primary
                        : Theme.of(context).colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(14),
                      topRight: const Radius.circular(14),
                      bottomLeft: isMe
                          ? const Radius.circular(14)
                          : const Radius.circular(4),
                      bottomRight: isMe
                          ? const Radius.circular(4)
                          : const Radius.circular(14),
                    ),
                  ),
                  child: Text(
                    message,
                    style: TextStyle(
                      fontSize: 13,
                      color: isMe ? Colors.white : null,
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.only(top: 2, left: 4, right: 4),
                  child: Text(
                    time,
                    style: const TextStyle(
                        fontSize: 10, color: Colors.grey),
                  ),
                ),
              ],
            ),
          ),
          if (isMe) const SizedBox(width: 6),
        ],
      ),
    );
  }
}
