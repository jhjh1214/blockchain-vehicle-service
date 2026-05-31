import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppNotification {
  final String title;
  final String body;
  final Map<String, String> data;
  final DateTime receivedAt;
  bool read;

  AppNotification({
    required this.title,
    required this.body,
    required this.data,
    required this.receivedAt,
    this.read = false,
  });

  Map<String, dynamic> toJson() => {
        'title': title,
        'body': body,
        'data': data,
        'receivedAt': receivedAt.toIso8601String(),
        'read': read,
      };

  factory AppNotification.fromJson(Map<String, dynamic> j) => AppNotification(
        title: j['title'] as String? ?? '',
        body: j['body'] as String? ?? '',
        data: Map<String, String>.from(j['data'] as Map? ?? {}),
        receivedAt: DateTime.tryParse(j['receivedAt'] as String? ?? '') ?? DateTime.now(),
        read: j['read'] as bool? ?? false,
      );
}

class NotificationsProvider extends ChangeNotifier {
  static const _key = 'vc_notifications';
  static const _maxStored = 50;

  List<AppNotification> _items = [];

  List<AppNotification> get items => _items;
  int get unreadCount => _items.where((n) => !n.read).length;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null) return;
    try {
      final list = jsonDecode(raw) as List;
      _items = list.map((e) => AppNotification.fromJson(e as Map<String, dynamic>)).toList();
      notifyListeners();
    } catch (_) {}
  }

  Future<void> add(String title, String body, Map<String, String> data) async {
    _items.insert(0, AppNotification(title: title, body: body, data: data, receivedAt: DateTime.now()));
    if (_items.length > _maxStored) _items = _items.sublist(0, _maxStored);
    await _persist();
    notifyListeners();
  }

  Future<void> markAllRead() async {
    for (final n in _items) {
      n.read = true;
    }
    await _persist();
    notifyListeners();
  }

  Future<void> clear() async {
    _items = [];
    await _persist();
    notifyListeners();
  }

  Future<void> _persist() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(_items.map((n) => n.toJson()).toList()));
  }
}
