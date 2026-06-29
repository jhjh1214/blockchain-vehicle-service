import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:local_auth/local_auth.dart';
import 'package:provider/provider.dart';
import '../../core/storage/token_storage.dart';
import 'auth_provider.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _obscurePassword = true;
  bool _rememberMe = true;
  bool _biometricAvailable = false;
  bool _biometricInProgress = false;
  String? _savedPassword;
  final _localAuth = LocalAuthentication();

  @override
  void initState() {
    super.initState();
    _initCredentials();
  }

  /// Pre-fill saved credentials and show biometric button if user opted in.
  /// If biometric login is enabled, prompt for fingerprint immediately —
  /// it's the gate guarding the remembered session, not an optional shortcut.
  Future<void> _initCredentials() async {
    try {
      final creds = await TokenStorage.loadCredentials();
      if (creds == null || !mounted) return;
      // Pre-fill email only — the password stays hidden, used only internally
      // to complete a successful biometric unlock.
      setState(() {
        _emailCtrl.text = creds.email;
        _savedPassword = creds.password;
        _rememberMe = true;
      });

      final enabled = await TokenStorage.isBiometricEnabled();
      if (!enabled || !mounted) return;
      final canCheck = await _localAuth.canCheckBiometrics;
      final isSupported = await _localAuth.isDeviceSupported();
      if (!mounted || !canCheck || !isSupported) return;
      setState(() => _biometricAvailable = true);
      _biometricLogin();
    } catch (_) {}
  }

  Future<void> _biometricLogin() async {
    if (_biometricInProgress || _savedPassword == null) return;
    setState(() => _biometricInProgress = true);
    try {
      final authenticated = await _localAuth.authenticate(
        localizedReason: 'Authenticate to sign in to VehicleChain',
        options: const AuthenticationOptions(biometricOnly: false),
      );
      if (!authenticated || !mounted) return;
      final auth = context.read<AuthProvider>();
      final ok = await auth.login(
        _emailCtrl.text.trim(),
        _savedPassword!,
        rememberMe: true,
      );
      if (!mounted) return;
      if (ok) {
        context.go('/home');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text(auth.error ?? 'Biometric sign-in failed'),
              backgroundColor: Colors.red),
        );
      }
    } on PlatformException catch (e) {
      // A simple user cancellation comes back as `authenticated == false`,
      // not an exception — anything thrown here is a real failure (no
      // hardware, nothing enrolled, lockout, etc.) and should be visible
      // rather than silently doing nothing.
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text(e.message ?? 'Biometric authentication unavailable'),
              backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _biometricInProgress = false);
    }
  }

  /// After first remembered login, ask once if the user wants biometric login.
  Future<void> _offerBiometricSetup() async {
    try {
      final alreadyDecided = await TokenStorage.hasBiometricDecision();
      if (alreadyDecided || !mounted) return;
      final canCheck = await _localAuth.canCheckBiometrics;
      final isSupported = await _localAuth.isDeviceSupported();
      if (!canCheck || !isSupported || !mounted) return;

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

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    final auth = context.read<AuthProvider>();
    final ok = await auth.login(
      _emailCtrl.text.trim(),
      _passwordCtrl.text,
      rememberMe: _rememberMe,
    );
    if (!mounted) return;
    if (ok) {
      if (_rememberMe) {
        await _offerBiometricSetup();
      }
      if (mounted) context.go('/home');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(auth.error ?? 'Login failed'),
            backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final colorScheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 48),
                Icon(Icons.directions_car, size: 72, color: colorScheme.primary),
                const SizedBox(height: 16),
                Text('Vehicle Service',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        fontWeight: FontWeight.bold)),
                Text('Owner Portal',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: Colors.grey[600])),
                const SizedBox(height: 48),
                TextFormField(
                  controller: _emailCtrl,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(
                    labelText: 'Email',
                    prefixIcon: Icon(Icons.email_outlined),
                  ),
                  validator: (v) =>
                      v == null || !v.contains('@') ? 'Enter a valid email' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _passwordCtrl,
                  obscureText: _obscurePassword,
                  decoration: InputDecoration(
                    labelText: 'Password',
                    prefixIcon: const Icon(Icons.lock_outlined),
                    suffixIcon: IconButton(
                      icon: Icon(_obscurePassword
                          ? Icons.visibility_off
                          : Icons.visibility),
                      tooltip: _obscurePassword ? 'Show password' : 'Hide password',
                      onPressed: () =>
                          setState(() => _obscurePassword = !_obscurePassword),
                    ),
                  ),
                  validator: (v) =>
                      v == null || v.isEmpty ? 'Password required' : null,
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Semantics(
                      label: 'Remember me',
                      child: Checkbox(
                        value: _rememberMe,
                        onChanged: (v) => setState(() => _rememberMe = v ?? true),
                      ),
                    ),
                    GestureDetector(
                      onTap: () => setState(() => _rememberMe = !_rememberMe),
                      child: const Text('Remember me'),
                    ),
                    const Spacer(),
                    TextButton(
                      onPressed: () => context.push('/forgot-password'),
                      child: const Text('Forgot password?'),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: auth.loading ? null : _submit,
                  child: auth.loading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                              color: Colors.white, strokeWidth: 2))
                      : const Text('Sign In'),
                ),
                if (_biometricAvailable) ...[
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: (auth.loading || _biometricInProgress)
                        ? null
                        : _biometricLogin,
                    icon: _biometricInProgress
                        ? const SizedBox(
                            height: 18,
                            width: 18,
                            child: CircularProgressIndicator(strokeWidth: 2))
                        : const Icon(Icons.fingerprint),
                    label: Text(_biometricInProgress
                        ? 'Waiting for fingerprint…'
                        : 'Sign in with Biometrics'),
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size.fromHeight(48),
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text("Don't have an account? "),
                    TextButton(
                      onPressed: () => context.go('/register'),
                      child: const Text('Register'),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                Center(
                  child: Text.rich(
                    TextSpan(
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[500]),
                      children: [
                        const TextSpan(text: 'By signing in you agree to our '),
                        TextSpan(
                          text: 'Privacy Policy',
                          style: TextStyle(
                              color: colorScheme.primary,
                              decoration: TextDecoration.underline),
                          recognizer: TapGestureRecognizer()
                            ..onTap = () => context.push('/privacy-policy'),
                        ),
                        const TextSpan(text: ' and '),
                        TextSpan(
                          text: 'Terms of Service',
                          style: TextStyle(
                              color: colorScheme.primary,
                              decoration: TextDecoration.underline),
                          recognizer: TapGestureRecognizer()
                            ..onTap = () => context.push('/privacy-policy'),
                        ),
                        const TextSpan(text: '.'),
                      ],
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
