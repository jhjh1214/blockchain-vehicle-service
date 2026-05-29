import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../features/services/services_provider.dart';

class ShellScreen extends StatelessWidget {
  final Widget child;
  const ShellScreen({super.key, required this.child});

  static const _tabs = [
    (icon: Icons.directions_car_outlined, activeIcon: Icons.directions_car, label: 'Vehicles', path: '/home'),
    (icon: Icons.build_outlined, activeIcon: Icons.build, label: 'Pending', path: '/services/pending'),
    (icon: Icons.history, activeIcon: Icons.history, label: 'History', path: '/services/history'),
    (icon: Icons.shield_outlined, activeIcon: Icons.shield, label: 'Warranty', path: '/warranties'),
    (icon: Icons.person_outlined, activeIcon: Icons.person, label: 'Profile', path: '/profile'),
  ];

  int _currentIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    return _tabs.indexWhere((t) => location.startsWith(t.path));
  }

  @override
  Widget build(BuildContext context) {
    final index = _currentIndex(context);
    final pendingCount = context.watch<ServicesProvider>().pending.length;
    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: index < 0 ? 0 : index,
        onDestinationSelected: (i) => context.go(_tabs[i].path),
        destinations: [
          for (final t in _tabs)
            NavigationDestination(
              icon: t.path == '/services/pending' && pendingCount > 0
                  ? Badge(
                      label: Text('$pendingCount'),
                      child: Icon(t.icon),
                    )
                  : Icon(t.icon),
              selectedIcon: t.path == '/services/pending' && pendingCount > 0
                  ? Badge(
                      label: Text('$pendingCount'),
                      child: Icon(t.activeIcon),
                    )
                  : Icon(t.activeIcon),
              label: t.label,
            ),
        ],
      ),
    );
  }
}
