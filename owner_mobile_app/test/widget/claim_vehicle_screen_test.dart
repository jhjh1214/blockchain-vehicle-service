import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mockito/mockito.dart';
import 'package:provider/provider.dart';
import 'package:owner_mobile_app/features/vehicles/claim_vehicle_screen.dart';
import 'package:owner_mobile_app/features/vehicles/vehicles_provider.dart';
import 'package:owner_mobile_app/shared/theme/app_theme.dart';

class MockVehiclesProvider extends Mock implements VehiclesProvider {
  @override
  Future<String?> claimVehicle(String vin) async => null;
  @override
  Future<void> loadVehicles() async {}
}

Widget _buildTestApp(VehiclesProvider provider) =>
    ChangeNotifierProvider<VehiclesProvider>.value(
      value: provider,
      child: MaterialApp.router(
        theme: AppTheme.light,
        routerConfig: GoRouter(
          routes: [
            GoRoute(path: '/vehicles/claim', builder: (_, __) => const ClaimVehicleScreen()),
            GoRoute(path: '/home', builder: (_, __) => const Scaffold(body: Text('Home'))),
          ],
          initialLocation: '/vehicles/claim',
        ),
      ),
    );

void main() {
  group('ClaimVehicleScreen', () {
    testWidgets('renders VIN field and claim button', (tester) async {
      await tester.pumpWidget(_buildTestApp(MockVehiclesProvider()));
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsOneWidget);
      expect(find.text('Claim Vehicle'), findsOneWidget);
    });

    testWidgets('shows error when VIN is empty', (tester) async {
      await tester.pumpWidget(_buildTestApp(MockVehiclesProvider()));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Claim Vehicle'));
      await tester.pumpAndSettle();

      expect(find.text('VIN required'), findsOneWidget);
    });

    testWidgets('shows error when VIN is not 17 characters', (tester) async {
      await tester.pumpWidget(_buildTestApp(MockVehiclesProvider()));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextFormField), 'SHORT');
      await tester.tap(find.text('Claim Vehicle'));
      await tester.pumpAndSettle();

      expect(find.text('VIN must be 17 characters'), findsOneWidget);
    });

    testWidgets('shows success snackbar on valid VIN claim', (tester) async {
      final p = MockVehiclesProvider();
      when(p.claimVehicle(any)).thenAnswer((_) async => null);
      when(p.loadVehicles()).thenAnswer((_) async {});

      await tester.pumpWidget(_buildTestApp(p));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextFormField), '1HGBH41JXMN109186');
      await tester.tap(find.text('Claim Vehicle'));
      await tester.pumpAndSettle();

      expect(find.text('Vehicle claimed successfully'), findsOneWidget);
    });

    testWidgets('shows error snackbar when claim fails', (tester) async {
      final p = MockVehiclesProvider();
      when(p.claimVehicle(any))
          .thenAnswer((_) async => 'Vehicle already claimed');

      await tester.pumpWidget(_buildTestApp(p));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextFormField), '1HGBH41JXMN109186');
      await tester.tap(find.text('Claim Vehicle'));
      await tester.pumpAndSettle();

      expect(find.text('Vehicle already claimed'), findsOneWidget);
    });
  });
}
