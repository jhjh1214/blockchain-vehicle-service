import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:owner_mobile_app/shared/theme/app_theme.dart';
import 'package:owner_mobile_app/shared/widgets/status_badge.dart';

Widget _wrap(Widget child) =>
    MaterialApp(theme: AppTheme.light, home: Scaffold(body: child));

void main() {
  group('StatusBadge', () {
    testWidgets('renders Pending label for pending status', (tester) async {
      await tester.pumpWidget(_wrap(const StatusBadge(status: 'pending')));
      expect(find.text('Pending'), findsOneWidget);
    });

    testWidgets('renders Verified label for verified status', (tester) async {
      await tester.pumpWidget(_wrap(const StatusBadge(status: 'verified')));
      expect(find.text('Verified'), findsOneWidget);
    });

    testWidgets('renders Disputed label for disputed status', (tester) async {
      await tester.pumpWidget(_wrap(const StatusBadge(status: 'disputed')));
      expect(find.text('Disputed'), findsOneWidget);
    });

    testWidgets('renders Approved label for approved status', (tester) async {
      await tester.pumpWidget(_wrap(const StatusBadge(status: 'approved')));
      expect(find.text('Approved'), findsOneWidget);
    });

    testWidgets('renders Denied label for denied status', (tester) async {
      await tester.pumpWidget(_wrap(const StatusBadge(status: 'denied')));
      expect(find.text('Denied'), findsOneWidget);
    });

    testWidgets('renders Active label for active status', (tester) async {
      await tester.pumpWidget(_wrap(const StatusBadge(status: 'active')));
      expect(find.text('Active'), findsOneWidget);
    });

    testWidgets('renders Expired label for expired status', (tester) async {
      await tester.pumpWidget(_wrap(const StatusBadge(status: 'expired')));
      expect(find.text('Expired'), findsOneWidget);
    });

    testWidgets('renders raw status for unknown status', (tester) async {
      await tester.pumpWidget(_wrap(const StatusBadge(status: 'unknown_xyz')));
      expect(find.text('unknown_xyz'), findsOneWidget);
    });

    testWidgets('is case-insensitive for known statuses', (tester) async {
      await tester.pumpWidget(_wrap(const StatusBadge(status: 'PENDING')));
      expect(find.text('Pending'), findsOneWidget);
    });

    testWidgets('applies correct color for pending', (tester) async {
      await tester.pumpWidget(_wrap(const StatusBadge(status: 'pending')));
      await tester.pumpAndSettle();
      final text = tester.widget<Text>(find.text('Pending'));
      expect(text.style?.color, AppColors.pending);
    });

    testWidgets('applies correct color for verified', (tester) async {
      await tester.pumpWidget(_wrap(const StatusBadge(status: 'verified')));
      await tester.pumpAndSettle();
      final text = tester.widget<Text>(find.text('Verified'));
      expect(text.style?.color, AppColors.verified);
    });
  });
}
