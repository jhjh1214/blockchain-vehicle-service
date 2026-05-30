# VehicleChain — Blockchain Vehicle Service Management System

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
- Resolve disputed service records (approve or reject with resolution notes)
- View the entire fleet registered under their brand with health analytics
- Manage and activate/suspend authorised service centres
- View dashboard statistics: total vehicles, active warranties, pending claims, dispute rate

### Service Centre
- Submit service records for any vehicle (metadata hashed SHA-256, hash anchored on-chain)
- View pending and finalized service history for any VIN
- Look up vehicle details and warranty status by VIN
- Participate in dispute chat with vehicle owners

### Owner (Mobile + Web)
- Register and log in via mobile app (Flutter/Android) or web
- Claim ownership of a pre-registered vehicle using its VIN
- View owned vehicles, warranty status, expiry countdown
- Transfer vehicle ownership to another registered user
- Review pending service records and verify or dispute them
- Submit warranty claims with issue description and optional photos
- Track warranty claim status (pending → approved / denied)
- View full finalized service history with filtering
- Password reset via email
- PDPA-compliant data consent at registration

---

## Smart Contracts

| Contract | Responsibility |
|---|---|
| `VehicleRegistry` | Register vehicles, track ownership, store finalized service hashes per VIN |
| `ServiceLog` | Two-stage service verification (submit → verify/dispute → resolve) |
| `WarrantyTracker` | Manage warranty claim lifecycle (submit → approve/deny) |

### Role-Based Access Control (OpenZeppelin AccessControl)

| Role | Holder | Permissions |
|---|---|---|
| `DEFAULT_ADMIN_ROLE` | Deployer EOA | Grant/revoke roles, resolve disputes, approve/deny claims |
| `MANUFACTURER_ROLE` | Manufacturer wallet | Register vehicles on-chain |
| `SERVICE_CENTER_ROLE` | Service centre wallet | Submit service records |
| `OWNER_ROLE` | Vehicle owner wallet | Verify/dispute services, submit warranty claims |
| `SERVICE_LOG_ROLE` | ServiceLog contract | Call `addServiceHash` on VehicleRegistry |

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

All endpoints prefixed `/api`.

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
| GET | `/export/<vin>` | JWT | Export service history as PDF |

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

2. Owner → POST /api/service/owner/verify
   Backend calls ServiceLog.verifyService(vinHash, recordIndex)
   Contract finalizes record (verified=true)
   Contract calls VehicleRegistry.addServiceHash(vinHash, metadataHash)
   Status: FINALIZED — permanent on-chain history

3. Owner → POST /api/service/owner/dispute
   Backend calls ServiceLog.disputeService(vinHash, recordIndex, reason)
   Status: DISPUTED on-chain

4. Manufacturer → POST /api/service/resolve-dispute
   Backend calls ServiceLog.resolveDispute(vinHash, recordIndex, decision, resolutionHash)
   decision=1 (APPROVE): record finalized
   decision=2 (REJECT): record removed
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
│   ├── tests/                      # 433 passing pytest tests
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

### Backend (433 tests — no Ganache required)

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

### Smart Contracts

```powershell
cd smart-contracts
npx hardhat test
```

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
SECRET_KEY=<32-char hex>
JWT_SECRET_KEY=<32-char hex>
KEYSTORE_PASSWORD=<Fernet key>
ADMIN_SECRET=<random string>
PASSWORD_RESET_EXPIRY_MINUTES=60

# Blockchain
GANACHE_URL=https://ganache-production-83a3.up.railway.app
CHAIN_ID=1337
VEHICLE_REGISTRY_ADDRESS=0xe78A0F7E598Cc8b0Bb87894B0F60dD2a88d6a8Ab
SERVICE_LOG_ADDRESS=0x5b1869D9A4C187F2EAa108f3062412ecf0526b24
WARRANTY_TRACKER_ADDRESS=0xCfEB869F69431e42cdB54A4F4f105C19C080A601
DEPLOYER_ADDRESS=0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1
DEPLOYER_PRIVATE_KEY=<deployer private key>

# CORS / URLs
CORS_ORIGINS=https://vehiclechain.up.railway.app
FRONTEND_URL=https://vehiclechain.up.railway.app
USE_HTTPS=true

# Email (Resend)
RESEND_API_KEY=re_<key>
MAIL_DEFAULT_SENDER=VehicleChain <noreply@yourdomain.com>
MAIL_SUPPRESS_SEND=false
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

**Swap-and-pop in ServiceLog:** Solidity removes pending records with swap-and-pop for O(1) gas. This means `recordIndex` values shift after removals. All clients always re-fetch fresh indices from chain rather than caching stale values.

**VIN encoding:** VINs are hashed with `keccak256(abi.encodePacked(vin))` for on-chain storage. The `VehicleVINMapping` table maps the human-readable VIN to its on-chain key.

**Blockchain-first ordering:** All critical operations (vehicle registration, service submission, warranty claims) hit the blockchain before writing to the database. If the chain transaction fails, no DB record is created — ensuring consistency.

**PDPA consent:** OWNER role registration requires explicit consent. The `consent_given_at` timestamp is stored and the backend rejects OWNER registrations without `consent_given: true`. Non-OWNER roles (B2B) are exempt.

**Remember Me (Flutter):** `TokenStorage` uses `FlutterSecureStorage` for persistent sessions (remember me = true) and in-memory variables for session-only (remember me = false, cleared on process kill).

**Email delivery:** Flask-Mail + SMTP is blocked by Railway's network on port 587. The system uses the Resend HTTP API (port 443) for password reset emails to bypass this restriction.
