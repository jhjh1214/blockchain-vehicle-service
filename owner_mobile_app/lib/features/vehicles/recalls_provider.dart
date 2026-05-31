import 'package:flutter/foundation.dart';
import 'package:dio/dio.dart';
import '../../core/api/api_client.dart';
import '../../core/api/api_endpoints.dart';

class RecallsProvider extends ChangeNotifier {
  List<dynamic> _recalls = [];
  bool _loading = false;

  List<dynamic> get recalls => _recalls;
  bool get loading => _loading;

  int get unservicedCount {
    int count = 0;
    for (final r in _recalls) {
      final myAffected = (r['my_affected_vins'] as List?)?.length ?? 0;
      final myServiced = (r['my_serviced_vins'] as List?)?.length ?? 0;
      if (myAffected > myServiced) count++;
    }
    return count;
  }

  Future<void> load() async {
    _loading = true;
    notifyListeners();
    try {
      final res = await ApiClient.instance.dio.get(ApiEndpoints.ownerRecalls);
      _recalls = (res.data['recalls'] as List?) ?? [];
    } on DioException {
      _recalls = [];
    } catch (_) {
      _recalls = [];
    }
    _loading = false;
    notifyListeners();
  }
}
