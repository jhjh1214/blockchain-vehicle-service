# VehicleChain — Blockchain Vehicle Service Management System

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Backend Tests](https://img.shields.io/badge/backend%20tests-453%20passing-brightgreen)](backend/tests/)
[![Contract Tests](https://img.shields.io/badge/contract%20tests-48%20passing-brightgreen)](smart-contracts/test/)
[![Angular Tests](https://img.shields.io/badge/angular%20tests-106%20passing-brightgreen)](vehicle-service-frontend/src/)
[![Flutter Tests](https://img.shields.io/badge/flutter%20tests-95%20passing-brightgreen)](owner_mobile_app/test/)
[![Live Demo](https://img.shields.io/badge/live-vehiclechain.up.railway.app-blue)](https://vehiclechain.up.railway.app)

A full-stack decentralised application for vehicle registration, service history, and warranty management built for a Final Year Project (FYP). The system uses Ethereum smart contracts as the immutable source of truth while a Flask REST API bridges the blockchain with two client interfaces: an Angular web dashboard for Manufacturers and Service Centres, and a Flutter mobile app for vehicle Owners.

---

## Live Demo

| Service | URL |
|---|---|
| Web App | https://vehiclechain.up.railway.app |
| Backend API | https://blockchain-vehicle-service-production.up.railway.app |
| Health Check | https://vehiclechain.up.railway.app/api/health |

---

## Architecture

```
                        Internet
                            │
              ┌─────────────▼──────────────┐
              │         Cloudflare         │  HTTPS, DNS
              └─────────────┬──────────────┘
                            │
          ┌─────────────────▼──────────────────────┐
          │            Railway Hosting              │
          │                                         │
          │  ┌──────────────────────────────────┐   │
          │  │   frontend (Nginx + Angular)     │   │  vehiclechain.up.railway.app
          │  │   Manufacturer / SC dashboards   │   │
          │  └──────────────────────────────────┘   │
          │                                         │
          │  ┌──────────────────────────────────┐   │
          │  │   backend (Flask + Gunicorn)     │   │  blockchain-vehicle-service-production.up.railway.app
          │  │   REST API · JWT Auth · Web3.py  │   │
          │  └──────────────────────────────────┘   │
          │                                         │
          │  ┌──────────────┐ ┌─────────────────┐   │
          │  │  PostgreSQL  │ │     Ganache      │   │
          │  │  (Railway    │ │  (EVM node,      │   │
          │  │   managed)   │ │   deterministic) │   │
          │  └──────────────┘ └─────────────────┘   │
          └─────────────────────────────────────────┘

          ┌──────────────────────────────────────────┐
          │   Flutter Owner Mobile App (Android APK) │
          │   Calls blockchain-vehicle-service-       │
          │   production.up.railway.app/api directly  │
          └──────────────────────────────────────────┘

          ┌──────────────────────────────────────────┐
          │   Solidity Smart Contracts (Hardhat)     │
          │   VehicleRegistry · ServiceLog           │
          │   WarrantyTracker                        │
          │   Deployed to Ganache (Railway)          │
          └──────────────────────────────────────────┘
```

**Design principle:** The blockchain is the immutable source of truth for ownership, service record finality, and warranty state. PostgreSQL stores human-readable metadata. Neither layer alone is sufficient — this is intentional for tamper-proof auditability.

---

## Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Smart contracts | Solidity + Hardhat | 0.8.28 / 2.28 |
| Contract library | OpenZeppelin Contracts | 5.x |
| Backend | Python + Flask | 3.11 / 3.0 |
| WSGI server | Gunicorn | 21.2 |
| ORM | SQLAlchemy + Flask-SQLAlchemy | 2.0 / 3.1 |
| Blockchain client | Web3.py | 6.11 |
| Authentication | PyJWT + bcrypt | 2.8 / 4.1 |
| Wallet encryption | Cryptography (Fernet) | 41.x |
| Rate limiting | Flask-Limiter | 3.5 |
| Email (transactional) | Resend HTTP API | 2.4 |
| Scheduler | APScheduler | 3.10 |
| Database (prod) | PostgreSQL | 16 |
| Database (dev/test) | SQLite | bundled |
| Web frontend | Angular (standalone) | 21.2 |
| Mobile app | Flutter | 3.44+ |
| Local EVM | Ganache | 7.x |
| Container runtime | Docker + Docker Compose | 29.x |
| Reverse proxy | Nginx | 1.25 |
| Backend tests | pytest + pytest-flask | 8.3 / 1.3 |
| Contract tests | Hardhat + Chai + Ethers.js | v6 |

---

## User Roles and Features

### Manufacturer
- Register new vehicles on-chain (VIN, owner email, warranty period, make/model/year)
- Pre-register vehicles without an owner (pending status — owner claims later)
- Approve or deny warranty claims submitted by vehicle owners
- Resolve disputed service records (approve, reject, or request modification with resolution notes)
- Issue safety recalls with optional VIN range to scope recalls to a specific production batch
- View the entire fleet registered under their brand with health analytics
- Manage and activate/suspend authorised service centres
- View dashboard statistics: total vehicles, active warranties, pending claims, dispute rate
- Export full fleet audit report as PDF

### Service Centre
- Submit service records for any vehicle (metadata hashed SHA-256, hash anchored on-chain)
- View pending and finalized service history for any VIN
- Look up vehicle details and warranty status by VIN
- Submit dispute rebuttals with notes before manufacturer resolution
- Escalate disputed records to manufacturer priority review
- Participate in dispute chat with vehicle owners
- Mark recall service as completed for a specific VIN

### Owner (Mobile + Web)
- Register and log in via mobile app (Flutter/Android) or web; biometric login (TouchID/FaceID) after first successful login
- Claim ownership of a pre-registered vehicle using its VIN
- View owned vehicles, warranty status, expiry countdown
- Transfer vehicle ownership to another registered user
- Review pending service records and verify or dispute them
- Submit warranty claims with issue description and optional photos
- Track warranty claim status (pending → approved / denied)
- View full finalized service history with filtering
- View active safety recalls — shows VIN range and whether each specific VIN is in the affected range
- Password reset via email
- PDPA-compliant data consent at registration
- Export vehicle service history as PDF

### Public (No Account Required)
- Look up any VIN on the public verify page (`/verify`) — shows registration status, warranty, service history, and recall history with per-VIN affected status
- Accessible at the root URL (`/`); no login required

---

## Smart Contracts

| Contract | Responsibility |
|---|---|
| `VehicleRegistry` | Register vehicles, track ownership, store finalized service hashes per VIN |
| `ServiceLog` | Two-stage service verification (submit → verify/dispute → resolve) |
| `WarrantyTracker` | Manage warranty claim lifecycle (submit → approve/deny) |

### Role-Based Access Control (OpenZeppelin AccessControl)

| Role | Contract | Holder | Permissions |
|---|---|---|---|
| `DEFAULT_ADMIN_ROLE` | All 3 | Deployer EOA | Grant/revoke roles (system admin only) |
| `MANUFACTURER_ROLE` | VehicleRegistry | Manufacturer wallet | Register vehicles on-chain |
| `MANUFACTURER_ADMIN_ROLE` | ServiceLog + WarrantyTracker | Manufacturer wallet | Resolve disputes, approve/deny warranty claims, void warranties |
| `SERVICE_CENTER_ROLE` | ServiceLog | SC wallet | Submit service records; revoked on account suspension |
| `OWNER_ROLE` | VehicleRegistry | Owner wallet | Verify/dispute services, submit warranty claims |
| `SERVICE_LOG_ROLE` | VehicleRegistry | ServiceLog contract | Internal: write finalized service hashes |

`MANUFACTURER_ADMIN_ROLE` uses the same `keccak256("MANUFACTURER_ADMIN_ROLE")` hash on both ServiceLog and WarrantyTracker — one logical role, two contracts. It is intentionally **not** `DEFAULT_ADMIN_ROLE` so manufacturers cannot call `grantRole()` to escalate privileges.

---

## Database Models

| Model | Purpose |
|---|---|
| `User` | Accounts: role, blockchain address, name, phone, brand, PDPA consent timestamp, lockout tracking |
| `RefreshToken` | Token revocation — hashed tokens with expiry |
| `DeviceToken` | FCM push notification tokens per user/platform |
| `ServiceMetadata` | Off-chain service record details (type, date, mileage, notes, photos) |
| `WarrantyClaimMetadata` | Off-chain claim details (issue description, photos, resolution) |
| `VehicleVINMapping` | VIN ↔ keccak256 hash mapping, owner address, make/model/year, warranty months |
| `VehicleRecall` | Safety recalls: brand, title, description, status (active/closed), optional `vin_range_start` / `vin_range_end` (17-char VIN bounds for batch-scoped recalls) |
| `RecallVINService` | Records which VINs have been serviced for a given recall |
| `AuthorizedSCLicense` | Pre-registered SSM licence numbers — only matching SCs can register as authorised |
| `AuditLog` | Security audit trail: login success/failure, password changes, key actions with IP |
| `PasswordResetToken` | Hashed password reset tokens with expiry |

---

## Security Features

- **JWT authentication** with short-lived access tokens and refresh token rotation
- **bcrypt** password hashing (cost factor 12)
- **Fernet encryption** for Ethereum private keys at rest
- **Rate limiting** on all auth endpoints (Flask-Limiter)
- **MIME magic byte validation** on file uploads (prevents extension spoofing)
- **HMAC-SHA256** time-windowed signature on the admin reset endpoint (replay-resistant)
- **Account lockout** after 5 failed login attempts (15-minute cooldown)
- **Audit logging** of all key security events with IP address
- **CSP headers** on both backend responses and Angular index.html
- **HSTS** in production (`USE_HTTPS=true`)
- **Session inactivity timeout** on Angular (30-minute warning at 25 min, auto-logout)
- **PDPA consent** required at OWNER registration; `consent_given_at` timestamp stored

---

## API Reference

All endpoints prefixed `/api`. The table below covers the main feature-facing endpoints. Additional internal/operational endpoints exist under `/api/sc/` (SC management), `/api/notifications/`, `/api/upload/`, and `/api/admin/`.

### Auth — `/api/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/register` | None | Create account (MANUFACTURER / SERVICE_CENTER / OWNER) |
| POST | `/login` | None | Authenticate, receive access + refresh tokens |
| POST | `/logout` | JWT | Revoke refresh token |
| GET | `/me` | JWT | Current user profile |
| PUT | `/profile` | JWT | Update name, phone, city, state |
| POST | `/change-password` | JWT | Change password (revokes session) |
| POST | `/forgot-password` | None | Send password reset email via Resend |
| POST | `/reset-password` | None | Reset password with token from email |
| POST | `/device-token` | JWT | Register FCM push notification token |
| GET | `/privacy-policy` | None | PDPA Privacy Policy content (JSON) |
| GET | `/terms` | None | Terms of Service content (JSON) |

### Vehicles — `/api/vehicle`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/register` | MANUFACTURER | Register vehicle on-chain |
| POST | `/claim` | OWNER | Claim ownership of pending vehicle |
| POST | `/transfer` | OWNER | Transfer vehicle to another owner |
| GET | `/public/<vin>` | None | Public vehicle details + warranty |
| GET | `/<vin>` | JWT | Full vehicle details |
| GET | `/owner/vehicles` | OWNER | List all vehicles owned by caller |
| GET | `/export/<vin>` | None | Export vehicle service history as PDF |
| GET | `/fleet` | MANUFACTURER | Paginated fleet list |
| GET | `/fleet-export` | MANUFACTURER | Fleet audit report as PDF |
| GET | `/stats` | MANUFACTURER | Aggregate manufacturer stats |
| GET | `/dashboard-stats` | MANUFACTURER | Full dashboard KPIs + charts data (60s TTL cache) |
| GET | `/activity-feed` | MANUFACTURER | Recent registrations, claims, disputes |
| POST | `/reconcile` | MANUFACTURER | Integrity check — recompute hashes, flag tampered records |
| POST | `/recall` | MANUFACTURER | Issue safety recall; optional `vin_range_start`/`vin_range_end` |
| GET | `/recalls` | MANUFACTURER | List recalls by status (active/closed) |
| POST | `/recalls/<id>/close` | MANUFACTURER | Close a recall |
| POST | `/recalls/<id>/service` | SERVICE_CENTER | Mark recall service completed for a VIN |
| GET | `/recalls/check/<vin>` | None | Active recalls for a VIN with `vin_affected` flag |
| GET | `/recalls/owner` | OWNER | All active recalls relevant to owner's vehicles with affected status |
| GET | `/reclaim-requests` | MANUFACTURER | List pending vehicle reclaim requests |
| POST | `/reclaim-request/<id>/approve` | MANUFACTURER | Approve reclaim |
| POST | `/reclaim-request/<id>/reject` | MANUFACTURER | Reject reclaim |

### Services — `/api/service`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/submit` | SERVICE_CENTER | Hash metadata and anchor on-chain |
| GET | `/pending/<vin>` | JWT | Pending (unverified) records |
| GET | `/history/<vin>` | JWT | Finalized records |
| POST | `/verify` | OWNER | Verify pending record → on-chain finalization |
| POST | `/dispute` | OWNER | Dispute pending record with reason |
| POST | `/resolve-dispute` | MANUFACTURER | Approve or reject disputed record |
| GET | `/owner/pending` | OWNER | All pending records across owned vehicles |
| GET | `/owner/history` | OWNER | All finalized records (filterable by status, type, date) |
| GET | `/sc/pending` | SERVICE_CENTER | All pending records for the authenticated SC |
| GET | `/sc/my-stats` | SERVICE_CENTER | SC dispute rate, submission count, flagged status |
| POST | `/dispute-response` | SERVICE_CENTER | Submit rebuttal notes on a disputed record |
| POST | `/escalate-dispute` | SERVICE_CENTER | Escalate dispute to manufacturer priority review |
| GET | `/owner/pending` | OWNER | All pending records across all owned vehicles |
| GET | `/owner/history` | OWNER | All finalized records across all owned vehicles (filterable) |
| GET | `/dispute-messages/<vin>/<idx>` | JWT | Dispute chat thread |
| POST | `/dispute-messages` | JWT | Post message in dispute chat |

### Warranties — `/api/warranty`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/check/<vin>` | JWT | Warranty validity, expiry, days remaining |
| GET | `/check-eligibility/<vin>` | JWT | Check claim eligibility |
| POST | `/submit-claim` | OWNER | Submit warranty claim |
| GET | `/claims/<vin>` | JWT | Claims for a VIN |
| POST | `/approve-claim` | MANUFACTURER | Approve claim on-chain |
| POST | `/deny-claim` | MANUFACTURER | Deny claim with reason |
| GET | `/owner/claims` | OWNER | All claims across owned vehicles |

---

## Data Flows

### Service Record Lifecycle
```
1. Service Centre → POST /api/service/submit
   Backend hashes metadata (SHA-256, key-sorted JSON)
   Metadata saved to PostgreSQL (ServiceMetadata)
   Hash submitted on-chain → ServiceLog.submitService(vinHash, metadataHash)
   Status: PENDING on-chain

2. Owner → POST /api/service/owner/verify  { vin, metadata_hash }
   Backend calls ServiceLog.verifyService(vinHash, metadataHash)
   Contract finds record by metadataHash (not index — swap-and-pop safe)
   Contract calls VehicleRegistry.addServiceHash(vinHash, metadataHash)
   Status: FINALIZED — permanent on-chain history

3. Owner → POST /api/service/owner/dispute  { vin, metadata_hash, reason }
   Backend calls ServiceLog.disputeService(vinHash, metadataHash, reason)
   Status: DISPUTED on-chain

4. Manufacturer → POST /api/service/resolve-dispute  { vin, metadata_hash, decision }
   Backend calls ServiceLog.resolveDispute(vinHash, metadataHash, decision, resolutionHash)
   decision=1 (APPROVE): record finalized and added to VehicleRegistry.serviceHashes
   decision=2 (REJECT): record removed from pending array
```

### Vehicle Claim Lifecycle
```
1. Manufacturer → POST /api/vehicle/register (no owner_email)
   Vehicle registered on-chain with manufacturer as temporary owner
   registration_status = 'pending' in PostgreSQL

2. Owner → POST /api/vehicle/claim (vin)
   Deployer executes adminTransferOwnership on-chain
   Owner address set as new owner on-chain
   registration_status = 'active' in PostgreSQL
```

---

## Project Structure

```
blockchain-vehicle-service/
├── backend/                        # Flask REST API
│   ├── api/                        # Route blueprints
│   │   ├── auth.py                 # Auth, forgot/reset password, device tokens, privacy policy
│   │   ├── vehicles.py             # Vehicle CRUD + PDF export
│   │   ├── services.py             # Service lifecycle + dispute chat
│   │   ├── warranties.py           # Warranty claims
│   │   ├── uploads.py              # File uploads (MIME validated, rate limited)
│   │   ├── sc_management.py        # Service centre management
│   │   ├── admin.py                # Admin reset (HMAC-protected)
│   │   └── middleware.py           # @token_required, @role_required
│   ├── blockchain/
│   │   ├── client.py               # Web3 HTTPProvider singleton
│   │   ├── keystore.py             # Fernet-encrypted private key store
│   │   ├── utils.py                # sha256_hash(), keccak256_hash(), vin_to_hex()
│   │   ├── event_monitor.py        # Background blockchain event listener
│   │   └── adapters/               # Contract wrapper classes
│   ├── core/                       # Business logic (no Flask imports)
│   │   ├── auth_service.py         # Register, login, bcrypt, JWT
│   │   ├── audit.py                # Audit event logger
│   │   ├── scheduler.py            # APScheduler — warranty expiry reminders
│   │   ├── vehicle_service.py
│   │   ├── service_log_service.py  # Includes _apply_filters()
│   │   └── warranty_service.py
│   ├── db/
│   │   ├── models.py               # All SQLAlchemy models
│   │   └── repositories/           # DB query helpers
│   ├── tests/                      # 453 passing pytest tests
│   │   ├── test_auth.py            # Auth + profile
│   │   ├── test_vehicles.py        # Vehicle operations
│   │   ├── test_services.py        # Service lifecycle + dispute chat
│   │   ├── test_warranties.py      # Warranty lifecycle
│   │   ├── test_sc_management.py   # SC management
│   │   ├── test_stats.py           # Stats, analytics, PDF export
│   │   ├── test_security.py        # All security/hardening tests (HMAC, MIME, audit, PDPA)
│   │   ├── test_utils.py           # Hashing utilities
│   │   └── test_integration.py     # End-to-end workflow tests
│   ├── Dockerfile                  # Python 3.11-slim + Gunicorn
│   ├── app.py                      # Flask app factory
│   ├── config.py                   # .env configuration loader
│   ├── conftest.py                 # pytest fixtures (mocked blockchain)
│   ├── extensions.py               # Flask-Limiter, Flask-Mail instances
│   └── requirements.txt
│
├── smart-contracts/                # Hardhat project
│   ├── contracts/
│   │   ├── VehicleRegistry.sol
│   │   ├── ServiceLog.sol
│   │   └── WarrantyTracker.sol
│   ├── scripts/
│   │   ├── deploy.js               # Deploys all contracts + grants roles
│   │   └── seed.js                 # Seeds test data
│   ├── test/test_contracts.js      # Hardhat/Chai contract tests
│   └── hardhat.config.js           # ganache + railway networks
│
├── vehicle-service-frontend/       # Angular 21 web application
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/               # Guards, interceptors, auth service, models
│   │   │   ├── features/
│   │   │   │   ├── auth/           # Login, register, forgot/reset password, privacy policy
│   │   │   │   ├── manufacturer/   # Fleet, vehicles, warranty claims, dispute resolution
│   │   │   │   ├── dealer/         # Service submission, pending records, VIN lookup
│   │   │   │   ├── shared/         # Profile, change password
│   │   │   │   └── public/         # Public VIN verify, privacy policy page
│   │   │   └── shared/shell/       # Role shells with inactivity timeout
│   │   ├── environments/
│   │   │   ├── environment.ts      # Dev: http://localhost:5000/api
│   │   │   └── environment.prod.ts # Prod: Railway backend URL
│   │   └── index.html              # CSP meta tag
│   ├── nginx.conf                  # SPA routing (no proxy — Angular calls backend directly)
│   └── Dockerfile                  # Node 20 build + Nginx serve
│
├── owner_mobile_app/               # Flutter owner mobile application
│   └── lib/
│       ├── core/
│       │   ├── api/                # ApiClient (Dio), ApiEndpoints
│       │   ├── models/             # User, Vehicle, ServiceRecord, WarrantyClaim
│       │   ├── services/           # PushNotificationService
│       │   └── storage/            # TokenStorage (secure + in-memory)
│       ├── features/
│       │   ├── auth/               # Login (remember me), Register (PDPA consent),
│       │   │                       # ForgotPassword, PrivacyPolicy screens
│       │   ├── vehicles/           # Vehicle list, detail, claim, transfer
│       │   ├── services/           # Pending services, history (filtered), dispute chat
│       │   ├── warranties/         # Warranty claims, submit claim
│       │   └── profile/            # Profile, change password
│       └── router/                 # GoRouter with auth guard
│
├── docker-compose.yml              # Local: backend + frontend + postgres + ganache
├── .env.example                    # Template for all required environment variables
├── setup.ps1                       # Windows automated local setup script
└── seed.py                         # Database seed script
```

---

## Running Locally (Docker — Recommended)

### Prerequisites
- Docker Desktop installed and running

### Steps

```powershell
# 1. Clone and enter the repo
git clone https://github.com/jhjh1214/blockchain-vehicle-service.git
cd blockchain-vehicle-service

# 2. Create your .env from the template
cp .env.example .env
# Edit .env — fill in POSTGRES_PASSWORD, SECRET_KEY, JWT_SECRET_KEY, KEYSTORE_PASSWORD

# 3. Build and start all 4 containers
docker compose up --build

# 4. Deploy smart contracts to the local Ganache
cd smart-contracts
npx hardhat run scripts/deploy.js --network ganache

# 5. Open the app
# Web:     http://localhost
# API:     http://localhost:5000/api/health
```

### Services
| Container | Port | Description |
|---|---|---|
| `frontend` | 80 | Nginx + Angular web app |
| `backend` | 5000 | Flask + Gunicorn REST API |
| `db` | 5432 (internal) | PostgreSQL 16 |
| `ganache` | 8545 | Local Ethereum node |

---

## Running Tests

**Total: 702 tests across all layers** (453 backend · 48 smart contracts · 106 Angular · 95 Flutter)

### Backend (453 tests — no Ganache required)

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pytest
pytest --cov=. --cov-report=term-missing   # with coverage
```

The blockchain adapters are fully mocked in `conftest.py`.

| Test File | Coverage |
|---|---|
| `test_auth.py` | Registration, login, lockout, JWT, forgot/reset password, device tokens, profile |
| `test_vehicles.py` | Registration, RBAC, claim, transfer, privacy, service stats |
| `test_services.py` | Submit, verify, dispute, resolve, owner endpoints, dispute chat, filtering |
| `test_warranties.py` | Check warranty, submit claim, approve/deny, persistence |
| `test_sc_management.py` | Service centre listing, activation, brand isolation |
| `test_stats.py` | Dashboard stats, fleet stats, PDF export, public verify |
| `test_security.py` | HMAC admin, MIME validation, audit logging, PDPA, JWT type check, production hardening |
| `test_utils.py` | SHA-256, keccak256 hashing |
| `test_integration.py` | Full end-to-end workflow (requires Ganache) |

### Smart Contracts (48 tests — 100% line coverage)

```powershell
cd smart-contracts
npx hardhat test
npx hardhat coverage   # solidity-coverage report
```

### Angular Web App (106 tests)

```powershell
cd vehicle-service-frontend
npm test
```

Covers all service classes and key components (AuthService, VehicleService, WarrantyService, ServiceService, LoginComponent, DealerDashboardComponent).

### Flutter Mobile App (95 tests — 65 unit + 30 widget)

```powershell
cd owner_mobile_app
flutter test
```

Covers models, providers (auth, vehicles, services, warranties), and widget rendering for key screens.

---

## Deployment (Railway)

The system is deployed on Railway with 4 services. To redeploy after a Ganache restart (wipes chain state):

```powershell
cd smart-contracts
npx hardhat run scripts/deploy.js --network railway
```

Contract addresses are deterministic (same mnemonic → same addresses every time).

### Required Backend Environment Variables

```env
# Database
DATABASE_URL=postgresql://...          # Provided by Railway PostgreSQL addon

# Flask
FLASK_ENV=production
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_hex(32))">
JWT_SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_hex(32))">
KEYSTORE_PASSWORD=<generate: python -c "import secrets; print(secrets.token_hex(32))">
ADMIN_SECRET=<generate: python -c "import secrets; print(secrets.token_hex(32))">
PASSWORD_RESET_EXPIRY_MINUTES=60

# Blockchain — addresses printed by deploy.js, store in Railway env vars, never in code
GANACHE_URL=<your Hardhat/Ganache RPC URL>
CHAIN_ID=1337
VEHICLE_REGISTRY_ADDRESS=<from deploy.js output>
SERVICE_LOG_ADDRESS=<from deploy.js output>
WARRANTY_TRACKER_ADDRESS=<from deploy.js output>
DEPLOYER_ADDRESS=<from deploy.js output>
DEPLOYER_PRIVATE_KEY=<from Hardhat node — store in Railway secrets only>

# CORS / URLs
CORS_ORIGINS=https://your-frontend.up.railway.app
FRONTEND_URL=https://your-frontend.up.railway.app
USE_HTTPS=true

# Email (Resend)
RESEND_API_KEY=<from resend.com dashboard>
MAIL_DEFAULT_SENDER=VehicleChain <noreply@yourdomain.com>
MAIL_SUPPRESS_SEND=false

# Trusted proxy IPs (set to Railway's internal proxy CIDR)
TRUSTED_PROXY_IPS=<railway-proxy-ip>

# Admin email for abuse alerts
ADMIN_CONTACT_EMAIL=<your email>
```

---

## Hashing Strategy

| Purpose | Algorithm | Location |
|---|---|---|
| Service metadata fingerprint | SHA-256 (key-sorted JSON) | `blockchain/utils.py` |
| Warranty claim fingerprint | SHA-256 | `blockchain/utils.py` |
| VIN → on-chain `bytes32` | keccak256 | `blockchain/utils.py` |
| Password storage | bcrypt (cost 12) | `core/auth_service.py` |
| Password reset token | SHA-256 | `api/auth.py` |
| Admin endpoint replay prevention | HMAC-SHA256 (30s window) | `api/admin.py` |

---

## Key Design Decisions

**Dual storage model:** Every on-chain record has a corresponding PostgreSQL row linked by hash. The blockchain stores hashes; the DB stores full metadata. Either can independently verify the other — tampering with DB metadata is detectable by recomputing and comparing the hash.

**Metadata-hash-based record lookup:** ServiceLog identifies records by their `metadataHash` (SHA-256 of the service metadata) rather than array indices. This eliminates the index-shifting race condition that swap-and-pop removal would otherwise cause. The `record_index` field returned in API responses is display-only and not used for any chain operation.

**VIN encoding:** VINs are hashed with `keccak256(abi.encodePacked(vin))` for on-chain storage. The `VehicleVINMapping` table maps the human-readable VIN to its on-chain key.

**Blockchain-first ordering:** All critical operations (vehicle registration, service submission, warranty claims) hit the blockchain before writing to the database. If the chain transaction fails, no DB record is created — ensuring consistency.

**PDPA consent:** OWNER role registration requires explicit consent. The `consent_given_at` timestamp is stored and the backend rejects OWNER registrations without `consent_given: true`. Non-OWNER roles (B2B) are exempt.

**Remember Me (Flutter):** `TokenStorage` uses `FlutterSecureStorage` for persistent sessions (remember me = true) and in-memory variables for session-only (remember me = false, cleared on process kill).

**Email delivery:** Flask-Mail + SMTP is blocked by Railway's network on port 587. The system uses the Resend HTTP API (port 443) for password reset emails to bypass this restriction.

---

## License

Copyright (c) 2026 Lim Jun Hong.

This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International License** — see the [LICENSE](LICENSE) file for details.

You may view and share this code with attribution, but **commercial use is prohibited** without explicit written permission from the author. The author reserves the right to release this project under different terms for commercial purposes.
