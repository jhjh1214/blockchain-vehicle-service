import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import '../../core/api/api_client.dart';
import '../../core/api/api_endpoints.dart';
import '../../core/models/user.dart';
import '../../core/storage/token_storage.dart';
import '../../core/services/push_notification_service.dart';

class AuthProvider extends ChangeNotifier {
  User? _user;
  bool _loading = false;
  String? _error;

  AuthProvider() {
    ApiClient.onSessionExpired = _handleSessionExpired;
  }

  void _handleSessionExpired() {
    _user = null;
    notifyListeners();
  }

  User? get user => _user;
  bool get loading => _loading;
  String? get error => _error;
  bool get isAuthenticated => _user != null;

  Future<void> tryAutoLogin() async {
    final hasToken = await TokenStorage.hasToken();
    if (!hasToken) return;
    // Biometric login is the gate the user opted into — resuming the session
    // silently here would skip it entirely. Leave _user unset so the router
    // stays on /login, where LoginScreen prompts for fingerprint instead.
    if (await TokenStorage.isBiometricEnabled()) return;
    try {
      final res = await ApiClient.instance.dio.get(ApiEndpoints.me);
      final user = User.fromJson(res.data);
      if (user.role != 'OWNER') {
        await TokenStorage.clear();
        return;
      }
      _user = user;
      notifyListeners();
      PushNotificationService.instance.init();
    } catch (_) {
      await TokenStorage.clear();
    }
  }

  Future<bool> login(String email, String password,
      {bool rememberMe = true}) async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      final res = await ApiClient.instance.dio.post(ApiEndpoints.login,
          data: {'email': email, 'password': password});
      await TokenStorage.save(res.data['access_token'], res.data['refresh_token'],
          rememberMe: rememberMe);
      if (rememberMe) {
        await TokenStorage.saveCredentials(email, password);
      }
      _user = User.fromJson(res.data['user']);
      PushNotificationService.instance.init();
      return true;
    } on DioException catch (e) {
      _error = e.response?.data['error'] ?? 'Login failed';
      return false;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<bool> register(String email, String password, String name,
      {String? phone, bool consentGiven = false}) async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      final res = await ApiClient.instance.dio.post(ApiEndpoints.register,
          data: {
            'email': email,
            'password': password,
            'name': name,
            'role': 'OWNER',
            'consent_given': consentGiven,
            if (phone != null) 'phone': phone,
          });
      await TokenStorage.save(res.data['access_token'], res.data['refresh_token']);
      _user = User.fromJson(res.data['user']);
      PushNotificationService.instance.init();
      return true;
    } on DioException catch (e) {
      _error = e.response?.data['error'] ?? 'Registration failed';
      return false;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    try {
      final refresh = await TokenStorage.getRefreshToken();
      try {
        await ApiClient.instance.dio
            .post(ApiEndpoints.logout, data: {'refresh_token': refresh});
      } catch (_) {}
      await TokenStorage.clear();
      await TokenStorage.clearCredentials();
    } catch (_) {}
    _user = null;
    notifyListeners();
  }

  Future<bool> updateProfile(
      {String? name, String? phone, String? city, String? state}) async {
    _loading = true;
    notifyListeners();
    try {
      final res = await ApiClient.instance.dio.put(ApiEndpoints.profile,
          data: {
            if (name != null) 'name': name,
            if (phone != null) 'phone': phone,
            if (city != null) 'city': city,
            if (state != null) 'state': state,
          });
      _user = User.fromJson(res.data['user']);
      return true;
    } on DioException catch (e) {
      _error = e.response?.data['error'] ?? 'Update failed';
      return false;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<bool> changePassword(String current, String newPassword) async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      await ApiClient.instance.dio.post(ApiEndpoints.changePassword,
          data: {'current_password': current, 'new_password': newPassword});
      await logout();
      return true;
    } on DioException catch (e) {
      _error = e.response?.data['error'] ?? 'Password change failed';
      return false;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<bool> resendVerification() async {
    try {
      await ApiClient.instance.dio.post(ApiEndpoints.resendVerification);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<String?> deleteAccount(String password) async {
    try {
      await ApiClient.instance.dio.delete(
        ApiEndpoints.deleteAccount,
        data: {'password': password},
      );
      await TokenStorage.clear();
      await TokenStorage.clearCredentials();
      _user = null;
      notifyListeners();
      return null;
    } on DioException catch (e) {
      return (e.response?.data as Map?)?['error'] as String? ?? 'Failed to delete account';
    } catch (_) {
      return 'Failed to delete account';
    }
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  // ignore: invalid_use_of_visible_for_testing_member
  void setUserForTest(Map<String, dynamic> json) {
    _user = User.fromJson(json);
    notifyListeners();
  }
}
