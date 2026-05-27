import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import '../../core/api/api_client.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/models/vehicle.dart';

class VehiclesProvider extends ChangeNotifier {
  List<Vehicle> _vehicles = [];
  bool _loading = false;
  String? _error;

  List<Vehicle> get vehicles => _vehicles;
  bool get loading => _loading;
  String? get error => _error;

  Future<void> loadVehicles() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      final res =
          await ApiClient.instance.dio.get(ApiEndpoints.myVehicles);
      final list = res.data['vehicles'] as List;
      _vehicles = list.map((v) => Vehicle.fromJson(v)).toList();
    } on DioException catch (e) {
      _error = e.response?.data['error'] ?? 'Failed to load vehicles';
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<Vehicle?> getVehicle(String vin) async {
    try {
      final res = await ApiClient.instance.dio
          .get(ApiEndpoints.vehicleDetail(vin));
      return Vehicle.fromJson(res.data);
    } catch (_) {
      return null;
    }
  }

  Future<String?> claimVehicle(String vin) async {
    try {
      await ApiClient.instance.dio
          .post(ApiEndpoints.claimVehicle, data: {'vin': vin});
      await loadVehicles();
      return null;
    } on DioException catch (e) {
      return e.response?.data['error'] ?? 'Failed to claim vehicle';
    }
  }

  Future<String?> transferVehicle(String vin, String newOwnerEmail) async {
    try {
      await ApiClient.instance.dio.post(ApiEndpoints.transferVehicle,
          data: {'vin': vin, 'new_owner_email': newOwnerEmail});
      await loadVehicles();
      return null;
    } on DioException catch (e) {
      return e.response?.data['error'] ?? 'Failed to transfer vehicle';
    }
  }

  Future<Map<String, dynamic>?> checkWarranty(String vin) async {
    try {
      final res = await ApiClient.instance.dio
          .get(ApiEndpoints.warrantyCheck(vin));
      return res.data as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>?> checkEligibility(String vin) async {
    try {
      final res = await ApiClient.instance.dio
          .get(ApiEndpoints.warrantyEligibilityCheck(vin));
      return res.data as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }
}
