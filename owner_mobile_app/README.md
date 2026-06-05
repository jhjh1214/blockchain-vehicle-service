# Owner Mobile App — Blockchain Vehicle Service

Flutter mobile application for **vehicle owners**. Provides access to owned vehicles, service history, warranty status, and claim submission. Connects to the Flask backend via REST API. Distributed as an Android APK.

---

## Features

| Feature | Description |
|---|---|
| Authentication | Login (with Remember Me), register (PDPA consent), auto-login on app restart, logout |
| Forgot Password | Request a password reset email; reset password with token link |
| My Vehicles | List owned vehicles with warranty status badge |
| Claim Vehicle | Claim ownership of a pre-registered vehicle by scanning a QR/barcode or typing VIN |
| Vehicle Detail | Warranty expiry, service count, transfer ownership |
| Pending Services | Review unverified service records, verify or dispute each one |
| Dispute Chat | Message thread between owner and manufacturer for disputed records |
| Service History | Browse finalized service records with full metadata; report abusive service centres |
| Warranty Claims | View all claims, submit new claims with issue description |
| Warranty Void Requests | View void requests raised by service centres; dispute any request you believe is incorrect |
| Active Recalls | View safety recalls issued for your vehicles |
| Notifications | In-app notification inbox for service, warranty, and recall events |
| Profile | Update name, phone, city, state; change password; data export; delete account |
| Privacy Policy | PDPA privacy policy screen (linked from registration) |
| Push Notifications | FCM-based push notifications (token registered after login); routes to relevant screen on tap |

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
| QR / barcode scanner | mobile_scanner 5.x |
| Camera permissions | permission_handler 11.x |
| Biometric auth | local_auth 2.x |
| Push notifications | firebase_messaging 15.x + firebase_core 3.x |
| Localisation | intl 0.19 |
| Preferences | shared_preferences 2.x |

---

## Project Structure

```
owner_mobile_app/
└── lib/
    ├── main.dart                              # App entry — MultiProvider setup
    │
    ├── core/
    │   ├── api/
    │   │   ├── api_client.dart               # Dio singleton (base URL, auth header)
    │   │   └── api_endpoints.dart            # All API path constants
    │   ├── models/
    │   │   ├── user.dart                     # User.fromJson
    │   │   ├── vehicle.dart                  # Vehicle.fromJson, displayName, warrantyValid
    │   │   ├── service_record.dart           # ServiceRecord.fromJson, status helpers
    │   │   └── warranty_claim.dart           # WarrantyClaim.fromJson, status helpers
    │   ├── services/
    │   │   └── push_notification_service.dart # FCM token registration (registered after login)
    │   └── storage/
    │       └── token_storage.dart            # flutter_secure_storage wrapper (save/get/clear)
    │
    ├── features/
    │   ├── auth/
    │   │   ├── auth_provider.dart            # login(), register(), logout(), tryAutoLogin()
    │   │   ├── login_screen.dart             # Login form with Remember Me toggle
    │   │   ├── register_screen.dart          # Registration with PDPA consent checkbox
    │   │   ├── forgot_password_screen.dart   # Request password reset email
    │   │   └── privacy_policy_screen.dart    # PDPA privacy policy viewer
    │   │
    │   ├── vehicles/
    │   │   ├── vehicles_provider.dart        # loadVehicles(), claimVehicle(), transferVehicle(), checkWarranty()
    │   │   ├── vehicles_screen.dart          # Vehicle list with warranty badges
    │   │   ├── vehicle_detail_screen.dart
    │   │   ├── claim_vehicle_screen.dart     # QR/barcode scanner with camera permission flow
    │   │   ├── transfer_vehicle_screen.dart
    │   │   ├── recalls_provider.dart         # loadRecalls()
    │   │   └── recalls_screen.dart           # Active safety recalls for owned vehicles
    │   │
    │   ├── services/
    │   │   ├── services_provider.dart        # loadPendingServices(), loadServiceHistory(), verifyService(), disputeService()
    │   │   ├── pending_services_screen.dart
    │   │   ├── service_history_screen.dart   # Finalized history with abuse reporting
    │   │   ├── dispute_chat_screen.dart      # Real-time dispute message thread
    │   │   └── void_requests_screen.dart     # Warranty void requests with dispute action
    │   │
    │   ├── warranties/
    │   │   ├── warranties_provider.dart      # loadClaims(), submitClaim()
    │   │   ├── warranty_claims_screen.dart
    │   │   └── submit_claim_screen.dart
    │   │
    │   ├── notifications/
    │   │   ├── notifications_provider.dart   # loadNotifications(), markRead()
    │   │   └── notifications_screen.dart     # In-app notification inbox
    │   │
    │   └── profile/
    │       ├── profile_screen.dart           # Profile update, data export, delete account
    │       └── change_password_screen.dart
    │
    ├── shared/
    │   ├── widgets/
    │   │   ├── status_badge.dart             # Coloured status chip (pending/verified/disputed)
    │   │   ├── empty_state.dart              # Full-page empty state with icon and CTA
    │   │   └── error_view.dart              # Error display with retry button
    │   └── theme/
    │       └── app_theme.dart               # Material 3 light theme
    │
    └── router/
        ├── app_router.dart                  # GoRouter — all named routes
        └── shell_screen.dart               # Bottom navigation bar shell
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

---

## API Configuration

Base URL is set in [lib/core/api/api_client.dart](lib/core/api/api_client.dart):

```dart
const String _baseUrl = 'http://10.0.2.2:5000/api';
```

All endpoint paths are defined in [lib/core/api/api_endpoints.dart](lib/core/api/api_endpoints.dart):

```dart
class ApiEndpoints {
  // Auth
  static const login              = '/auth/login';
  static const register           = '/auth/register';
  static const logout             = '/auth/logout';
  static const me                 = '/auth/me';
  static const profile            = '/auth/profile';
  static const changePassword     = '/auth/change-password';
  static const forgotPassword     = '/auth/forgot-password';
  static const resetPassword      = '/auth/reset-password';
  static const deviceToken        = '/auth/device-token';
  static const deleteAccount      = '/auth/account';
  static const dataExport         = '/auth/data-export';
  static const resendVerification = '/auth/resend-verification';

  // Vehicles
  static const myVehicles         = '/vehicle/owner/vehicles';
  static const claimVehicle       = '/vehicle/claim';
  static const transferVehicle    = '/vehicle/transfer';
  static String vehicleDetail(String vin) => '/vehicle/$vin';
  static String vehicleExport(String vin) => '/vehicle/export/$vin';
  static String warrantyCheck(String vin) => '/warranty/check/$vin';
  static String warrantyEligibilityCheck(String vin) => '/warranty/check-eligibility/$vin';

  // Services
  static const ownerPendingServices = '/service/owner/pending';
  static const ownerVerifyService   = '/service/owner/verify';
  static const ownerDisputeService  = '/service/owner/dispute';
  static const ownerServiceHistory  = '/service/owner/history';
  static String disputeMessages(String vin, int idx) => '/service/dispute-messages/$vin/$idx';
  static const postDisputeMessage   = '/service/dispute-messages';

  // Warranties
  static const submitClaim  = '/warranty/submit-claim';
  static const ownerClaims  = '/warranty/owner/claims';
  static String vehicleClaims(String vin) => '/warranty/claims/$vin';

  // Void requests
  static const ownerVoidRequests = '/service/void-requests/owner';
  static String voidRequestDispute(int id) => '/service/void-requests/$id/dispute';

  // Recalls
  static const ownerRecalls = '/vehicle/recalls/owner';

  // Reporting
  static const reportUser = '/service/report';
}
```

---

## Authentication Flow

1. User enters credentials on `LoginScreen` with optional **Remember Me** toggle
2. `AuthProvider.login()` calls `POST /api/auth/login`
3. Tokens are saved via `TokenStorage`:
   - Remember Me = true → `flutter_secure_storage` (persists across app restarts)
   - Remember Me = false → in-memory only (cleared when process is killed)
4. On subsequent app launches, `AuthProvider.tryAutoLogin()` calls `GET /api/auth/me` with the stored token to restore the session
5. Logout calls `POST /api/auth/logout` to revoke the refresh token, then clears local storage

For forgotten passwords: `ForgotPasswordScreen` calls `POST /api/auth/forgot-password`, the backend sends a reset link via the Resend API, and the user follows the link to the web reset page.

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

**Expected: 94 passing**

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
  provider: ^6.1.2                 # State management
  go_router: ^14.2.0               # Navigation
  dio: ^5.4.3                      # HTTP client
  flutter_secure_storage: ^9.2.2   # JWT token storage (Remember Me)
  shared_preferences: ^2.3.2       # Lightweight key-value storage
  mobile_scanner: ^5.2.3           # QR / barcode scanning (camera)
  permission_handler: ^11.3.1      # Runtime camera permission requests
  local_auth: ^2.3.0               # Biometric / device credential auth
  image_picker: ^1.1.2             # Warranty claim photo attachment
  open_file: ^3.3.2                # Open exported files
  path_provider: ^2.1.3            # Access device file paths
  firebase_core: ^3.6.0            # Firebase initialisation
  firebase_messaging: ^15.1.3      # FCM push notifications
  intl: ^0.19.0                    # Date formatting

dev_dependencies:
  flutter_test: { sdk: flutter }
  flutter_lints: ^4.0.0
  mockito: ^5.4.4                  # Mocking for tests
  build_runner: ^2.4.9             # Mock generation
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

**QR scanner does not open / camera black screen**
`go_router` v14 intercepts `Navigator.push` by default. Open the scanner with `Navigator.of(context, rootNavigator: true).push(...)` to bypass the router. Also request camera permission explicitly via `permission_handler` before launching the scanner; if the user permanently denies, show a dialog linking to system settings.

**Push notifications not arriving (token never registered)**
The FCM token must be registered with the backend **after** a successful login, not at app startup. `PushNotificationService.init()` is called in `AuthProvider` after `login()`, `register()`, and `tryAutoLogin()` — never from `main.dart` before auth completes.
