# Owner Mobile App — Blockchain Vehicle Service

Flutter mobile application for **vehicle owners**. Provides access to owned vehicles, service history, warranty status, and claim submission. Connects to the Flask backend via REST API.

---

## Features

| Feature | Description |
|---|---|
| Authentication | Login, register, auto-login on app restart, logout |
| My Vehicles | List owned vehicles with warranty status badge |
| Claim Vehicle | Claim ownership of a pre-registered vehicle using its VIN |
| Vehicle Detail | Warranty expiry, service count, transfer ownership |
| Pending Services | Review unverified service records, verify or dispute each one |
| Service History | Browse finalized service records with full metadata |
| Warranty Claims | View all claims, submit new claims with issue description |
| Profile | Update name, phone, city, state; change password |

---

## Tech Stack

| Technology | Version |
|---|---|
| Flutter | 3.44+ |
| Dart | 3.3+ |
| State management | Provider (ChangeNotifier) |
| Navigation | GoRouter 14.x |
| HTTP client | Dio 5.x |
| Secure storage | flutter_secure_storage 9.x |
| Localisation | intl 0.19 |

---

## Project Structure

```
owner_mobile_app/
└── lib/
    ├── main.dart                        # App entry — MultiProvider setup
    │
    ├── core/
    │   ├── api/
    │   │   ├── api_client.dart          # Dio singleton (base URL, auth header)
    │   │   └── api_endpoints.dart       # All API path constants
    │   ├── models/
    │   │   ├── user.dart                # User.fromJson
    │   │   ├── vehicle.dart             # Vehicle.fromJson, displayName, warrantyValid
    │   │   ├── service_record.dart      # ServiceRecord.fromJson, status helpers
    │   │   └── warranty_claim.dart      # WarrantyClaim.fromJson, status helpers
    │   └── storage/
    │       └── token_storage.dart       # flutter_secure_storage wrapper (save/get/clear)
    │
    ├── features/
    │   ├── auth/
    │   │   ├── auth_provider.dart       # login(), register(), logout(), tryAutoLogin()
    │   │   ├── login_screen.dart
    │   │   └── register_screen.dart
    │   │
    │   ├── vehicles/
    │   │   ├── vehicles_provider.dart   # loadVehicles(), claimVehicle(), transferVehicle(), checkWarranty()
    │   │   ├── vehicles_screen.dart     # Vehicle list with warranty badges
    │   │   ├── vehicle_detail_screen.dart
    │   │   ├── claim_vehicle_screen.dart
    │   │   └── transfer_vehicle_screen.dart
    │   │
    │   ├── services/
    │   │   ├── services_provider.dart   # loadPendingServices(), loadServiceHistory(), verifyService(), disputeService()
    │   │   ├── pending_services_screen.dart
    │   │   └── service_history_screen.dart
    │   │
    │   ├── warranties/
    │   │   ├── warranties_provider.dart # loadClaims(), submitClaim()
    │   │   ├── warranty_claims_screen.dart
    │   │   └── submit_claim_screen.dart
    │   │
    │   └── profile/
    │       ├── profile_screen.dart
    │       └── change_password_screen.dart
    │
    ├── shared/
    │   ├── widgets/
    │   │   ├── status_badge.dart        # Coloured status chip (pending/verified/disputed)
    │   │   ├── empty_state.dart         # Full-page empty state with icon and CTA
    │   │   └── error_view.dart          # Error display with retry button
    │   └── theme/
    │       └── app_theme.dart           # Material 3 light theme
    │
    └── router/
        ├── app_router.dart              # GoRouter — all named routes
        └── shell_screen.dart            # Bottom navigation bar shell
```

---

## Prerequisites

- Flutter 3.44+ ([install guide](https://docs.flutter.dev/get-started/install))
- Android SDK (for emulator or physical device)
- The Flask backend running at `localhost:5000` (see root README)

Verify Flutter is ready:

```bash
flutter doctor
```

---

## Setup

```bash
cd owner_mobile_app
flutter pub get
```

---

## Run

### Android Emulator

Start an AVD from Android Studio (or `avdmanager`), then:

```bash
flutter run
```

The app connects to `http://10.0.2.2:5000/api` — the Android emulator's loopback address for the host machine.

### Physical Android Device

Enable USB debugging on the device, connect via USB, then update the base URL:

```dart
// lib/core/api/api_client.dart
const String _baseUrl = 'http://<host-LAN-ip>:5000/api';
```

```bash
flutter run
```

### iOS Simulator

Update `_baseUrl` to `http://localhost:5000/api` (iOS simulator uses the host loopback directly), then:

```bash
flutter run -d "iPhone 15"
```

---

## API Configuration

Base URL is set in [lib/core/api/api_client.dart](lib/core/api/api_client.dart):

```dart
const String _baseUrl = 'http://10.0.2.2:5000/api';
```

All endpoint paths are defined in [lib/core/api/api_endpoints.dart](lib/core/api/api_endpoints.dart):

```dart
class ApiEndpoints {
  static const login            = '/auth/login';
  static const register         = '/auth/register';
  static const logout           = '/auth/logout';
  static const me               = '/auth/me';
  static const profile          = '/auth/profile';
  static const changePassword   = '/auth/change-password';
  static const myVehicles       = '/vehicle/owner/vehicles';
  static const claimVehicle     = '/vehicle/claim';
  static const transferVehicle  = '/vehicle/transfer';
  static String vehicleDetail(String vin) => '/vehicle/$vin';
  static String warrantyCheck(String vin) => '/warranty/check/$vin';
  static const ownerPendingServices = '/service/owner/pending';
  static const ownerVerifyService   = '/service/owner/verify';
  static const ownerDisputeService  = '/service/owner/dispute';
  static const ownerServiceHistory  = '/service/owner/history';
  static const submitClaim  = '/warranty/submit-claim';
  static const ownerClaims  = '/warranty/owner/claims';
  static String vehicleClaims(String vin) => '/warranty/claims/$vin';
}
```

---

## Authentication Flow

1. User enters credentials on `LoginScreen`
2. `AuthProvider.login()` calls `POST /api/auth/login`
3. Access and refresh tokens are saved via `TokenStorage` (flutter_secure_storage)
4. On subsequent app launches, `AuthProvider.tryAutoLogin()` calls `GET /api/auth/me` with the stored token to restore the session
5. Logout calls `POST /api/auth/logout` to revoke the refresh token, then clears local storage

The access token is attached to every Dio request via the `Authorization: Bearer <token>` header, configured in `api_client.dart`.

---

## State Management

Provider pattern with `ChangeNotifier`. All providers registered at root via `MultiProvider` in `main.dart`:

| Provider | Manages |
|---|---|
| `AuthProvider` | Current user, loading/error state, login / register / logout / auto-login |
| `VehiclesProvider` | Vehicle list, claim vehicle, transfer ownership, warranty check |
| `ServicesProvider` | Pending and history service records, verify, dispute |
| `WarrantiesProvider` | Warranty claims list, submit new claim |

---

## Testing

```bash
flutter test
```

**Expected: 88 passing**

| Directory | What is tested |
|---|---|
| `test/unit/models/` | JSON parsing for `User`, `Vehicle`, `ServiceRecord`, `WarrantyClaim` |
| `test/unit/providers/` | `AuthProvider`, `VehiclesProvider`, `ServicesProvider`, `WarrantiesProvider` — Dio mocked |
| `test/widget/` | `LoginScreen`, `VehiclesScreen`, `ClaimVehicleScreen`, `StatusBadge` widget rendering and interactions |

The unit provider tests inject a `MockDio` into the `ApiClient` singleton using Mockito. Widget tests use hand-written Mockito mocks with the null-safe `super.noSuchMethod` pattern for non-nullable return types.

---

## Dependencies

```yaml
dependencies:
  flutter: { sdk: flutter }
  provider: ^6.1.2          # State management
  go_router: ^14.2.0        # Navigation
  dio: ^5.4.3               # HTTP client
  flutter_secure_storage: ^9.2.2   # JWT token storage
  intl: ^0.19.0             # Date formatting

dev_dependencies:
  flutter_test: { sdk: flutter }
  flutter_lints: ^4.0.0
  mockito: ^5.4.4           # Mocking for tests
  build_runner: ^2.4.9      # Mock generation
```

---

## Common Issues

**`MissingPluginException` for flutter_secure_storage in unit tests**
Add `TestWidgetsFlutterBinding.ensureInitialized()` and mock the `plugins.it_nomads.com/flutter_secure_storage` method channel in `setUpAll()`. See `test/unit/providers/auth_provider_test.dart` for the pattern.

**`CardTheme` compile error**
Flutter 3.44 renamed `CardTheme` to `CardThemeData`. Ensure SDK is 3.44 or later.

**App cannot reach backend on emulator**
`10.0.2.2` is the Android emulator's alias for the host machine's localhost. For a physical device, use the host LAN IP instead.

**Mockito `when()` fails with non-nullable getters**
Plain `Mock` subclasses without explicit overrides return `null` for non-nullable types, which throws a type error in null-safe Dart. Override each non-nullable getter/method using `super.noSuchMethod(Invocation.getter(#name), returnValue: <default>, returnValueForMissingStub: <default>)`. This lets Mockito intercept the call while providing a safe default.
