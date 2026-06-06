import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mockito/mockito.dart';
import 'package:provider/provider.dart';
import 'package:owner_mobile_app/features/vehicles/claim_vehicle_screen.dart';
import 'package:owner_mobile_app/features/vehicles/vehicles_provider.dart';
import 'package:owner_mobile_app/shared/theme/app_theme.dart';

// Null-safe Mockito: override claimVehicle via super.noSuchMethod so that
// when() interception works. ClaimVehicleScreen only reads claimVehicle().
class MockVehiclesProvider extends Mock implements VehiclesProvider {
  @override
  Future<ClaimResult> claimVehicle(String vin) => super.noSuchMethod(
        Invocation.method(#claimVehicle, [vin]),
        returnValue: Future.value(const ClaimResult()),
        returnValueForMissingStub: Future.value(const ClaimResult()),
      ) as Future<ClaimResult>;
}

Widget _buildTestApp(VehiclesProvider provider) =>
    ChangeNotifierProvider<VehiclesProvider>.value(
      value: provider,
      child: MaterialApp.router(
        theme: AppTheme.light,
        routerConfig: GoRouter(
          // Nest /vehicles/claim under / so context.pop() has a parent to return to.
          routes: [
            GoRoute(
              path: '/',
              builder: (_, __) => const Scaffold(body: Text('Home')),
              routes: [
                GoRoute(
                  path: 'vehicles/claim',
                  builder: (_, __) => const ClaimVehicleScreen(),
                ),
              ],
            ),
          ],
          initialLocation: '/vehicles/claim',
        ),
      ),
    );

const _testVin = '1HGBH41JXMN109186';

void main() {
  group('ClaimVehicleScreen', () {
    testWidgets('renders VIN field and claim button', (tester) async {
      await tester.pumpWidget(_buildTestApp(MockVehiclesProvider()));
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsOneWidget);
      // AppBar title + ElevatedButton both say 'Claim Vehicle'
      expect(find.text('Claim Vehicle'), findsWidgets);
      expect(find.byType(ElevatedButton), findsOneWidget);
    });

    testWidgets('shows error when VIN is empty', (tester) async {
      await tester.pumpWidget(_buildTestApp(MockVehiclesProvider()));
      await tester.pumpAndSettle();

      await tester.tap(find.byType(ElevatedButton));
      await tester.pumpAndSettle();

      expect(find.text('VIN required'), findsOneWidget);
    });

    testWidgets('shows error when VIN is not 17 characters', (tester) async {
      await tester.pumpWidget(_buildTestApp(MockVehiclesProvider()));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextFormField), 'SHORT');
      await tester.tap(find.byType(ElevatedButton));
      await tester.pumpAndSettle();

      expect(find.text('VIN must be 17 characters'), findsOneWidget);
    });

    testWidgets('shows success snackbar on valid VIN claim', (tester) async {
      final p = MockVehiclesProvider();
      when(p.claimVehicle(_testVin)).thenAnswer((_) async => const ClaimResult());

      await tester.pumpWidget(_buildTestApp(p));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextFormField), _testVin);
      await tester.tap(find.byType(ElevatedButton));
      await tester.pumpAndSettle();

      expect(find.text('Vehicle claimed successfully'), findsOneWidget);
    });

    testWidgets('shows error snackbar when claim fails', (tester) async {
      final p = MockVehiclesProvider();
      when(p.claimVehicle(_testVin))
          .thenAnswer((_) async => const ClaimResult(error: 'Vehicle already claimed'));

      await tester.pumpWidget(_buildTestApp(p));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextFormField), _testVin);
      await tester.tap(find.byType(ElevatedButton));
      await tester.pumpAndSettle();

      expect(find.text('Vehicle already claimed'), findsOneWidget);
    });
  });
}
