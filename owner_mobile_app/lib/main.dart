import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:firebase_core/firebase_core.dart';
import 'features/auth/auth_provider.dart';
import 'features/vehicles/vehicles_provider.dart';
import 'features/vehicles/recalls_provider.dart';
import 'features/services/services_provider.dart';
import 'features/warranties/warranties_provider.dart';
import 'features/notifications/notifications_provider.dart';
import 'router/app_router.dart';
import 'shared/theme/app_theme.dart';
import 'shared/theme/theme_provider.dart';
import 'core/services/push_notification_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await Firebase.initializeApp();
  } catch (_) {
    // Firebase not configured — push notifications unavailable
  }
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
        ChangeNotifierProvider(create: (_) => RecallsProvider()),
        ChangeNotifierProvider(create: (_) => ServicesProvider()),
        ChangeNotifierProvider(create: (_) => WarrantiesProvider()),
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
        ChangeNotifierProvider(create: (_) => NotificationsProvider()),
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
    final notifProvider = context.read<NotificationsProvider>();
    notifProvider.load();
    PushNotificationService.instance.attachStore(notifProvider);
    PushNotificationService.instance.attachServices(context.read<ServicesProvider>());
    PushNotificationService.instance.attachRouter(_router);
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
