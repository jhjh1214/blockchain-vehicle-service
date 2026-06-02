import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mockito/mockito.dart';
import 'package:provider/provider.dart';
import 'package:owner_mobile_app/core/models/service_record.dart';
import 'package:owner_mobile_app/core/models/vehicle.dart';
import 'package:owner_mobile_app/features/services/services_provider.dart';
import 'package:owner_mobile_app/features/vehicles/recalls_provider.dart';
import 'package:owner_mobile_app/features/vehicles/vehicles_provider.dart';
import 'package:owner_mobile_app/features/vehicles/vehicles_screen.dart';
import 'package:owner_mobile_app/shared/theme/app_theme.dart';

// Null-safe Mockito: override non-nullable getters/methods via super.noSuchMethod
// so that when() interception works and bare mock instantiation has safe defaults.
class MockVehiclesProvider extends Mock implements VehiclesProvider {
  @override
  List<Vehicle> get vehicles => super.noSuchMethod(
        Invocation.getter(#vehicles),
        returnValue: <Vehicle>[],
        returnValueForMissingStub: <Vehicle>[],
      ) as List<Vehicle>;

  @override
  bool get loading => super.noSuchMethod(
        Invocation.getter(#loading),
        returnValue: false,
        returnValueForMissingStub: false,
      ) as bool;

  @override
  String? get error => super.noSuchMethod(
        Invocation.getter(#error),
        returnValue: null,
        returnValueForMissingStub: null,
      ) as String?;

  @override
  Future<void> loadVehicles() => super.noSuchMethod(
        Invocation.method(#loadVehicles, []),
        returnValue: Future<void>.value(),
        returnValueForMissingStub: Future<void>.value(),
      ) as Future<void>;
}

class MockRecallsProvider extends Mock implements RecallsProvider {
  @override
  List<dynamic> get recalls => super.noSuchMethod(
        Invocation.getter(#recalls),
        returnValue: <dynamic>[],
        returnValueForMissingStub: <dynamic>[],
      ) as List<dynamic>;

  @override
  bool get loading => super.noSuchMethod(
        Invocation.getter(#loading),
        returnValue: false,
        returnValueForMissingStub: false,
      ) as bool;

  @override
  int get unservicedCount => super.noSuchMethod(
        Invocation.getter(#unservicedCount),
        returnValue: 0,
        returnValueForMissingStub: 0,
      ) as int;

  @override
  Future<void> load() => super.noSuchMethod(
        Invocation.method(#load, []),
        returnValue: Future<void>.value(),
        returnValueForMissingStub: Future<void>.value(),
      ) as Future<void>;
}

class MockServicesProvider extends Mock implements ServicesProvider {
  @override
  List<ServiceRecord> get pending => super.noSuchMethod(
        Invocation.getter(#pending),
        returnValue: <ServiceRecord>[],
        returnValueForMissingStub: <ServiceRecord>[],
      ) as List<ServiceRecord>;

  @override
  bool get loading => super.noSuchMethod(
        Invocation.getter(#loading),
        returnValue: false,
        returnValueForMissingStub: false,
      ) as bool;

  @override
  Future<void> loadPending() => super.noSuchMethod(
        Invocation.method(#loadPending, []),
        returnValue: Future<void>.value(),
        returnValueForMissingStub: Future<void>.value(),
      ) as Future<void>;
}

Widget _buildTestApp(VehiclesProvider vehiclesProvider,
    {ServicesProvider? servicesProvider,
    RecallsProvider? recallsProvider}) =>
    MultiProvider(
      providers: [
        ChangeNotifierProvider<VehiclesProvider>.value(value: vehiclesProvider),
        ChangeNotifierProvider<ServicesProvider>.value(
            value: servicesProvider ?? MockServicesProvider()),
        ChangeNotifierProvider<RecallsProvider>.value(
            value: recallsProvider ?? MockRecallsProvider()),
      ],
      child: MaterialApp.router(
        theme: AppTheme.light,
        routerConfig: GoRouter(
          routes: [
            GoRoute(path: '/home', builder: (_, __) => const VehiclesScreen()),
            GoRoute(path: '/vehicles/claim', builder: (_, __) => const Scaffold(body: Text('Claim'))),
            GoRoute(path: '/vehicles/:vin', builder: (_, state) => Scaffold(body: Text('Detail ${state.pathParameters['vin']}'))),
          ],
          initialLocation: '/home',
        ),
      ),
    );

Vehicle _makeVehicle({bool warrantyValid = true}) => Vehicle.fromJson({
      'vin': '1HGBH41JXMN109186',
      'make': 'Honda',
      'model': 'Civic',
      'year': 2022,
      'warranty_valid': warrantyValid,
    });

void main() {
  group('VehiclesScreen', () {
    testWidgets('shows empty state when no vehicles', (tester) async {
      await tester.pumpWidget(_buildTestApp(MockVehiclesProvider()));
      await tester.pumpAndSettle();

      expect(find.text('No vehicles yet'), findsOneWidget);
      expect(find.text('Claim your vehicle using its VIN number'), findsOneWidget);
    });

    testWidgets('shows loading indicator while loading', (tester) async {
      final p = MockVehiclesProvider();
      when(p.loading).thenReturn(true);

      await tester.pumpWidget(_buildTestApp(p));
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows error view on error', (tester) async {
      final p = MockVehiclesProvider();
      when(p.error).thenReturn('Failed to load vehicles');

      await tester.pumpWidget(_buildTestApp(p));
      await tester.pumpAndSettle();

      expect(find.text('Failed to load vehicles'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('shows vehicle list when vehicles present', (tester) async {
      final p = MockVehiclesProvider();
      when(p.vehicles).thenReturn([_makeVehicle()]);

      await tester.pumpWidget(_buildTestApp(p));
      await tester.pumpAndSettle();

      expect(find.text('2022 Honda Civic'), findsOneWidget);
      expect(find.text('VIN: 1HGBH41JXMN109186'), findsOneWidget);
    });

    testWidgets('shows warranty icon for active warranty', (tester) async {
      final p = MockVehiclesProvider();
      when(p.vehicles).thenReturn([_makeVehicle(warrantyValid: true)]);

      await tester.pumpWidget(_buildTestApp(p));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.verified), findsOneWidget);
      expect(find.text('Warranty'), findsOneWidget);
    });

    testWidgets('shows no warranty icon for expired warranty', (tester) async {
      final p = MockVehiclesProvider();
      when(p.vehicles).thenReturn([_makeVehicle(warrantyValid: false)]);

      await tester.pumpWidget(_buildTestApp(p));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.shield_outlined), findsOneWidget);
      expect(find.text('No warranty'), findsOneWidget);
    });

    testWidgets('Claim Vehicle FAB is present', (tester) async {
      await tester.pumpWidget(_buildTestApp(MockVehiclesProvider()));
      await tester.pumpAndSettle();

      // FAB label appears in empty state and in the FloatingActionButton
      expect(find.text('Claim Vehicle'), findsWidgets);
    });
  });
}
