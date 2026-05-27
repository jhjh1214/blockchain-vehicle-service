# Blockchain Vehicle Service System

A full-stack decentralised application for vehicle registration, service history, and warranty management. The system combines Ethereum smart contracts with a traditional Flask API so that all critical records are anchored on-chain while human-readable metadata is stored off-chain in SQLite.

Two client interfaces are provided:
- **Angular 21 web app** — for Manufacturers and Service Centres
- **Flutter mobile app** — for vehicle Owners

---

## Architecture Overview

```
┌────────────────────────────┐   ┌──────────────────────────────────┐
│   Angular Web Frontend     │   │   Flutter Owner Mobile App       │
│  Manufacturer / Service    │   │   (Android / iOS)                │
│  Centre dashboards         │   │   Dio · Provider · GoRouter      │
└─────────────┬──────────────┘   └────────────────┬─────────────────┘
              │ REST / JSON                        │ REST / JSON
              └──────────────────┬─────────────────┘
                                 │
              ┌──────────────────▼─────────────────────────────────┐
              │                Flask REST API                      │
              │   /api/auth · /api/vehicle · /api/service          │
              │   /api/warranty · /api/uploads                     │
              │              JWT + Role-Based Access               │
              │                                                    │
              │  ┌─────────────────┐   ┌─────────────────────┐    │
              │  │   SQLite DB     │   │  Web3.py → Ganache  │    │
              │  │  Users, tokens  │   │  Ethereum EVM       │    │
              │  │  Metadata,      │   │  Ownership, hashes  │    │
              │  │  VIN mappings   │   │  Warranty state     │    │
              │  └─────────────────┘   └─────────────────────┘    │
              └────────────────────────────────────────────────────┘
                                 │ Web3.py
              ┌──────────────────▼─────────────────────────────────┐
              │         Solidity Smart Contracts (Hardhat)         │
              │   VehicleRegistry · ServiceLog · WarrantyTracker   │
              │               OpenZeppelin AccessControl           │
              └────────────────────────────────────────────────────┘
```

**Design principle:** The blockchain is the source of truth for ownership, warranty validity, service record finality, and claim status. SQLite holds human-readable metadata (service notes, photos, names). Neither layer alone is sufficient — this is intentional.

---

## Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Smart contracts | Solidity + Hardhat | 0.8.28 / 2.28 |
| Contract library | OpenZeppelin Contracts | 5.x |
| Backend framework | Python + Flask | 3.11 / 3.0 |
| ORM | SQLAlchemy + Flask-SQLAlchemy | 2.0 / 3.1 |
| Blockchain client | Web3.py | 6.11 |
| Authentication | PyJWT + bcrypt | 2.8 / 4.1 |
| Encryption | Cryptography (Fernet) | 41.x |
| Database | SQLite (dev) | bundled |
| Web frontend | Angular (standalone components) | 21.2 |
| Mobile app | Flutter | 3.44+ |
| Local EVM | Ganache | 7.x |
| Node.js | Node.js | 18+ |
| Backend tests | pytest + pytest-flask | 8.3 / 1.3 |
| Contract tests | Hardhat + Chai + Ethers.js | v6 |
| Mobile tests | flutter_test + Mockito | 5.7 |

---

## User Roles and Features

### Manufacturer
- Register new vehicles on-chain (VIN, owner email, warranty period, make/model/year)
- Pre-register vehicles before owner claims them (pending status)
- Approve or deny warranty claims submitted by vehicle owners
- Resolve disputed service records (approve or reject with resolution notes)
- View all vehicles registered under their brand
- Manage authorised service centres

### Service Centre (Dealer)
- Submit service records for any vehicle (off-chain metadata hashed to SHA-256, hash anchored on-chain)
- View pending and finalized service history for any VIN
- Look up vehicle details and warranty status by VIN

### Owner (Web + Mobile)
- Claim ownership of a pre-registered vehicle using its VIN
- View owned vehicles, warranty status, and expiry
- Transfer vehicle ownership to another registered user
- Review pending service records submitted by service centres
- Verify a service record (triggers on-chain finalization + service hash written to VehicleRegistry)
- Dispute a service record with a reason (queues for manufacturer resolution)
- Submit warranty claims with issue description and photos
- Track warranty claim status (pending / approved / denied)

---

## Smart Contracts

| Contract | Responsibility |
|---|---|
| `VehicleRegistry` | Register vehicles, track ownership transfers, store finalized service hashes per VIN |
| `ServiceLog` | Two-stage service verification (submit → verify/dispute → resolve), calls `addServiceHash` on finalization |
| `WarrantyTracker` | Read warranty expiry from VehicleRegistry, manage claim lifecycle (submit → approve/deny) |

### Roles (OpenZeppelin AccessControl)

| Role | Holder | Permissions |
|---|---|---|
| `DEFAULT_ADMIN_ROLE` | Deployer EOA | Grant/revoke all roles, resolve disputes, approve/deny warranty claims |
| `MANUFACTURER_ROLE` | Manufacturer account | Register vehicles on-chain |
| `SERVICE_CENTER_ROLE` | Service centre account | Submit service records |
| `OWNER_ROLE` | Vehicle owner account | Verify/dispute services, submit warranty claims |
| `SERVICE_LOG_ROLE` | ServiceLog contract address | Call `addServiceHash` on VehicleRegistry |

---

## Project Structure

```
blockchain-vehicle-service/
├── backend/                        # Flask REST API
│   ├── api/                        # Route blueprints
│   │   ├── auth.py                 # /api/auth — register, login, /me, profile, change-password
│   │   ├── vehicles.py             # /api/vehicle — register, claim, transfer, get, my-vehicles
│   │   ├── services.py             # /api/service — submit, pending, history, verify, dispute, resolve, owner endpoints
│   │   ├── warranties.py           # /api/warranty — check, submit-claim, approve, deny, owner/claims
│   │   ├── middleware.py           # @token_required, @role_required decorators
│   │   ├── sc_management.py        # /api/sc — smart contract config management
│   │   ├── admin.py                # /api/admin — admin endpoints
│   │   └── uploads.py              # /api/upload — file uploads
│   ├── blockchain/
│   │   ├── client.py               # Web3 HTTPProvider singleton (Ganache)
│   │   ├── keystore.py             # Fernet-encrypted Ethereum private key store
│   │   ├── utils.py                # sha256_hash(), keccak256_hash(), vin_to_hex()
│   │   ├── event_monitor.py        # Background thread for on-chain event listening
│   │   └── adapters/
│   │       ├── vehicle_registry.py # VehicleRegistry contract wrapper
│   │       ├── service_log.py      # ServiceLog contract wrapper
│   │       └── warranty_tracker.py # WarrantyTracker contract wrapper
│   ├── core/                       # Business logic (no Flask imports)
│   │   ├── auth_service.py         # Register/login, bcrypt, JWT issuance/refresh
│   │   ├── vehicle_service.py      # Vehicle registration, claim, transfer, lookup
│   │   ├── service_log_service.py  # Service submission, verification, owner aggregation
│   │   └── warranty_service.py     # Warranty check, claim lifecycle, owner aggregation
│   ├── db/
│   │   ├── models.py               # SQLAlchemy models (User, RefreshToken, ServiceMetadata, etc.)
│   │   └── repositories/           # DB query helpers per model
│   ├── tests/                      # pytest test suite (142 tests)
│   ├── abis/                       # Compiled ABI JSON files (copied from Hardhat)
│   ├── keystore/                   # Encrypted private key files
│   ├── app.py                      # Flask app factory + blueprint registration
│   ├── config.py                   # Configuration loader (.env)
│   ├── conftest.py                 # pytest fixtures with mocked blockchain
│   ├── init_db.py                  # One-time database initialisation
│   ├── requirements.txt
│   └── .env                        # Environment config (not committed)
│
├── smart-contracts/                # Hardhat project
│   ├── contracts/
│   │   ├── VehicleRegistry.sol
│   │   ├── ServiceLog.sol
│   │   └── WarrantyTracker.sol
│   ├── scripts/deploy.js           # Deploys all contracts, grants SERVICE_LOG_ROLE
│   ├── test/test_contracts.js      # Hardhat/Chai test suite (20+ cases)
│   └── hardhat.config.js           # Solidity 0.8.28, ganache @ localhost:8545
│
├── vehicle-service-frontend/       # Angular 21 web application
│   └── src/app/
│       ├── core/                   # Guards, interceptors, HTTP services, models
│       ├── features/
│       │   ├── auth/               # Login / register pages
│       │   ├── manufacturer/       # Manufacturer dashboards
│       │   ├── dealer/             # Service centre dashboards
│       │   └── public/             # Public VIN verification page
│       └── shared/shell/           # Role-specific navigation layouts
│
├── owner_mobile_app/               # Flutter owner mobile application
│   └── lib/
│       ├── core/                   # API client, models, secure token storage
│       ├── features/               # Auth, vehicles, services, warranties, profile
│       ├── shared/                 # Widgets, theme
│       └── router/                 # GoRouter configuration
│
├── setup.ps1                       # Windows automated setup script
├── seed.py                         # Database seed script (test users/vehicles)
└── CLAUDE.md                       # AI assistant instructions
```

---

## Prerequisites

Install the following before running the project.

### 1. Python 3.11 (recommended)

> Python 3.13+ is not recommended — some web3 C extensions lack pre-built wheels.

Download from **https://www.python.org/downloads/** and choose **3.11.x**.

On Windows: check **"Add Python to PATH"** during installation.

```powershell
python --version   # Python 3.11.x
```

### 2. Node.js 18 or later (LTS)

Download from **https://nodejs.org/**

```powershell
node --version   # v18.x or higher
npm --version    # 9.x or higher
```

### 3. Ganache (local Ethereum node)

```powershell
npm install -g ganache
ganache --version
```

### 4. Flutter SDK (for mobile app only)

Download from **https://docs.flutter.dev/get-started/install**

```powershell
flutter --version   # Flutter 3.44.0 or later
```

Android SDK is required for Android emulator/device testing.

---

## Setup

### Automated (Windows — recommended)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup.ps1
```

The script checks versions, creates the Python venv, installs all dependencies, compiles contracts, copies ABIs, and initialises the database.

Then skip to **Step 4** below (Start Ganache).

---

### Manual Setup

#### Step 1 — Backend Python environment

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows
# source venv/bin/activate         # macOS / Linux
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 2 — Smart contracts

```powershell
cd ..\smart-contracts
npm install
npx hardhat compile
```

Copy compiled ABIs to the backend:

```powershell
# from smart-contracts/
Copy-Item "artifacts\contracts\VehicleRegistry.sol\VehicleRegistry.json" "..\backend\abis\"
Copy-Item "artifacts\contracts\ServiceLog.sol\ServiceLog.json"           "..\backend\abis\"
Copy-Item "artifacts\contracts\WarrantyTracker.sol\WarrantyTracker.json" "..\backend\abis\"
```

#### Step 3 — Web frontend dependencies

```powershell
cd ..\vehicle-service-frontend
npm install
```

#### Step 4 — Start Ganache (keep running in a dedicated terminal)

```powershell
ganache --port 8545 --chainId 1337 --deterministic
```

`--deterministic` produces the same 10 HD-wallet accounts every time, which keeps `.env` stable across restarts.

#### Step 5 — Deploy smart contracts

```powershell
cd smart-contracts
npx hardhat run scripts/deploy.js --network ganache
```

Output:
```
VehicleRegistry deployed to: 0xABC...
ServiceLog deployed to:      0xDEF...
WarrantyTracker deployed to: 0x123...
SERVICE_LOG_ROLE granted to ServiceLog
```

#### Step 6 — Configure the backend

Edit `backend/.env` with the addresses printed above and the Ganache account addresses:

```env
GANACHE_URL=http://127.0.0.1:8545

VEHICLE_REGISTRY_ADDRESS=0xABC...
SERVICE_LOG_ADDRESS=0xDEF...
WARRANTY_TRACKER_ADDRESS=0x123...

# Ganache deterministic accounts (ganache --deterministic)
DEPLOYER_ADDRESS=<account[0]>
MANUFACTURER_ADDRESS=<account[1]>
SERVICE_CENTER_ADDRESS=<account[2]>
OWNER1_ADDRESS=<account[3]>
OWNER2_ADDRESS=<account[4]>

SECRET_KEY=change-this-in-production
DATABASE_URI=sqlite:///vehicle_service.db
KEYSTORE_DIR=keystore
KEYSTORE_ENCRYPTION_KEY=change-this-in-production
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216
```

#### Step 7 — Initialise the database

```powershell
cd backend
# venv must be active
python init_db.py
```

#### Step 8 — Start the backend

```powershell
# backend/ with venv active
python app.py
```

API is available at `http://localhost:5000`.

#### Step 9 — Start the web frontend

```powershell
cd vehicle-service-frontend
npx ng serve
```

Web app is available at `http://localhost:4200`.

#### Step 10 — Run the mobile app (optional)

```powershell
cd owner_mobile_app
flutter pub get
flutter run
```

The mobile app targets `http://10.0.2.2:5000/api` (Android emulator loopback to host). Change `lib/core/api/api_client.dart` for a physical device or different host.

---

## Running Tests

### Smart contract tests (no Ganache required)

```powershell
cd smart-contracts
npx hardhat test
```

Covers: vehicle registration, duplicate VIN rejection, role-based access control, service two-stage verification, dispute approve/reject, warranty claim lifecycle.

**Expected: 20+ passing**

---

### Backend unit and API tests (no Ganache required — blockchain is mocked)

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pytest
```

The blockchain adapters are patched to MagicMock objects in `conftest.py` so no Ganache connection is needed.

| Test file | Coverage |
|---|---|
| `test_utils.py` | SHA-256 and keccak256 hashing (determinism, order-independence, format) |
| `test_auth.py` | Register, login, /me, duplicate and invalid-role rejection |
| `test_vehicles.py` | Registration RBAC, get vehicle, my-vehicles, claim, transfer |
| `test_services.py` | Submit, pending, history, verify, dispute, resolve, owner endpoints |
| `test_warranties.py` | Check warranty, submit-claim, approve/deny, owner/claims |
| `test_profile.py` | User profile updates, change password |
| `test_sc_management.py` | Smart contract address config endpoints |
| `test_stats.py` | Statistics and analytics endpoints |
| `test_integration.py` | Full workflow (excluded by default, requires Ganache) |

**Expected: 142 passing**

With coverage report:

```powershell
pytest --cov=. --cov-report=term-missing
```

---

### End-to-end integration tests (requires running Ganache + deployed contracts + backend)

```powershell
cd backend
pytest -m e2e -v
```

Covers: full 10-step registration → service → warranty claim workflow; dispute resolution workflow.

---

### Mobile app tests

```powershell
cd owner_mobile_app
flutter test
```

| Test area | Coverage |
|---|---|
| `unit/models/` | `User`, `Vehicle`, `ServiceRecord`, `WarrantyClaim` JSON parsing |
| `unit/providers/` | `AuthProvider`, `VehiclesProvider`, `ServicesProvider`, `WarrantiesProvider` |
| `widget/` | `LoginScreen`, `VehiclesScreen`, `ClaimVehicleScreen`, `StatusBadge` |

**Expected: 88 passing**

---

### Web frontend type-check

```powershell
cd vehicle-service-frontend
npx ng build --configuration development
```

A clean build confirms all TypeScript types and Angular templates are valid.

---

## API Reference

All endpoints are prefixed `/api`.

### Authentication — `/api/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/register` | None | Create account (role: MANUFACTURER / SERVICE_CENTER / OWNER) |
| POST | `/login` | None | Authenticate, receive access + refresh tokens |
| POST | `/logout` | JWT | Revoke refresh token |
| GET | `/me` | JWT | Current user profile |
| PUT | `/profile` | JWT | Update name, phone, city, state |
| POST | `/change-password` | JWT | Change password (revokes session) |

### Vehicles — `/api/vehicle`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/register` | MANUFACTURER | Register vehicle on-chain (with or without owner email) |
| POST | `/claim` | OWNER | Claim ownership of a pending (pre-registered) vehicle |
| POST | `/transfer` | OWNER | Transfer vehicle to another registered owner |
| GET | `/public/<vin>` | None | Public vehicle details and warranty status |
| GET | `/<vin>` | JWT | Full vehicle details + warranty |
| GET | `/owner/vehicles` | OWNER | List all vehicles owned by the caller |

### Services — `/api/service`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/submit` | SERVICE_CENTER | Hash service metadata, anchor hash on-chain |
| GET | `/pending/<vin>` | JWT | Pending (unverified) records for a VIN |
| GET | `/history/<vin>` | JWT | Finalized service records for a VIN |
| POST | `/verify` | OWNER | Verify a pending record → on-chain finalization |
| POST | `/dispute` | OWNER | Flag a pending record with a dispute reason |
| POST | `/resolve-dispute` | MANUFACTURER | Approve (1) or reject (2) a disputed record |
| GET | `/owner/pending` | OWNER | All pending records across owner's vehicles |
| GET | `/owner/history` | OWNER | All finalized records across owner's vehicles |
| POST | `/owner/verify` | OWNER | Alias for `/verify` (mobile-friendly) |
| POST | `/owner/dispute` | OWNER | Alias for `/dispute` (mobile-friendly) |

### Warranties — `/api/warranty`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/check/<vin>` | JWT | Warranty validity, expiry timestamp, days remaining |
| POST | `/submit-claim` | OWNER | Submit a warranty claim with issue description |
| GET | `/claims/<vin>` | JWT | All claims for a VIN |
| POST | `/approve-claim` | MANUFACTURER | Approve a pending warranty claim on-chain |
| POST | `/deny-claim` | MANUFACTURER | Deny a claim with a reason (reason stored as hash) |
| GET | `/owner/claims` | OWNER | All claims across owner's vehicles |

---

## Hashing Strategy

| Purpose | Algorithm | Location |
|---|---|---|
| Service metadata fingerprint | SHA-256, deterministic key-sorted JSON | `blockchain/utils.py` |
| Warranty claim fingerprint | SHA-256 | `blockchain/utils.py` |
| VIN → on-chain `bytes32` key | keccak256 | `blockchain/utils.py` |
| Dispute resolution notes | SHA-256 | `blockchain/utils.py` |

All hashes are stored on-chain as `bytes32`. The raw metadata lives in SQLite and can be independently verified by recomputing the hash from the stored record.

---

## Data Flows

### Service Record Lifecycle

```
1. Service Centre  →  POST /api/service/submit
   Backend hashes metadata (SHA-256, key-sorted JSON)
   Metadata saved to SQLite (ServiceMetadata)
   Hash submitted on-chain via ServiceLog.submitService(vinHash, metadataHash)
   Record is PENDING on-chain (verified=false)

2. Owner  →  POST /api/service/owner/verify
   Backend calls ServiceLog.verifyService(vinHash, recordIndex)
   Contract marks record as FINALIZED (verified=true)
   Contract calls VehicleRegistry.addServiceHash(vinHash, metadataHash)
   Record is now in permanent on-chain history

3. Owner  →  POST /api/service/owner/dispute
   Backend calls ServiceLog.disputeService(vinHash, recordIndex, reason)
   Record marked DISPUTED on-chain

4. Manufacturer  →  POST /api/service/resolve-dispute
   Backend calls ServiceLog.resolveDispute(vinHash, recordIndex, decision, resolutionHash)
   decision=1 (APPROVE): record moves to finalized
   decision=2 (REJECT): record removed from pending
```

### Vehicle Claim Lifecycle

```
1. Manufacturer  →  POST /api/vehicle/register  (no owner_email)
   Vehicle registered on-chain with manufacturer as temporary owner
   registration_status = 'pending' in SQLite

2. Owner  →  POST /api/vehicle/claim  (vin)
   Admin (deployer) executes adminTransferOwnership on-chain
   Owner address set as new owner on-chain
   registration_status = 'active' in SQLite
```

### Warranty Claim Lifecycle

```
1. Owner  →  POST /api/warranty/submit-claim
   Backend hashes claim details (SHA-256)
   Claim saved to SQLite (WarrantyClaimMetadata)
   Hash submitted on-chain via WarrantyTracker.submitClaim(vinHash, claimHash)
   Claim status = PENDING on-chain

2. Manufacturer  →  POST /api/warranty/approve-claim or /deny-claim
   Backend calls WarrantyTracker.approveClaim or denyClaim on-chain
   Claim status updated on-chain (APPROVED / DENIED)
```

---

## Common Issues

**`lru-dict` or `ckzg` build error on Windows**
Use Python 3.11 or 3.12 (pre-built wheels available). Alternatively install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).

**`.\venv\Scripts\Activate.ps1` opens Notepad or is blocked**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**`AccessControlUnauthorizedAccount` on service hash write**
`SERVICE_LOG_ROLE` was not granted to the ServiceLog contract. Re-run `deploy.js` — it handles this automatically.

**Flutter: `CardTheme` compile error**
Ensure Flutter SDK is 3.44+. The app uses `CardThemeData` (renamed in 3.44).

**Mobile app cannot reach backend on emulator**
The app connects to `http://10.0.2.2:5000/api` (Android emulator loopback). If using a physical device or different host, update `lib/core/api/api_client.dart`.

**Stale pending record indices after dispute resolution**
Solidity uses swap-and-pop for array removals, so indices shift. Always re-fetch from chain after resolve actions.

---

## Deployment Notes (Production)

- Replace SQLite with PostgreSQL: `DATABASE_URI=postgresql://user:pass@host/db`
- Replace Ganache with a real network (Ethereum mainnet, Polygon, or a private Besu/Geth chain)
- Update `hardhat.config.js` with the target RPC URL and funded deployer key
- Rotate `SECRET_KEY` and `KEYSTORE_ENCRYPTION_KEY` to strong random values
- Serve Angular build via Nginx: `ng build --configuration production`
- Run Flask behind Gunicorn + Nginx (not the dev server)
- Store private keys in a proper secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- Set `CORS_ORIGINS` in `.env` to restrict origins
- Enable HTTPS — the mobile app requires HTTPS on production endpoints

---

## Database Models

| Model | Purpose |
|---|---|
| `User` | Accounts with role, blockchain address, name, phone, brand (MFR only), account lockout |
| `RefreshToken` | Token revocation — hashed tokens with expiry |
| `DeviceToken` | Mobile push notification tokens per user/platform |
| `ServiceMetadata` | Off-chain service record details (type, date, mileage, technician, photos) |
| `WarrantyClaimMetadata` | Off-chain claim details (issue description, photos) |
| `VehicleVINMapping` | String VIN ↔ keccak256 hash mapping, owner address, make/model/year |

---

## Developer Reference

### Backend test fixtures (`conftest.py`)

All blockchain adapters (`vehicle_registry`, `service_log`, `warranty_tracker`) are replaced with `MagicMock` instances in the test session. This means:
- Tests run without Ganache
- On-chain calls return configurable mock values
- Tests verify HTTP behaviour, auth, and business logic only

The `register_and_login(client, role, ...)` helper creates a user and returns `(token, user_data)`.

### Backend blueprint mounts

| Blueprint | URL prefix |
|---|---|
| `auth` | `/api/auth` |
| `vehicles` | `/api/vehicle` |
| `services` | `/api/service` |
| `warranties` | `/api/warranty` |
| `uploads` | `/api/upload` |
| `sc_management` | `/api/sc` |
| `admin` | `/api/admin` |

### Mobile app API base URL

```dart
// lib/core/api/api_client.dart
const String _baseUrl = 'http://10.0.2.2:5000/api';
```

`10.0.2.2` is the Android emulator's loopback to the host machine. Change to `http://localhost:5000/api` for a desktop/web run, or the host LAN IP for a physical Android device.

### Key design decisions

**Swap-and-pop in ServiceLog:** Solidity removes pending records using swap-and-pop for O(1) gas cost. This means `recordIndex` values change after any removal. The frontend and backend always re-fetch fresh indices from the chain rather than holding stale state.

**Dual storage:** Every on-chain record has a corresponding SQLite row linked by hash. The chain stores hashes; SQLite stores the full metadata. Either can be used to verify the other.

**VIN encoding:** VINs (17 characters) are encoded as `keccak256(abi.encodePacked(vin))` for on-chain storage. The `VehicleVINMapping` table keeps the human-readable VIN ↔ hash mapping.

**Brand validation:** Manufacturers can only register vehicles with a `make` that matches their registered `brand`. This is enforced in `backend/api/vehicles.py`.

**Token refresh:** Access tokens expire (short-lived). Clients call `POST /api/auth/login` with refresh token to obtain a new access token. Logout revokes the refresh token.
