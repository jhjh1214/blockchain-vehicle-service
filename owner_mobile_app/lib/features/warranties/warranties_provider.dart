import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:image_picker/image_picker.dart';
import '../../core/api/api_client.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/models/warranty_claim.dart';

class WarrantiesProvider extends ChangeNotifier {
  List<WarrantyClaim> _claims = [];
  bool _loading = false;
  String? _error;

  List<WarrantyClaim> get claims => _claims;
  bool get loading => _loading;
  String? get error => _error;

  Future<void> loadClaims() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      final res =
          await ApiClient.instance.dio.get(ApiEndpoints.ownerClaims);
      final list = res.data['claims'] as List;
      _claims = list.map((c) => WarrantyClaim.fromJson(c)).toList();
    } on DioException catch (e) {
      _error = e.response?.data['error'] ?? 'Failed to load claims';
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<String?> submitClaim(
    String vin,
    String issueDescription, {
    List<XFile> photos = const [],
  }) async {
    try {
      if (photos.isNotEmpty) {
        final formData = FormData.fromMap({
          'vin': vin,
          'issue_description': issueDescription,
          'photos': await Future.wait(photos.map((f) async =>
              MultipartFile.fromFile(f.path, filename: f.name))),
        });
        await ApiClient.instance.dio.post(ApiEndpoints.submitClaim, data: formData);
      } else {
        await ApiClient.instance.dio.post(ApiEndpoints.submitClaim,
            data: {'vin': vin, 'issue_description': issueDescription});
      }
      await loadClaims();
      return null;
    } on DioException catch (e) {
      return e.response?.data['error'] ?? 'Failed to submit claim';
    }
  }
}
