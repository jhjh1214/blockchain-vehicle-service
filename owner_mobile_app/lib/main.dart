import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'features/auth/auth_provider.dart';
import 'features/vehicles/vehicles_provider.dart';
import 'features/services/services_provider.dart';
import 'features/warranties/warranties_provider.dart';
import 'router/app_router.dart';
import 'shared/theme/app_theme.dart';
import 'shared/theme/theme_provider.dart';

void main() {
  runApp(const OwnerApp());
}

class OwnerApp extends StatelessWidget {
  const OwnerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => VehiclesProvider()),
        ChangeNotifierProvider(create: (_) => ServicesProvider()),
        ChangeNotifierProvider(create: (_) => WarrantiesProvider()),
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
      ],
      child: _AppWithRouter(),
    );
  }
}

class _AppWithRouter extends StatefulWidget {
  @override
  State<_AppWithRouter> createState() => _AppWithRouterState();
}

class _AppWithRouterState extends State<_AppWithRouter> {
  late final _router;
  late final AuthProvider _auth;

  @override
  void initState() {
    super.initState();
    _auth = context.read<AuthProvider>();
    _router = createRouter(_auth);
    _auth.tryAutoLogin();
  }

  @override
  Widget build(BuildContext context) {
    final themeProvider = context.watch<ThemeProvider>();
    return MaterialApp.router(
      title: 'Vehicle Owner',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: themeProvider.themeMode,
      routerConfig: _router,
      debugShowCheckedModeBanner: false,
    );
  }
}
