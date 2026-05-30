import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _storage = FlutterSecureStorage(
  aOptions: AndroidOptions(encryptedSharedPreferences: true),
);
const _accessKey  = 'access_token';
const _refreshKey = 'refresh_token';
const _rememberKey = 'remember_me';

/// In-memory fallback for session-only mode (remember me = false).
/// Cleared when the app process is killed.
String? _memAccess;
String? _memRefresh;

class TokenStorage {
  /// Save tokens.
  /// [rememberMe] = true  → persist to secure storage (survives app restart)
  /// [rememberMe] = false → keep in memory only (cleared on process kill)
  static Future<void> save(String access, String refresh,
      {bool rememberMe = true}) async {
    if (rememberMe) {
      await _storage.write(key: _accessKey,   value: access);
      await _storage.write(key: _refreshKey,  value: refresh);
      await _storage.write(key: _rememberKey, value: 'true');
      _memAccess = null;
      _memRefresh = null;
    } else {
      // Wipe any previously persisted tokens (e.g. from a prior "remember me" session)
      await _storage.delete(key: _accessKey);
      await _storage.delete(key: _refreshKey);
      await _storage.delete(key: _rememberKey);
      _memAccess  = access;
      _memRefresh = refresh;
    }
  }

  static Future<String?> getAccessToken() async {
    if (_memAccess != null) return _memAccess;
    return _storage.read(key: _accessKey);
  }

  static Future<String?> getRefreshToken() async {
    if (_memRefresh != null) return _memRefresh;
    return _storage.read(key: _refreshKey);
  }

  static Future<void> clear() async {
    _memAccess  = null;
    _memRefresh = null;
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
    await _storage.delete(key: _rememberKey);
  }

  /// Returns true only if a persisted token exists (remember me was set).
  /// In-memory-only sessions are not auto-resumed after restart.
  static Future<bool> hasToken() async {
    if (_memAccess != null) return true;
    final t = await _storage.read(key: _accessKey);
    return t != null;
  }
}
