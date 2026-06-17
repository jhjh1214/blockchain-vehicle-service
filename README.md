<div align="center">

# ⛓️ VehicleChain

### Blockchain-Backed Vehicle Service & Warranty Management

<p>
  <a href="https://creativecommons.org/licenses/by-nc/4.0/"><img src="https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey?style=for-the-badge" alt="License"/></a>
  &nbsp;
  <a href="https://vehiclechain.up.railway.app"><img src="https://img.shields.io/badge/🌐%20Live%20Demo-vehiclechain.up.railway.app-0369a1?style=for-the-badge" alt="Live Demo"/></a>
</p>

<p>
  <img src="https://img.shields.io/badge/Backend-453%20tests%20passing-22c55e?style=flat-square&logo=pytest&logoColor=white" alt="Backend Tests"/>
  &nbsp;
  <img src="https://img.shields.io/badge/Contracts-48%20tests%20passing-22c55e?style=flat-square&logo=ethereum&logoColor=white" alt="Contract Tests"/>
  &nbsp;
  <img src="https://img.shields.io/badge/Angular-106%20tests%20passing-22c55e?style=flat-square&logo=angular&logoColor=white" alt="Angular Tests"/>
  &nbsp;
  <img src="https://img.shields.io/badge/Flutter-95%20tests%20passing-22c55e?style=flat-square&logo=flutter&logoColor=white" alt="Flutter Tests"/>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white"/>
  <img src="https://img.shields.io/badge/Solidity-363636?style=flat-square&logo=solidity&logoColor=white"/>
  <img src="https://img.shields.io/badge/Hardhat-FFF100?style=flat-square&logo=hardhat&logoColor=black"/>
  <img src="https://img.shields.io/badge/Angular-DD0031?style=flat-square&logo=angular&logoColor=white"/>
  <img src="https://img.shields.io/badge/Flutter-02569B?style=flat-square&logo=flutter&logoColor=white"/>
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=flat-square&logo=postgresql&logoColor=white"/>
  <img src="https://img.shields.io/badge/Ethereum-3C3C3D?style=flat-square&logo=ethereum&logoColor=white"/>
  <img src="https://img.shields.io/badge/Firebase-FFCA28?style=flat-square&logo=firebase&logoColor=black"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white"/>
</p>

<br/>

A full-stack decentralised application for the Malaysian automotive industry.<br/>
Smart contracts enforce tamper-proof service records and warranty state on a private Ethereum node.<br/>
A Flask REST API bridges the blockchain with an Angular web dashboard and a Flutter mobile app.

<br/>

<a href="https://vehiclechain.up.railway.app">
  <img src="https://img.shields.io/badge/%F0%9F%9A%80%20Open%20Live%20Demo-0369a1?style=for-the-badge" height="36" alt="Open Live Demo"/>
</a>

</div>

---

## 📑 Table of Contents

- [Live Demo](#-live-demo)
- [Architecture](#️-architecture)
- [Technology Stack](#-technology-stack)
- [User Roles & Features](#-user-roles--features)
- [Smart Contracts](#-smart-contracts)
- [Database Models](#️-database-models)
- [Security](#-security)
- [Quick Start](#-quick-start-docker)
- [Running Tests](#-running-tests)
- [API Reference](#-api-reference)
- [Data Flows](#-data-flows)
- [Key Design Decisions](#-key-design-decisions)
- [Deployment](#-deployment)
- [License](#-license)

---

## 🌐 Live Demo

| Service | URL |
|:---|:---|
| Web App | https://vehiclechain.up.railway.app |
| Backend API | https://blockchain-vehicle-service-production.up.railway.app |
| Health Check | https://blockchain-vehicle-service-production.up.railway.app/api/health |

> **Demo credentials** — run `python init_db.py --seed` locally to generate demo accounts, or contact the author.

---

## 🏗️ Architecture

```
                        Internet
                            │
              ┌─────────────▼──────────────┐
              │         Cloudflare         │  HTTPS, DNS
              └─────────────┬──────────────┘
                            │
          ┌─────────────────▼──────────────────────┐
          │            Railway Hosting             │
          │                                        │
          │  ┌──────────────────────────────────┐  │
          │  │   frontend (Nginx + Angular)     │  │  vehiclechain.up.railway.app
          │  │   Manufacturer / SC dashboards   │  │
          │  └──────────────────────────────────┘  │
          │                                        │
          │  ┌──────────────────────────────────┐  │
          │  │   backend (Flask + Gunicorn)     │  │  blockchain-vehicle-service-production.up.railway.app
          │  │   REST API · JWT Auth · Web3.py  │  │
          │  └──────────────────────────────────┘  │
          │                                        │
          │  ┌──────────────┐ ┌─────────────────┐  │
          │  │  PostgreSQL  │ │     Ganache     │  │
          │  │  (managed)   │ │  (private EVM)  │  │
          │  └──────────────┘ └─────────────────┘  │
          └────────────────────────────────────────┘

          ┌──────────────────────────────────────────┐
          │   Flutter Owner Mobile App (Android APK) │
          │   Direct REST API calls to backend       │
          └──────────────────────────────────────────┘

          ┌──────────────────────────────────────────┐
          │   Solidity Smart Contracts (Hardhat)     │
          │   VehicleRegistry · ServiceLog           │
          │   WarrantyTracker                        │
          │   Deployed to Ganache (Railway)          │
          └──────────────────────────────────────────┘
```

> **Design principle:** The blockchain is the immutable source of truth for ownership, service record finality, and warranty state. PostgreSQL stores human-readable metadata. Neither layer alone is sufficient — this is intentional for tamper-proof auditability.

---

## 🔧 Technology Stack

| Layer | Technology | Version |
|:---|:---|:---|
| Smart contracts | Solidity + Hardhat | 0.8.28 / 2.28 |
| Contract library | OpenZeppelin Contracts | 5.x |
| Backend | Python + Flask | 3.11 / 3.0 |
| WSGI server | Gunicorn | 21.2 |
| ORM | SQLAlchemy + Flask-SQLAlchemy | 2.0 / 3.1 |
| Blockchain client | Web3.py | 6.11 |
| Authentication | PyJWT + bcrypt | 2.8 / 4.1 |
| Wallet encryption | Cryptography (Fernet) | 41.x |
| Rate limiting | Flask-Limiter | 3.5 |
| Email | Resend HTTP API | 2.4 |
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

## 👥 User Roles & Features

### 🏭 Manufacturer
- Register vehicles on-chain (VIN, owner email, warranty period, make/model/year)
- Pre-register vehicles without an owner — owner claims later via mobile app
- Approve or deny warranty claims submitted by vehicle owners
- Resolve disputed service records (approve, reject, or request modification)
- Issue safety recalls with optional VIN range to scope to a specific production batch
- View the full brand fleet with health analytics, charts, and fleet score
- Manage and activate/suspend authorised service centres
- Export full fleet audit report as PDF

### 🔧 Service Centre
- Submit service records — SHA-256 hash of metadata anchored on-chain
- View pending and finalized service history for any VIN
- Submit dispute rebuttals and escalate to manufacturer priority review
- Participate in threaded dispute chat with owners
- Mark recall service as completed for a specific VIN

### 📱 Owner *(Flutter Mobile App)*
- Biometric login (TouchID / FaceID) after first successful login
- Claim ownership of a pre-registered vehicle using its VIN
- View owned vehicles, warranty status, and expiry countdown
- Transfer vehicle ownership to another registered user
- Review pending service records — verify or dispute on-chain
- Submit warranty claims with photos
- View active safety recalls — shows affected VIN range and whether your specific VIN is affected
- Export vehicle service history as PDF

### 🌍 Public *(No Account Required)*
- Look up any VIN at the root URL (`/`) — registration status, warranty, full service history, and recall history
- Tamper badge shown on any record where the hash doesn't match the chain
- Mileage trend chart and QR code linking back to the vehicle page

---

## 📜 Smart Contracts

| Contract | Responsibility |
|:---|:---|
| `VehicleRegistry` | Register vehicles, track ownership, store finalized service hashes per VIN |
| `ServiceLog` | Two-stage service verification: submit → verify/dispute → resolve |
| `WarrantyTracker` | Warranty claim lifecycle: submit → approve/deny; on-chain warranty voiding |

### Role-Based Access Control (OpenZeppelin `AccessControl`)

| Role | Contract | Holder | Permissions |
|:---|:---|:---|:---|
| `DEFAULT_ADMIN_ROLE` | All 3 | Deployer EOA | Grant/revoke roles |
| `MANUFACTURER_ROLE` | VehicleRegistry | Manufacturer wallet | Register vehicles |
| `MANUFACTURER_ADMIN_ROLE` | ServiceLog + WarrantyTracker | Manufacturer wallet | Resolve disputes, approve/deny claims, void warranties |
| `SERVICE_CENTER_ROLE` | ServiceLog | SC wallet | Submit records; revoked on suspension |
| `OWNER_ROLE` | VehicleRegistry | Owner wallet | Verify/dispute services, submit warranty claims |
| `SERVICE_LOG_ROLE` | VehicleRegistry | ServiceLog contract | Internal: write finalized service hashes |

> `MANUFACTURER_ADMIN_ROLE` is intentionally **not** `DEFAULT_ADMIN_ROLE` — manufacturers cannot call `grantRole()` to escalate privileges.

---

## 🗄️ Database Models

| Model | Purpose |
|:---|:---|
| `User` | Accounts: role, blockchain address, brand, PDPA consent timestamp, lockout tracking |
| `VehicleVINMapping` | VIN ↔ keccak256 hash, owner address, make/model/year, `registration_status` |
| `ServiceMetadata` | Off-chain service record details (type, date, mileage, notes, photos, ECU modules) |
| `WarrantyClaimMetadata` | Off-chain claim details (issue description, photos, resolution) |
| `VehicleRecall` | Safety recalls: brand, title, optional `vin_range_start`/`vin_range_end` for batch scoping |
| `RecallVINService` | Tracks which VINs have been serviced under each recall |
| `AuthorizedSCLicense` | Pre-registered SSM licence numbers for authorised SC gating |
| `DisputeMessage` | Threaded dispute chat; `sender_id` is `SET NULL` on delete (audit history preserved) |
| `Notification` | Persistent in-app inbox — survives FCM downtime |
| `EthFundRequest` | SC ETH requests to manufacturer |
| `VehicleReclaimRequest` | Reclaim requests for `owner_deleted` vehicles |
| `AuditLog` | Security event trail: login, password changes, key actions with IP (90-day TTL) |
| `RefreshToken` | Hashed refresh tokens with revocation support |
| `DeviceToken` | FCM tokens per user/platform |

---

## 🔒 Security

| Control | Implementation |
|:---|:---|
| Authentication | JWT — 15-min access token + 30-day rotating refresh token, HttpOnly cookies |
| Password hashing | bcrypt, cost factor 12 |
| Private key storage | Fernet symmetric encryption at rest |
| Rate limiting | Flask-Limiter on all auth, upload, and notification-flood-risk endpoints |
| File upload validation | MIME magic byte check (prevents extension spoofing) |
| Admin endpoint | HMAC-SHA256 with 30-second time window (replay-resistant) |
| Account lockout | 5 failed attempts → 15-minute cooldown |
| On-chain suspension | SC suspension revokes `SERVICE_CENTER_ROLE` on-chain — SC cannot bypass Flask |
| On-chain warranty voiding | `voidWarranty()` in `WarrantyTracker` — enforced at contract level, not just API |
| Two-layer integrity check | DB hash recompute + on-chain hash comparison — detects both naive and sophisticated tampering |
| PDPA compliance | Data export (`GET /auth/data-export`) + full account deletion with role-specific cleanup |
| Email verification gate | All state-changing operations blocked for unverified accounts |
| Session inactivity | Angular auto-logout after 30 minutes idle (warning at 25 min) |

---

## 🚀 Quick Start (Docker)

### Prerequisites
- Docker Desktop installed and running

```powershell
# 1. Clone
git clone https://github.com/jhjh1214/blockchain-vehicle-service.git
cd blockchain-vehicle-service

# 2. Configure environment
cp .env.example .env
# Fill in: POSTGRES_PASSWORD, SECRET_KEY, JWT_SECRET_KEY, KEYSTORE_PASSWORD

# 3. Start all containers
docker compose up --build

# 4. Deploy smart contracts to local Ganache
cd smart-contracts
npx hardhat run scripts/deploy.js --network ganache

# 5. (Optional) Seed demo data
cd ../backend
python init_db.py --seed
```

| Container | Port | Description |
|:---|:---|:---|
| `frontend` | 80 | Nginx + Angular SPA |
| `backend` | 5000 | Flask + Gunicorn REST API |
| `db` | 5432 | PostgreSQL 16 |
| `ganache` | 8545 | Local Ethereum node |

---

## 🧪 Running Tests

**702 total tests across all layers**

| Layer | Count | Command |
|:---|:---:|:---|
| Backend (pytest) | 453 | `cd backend && pytest` |
| Smart Contracts (Hardhat) | 48 | `cd smart-contracts && npx hardhat test` |
| Angular (vitest) | 106 | `cd vehicle-service-frontend && npm test` |
| Flutter | 95 | `cd owner_mobile_app && flutter test` |

<details>
<summary>📋 Backend test file breakdown</summary>

| File | Coverage |
|:---|:---|
| `test_auth.py` | Registration, login, lockout, JWT, forgot/reset password, device tokens, profile |
| `test_vehicles.py` | Registration, RBAC, claim, transfer, privacy, service stats |
| `test_services.py` | Submit, verify, dispute, resolve, owner endpoints, dispute chat, filtering |
| `test_warranties.py` | Check warranty, submit claim, approve/deny, persistence |
| `test_sc_management.py` | Service centre listing, activation, brand isolation |
| `test_stats.py` | Dashboard stats, fleet stats, PDF export, public verify |
| `test_security.py` | HMAC admin, MIME validation, audit logging, PDPA, JWT type check, production hardening |
| `test_utils.py` | SHA-256, keccak256 hashing |
| `test_integration.py` | Full end-to-end workflow (requires Ganache) |

The blockchain adapters are fully mocked in `conftest.py` — Ganache is only required for `test_integration.py`.

</details>

---

## 📡 API Reference

> ~93 routes total across all blueprints. The tables below cover all feature-facing endpoints.

<details>
<summary>🔑 Auth — <code>/api/auth</code></summary>

| Method | Path | Auth | Description |
|:---|:---|:---|:---|
| POST | `/register` | None | Create account (MANUFACTURER / SERVICE_CENTER / OWNER) |
| POST | `/login` | None | Authenticate, receive access + refresh tokens |
| POST | `/logout` | JWT | Revoke refresh token |
| POST | `/logout-all` | JWT | Revoke all sessions (all devices) |
| GET | `/me` | JWT | Current user profile |
| PUT | `/profile` | JWT | Update name, phone, city, state, theme |
| POST | `/change-password` | JWT | Change password (revokes all sessions) |
| POST | `/forgot-password` | None | Send password reset email |
| POST | `/reset-password` | None | Reset password with token from email |
| GET | `/verify-email` | None | Verify email address from link |
| POST | `/resend-verification` | JWT | Resend verification email |
| POST | `/device-token` | JWT | Register FCM push notification token |
| GET | `/privacy-policy` | None | PDPA Privacy Policy (JSON) |
| GET | `/terms` | None | Terms of Service (JSON) |
| GET | `/data-export` | JWT | PDPA — export all personal data |
| DELETE | `/account` | JWT | PDPA — delete account and all personal data |

</details>

<details>
<summary>🚗 Vehicles — <code>/api/vehicle</code></summary>

| Method | Path | Auth | Description |
|:---|:---|:---|:---|
| POST | `/register` | MANUFACTURER | Register vehicle on-chain |
| POST | `/claim` | OWNER | Claim ownership of pending vehicle |
| POST | `/transfer` | OWNER | Transfer vehicle to another owner |
| GET | `/public/<vin>` | None | Public vehicle details + service history |
| GET | `/<vin>` | JWT | Full vehicle details |
| GET | `/owner/vehicles` | OWNER | List all vehicles owned by caller |
| GET | `/export/<vin>` | None | Download PDF service history report |
| GET | `/fleet` | MANUFACTURER | Paginated fleet list with health stats |
| GET | `/fleet-export` | MANUFACTURER | Fleet audit report as PDF |
| GET | `/stats` | MANUFACTURER | Aggregate stats |
| GET | `/dashboard-stats` | MANUFACTURER | Full dashboard KPIs + chart data (15s cache) |
| GET | `/activity-feed` | MANUFACTURER | Recent registrations, claims, disputes |
| POST | `/reconcile` | MANUFACTURER | Two-layer integrity check — flag tampered records |
| POST | `/recall` | MANUFACTURER | Issue safety recall (optional VIN range) |
| GET | `/recalls` | MANUFACTURER / SC | List recalls by status |
| POST | `/recalls/<id>/close` | MANUFACTURER | Close a recall |
| POST | `/recalls/<id>/service` | SERVICE_CENTER | Mark recall service complete for a VIN |
| GET | `/recalls/check/<vin>` | None | Active recalls for a VIN with `vin_affected` flag |
| GET | `/recalls/owner` | OWNER | All active recalls relevant to owner's vehicles |
| POST | `/reclaim-request` | OWNER | Request reclaim of an `owner_deleted` vehicle |
| GET | `/reclaim-requests` | MANUFACTURER | List pending reclaim requests |
| POST | `/reclaim-request/<id>/approve` | MANUFACTURER | Approve reclaim |
| POST | `/reclaim-request/<id>/reject` | MANUFACTURER | Reject reclaim |

</details>

<details>
<summary>🔩 Services — <code>/api/service</code></summary>

| Method | Path | Auth | Description |
|:---|:---|:---|:---|
| POST | `/submit` | SERVICE_CENTER | Hash metadata and anchor on-chain |
| GET | `/pending/<vin>` | JWT | Pending (unverified) records |
| GET | `/history/<vin>` | JWT | Finalized records |
| POST | `/verify` | OWNER | Verify pending record → on-chain finalization |
| POST | `/dispute` | OWNER | Dispute pending record with reason |
| POST | `/resolve-dispute` | MANUFACTURER | Approve or reject disputed record |
| GET | `/owner/pending` | OWNER | All pending records across owned vehicles |
| GET | `/owner/history` | OWNER | All finalized records (filterable) |
| GET | `/center/pending` | SERVICE_CENTER | All pending records for the authenticated SC |
| GET | `/sc/my-stats` | SERVICE_CENTER | SC dispute rate, submission count, ETH balance |
| POST | `/dispute-response` | SERVICE_CENTER | Submit rebuttal notes on a disputed record |
| POST | `/escalate-dispute` | SERVICE_CENTER | Escalate to manufacturer priority review |
| GET | `/dispute-messages/<vin>/<idx>` | JWT | Dispute chat thread |
| POST | `/dispute-messages` | JWT | Post message in dispute chat |
| POST | `/void-request` | SERVICE_CENTER | Submit warranty void request |
| GET | `/void-requests/manufacturer` | MANUFACTURER | List void requests for own brand |
| GET | `/void-requests/owner` | OWNER | List void requests for own vehicles |
| POST | `/void-requests/<id>/resolve` | MANUFACTURER | Approve or deny void request |
| POST | `/void-requests/<id>/dispute` | OWNER | Dispute a pending void request |
| POST | `/report` | OWNER / MANUFACTURER / SC | Report an independent workshop |

</details>

<details>
<summary>🛡️ Warranties — <code>/api/warranty</code></summary>

| Method | Path | Auth | Description |
|:---|:---|:---|:---|
| GET | `/check/<vin>` | JWT | Warranty validity, expiry, days remaining |
| GET | `/check-eligibility/<vin>` | JWT | Check claim eligibility |
| POST | `/submit-claim` | OWNER | Submit warranty claim |
| GET | `/claims/<vin>` | JWT | Claims for a VIN |
| POST | `/approve-claim` | MANUFACTURER | Approve claim on-chain |
| POST | `/deny-claim` | MANUFACTURER | Deny claim with reason |
| GET | `/owner/claims` | OWNER | All claims across owned vehicles |

</details>

<details>
<summary>🏢 SC Management — <code>/api/sc</code></summary>

| Method | Path | Auth | Description |
|:---|:---|:---|:---|
| GET | `/service-centers` | MANUFACTURER | List brand's service centres |
| GET | `/service-centers/<id>` | MANUFACTURER | SC detail + live ETH balance |
| POST | `/service-centers/<id>/activate` | MANUFACTURER | Activate a pending SC |
| POST | `/service-centers/<id>/suspend` | MANUFACTURER | Suspend SC (revokes on-chain role) |
| POST | `/service-centers/<id>/fund` | MANUFACTURER | Transfer ETH to SC |
| POST | `/fund-all` | MANUFACTURER | Fund all active SCs |
| POST | `/eth-request` | SERVICE_CENTER | Request ETH from manufacturer |
| GET | `/manufacturer/eth-requests` | MANUFACTURER | List pending ETH requests |
| GET | `/authorized-licenses` | MANUFACTURER | List pre-registered SSM numbers |
| POST | `/authorized-licenses` | MANUFACTURER | Add authorised SSM number |
| DELETE | `/authorized-licenses/<id>` | MANUFACTURER | Remove authorised SSM number |

</details>

<details>
<summary>🔔 Notifications — <code>/api/notifications</code></summary>

| Method | Path | Auth | Description |
|:---|:---|:---|:---|
| GET | `/` | JWT | List notifications (unread first) |
| GET | `/count` | JWT | Unread count (for badge polling) |
| POST | `/<id>/read` | JWT | Mark one as read |
| POST | `/read-all` | JWT | Mark all as read |

</details>

---

## 🔄 Data Flows

<details>
<summary>Service Record Lifecycle</summary>

```
1. Service Centre → POST /api/service/submit
   Backend hashes metadata (SHA-256, key-sorted JSON)
   Metadata saved to PostgreSQL
   Hash submitted on-chain → ServiceLog.submitService(vinHash, metadataHash)
   Status: PENDING on-chain

2. Owner → POST /api/service/owner/verify
   Backend calls ServiceLog.verifyService(vinHash, metadataHash)
   Contract finds record by metadataHash (swap-and-pop safe)
   Contract calls VehicleRegistry.addServiceHash(vinHash, metadataHash)
   Status: FINALIZED — permanent on-chain history

3. Owner → POST /api/service/owner/dispute
   Backend calls ServiceLog.disputeService(vinHash, metadataHash, reason)
   Status: DISPUTED on-chain

4. Manufacturer → POST /api/service/resolve-dispute
   Backend calls ServiceLog.resolveDispute(vinHash, metadataHash, decision, resolutionHash)
   APPROVE → finalized + added to VehicleRegistry.serviceHashes
   REJECT  → removed from pending array
```

</details>

<details>
<summary>Vehicle Claim Lifecycle</summary>

```
1. Manufacturer → POST /api/vehicle/register (no owner_email)
   Vehicle registered on-chain with manufacturer as temporary owner
   registration_status = 'pending' in PostgreSQL

2. Owner → POST /api/vehicle/claim (vin)
   Deployer executes adminTransferOwnership on-chain
   Owner address set as new owner on-chain
   registration_status = 'active' in PostgreSQL
```

</details>

---

## 💡 Key Design Decisions

**Dual storage model** — Every on-chain record has a linked PostgreSQL row. The blockchain stores hashes; the DB stores full metadata. Tampering with DB metadata is detectable by recomputing and comparing hashes via `POST /vehicle/reconcile`.

**Metadata-hash-based record lookup** — `ServiceLog` identifies records by their SHA-256 `metadataHash`, not array indices. This eliminates the index-shifting race condition that swap-and-pop removal would otherwise cause.

**Blockchain-first ordering** — All critical operations hit the blockchain before writing to PostgreSQL. If the chain transaction fails, no DB record is created.

**On-chain role revocation** — SC suspension calls `revokeRole(SERVICE_CENTER_ROLE)` on-chain. A suspended SC cannot bypass Flask by calling the contract directly with their private key.

**Owner ETH subsidy** — Owners register with 0 ETH. `ensure_owner_eth()` silently tops up their wallet from the deployer before any blockchain write. Completely transparent to the user.

**PDPA compliance** — Data export and full account deletion are fully implemented, with role-specific cleanup chains (OWNER → marks vehicles `owner_deleted`; SC → escalates disputes; MANUFACTURER → closes recalls).

---

## 🚢 Deployment

<details>
<summary>Required backend environment variables</summary>

```env
# Database
DATABASE_URL=postgresql://...

# Flask
FLASK_ENV=production
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
JWT_SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
KEYSTORE_PASSWORD=<python -c "import secrets; print(secrets.token_hex(32))">
ADMIN_SECRET=<python -c "import secrets; print(secrets.token_hex(32))">

# Blockchain
GANACHE_URL=<Ganache JSON-RPC endpoint>
CHAIN_ID=1337
VEHICLE_REGISTRY_ADDRESS=<from deploy.js output>
SERVICE_LOG_ADDRESS=<from deploy.js output>
WARRANTY_TRACKER_ADDRESS=<from deploy.js output>
DEPLOYER_ADDRESS=<from deploy.js output>
DEPLOYER_PRIVATE_KEY=<store in Railway secrets only>

# CORS
CORS_ORIGINS=https://your-frontend.up.railway.app
FRONTEND_URL=https://your-frontend.up.railway.app
USE_HTTPS=true

# Email (Resend)
RESEND_API_KEY=<from resend.com>
MAIL_DEFAULT_SENDER=VehicleChain <noreply@yourdomain.com>

# Misc
TRUSTED_PROXY_IPS=<railway-proxy-ip>
ADMIN_CONTACT_EMAIL=<your email>
```

</details>

<details>
<summary>Project structure</summary>

```
blockchain-vehicle-service/
├── backend/                        # Flask REST API
│   ├── api/                        # Route blueprints
│   │   ├── auth.py                 # Auth, forgot/reset password, device tokens, PDPA
│   │   ├── vehicles.py             # Vehicle CRUD, recalls, reclaim, PDF export
│   │   ├── services.py             # Service lifecycle, dispute chat, void requests
│   │   ├── warranties.py           # Warranty claims
│   │   ├── uploads.py              # File uploads (MIME validated, rate limited)
│   │   ├── sc_management.py        # Service centre management
│   │   ├── notifications.py        # Notification inbox
│   │   ├── admin.py                # Admin reset (HMAC-protected)
│   │   └── middleware.py           # @token_required, @role_required
│   ├── blockchain/
│   │   ├── client.py               # Web3 HTTPProvider singleton
│   │   ├── keystore.py             # Fernet-encrypted private key store
│   │   ├── utils.py                # sha256_hash(), keccak256_hash(), vin_to_hex()
│   │   └── adapters/               # Contract wrapper classes
│   ├── core/                       # Business logic (no Flask imports)
│   │   ├── auth_service.py         # Register, login, bcrypt, JWT
│   │   ├── audit.py                # Audit event logger
│   │   ├── scheduler.py            # APScheduler — warranty reminders, log purge
│   │   ├── notifications.py        # FCM + DB inbox sender
│   │   ├── vehicle_service.py
│   │   ├── service_log_service.py
│   │   └── warranty_service.py
│   ├── db/models.py                # All SQLAlchemy models
│   ├── tests/                      # 453 passing pytest tests
│   ├── app.py                      # Flask app factory + startup migrations
│   └── requirements.txt
│
├── smart-contracts/                # Hardhat project
│   ├── contracts/
│   │   ├── VehicleRegistry.sol
│   │   ├── ServiceLog.sol
│   │   └── WarrantyTracker.sol
│   ├── scripts/deploy.js           # Deploys all contracts + grants roles
│   ├── test/test_contracts.js      # 48 Hardhat/Chai tests
│   └── hardhat.config.js
│
├── vehicle-service-frontend/       # Angular 21 web application
│   ├── src/app/
│   │   ├── core/                   # Guards, interceptors, services
│   │   ├── features/
│   │   │   ├── auth/               # Login, register, forgot/reset password
│   │   │   ├── manufacturer/       # Fleet, vehicles, warranty claims, disputes
│   │   │   ├── dealer/             # Service submission, pending records, VIN lookup
│   │   │   └── public/             # Public VIN verify page (home route)
│   │   └── shared/shell/           # Role shells with inactivity timeout
│   └── Dockerfile                  # Node 20 build + Nginx
│
├── owner_mobile_app/               # Flutter owner mobile application
│   └── lib/
│       ├── features/
│       │   ├── auth/               # Login (biometric), Register, ForgotPassword
│       │   ├── vehicles/           # Vehicle list, detail, claim
│       │   ├── services/           # Pending services, history, dispute chat
│       │   ├── warranties/         # Warranty claims, submit claim
│       │   ├── notifications/      # Notification inbox
│       │   └── profile/            # Profile, change password
│       └── router/                 # GoRouter with auth guard
│
├── docker-compose.yml
├── .env.example
└── setup.ps1                       # Windows automated local setup script
```

</details>

To redeploy after a Ganache restart (wipes chain state):

```powershell
cd smart-contracts
npx hardhat run scripts/deploy.js --network railway
```

Contract addresses are deterministic — same mnemonic produces the same addresses every time.

---

## 📄 License

Copyright © 2026 **Lim Jun Hong**

This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International License** — see the [LICENSE](LICENSE) file for details.

You may view and share this code with attribution, but **commercial use is prohibited** without explicit written permission from the author. The author reserves the right to release this project under different terms for commercial purposes.

---

<div align="center">
  <sub>Built as a Final Year Project (FYP) · Universiti · 2026</sub>
</div>
