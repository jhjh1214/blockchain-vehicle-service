import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../features/auth/auth_provider.dart';
import '../features/services/services_provider.dart';
import '../features/notifications/notifications_provider.dart';

class ShellScreen extends StatefulWidget {
  final Widget child;
  const ShellScreen({super.key, required this.child});

  @override
  State<ShellScreen> createState() => _ShellScreenState();
}

class _ShellScreenState extends State<ShellScreen> {
  static const _tabs = [
    (icon: Icons.directions_car_outlined, activeIcon: Icons.directions_car, label: 'Vehicles', path: '/home'),
    (icon: Icons.build_outlined, activeIcon: Icons.build, label: 'Pending', path: '/services/pending'),
    (icon: Icons.history, activeIcon: Icons.history, label: 'History', path: '/services/history'),
    (icon: Icons.shield_outlined, activeIcon: Icons.shield, label: 'Warranty', path: '/warranties'),
    (icon: Icons.notifications_outlined, activeIcon: Icons.notifications, label: 'Alerts', path: '/notifications'),
    (icon: Icons.person_outlined, activeIcon: Icons.person, label: 'Profile', path: '/profile'),
  ];

  bool _resending = false;
  bool _resendSent = false;

  int _currentIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    return _tabs.indexWhere((t) => location.startsWith(t.path));
  }

  Widget _buildTabIcon(String path, IconData icon, int pendingCount, int unreadNotifs) {
    if (path == '/services/pending' && pendingCount > 0) {
      return Badge(label: Text('$pendingCount'), child: Icon(icon));
    }
    if (path == '/notifications' && unreadNotifs > 0) {
      return Badge(label: Text('$unreadNotifs'), child: Icon(icon));
    }
    return Icon(icon);
  }

  Future<void> _handleResend(BuildContext context) async {
    if (_resending || _resendSent) return;
    setState(() => _resending = true);
    final ok = await context.read<AuthProvider>().resendVerification();
    if (!mounted) return;
    setState(() {
      _resending = false;
      _resendSent = ok;
    });
    if (!ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Failed to send verification email. Please try again.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final index = _currentIndex(context);
    final pendingCount = context.watch<ServicesProvider>().pending.length;
    final unreadNotifs = context.watch<NotificationsProvider>().unreadCount;
    final user = context.watch<AuthProvider>().user;
    final showBanner = user != null && !user.emailVerified;

    return Scaffold(
      body: Column(
        children: [
          if (showBanner)
            Builder(builder: (context) {
              final isDark = Theme.of(context).brightness == Brightness.dark;
              final bg = isDark ? const Color(0xFF2D2200) : const Color(0xFFFFFBEB);
              final fg = isDark ? const Color(0xFFFFD54F) : const Color(0xFF92400E);
              return Container(
                color: bg,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                child: SafeArea(
                  bottom: false,
                  child: Row(
                    children: [
                      Icon(Icons.mark_email_unread_outlined, size: 18, color: fg),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'Please verify your email address.',
                          style: TextStyle(
                            fontSize: 13,
                            color: fg,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                      TextButton(
                        onPressed: _resendSent ? null : () => _handleResend(context),
                        style: TextButton.styleFrom(
                          foregroundColor: fg,
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        child: Text(
                          _resending
                              ? 'Sending...'
                              : _resendSent
                                  ? 'Sent!'
                                  : 'Resend',
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            decoration: TextDecoration.underline,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }),
          Expanded(child: widget.child),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index < 0 ? 0 : index,
        onDestinationSelected: (i) => context.go(_tabs[i].path),
        destinations: [
          for (final t in _tabs)
            NavigationDestination(
              icon: _buildTabIcon(t.path, t.icon, pendingCount, unreadNotifs),
              selectedIcon: _buildTabIcon(t.path, t.activeIcon, pendingCount, unreadNotifs),
              label: t.label,
            ),
        ],
      ),
    );
  }
}
