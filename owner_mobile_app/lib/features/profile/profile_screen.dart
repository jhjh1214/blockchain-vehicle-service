import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../auth/auth_provider.dart';
import '../../core/models/user.dart';
import '../../shared/theme/theme_provider.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  User? _cachedUser;
  bool _editMode = false;
  final _nameCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _cityCtrl = TextEditingController();
  final _stateCtrl = TextEditingController();

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final user = context.read<AuthProvider>().user;
    if (user != null && !_editMode) {
      _nameCtrl.text = user.name;
      _phoneCtrl.text = user.phone ?? '';
      _cityCtrl.text = user.city ?? '';
      _stateCtrl.text = user.state ?? '';
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _phoneCtrl.dispose();
    _cityCtrl.dispose();
    _stateCtrl.dispose();
    super.dispose();
  }

  Future<void> _saveProfile() async {
    final auth = context.read<AuthProvider>();
    final ok = await auth.updateProfile(
      name: _nameCtrl.text.trim(),
      phone: _phoneCtrl.text.trim().isEmpty ? null : _phoneCtrl.text.trim(),
      city: _cityCtrl.text.trim().isEmpty ? null : _cityCtrl.text.trim(),
      state: _stateCtrl.text.trim().isEmpty ? null : _stateCtrl.text.trim(),
    );
    if (!mounted) return;
    if (ok) {
      setState(() => _editMode = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Profile updated'), backgroundColor: Colors.green),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(auth.error ?? 'Update failed'),
            backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _logout() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Sign Out'),
        content: const Text('Are you sure you want to sign out?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Sign Out'),
          ),
        ],
      ),
    );
    if (confirm == true && mounted) {
      await context.read<AuthProvider>().logout();
      // go_router's refreshListenable handles redirect to /login automatically
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    // Keep a cached copy so the profile stays visible during the logout
    // transition (one frame between notifyListeners and router redirect).
    if (auth.user != null) _cachedUser = auth.user;
    final user = _cachedUser;
    if (user == null) return const SizedBox.shrink();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile'),
        actions: [
          if (_editMode)
            TextButton(
              onPressed: auth.loading ? null : _saveProfile,
              child: auth.loading
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                          color: Colors.white, strokeWidth: 2))
                  : const Text('Save', style: TextStyle(color: Colors.white)),
            )
          else
            IconButton(
              icon: const Icon(Icons.edit),
              onPressed: () => setState(() => _editMode = true),
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Center(
            child: Column(
              children: [
                CircleAvatar(
                  radius: 40,
                  backgroundColor: Theme.of(context).colorScheme.primary,
                  child: Text(
                    user.name.isNotEmpty ? user.name[0].toUpperCase() : '?',
                    style: const TextStyle(fontSize: 32, color: Colors.white),
                  ),
                ),
                const SizedBox(height: 12),
                Text(user.email,
                    style: const TextStyle(color: Colors.grey, fontSize: 13)),
                const SizedBox(height: 4),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  decoration: BoxDecoration(
                    color: Theme.of(context)
                        .colorScheme
                        .primary
                        .withOpacity(0.1),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(user.role,
                      style: TextStyle(
                          color: Theme.of(context).colorScheme.primary,
                          fontWeight: FontWeight.w600,
                          fontSize: 12)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Personal Info',
                      style: TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 14)),
                  const Divider(height: 20),
                  _editMode
                      ? _EditableFields(
                          nameCtrl: _nameCtrl,
                          phoneCtrl: _phoneCtrl,
                          cityCtrl: _cityCtrl,
                          stateCtrl: _stateCtrl,
                        )
                      : _ReadOnlyFields(user: user),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.lock_outlined),
                  title: const Text('Change Password'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push('/profile/change-password'),
                ),
                const Divider(height: 1),
                Consumer<ThemeProvider>(
                  builder: (ctx, theme, _) => SwitchListTile(
                    secondary: Icon(
                      theme.isDark ? Icons.dark_mode : Icons.light_mode,
                    ),
                    title: const Text('Dark Mode'),
                    value: theme.isDark,
                    onChanged: (_) => theme.toggle(),
                  ),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.info_outlined),
                  title: const Text('Blockchain Address'),
                  subtitle: Text(
                    user.blockchainAddress.length > 18
                        ? '${user.blockchainAddress.substring(0, 10)}...${user.blockchainAddress.substring(user.blockchainAddress.length - 8)}'
                        : user.blockchainAddress.isEmpty
                            ? 'Not assigned'
                            : user.blockchainAddress,
                    style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          OutlinedButton.icon(
            onPressed: _logout,
            icon: const Icon(Icons.logout, color: Colors.red),
            label: const Text('Sign Out',
                style: TextStyle(color: Colors.red)),
            style: OutlinedButton.styleFrom(
                side: const BorderSide(color: Colors.red)),
          ),
        ],
      ),
    );
  }
}

class _ReadOnlyFields extends StatelessWidget {
  final dynamic user;
  const _ReadOnlyFields({required this.user});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _row('Name', user.name),
        _row('Phone', user.phone ?? '-'),
        _row('City', user.city ?? '-'),
        _row('State', user.state ?? '-'),
      ],
    );
  }

  Widget _row(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            SizedBox(
                width: 80,
                child: Text(label,
                    style: const TextStyle(
                        color: Colors.grey, fontSize: 13))),
            Expanded(
                child: Text(value, style: const TextStyle(fontSize: 13))),
          ],
        ),
      );
}

class _EditableFields extends StatelessWidget {
  final TextEditingController nameCtrl;
  final TextEditingController phoneCtrl;
  final TextEditingController cityCtrl;
  final TextEditingController stateCtrl;

  const _EditableFields({
    required this.nameCtrl,
    required this.phoneCtrl,
    required this.cityCtrl,
    required this.stateCtrl,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        TextField(
            controller: nameCtrl,
            decoration: const InputDecoration(labelText: 'Name')),
        const SizedBox(height: 12),
        TextField(
            controller: phoneCtrl,
            keyboardType: TextInputType.phone,
            decoration: const InputDecoration(labelText: 'Phone')),
        const SizedBox(height: 12),
        TextField(
            controller: cityCtrl,
            decoration: const InputDecoration(labelText: 'City')),
        const SizedBox(height: 12),
        TextField(
            controller: stateCtrl,
            decoration: const InputDecoration(labelText: 'State')),
      ],
    );
  }
}
