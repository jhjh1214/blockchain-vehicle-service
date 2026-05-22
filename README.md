# Blockchain Vehicle Service System

A full-stack decentralised application for vehicle registration, service history, and warranty management. The system combines an Ethereum-based smart contract layer with a traditional Web2 backend so end users interact with a standard web interface while all critical records are anchored on-chain.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Angular Frontend                        │
│          (Manufacturer / Dealer / Owner dashboards)         │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST / JSON
┌─────────────────────────▼───────────────────────────────────┐
│                    Flask REST API                           │
│   Auth · Vehicle · Service · Warranty · Uploads            │
│                  JWT + Role-Based Access                    │
│                                                             │
│   ┌──────────────┐          ┌──────────────────────────┐   │
│   │  SQLite DB   │          │   Web3.py → Ganache EVM  │   │
│   │  (metadata,  │          │   (ownership, hashes,    │   │
│   │   users,     │          │    warranty state on     │   │
│   │   off-chain  │          │    the blockchain)       │   │
│   │   records)   │          └──────────────────────────┘   │
│   └──────────────┘                                         │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              Solidity Smart Contracts (Hardhat)             │
│   VehicleRegistry · ServiceLog · WarrantyTracker           │
│              OpenZeppelin AccessControl                     │
└─────────────────────────────────────────────────────────────┘
```

**Design principle:** The blockchain is the source of truth for ownership, warranty validity, service record finality, and claim status. SQLite holds human-readable metadata (service notes, photos, names). Neither layer alone is sufficient — this is intentional.

---

## Smart Contracts

| Contract | Responsibility |
|---|---|
| `VehicleRegistry` | Register vehicles, track ownership transfers, store SHA-256 service hashes per VIN |
| `ServiceLog` | Two-stage service verification (submit → verify/dispute → resolve), calls `addServiceHash` on finalization |
| `WarrantyTracker` | Reads warranty expiry from VehicleRegistry, manages claim lifecycle (submit → approve/deny) |

All contracts use OpenZeppelin `AccessControl` with the following roles:

| Role | Holder | Permissions |
|---|---|---|
| `DEFAULT_ADMIN_ROLE` | Deployer EOA | Grant/revoke all roles, resolve disputes, approve/deny warranty claims |
| `MANUFACTURER_ROLE` | Manufacturer account | Register vehicles |
| `SERVICE_LOG_ROLE` | ServiceLog contract address | Call `addServiceHash` on VehicleRegistry |
| `SERVICE_CENTER_ROLE` | Service centre account | Submit service records |
| `OWNER_ROLE` | Vehicle owner account | Verify/dispute services, submit warranty claims |

---

## Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Smart contracts | Solidity + Hardhat | 0.8.28 / 2.x |
| Contract library | OpenZeppelin Contracts | 5.x |
| Backend | Python + Flask | 3.10+ / 3.0 |
| ORM | SQLAlchemy + Flask-SQLAlchemy | 2.0 / 3.1 |
| Blockchain client | Web3.py | 6.11 |
| Auth | PyJWT + bcrypt | 2.8 / 4.1 |
| Encryption | Cryptography (Fernet) | 41.x |
| Database | SQLite | (bundled with Python) |
| Frontend | Angular (standalone) | 21.x |
| Local blockchain | Ganache | 7.x |
| Node runtime | Node.js | 18+ |
| Package manager | npm | 9+ |
| Backend tests | pytest + pytest-flask | 8.3 / 1.3 |
| Contract tests | Hardhat + Chai + Ethers.js | — |

---

## User Roles & Features

### Manufacturer
- Register new vehicles (VIN, owner, warranty period, make/model/year)
- Approve or deny warranty claims submitted by vehicle owners
- Resolve disputed service records (approve or reject with resolution notes)
- View all vehicles registered under their account

### Service Centre (Dealer)
- Submit service records for a vehicle (off-chain metadata hashed to SHA-256, hash submitted on-chain)
- View pending and finalized service history for any VIN
- Look up vehicle details and warranty status by VIN

### Owner
- View their registered vehicles and warranty status
- Review pending service records submitted by service centres
- Verify a service record (triggers on-chain finalization)
- Dispute a service record with a reason (queues for manufacturer resolution)
- Submit warranty claims with issue description and photos
- Track warranty claim status (pending / approved / denied)

---

## Prerequisites

Install the following on a **fresh machine** before anything else.

### 1. Python 3.11 or 3.12 (recommended)

> Python 3.13+ is not recommended — some web3 C extensions lack pre-built wheels and require a C compiler.

Download from **https://www.python.org/downloads/** — choose **3.11.x** or **3.12.x**.

During installation on Windows: check **"Add Python to PATH"**.

Verify:
```powershell
python --version
# Python 3.11.x  or  Python 3.12.x
```

### 2. Node.js 18 or later

Download from **https://nodejs.org/** (LTS recommended).

Verify:
```powershell
node --version   # v18.x or higher
npm --version    # 9.x or higher
```

### 3. Ganache (local Ethereum node)

```powershell
npm install -g ganache
ganache --version
```

### 4. Angular CLI (optional — `npx ng` works without a global install)

```powershell
npm install -g @angular/cli
ng version
```

---

## Project Structure

```
blockchain-vehicle-service/
├── backend/                     # Flask REST API
│   ├── api/                     # Route blueprints (auth, vehicles, services, warranties, uploads)
│   ├── blockchain/              # Web3.py adapters, keystore, event monitor
│   │   └── adapters/            # One adapter per smart contract
│   ├── core/                    # Business logic services
│   ├── db/
│   │   ├── models.py            # SQLAlchemy models
│   │   └── repositories/        # DB query helpers
│   ├── keystore/                # Fernet-encrypted Ethereum private keys
│   ├── tests/                   # pytest test suite
│   ├── app.py                   # Flask application entry point
│   ├── config.py                # Configuration from .env
│   ├── conftest.py              # pytest fixtures (mocked blockchain)
│   ├── init_db.py               # One-time database initialisation
│   ├── pytest.ini               # pytest configuration
│   └── requirements.txt
│
├── smart-contracts/             # Hardhat project
│   ├── contracts/
│   │   ├── VehicleRegistry.sol
│   │   ├── ServiceLog.sol
│   │   └── WarrantyTracker.sol
│   ├── scripts/
│   │   └── deploy.js            # Deployment script (also grants SERVICE_LOG_ROLE)
│   ├── test/
│   │   └── test_contracts.js    # Hardhat/Chai test suite (20+ cases)
│   └── hardhat.config.js        # Network: ganache @ localhost:8545, chainId 1337
│
├── vehicle-service-frontend/    # Angular application
│   └── src/app/
│       ├── core/                # Guards, interceptors, models, HTTP services
│       ├── features/
│       │   ├── auth/            # Login / register pages
│       │   ├── dealer/          # Service centre dashboards
│       │   └── manufacturer/    # Manufacturer dashboards (including dispute resolution)
│       └── shared/shell/        # Role-specific navigation shells
│
└── setup.ps1                    # Automated setup script (Windows PowerShell)
```

---

## Setup on a New Machine

### Automated (Windows — recommended)

From the project root (`blockchain-vehicle-service/`):

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup.ps1
```

The script will:
1. Check Python and Node.js versions
2. Create `backend/venv` and install all Python dependencies
3. Copy `.env.example` → `.env` if no `.env` exists
4. `npm install` and `npx hardhat compile` in `smart-contracts/`
5. `npm install` in `vehicle-service-frontend/`
6. Copy compiled ABI files into `backend/abis/`
7. Initialise the SQLite database

Then continue from **step 3** of the manual guide below.

---

### Manual (all platforms)

#### Step 1 — Backend Python environment

```bash
cd backend
python3.11 -m venv venv          # use python3.12 if 3.11 is unavailable

# Windows
.\venv\Scripts\Activate.ps1
# macOS / Linux
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 2 — Smart contract dependencies

```bash
cd ../smart-contracts
npm install
npx hardhat compile
```

Compiled ABIs land in `artifacts/contracts/`. Copy them to the backend:

```powershell
# Windows PowerShell — run from smart-contracts/
Copy-Item "artifacts\contracts\VehicleRegistry.sol\VehicleRegistry.json" "..\backend\abis\"
Copy-Item "artifacts\contracts\ServiceLog.sol\ServiceLog.json"           "..\backend\abis\"
Copy-Item "artifacts\contracts\WarrantyTracker.sol\WarrantyTracker.json" "..\backend\abis\"
```

#### Step 3 — Frontend dependencies

```bash
cd ../vehicle-service-frontend
npm install
```

#### Step 4 — Start Ganache

Open a dedicated terminal and keep it running:

```bash
ganache --port 8545 --chainId 1337 --deterministic
```

> `--deterministic` gives the same 10 test accounts every time, which is useful during development.

#### Step 5 — Deploy contracts

In a new terminal (from `smart-contracts/`):

```bash
npx hardhat run scripts/deploy.js --network ganache
```

The script prints three contract addresses, for example:

```
VehicleRegistry deployed to: 0xABC...
ServiceLog deployed to:      0xDEF...
WarrantyTracker deployed to: 0x123...
SERVICE_LOG_ROLE granted to ServiceLog
```

#### Step 6 — Configure the backend

Edit `backend/.env` with the printed addresses:

```env
GANACHE_URL=http://127.0.0.1:8545

VEHICLE_REGISTRY_ADDRESS=0xABC...
SERVICE_LOG_ADDRESS=0xDEF...
WARRANTY_TRACKER_ADDRESS=0x123...

DEPLOYER_ADDRESS=<Ganache account 0>
MANUFACTURER_ADDRESS=<Ganache account 1>
SERVICE_CENTER_ADDRESS=<Ganache account 2>
OWNER1_ADDRESS=<Ganache account 3>
OWNER2_ADDRESS=<Ganache account 4>

SECRET_KEY=change-this-in-production
DATABASE_URI=sqlite:///vehicle_service.db
KEYSTORE_DIR=keystore
KEYSTORE_ENCRYPTION_KEY=change-this-in-production
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216
```

When using `--deterministic`, Ganache always uses the same HD wallet. The first account (index 0) is the deployer/admin.

#### Step 7 — Initialise the database

```bash
cd backend
python init_db.py
```

#### Step 8 — Start the backend

```bash
# backend/ with venv active
python app.py
```

API is available at `http://localhost:5000`.

#### Step 9 — Start the frontend

```bash
cd vehicle-service-frontend
npx ng serve
```

Application is available at `http://localhost:4200`.

---

## Running Tests

### Smart contract tests (no Ganache required — Hardhat in-memory EVM)

```bash
cd smart-contracts
npx hardhat test
```

Covers: vehicle registration, duplicate VIN rejection, role-based access control, service submission and two-stage verification, dispute approve/reject, warranty claim lifecycle, OWNER_ROLE multi-vehicle retention.

Expected output: **20+ passing**

---

### Backend unit and API tests (no Ganache required — blockchain is mocked)

```bash
cd backend
# activate venv first
pytest
```

The default `pytest.ini` configuration excludes `e2e` tests and runs everything else with `-v --tb=short`.

Covers:
- `test_utils.py` — SHA-256 and keccak256 hashing (determinism, order-independence, format)
- `test_auth.py` — Register, login, /me endpoint, duplicate and invalid-role rejection
- `test_vehicles.py` — Vehicle registration RBAC, get vehicle, my-vehicles
- `test_services.py` — Submit, pending, history, verify, dispute, resolve (valid/invalid decisions), owner endpoints
- `test_warranties.py` — Check warranty, submit-claim (OWNER-only), approve/deny (MANUFACTURER-only), owner/claims

Expected output: **all passing**

Run with coverage report:

```bash
pytest --cov=. --cov-report=term-missing
```

---

### End-to-end integration tests (requires running Ganache + deployed contracts + running backend)

Ensure Ganache is running, contracts are deployed, `.env` is updated, and `python app.py` is running on port 5000.

```bash
cd backend
pytest -m e2e -v
```

Covers:
- `test_full_workflow` — 10-step flow: register 3 users → register vehicle → submit service → verify on-chain → submit warranty claim → approve claim
- `test_dispute_workflow` — Register parties → submit service → dispute → manufacturer resolves → record finalized

---

### Frontend type check (no backend required)

```bash
cd vehicle-service-frontend
npx ng build --configuration development
```

A clean build (no errors) confirms all TypeScript types and Angular templates are valid.

---

## API Reference (Summary)

All endpoints are prefixed `/api`.

### Authentication — `/api/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/register` | None | Register user (role: MANUFACTURER / SERVICE_CENTER / OWNER) |
| POST | `/login` | None | Login, returns JWT |
| GET | `/me` | JWT | Current user profile |

### Vehicles — `/api/vehicle`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/register` | MANUFACTURER | Register vehicle, write to chain |
| GET | `/<vin>` | JWT | Vehicle details + warranty status |
| GET | `/my-vehicles` | OWNER | List owner's vehicles |

### Services — `/api/service`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/submit` | SERVICE_CENTER | Hash metadata, submit service record on-chain |
| GET | `/pending/<vin>` | JWT | Pending (unverified) service records |
| GET | `/history/<vin>` | JWT | Finalized service records |
| POST | `/verify` | OWNER | Verify service → on-chain finalization |
| POST | `/dispute` | OWNER | Flag service record with reason |
| POST | `/resolve-dispute` | MANUFACTURER | Approve (1) or reject (2) disputed record |
| GET | `/owner/pending` | OWNER | All pending records across owner's vehicles |
| GET | `/owner/history` | OWNER | All finalized records across owner's vehicles |
| POST | `/owner/verify` | OWNER | Alias for `/verify` |
| POST | `/owner/dispute` | OWNER | Alias for `/dispute` |

### Warranties — `/api/warranty`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/check/<vin>` | JWT | Warranty validity and expiry from chain |
| POST | `/submit-claim` | OWNER | Hash claim details, submit claim on-chain |
| GET | `/claims/<vin>` | JWT | All claims for a VIN |
| POST | `/approve-claim` | MANUFACTURER | Approve pending claim on-chain |
| POST | `/deny-claim` | MANUFACTURER | Deny claim with reason hash on-chain |
| GET | `/owner/claims` | OWNER | All claims across owner's vehicles |

---

## Hashing

| Purpose | Algorithm | Where |
|---|---|---|
| Service metadata fingerprint | SHA-256 (deterministic, key-sorted JSON) | `blockchain/utils.py` |
| Warranty claim fingerprint | SHA-256 | `blockchain/utils.py` |
| VIN → on-chain key | keccak256 | `blockchain/utils.py` |
| Dispute resolution notes | SHA-256 | `blockchain/utils.py` |

All hashes are stored on-chain as `bytes32`. The raw metadata lives in SQLite and can be independently verified by recomputing its hash.

---

## Common Issues

**`lru-dict` or `ckzg` build error on Windows**
These are C extensions. Either:
- Use Python 3.11 or 3.12 (pre-built wheels available), or
- Install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and select "Desktop development with C++"

**`.\venv\Scripts\Activate.ps1` opens Notepad**
PowerShell execution policy is blocking scripts. Run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**`AccessControlUnauthorizedAccount` on service hash write**
The `SERVICE_LOG_ROLE` was not granted to the ServiceLog contract address. Re-run `deploy.js` — it handles this automatically.

**Stale pending record indices after dispute resolution**
Solidity's `_removePendingService` uses swap-and-pop, so indices shift after any removal. The frontend always re-fetches from the chain after each resolution action rather than mutating local state.

---

## Deployment Notes (Production)

- Replace SQLite with PostgreSQL (`DATABASE_URI=postgresql://...`)
- Replace Ganache with a real network (Ethereum mainnet, Polygon, or a private chain)
- Update `hardhat.config.js` with the target network RPC URL and funded deployer key
- Rotate `SECRET_KEY` and `KEYSTORE_ENCRYPTION_KEY` to strong random values
- Serve Angular build (`ng build --configuration production`) via Nginx or CDN
- Run Flask behind Gunicorn + Nginx, not the development server
- Store private keys in a proper secrets manager (AWS Secrets Manager, HashiCorp Vault)

---

---

# Developer Reference (AI / Fresh Session Context)

This section is a complete technical reference for continuing development in a new session without prior context. Read this fully before making any changes.

---

## Project Root

```
c:\Users\yying\Documents\Jh FYP\blockchain-vehicle-service\
```

All paths in this document are relative to this root. Never add an extra `blockchain-vehicle-service\` segment — the project was restructured from a double-nested layout and the correct root is the single-nested one above.

---

## Key File Map

### Backend

| File | Purpose |
|---|---|
| `backend/app.py` | Flask app factory, registers all blueprints, initialises DB and event monitor |
| `backend/config.py` | Loads all settings from `backend/.env` via python-dotenv |
| `backend/init_db.py` | Creates all SQLAlchemy tables; run once on a new machine |
| `backend/conftest.py` | pytest session fixtures — patches blockchain, provides `client`, `register_and_login`, `auth` helpers |
| `backend/pytest.ini` | Excludes `e2e` by default; sets `testpaths = tests`, `pythonpath = .` |
| `backend/api/auth.py` | `/api/auth` — register, login, /me |
| `backend/api/vehicles.py` | `/api/vehicle` — register vehicle, get by VIN, my-vehicles |
| `backend/api/services.py` | `/api/service` — submit, pending, history, verify, dispute, resolve-dispute, owner endpoints |
| `backend/api/warranties.py` | `/api/warranty` — check, submit-claim (OWNER only), approve/deny, owner/claims |
| `backend/api/middleware.py` | `@token_required` and `@role_required(role)` decorators used across all protected routes |
| `backend/blockchain/client.py` | Creates the Web3 HTTPProvider pointed at Ganache; singleton |
| `backend/blockchain/keystore.py` | Fernet-encrypted store of Ethereum private keys keyed by role |
| `backend/blockchain/utils.py` | `sha256_hash(data_dict)` and `keccak256_hash(text)` — all hashing goes through here |
| `backend/blockchain/event_monitor.py` | Background thread that listens for on-chain events; patched to a no-op in tests |
| `backend/blockchain/adapters/vehicle_registry.py` | Python wrapper around VehicleRegistry contract calls |
| `backend/blockchain/adapters/service_log.py` | Python wrapper around ServiceLog contract calls |
| `backend/blockchain/adapters/warranty_tracker.py` | Python wrapper around WarrantyTracker contract calls |
| `backend/core/auth_service.py` | Register/login business logic, bcrypt password hashing, JWT issuance |
| `backend/core/vehicle_service.py` | Vehicle registration and lookup, including warranty status from chain |
| `backend/core/service_log_service.py` | Service submission, pending/finalized queries, owner aggregation across all VINs |
| `backend/core/warranty_service.py` | Warranty check, claim submission/approval/denial, owner claim aggregation |
| `backend/db/models.py` | SQLAlchemy models: `User`, `VehicleMapping`, `ServiceMetadata`, `WarrantyClaim` |
| `backend/db/repositories/users.py` | DB queries for User model |
| `backend/db/repositories/vehicles.py` | DB queries for VehicleMapping — find by VIN string or VIN hash |
| `backend/db/repositories/services.py` | DB queries for ServiceMetadata — find by metadata hash |
| `backend/db/repositories/warranties.py` | DB queries for WarrantyClaim |
| `backend/abis/` | Compiled ABI JSON files copied from Hardhat artifacts — must match deployed contracts |

### Smart Contracts

| File | Purpose |
|---|---|
| `smart-contracts/contracts/VehicleRegistry.sol` | Core registry — registerVehicle, transferOwnership, addServiceHash, getOwnedVehicles |
| `smart-contracts/contracts/ServiceLog.sol` | submitService, verifyService, disputeService, resolveDispute, getPendingServices, getFinalizedServices |
| `smart-contracts/contracts/WarrantyTracker.sol` | isWarrantyValid, submitClaim, approveClaim, denyClaim, getClaims |
| `smart-contracts/scripts/deploy.js` | Deploys all three contracts in order, grants SERVICE_LOG_ROLE to ServiceLog address, prints addresses |
| `smart-contracts/test/test_contracts.js` | Full Hardhat/Chai test suite — 20+ cases covering all contracts |
| `smart-contracts/hardhat.config.js` | Solidity 0.8.28, ganache network at localhost:8545 chainId 1337 |

### Frontend

| File/Folder | Purpose |
|---|---|
| `vehicle-service-frontend/src/app/app.routes.ts` | Root routes — lazy loads manufacturer and dealer shell routes |
| `vehicle-service-frontend/src/app/core/guards/auth-guard.ts` | Route guard — redirects to login if no JWT in localStorage |
| `vehicle-service-frontend/src/app/core/interceptors/auth-interceptor.ts` | Attaches `Authorization: Bearer <token>` to every HTTP request |
| `vehicle-service-frontend/src/app/core/services/auth.ts` | AuthService — login, register, logout, currentUser signal |
| `vehicle-service-frontend/src/app/core/services/vehicle.ts` | VehicleService — register, getVehicle, getMyVehicles |
| `vehicle-service-frontend/src/app/core/services/service.ts` | ServiceService — submit, pending, history, verify, dispute, resolveDispute |
| `vehicle-service-frontend/src/app/core/services/warranty.ts` | WarrantyService — check, submitClaim, approveClaim, denyClaim, ownerClaims |
| `vehicle-service-frontend/src/app/shared/shell/` | Manufacturer and dealer shell components with nav sidebar |
| `vehicle-service-frontend/src/app/features/auth/` | Login and register pages |
| `vehicle-service-frontend/src/app/features/manufacturer/` | Dashboard, vehicle registration, dispute resolution pages |
| `vehicle-service-frontend/src/app/features/dealer/` | Dashboard, vehicle lookup, pending records pages |

---

## Data Flow: Service Record Lifecycle

```
1. Service Centre submits via POST /api/service/submit
   → Backend hashes metadata as SHA-256 (key-sorted JSON)
   → Metadata saved to SQLite (ServiceMetadata table)
   → Hash submitted on-chain via ServiceLog.submitService(vinHash, metadataHash)
   → Record sits in pending queue on-chain (verified=false)

2. Owner verifies via POST /api/service/verify
   → Backend calls ServiceLog.verifyService(vinHash, recordIndex)
   → Contract moves record from pending to finalized (verified=true)
   → Contract calls VehicleRegistry.addServiceHash(vinHash, metadataHash)
   → Record now in permanent on-chain history

3. Owner disputes via POST /api/service/dispute
   → Backend calls ServiceLog.disputeService(vinHash, recordIndex, reason)
   → Record flagged as disputed=true, remains in pending queue

4. Manufacturer resolves via POST /api/service/resolve-dispute
   → decision=1 (approve): contract finalizes record, calls addServiceHash
   → decision=2 (reject): contract removes record from pending queue entirely
   → Resolution notes hashed and stored on-chain
```

## Data Flow: Warranty Claim Lifecycle

```
1. Owner submits via POST /api/warranty/submit-claim
   → Backend hashes claim details as SHA-256
   → Hash submitted on-chain via WarrantyTracker.submitClaim(vinHash, claimHash)
   → Claim status = PENDING (0)

2. Manufacturer approves via POST /api/warranty/approve-claim
   → Backend calls WarrantyTracker.approveClaim(vinHash, claimIndex)
   → Claim status = APPROVED (1)

3. Manufacturer denies via POST /api/warranty/deny-claim
   → Backend hashes denial reason
   → Calls WarrantyTracker.denyClaim(vinHash, claimIndex, reasonHash)
   → Claim status = DENIED (2)
```

---

## Critical Design Decisions

### 1. Swap-and-pop in ServiceLog pending queue

`ServiceLog._removePendingService` uses swap-and-pop (moves last element to deleted slot, pops last). This means **after any removal, all remaining record indices shift**. The frontend handles this by always re-fetching the full pending list from the chain after each verify/dispute/resolve action — it never mutates the local array by index. If you see wrong records being acted on, this is the likely cause.

### 2. SERVICE_LOG_ROLE must be granted to ServiceLog contract address

VehicleRegistry.addServiceHash is protected by `onlyRole(SERVICE_LOG_ROLE)`. This role must be granted to the ServiceLog **contract address** (not to any EOA). `deploy.js` handles this automatically. If you redeploy without running `deploy.js`, the grant will be missing and service verification will revert with `AccessControlUnauthorizedAccount`.

### 3. OWNER_ROLE retention across multiple vehicles

When an owner transfers a vehicle, the contract only revokes `OWNER_ROLE` if the owner has no remaining vehicles. This prevents losing access to other owned vehicles on a single transfer. The check in `VehicleRegistry.transferOwnership` is:
```solidity
if (ownedVINs[previousOwner].length == 0) {
    _revokeRole(OWNER_ROLE, previousOwner);
}
```

### 4. VIN storage — string on-chain is expensive

VINs are stored on-chain as `bytes32` keccak256 hashes. The human-readable VIN string is stored in SQLite (`VehicleMapping.vin`). The backend converts between them using `keccak256_hash(vin)` in `blockchain/utils.py`. Any lookup by VIN first converts to the hash before calling contract methods.

### 5. SHA-256 metadata fingerprinting

All service metadata and warranty claims are fingerprinted with SHA-256 before going on-chain. The hash function uses key-sorted JSON serialisation so field order in the request body never affects the hash:
```python
import hashlib, json
def sha256_hash(data: dict) -> str:
    serialised = json.dumps(data, sort_keys=True, default=str)
    return '0x' + hashlib.sha256(serialised.encode()).hexdigest()
```
To verify a record: fetch the metadata from SQLite and recompute its hash — it must match what is stored on-chain.

### 6. DisputeDecision enum only has APPROVE and REJECT

The `DisputeDecision` enum in `ServiceLog.sol` is `{ PENDING=0, APPROVE=1, REJECT=2 }`. A formerly present `MODIFY=3` was removed as dead code. The backend validates that `decision` is strictly 1 or 2 before calling the contract — 0 and anything above 2 return HTTP 400.

### 7. POST /api/warranty/submit-claim is OWNER-only

This endpoint uses `@role_required('OWNER')`, not just `@token_required`. Service centres and manufacturers receive HTTP 403. This was a security fix — the original implementation only checked for a valid JWT.

### 8. pytest mocks blockchain without Ganache

The test suite patches the blockchain adapter singleton methods directly after `create_app()` imports them. Web3.py does not make network calls at `HTTPProvider` or `Contract` object creation time — only when actual RPC methods are called. The event monitor thread is patched before `create_app()` to prevent it starting. This allows the full test suite to run with no Ganache node.

### 9. Unique blockchain addresses per test user

`conftest.py` uses `itertools.count(1)` with `_next_addr()` to generate a unique fake Ethereum address per registered user during tests. This prevents SQLAlchemy unique constraint violations on the `blockchain_address` column when multiple users are registered in a single test.

---

## Backend conftest.py Strategy

The session-scoped fixtures in `backend/conftest.py` work as follows:

```python
# 1. Patch event monitor BEFORE create_app() is called
with patch('blockchain.event_monitor.init_event_monitor'):
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})

# 2. After app creation, mock adapter singleton methods directly
from blockchain.adapters import vehicle_registry, service_log, warranty_tracker
vehicle_registry.register_vehicle = MagicMock(return_value={'tx_hash': '0xabc'})
# ... etc for every method used by the API routes

# 3. autouse fixture wipes all DB rows between tests
@pytest.fixture(autouse=True)
def clean_db(app):
    with app.app_context():
        db.session.query(User).delete()
        # ... delete all tables
        db.session.commit()
```

---

## Frontend Architecture

The Angular app uses standalone components throughout (no NgModules). Two shell layouts exist:
- `manufacturer-shell` — sidebar nav for Manufacturer role
- `dealer-shell` — sidebar nav for Dealer/Service Centre role

Route guards (`auth-guard.ts`) check for a JWT in `localStorage` and redirect to `/login` if absent. The auth interceptor automatically attaches the token to every HTTP call.

### Manufacturer pages
- `/manufacturer/dashboard` — summary cards, quick links
- `/manufacturer/register-vehicle` — register new vehicle on-chain
- `/manufacturer/dispute-resolution` — search VIN, view disputed service records, approve or reject inline

### Dealer pages
- `/dealer/dashboard` — summary cards
- `/dealer/vehicle-lookup` — search VIN, view vehicle info and service history
- `/dealer/pending-records` — list all pending service records, submit new service

### Key Angular service method signatures

```typescript
// service.ts
submitService(data: any): Observable<any>
getPendingServices(vin: string): Observable<any>
getServiceHistory(vin: string): Observable<any>
verifyService(vin: string, recordIndex: number): Observable<any>
disputeService(vin: string, recordIndex: number, reason: string): Observable<any>
resolveDispute(vin: string, recordIndex: number, decision: number, notes: string): Observable<any>

// warranty.ts
checkWarranty(vin: string): Observable<any>
submitClaim(vin: string, description: string, photos: string[]): Observable<any>
approveClaim(vin: string, claimIndex: number): Observable<any>
denyClaim(vin: string, claimIndex: number, reason: string): Observable<any>
getOwnerClaims(): Observable<any>
```

---

## Known Completed Work (do not redo)

- `VehicleRegistry.sol` — `addServiceHash` protected with `onlyRole(SERVICE_LOG_ROLE)` ✓
- `VehicleRegistry.sol` — `transferOwnership` only revokes OWNER_ROLE when owner has no remaining vehicles ✓
- `ServiceLog.sol` — `DisputeDecision.MODIFY` removed ✓
- `deploy.js` — grants `SERVICE_LOG_ROLE` to ServiceLog contract address post-deploy ✓
- `backend/api/warranties.py` — `submit-claim` changed from `@token_required` to `@role_required('OWNER')` ✓
- `backend/api/warranties.py` — `GET /owner/claims` endpoint added ✓
- `backend/api/services.py` — `resolve-dispute` validates and casts decision to int, rejects 0 and >2 ✓
- `backend/api/services.py` — `GET /owner/history` endpoint added ✓
- `backend/core/service_log_service.py` — `get_owner_finalized_services()` added ✓
- `backend/core/warranty_service.py` — `get_owner_claims()` added ✓
- `backend/core/service_log_service.py` — `get_owner_pending_services()` includes `photos` field ✓
- `vehicle-service-frontend/src/app/core/services/service.ts` — `resolveDispute()` uses `decision: number` not `string` ✓
- `vehicle-service-frontend/.../dispute-resolution/` — new manufacturer component (search VIN, view disputes, inline resolve form) ✓
- `vehicle-service-frontend/.../manufacturer-shell.html` — Dispute Resolution nav link added ✓
- `vehicle-service-frontend/src/app/app.routes.ts` — dispute-resolution route registered ✓
- `vehicle-service-frontend/.../manufacturer/dashboard` — dispute resolution shortcut card added ✓
- `backend/tests/` — full pytest suite added (test_auth, test_vehicles, test_services, test_warranties, test_utils, test_integration) ✓
- `backend/conftest.py` — session-scoped mocked fixtures, unique address generator ✓
- `backend/pytest.ini` — configured with e2e marker exclusion ✓
- `smart-contracts/test/test_contracts.js` — full rewrite with ethers v6 syntax, 20+ test cases ✓
- Frontend TypeScript build errors fixed — `record.metadata?.mileage` optional chain used consistently in ternary true-branch across `pending-records.html`, `vehicle-lookup.html`, `dispute-resolution.html` ✓
- Frontend build warning fixed — `record.metadata_hash.slice()` no longer uses unnecessary `?.` ✓

---

## What Remains / Potential Next Steps

- Run `pytest` on the laptop after setting up the Python venv to confirm all unit/API tests pass
- Run `npx hardhat test` to confirm smart contract tests pass
- Deploy to Ganache on the laptop and run `pytest -m e2e` for full end-to-end validation
- Owner dashboard pages (view my vehicles, warranty status, verify/dispute services, claim history) — the backend endpoints exist but the frontend owner-facing pages may not be fully built out
- File upload integration — `backend/api/uploads.py` and `backend/core/upload_service.py` exist but the photo upload flow in the frontend may need wiring
- Production hardening — swap SQLite for PostgreSQL, Ganache for a real network, dev server for Gunicorn+Nginx
