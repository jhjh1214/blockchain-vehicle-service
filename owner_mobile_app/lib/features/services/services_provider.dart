import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import '../../core/api/api_client.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/models/service_record.dart';

class ServicesProvider extends ChangeNotifier {
  List<ServiceRecord> _pending = [];
  List<ServiceRecord> _history = [];
  bool _loading = false;
  String? _error;

  List<ServiceRecord> get pending => _pending;
  List<ServiceRecord> get history => _history;
  bool get loading => _loading;
  String? get error => _error;

  Future<void> loadPending() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      final res = await ApiClient.instance.dio
          .get(ApiEndpoints.ownerPendingServices);
      final list = res.data['pending_services'] as List;
      _pending = list.map((s) => ServiceRecord.fromJson(s)).toList();
    } on DioException catch (e) {
      _error = e.response?.data['error'] ?? 'Failed to load pending services';
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> loadHistory() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      final res = await ApiClient.instance.dio
          .get(ApiEndpoints.ownerServiceHistory);
      final list = res.data['service_history'] as List;
      _history = list.map((s) => ServiceRecord.fromJson(s)).toList();
    } on DioException catch (e) {
      _error = e.response?.data['error'] ?? 'Failed to load service history';
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<String?> verifyService(String vin, int recordIndex) async {
    try {
      await ApiClient.instance.dio.post(ApiEndpoints.ownerVerifyService,
          data: {'vin': vin, 'record_index': recordIndex});
      await loadPending();
      return null;
    } on DioException catch (e) {
      return e.response?.data['error'] ?? 'Failed to verify service';
    }
  }

  Future<String?> disputeService(
      String vin, int recordIndex, String reason) async {
    try {
      await ApiClient.instance.dio.post(ApiEndpoints.ownerDisputeService,
          data: {'vin': vin, 'record_index': recordIndex, 'reason': reason});
      await loadPending();
      return null;
    } on DioException catch (e) {
      return e.response?.data['error'] ?? 'Failed to dispute service';
    }
  }
}
