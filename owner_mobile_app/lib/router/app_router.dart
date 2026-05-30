import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../features/auth/auth_provider.dart';
import '../features/auth/login_screen.dart';
import '../features/auth/register_screen.dart';
import '../features/vehicles/vehicles_screen.dart';
import '../features/vehicles/vehicle_detail_screen.dart';
import '../features/vehicles/claim_vehicle_screen.dart';
import '../features/vehicles/transfer_vehicle_screen.dart';
import '../features/services/pending_services_screen.dart';
import '../features/services/service_history_screen.dart';
import '../features/warranties/warranty_claims_screen.dart';
import '../features/warranties/submit_claim_screen.dart';
import '../features/profile/profile_screen.dart';
import '../features/profile/change_password_screen.dart';
import '../features/services/dispute_chat_screen.dart';
import '../features/auth/forgot_password_screen.dart';
import '../features/auth/privacy_policy_screen.dart';
import 'shell_screen.dart';

GoRouter createRouter(AuthProvider auth) => GoRouter(
      refreshListenable: auth,
      redirect: (context, state) {
        final loggedIn = auth.isAuthenticated;
        final publicRoutes = {'/login', '/register', '/forgot-password', '/privacy-policy'};
        final onAuth = state.matchedLocation == '/login' ||
            state.matchedLocation == '/register';
        if (!loggedIn && !publicRoutes.contains(state.matchedLocation)) return '/login';
        if (loggedIn && onAuth) return '/home';
        return null;
      },
      routes: [
        GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
        GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
        GoRoute(path: '/forgot-password', builder: (_, __) => const ForgotPasswordScreen()),
        GoRoute(path: '/privacy-policy', builder: (_, __) => const PrivacyPolicyScreen()),
        ShellRoute(
          builder: (context, state, child) => ShellScreen(child: child),
          routes: [
            GoRoute(
              path: '/home',
              builder: (_, __) => const VehiclesScreen(),
            ),
            GoRoute(
              path: '/services/pending',
              builder: (_, __) => const PendingServicesScreen(),
            ),
            GoRoute(
              path: '/services/history',
              builder: (_, __) => const ServiceHistoryScreen(),
            ),
            GoRoute(
              path: '/warranties',
              builder: (_, __) => const WarrantyClaimsScreen(),
            ),
            GoRoute(
              path: '/profile',
              builder: (_, __) => const ProfileScreen(),
            ),
          ],
        ),
        GoRoute(
          path: '/vehicles/claim',
          builder: (_, __) => const ClaimVehicleScreen(),
        ),
        GoRoute(
          path: '/vehicles/transfer/:vin',
          builder: (_, state) =>
              TransferVehicleScreen(vin: state.pathParameters['vin']!),
        ),
        GoRoute(
          path: '/vehicles/:vin',
          builder: (_, state) =>
              VehicleDetailScreen(vin: state.pathParameters['vin']!),
        ),
        GoRoute(
          path: '/warranties/submit/:vin',
          builder: (_, state) =>
              SubmitClaimScreen(vin: state.pathParameters['vin']!),
        ),
        GoRoute(
          path: '/profile/change-password',
          builder: (_, __) => const ChangePasswordScreen(),
        ),
        GoRoute(
          path: '/services/dispute-chat/:vin/:recordIndex',
          builder: (_, state) => DisputeChatScreen(
            vin: state.pathParameters['vin']!,
            recordIndex: int.parse(state.pathParameters['recordIndex']!),
            serviceType: state.uri.queryParameters['type'] ?? 'Service',
          ),
        ),
      ],
      initialLocation: '/login',
    );
