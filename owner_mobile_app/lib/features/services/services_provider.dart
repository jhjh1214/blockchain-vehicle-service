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

  Future<ServiceOpResult> verifyService(String vin, int recordIndex) async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      final res = await ApiClient.instance.dio.post(
          ApiEndpoints.ownerVerifyService,
          data: {'vin': vin, 'record_index': recordIndex});
      final txHash = _extractTxHash(res.data);
      await loadPending();
      return ServiceOpResult(txHash: txHash);
    } on DioException catch (e) {
      _loading = false;
      notifyListeners();
      return ServiceOpResult(error: _dioError(e, 'Failed to verify service'));
    } catch (_) {
      _loading = false;
      notifyListeners();
      return ServiceOpResult(error: 'Failed to verify service');
    }
  }

  Future<ServiceOpResult> disputeService(
      String vin, int recordIndex, String reason) async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      final res = await ApiClient.instance.dio.post(
          ApiEndpoints.ownerDisputeService,
          data: {'vin': vin, 'record_index': recordIndex, 'reason': reason});
      final txHash = _extractTxHash(res.data);
      await loadPending();
      return ServiceOpResult(txHash: txHash);
    } on DioException catch (e) {
      _loading = false;
      notifyListeners();
      return ServiceOpResult(error: _dioError(e, 'Failed to dispute service'));
    } catch (_) {
      _loading = false;
      notifyListeners();
      return ServiceOpResult(error: 'Failed to dispute service');
    }
  }

  static String? _extractTxHash(dynamic data) {
    try {
      return (data as Map?)?['transaction']?['tx_hash'] as String?;
    } catch (_) {
      return null;
    }
  }

  static String _dioError(DioException e, String fallback) {
    try {
      return (e.response?.data as Map?)?['error'] as String? ?? fallback;
    } catch (_) {
      return fallback;
    }
  }
}

class ServiceOpResult {
  final String? error;
  final String? txHash;
  const ServiceOpResult({this.error, this.txHash});
  bool get isSuccess => error == null;
}
