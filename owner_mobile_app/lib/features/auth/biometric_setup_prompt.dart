import 'package:flutter/material.dart';
import 'package:local_auth/local_auth.dart';
import '../../core/storage/token_storage.dart';

/// After a remembered login or a fresh registration, ask once if the user
/// wants biometric login. Shared between LoginScreen and RegisterScreen so
/// both paths offer it consistently.
///
/// [force] skips the "already decided" check — registration always
/// represents a brand new account, so it shouldn't silently inherit a
/// decision (and stale enabled flag with no matching saved credential) left
/// over from a previously logged-in account on the same device.
Future<void> offerBiometricSetup(BuildContext context, {bool force = false}) async {
  try {
    if (!force) {
      final alreadyDecided = await TokenStorage.hasBiometricDecision();
      if (alreadyDecided) return;
    }
    if (!context.mounted) return;
    final localAuth = LocalAuthentication();
    final canCheck = await localAuth.canCheckBiometrics;
    final isSupported = await localAuth.isDeviceSupported();
    if (!canCheck || !isSupported || !context.mounted) return;

    final enable = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: const Text('Enable Biometric Login?'),
        content: const Text(
            'Sign in faster next time using your fingerprint or face ID.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Not now'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Enable'),
          ),
        ],
      ),
    );

    await TokenStorage.setBiometricEnabled(enable == true);
  } catch (_) {}
}
