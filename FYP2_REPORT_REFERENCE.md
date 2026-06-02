# VehicleChain — FYP2 Report Reference

This document is the single source of truth for writing the FYP2 report in a separate Claude chat.
Refer to it for all technical claims, workflows, endpoints, and framing decisions.

---

## 1. System Overview

**VehicleChain** is a blockchain-backed vehicle service management platform built as a Final Year Project.
It targets Malaysia's automotive industry and demonstrates how blockchain's immutability can be used to
create tamper-proof vehicle service histories, protect consumers from odometer fraud and fake servicing,
and give manufacturers transparent oversight of their service centre network.

**Stack:**
- Backend: Python / Flask (Blueprint architecture), PostgreSQL (SQLAlchemy ORM), deployed on Railway
- Blockchain node: **Ganache** (Truffle Ganache 7.x) — the actual running EVM that processes transactions; hosted on Railway in production, runs locally via Docker for development
- Smart contract toolchain: **Hardhat** — used only for compilation (`npx hardhat compile`), testing (`npx hardhat test`), and deployment scripts (`npx hardhat run scripts/deploy.js --network ganache`). Hardhat is NOT the node; Ganache is the node. The `hardhat.config.js` defines `ganache` and `railway` networks pointing to Ganache instances.
- Blockchain client (Python): web3.py connecting to Ganache via `GANACHE_URL` env var (JSON-RPC)
- Solidity: OpenZeppelin AccessControl, compiled with Hardhat, deployed to Ganache
- Web frontend: Angular (standalone components, SSR-disabled, HttpOnly cookie auth)
- Mobile app: Flutter (GoRouter, Provider, FCM, flutter_secure_storage)
- Email: Resend API
- Push: Firebase Cloud Messaging (FCM)
- PDF export: ReportLab

**IMPORTANT for report writing:** Always say "Ganache" when referring to the blockchain node/network. "Hardhat" refers only to the development toolchain. The Flask backend config variable is called `GANACHE_URL`. Do not say "Hardhat node" or "Hardhat Network".

**Three smart contracts:**
1. `VehicleRegistry` — registers vehicles, sets owners, stores warranty expiry as Unix timestamp
2. `ServiceLog` — records service metadata hashes, handles pending/verified/disputed state machine
3. `WarrantyTracker` — handles warranty claim submission, approval, denial, and warranty voiding on-chain

**Pattern:** hash-on-chain, metadata-off-chain. SHA-256 of sorted JSON metadata is stored on-chain;
full metadata is in PostgreSQL. This is the industry-standard hybrid approach (cost vs. verifiability trade-off).

---

## 2. Roles

| Role | Description | Registration Path | Initial Status | ETH |
|---|---|---|---|---|
| MANUFACTURER | Registers vehicles, manages SC network, issues recalls, resolves disputes | SSM number + brand selection (37 Malaysian brands) | active | 1000 ETH |
| SERVICE_CENTER (Authorized) | Brand-aligned SC; submits service records for that brand's vehicles | SSM number must be pre-registered by the manufacturer in the system | pending, activated by manufacturer | 0.01 ETH (manufacturer funds them) |
| SERVICE_CENTER (Independent) | Third-party workshop, can service any vehicle | Self-registers, no manufacturer linkage | active immediately | 1000 ETH (no manufacturer to fund them) |
| OWNER | Vehicle owner; receives FCM push notifications; uses Flutter mobile app only | Mobile app only — the web portal shows a blue banner telling owners to use the app | N/A | Has blockchain address, doesn't need ETH |

---

## 3. Authentication & Security

### JWT Tokens
- **Access token:** 15-minute expiry, HttpOnly cookie (web) / Authorization Bearer header (Flutter)
- **Refresh token:** 30-day expiry, HttpOnly cookie, path-restricted to `/api/auth`
- **Rotation:** Every refresh issues a new refresh token and revokes the old one
- **Cookie-first middleware:** `_extract_token()` checks cookie first, then `Authorization` header — one code path serves both web and mobile
- **Remember me:** If `remember_me=false`, cookies are session-scoped (cleared on browser close); if `true`, cookies persist for 30 days

### Web Security
- No tokens in localStorage — Angular app stores only `currentUser` profile object
- `withCredentials: true` on all Angular HTTP requests
- Auto-refresh interceptor: on 401, attempts token refresh, retries original request
- On logout: cookies cleared server-side, local storage legacy keys cleared

### Rate Limiting (Flask-Limiter)
- Global: 60 requests/minute
- Login: 10/minute (account lockout after 5 failed attempts, configurable)
- Register: 20/minute
- Forgot password: 5/minute
- Verify email resend: 5/hour
- PDF export: 10/minute
- Public vehicle lookup: 30/minute
- Recall issuance: 10/hour (prevents notification flood attack)
- Warranty claim submission: 5/hour per user
- Dispute message posting: 30/minute per user
- Abuse reports: 1 per reporter per target per 24 hours (DB-enforced, not rate-limiter)

### Additional Security Hardening
- Email must be verified before login is allowed (prevents account squatting on others' emails)
- SC suspension revokes `SERVICE_CENTER_ROLE` on-chain — suspended SC cannot bypass Flask by calling the contract directly with their private key
- Admin secret compared using `hmac.compare_digest()` — constant-time, prevents timing attack
- Uploaded files require authentication (`@token_required`) — prevents unauthenticated file enumeration
- Photos array in service submission validated: must be a list of strings, max 20 entries
- X-Forwarded-For only trusted when request comes from a known proxy IP (`TRUSTED_PROXY_IPS` env var)

### PDPA Compliance (Malaysia)
- `GET /api/auth/data-export` — returns all personal data held about the user (right of access)
- `DELETE /api/auth/account` — permanently deletes account, personal data, audit logs, dispute messages (right to erasure)
- Blockchain records cannot be deleted (only hashes stored, no PII on-chain — documented in Privacy Policy)
- Privacy Policy and Terms of Service served from the API and displayed in the Flutter app

---

## 4. All API Endpoints

Base path: `/api`

### Auth (`/api/auth`)
| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/register` | Public | Register new account (manufacturer/SC) |
| POST | `/login` | Public | Login, returns HttpOnly cookies |
| POST | `/refresh` | Public | Rotate refresh token |
| POST | `/logout` | Public | Clear cookies, revoke refresh token |
| POST | `/logout-all` | Any auth | Revoke all refresh tokens (all devices) |
| GET | `/me` | Any auth | Get current user profile |
| PUT | `/profile` | Any auth | Update name/phone/city/state/theme |
| POST | `/change-password` | Any auth | Change password, revokes all sessions |
| POST | `/forgot-password` | Public | Send password reset email |
| POST | `/reset-password` | Public | Redeem reset token, set new password |
| GET | `/verify-email` | Public | Verify email address via token |
| POST | `/resend-verification` | Any auth | Resend verification email |
| DELETE | `/account` | Any auth | PDPA — delete account and all personal data |
| GET | `/data-export` | Any auth | PDPA — export all personal data as JSON |
| GET | `/privacy-policy` | Public | Returns Privacy Policy text |
| GET | `/terms` | Public | Returns Terms of Service text |
| POST | `/device-token` | Any auth | Register FCM device token for push notifications |

### Vehicles (`/api/vehicle`)
| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/register` | MANUFACTURER | Register a new vehicle (VIN, owner email, make/model/year, warranty years) |
| POST | `/claim` | OWNER | Owner claims a manufacturer pre-registered vehicle |
| GET | `/owner/vehicles` | OWNER | List owner's vehicles |
| POST | `/transfer` | OWNER | Transfer vehicle ownership to new owner email |
| GET | `/<vin>` | Any auth | Get vehicle details (owner email hidden from non-owners) |
| GET | `/fleet` | MANUFACTURER | Paginated fleet list with service stats |
| GET | `/stats` | MANUFACTURER | Basic stats (total vehicles, SC counts, warranty claims) |
| GET | `/dashboard-stats` | MANUFACTURER | Full dashboard: charts, fleet health score, top SCs, trends (15s cache) |
| GET | `/activity-feed` | MANUFACTURER | Recent registrations, warranty claims, disputes (last 15 events) |
| GET | `/public/<vin>` | Public (30/min) | Public vehicle verification — service history + recall history |
| GET | `/export/<vin>` | Public (10/min) | Download PDF vehicle history report |
| GET | `/fleet-export` | MANUFACTURER | Download PDF fleet audit report |
| POST | `/recall` | MANUFACTURER | Issue recall — saves to DB, FCM push to all owners, email all brand SCs |
| GET | `/recalls` | MANUFACTURER, SC | List recalls for own brand |
| GET | `/recalls/owner` | OWNER | List active recalls for owner's vehicles |
| POST | `/recalls/<id>/service` | SERVICE_CENTER | Mark a VIN as recall-serviced |
| POST | `/recalls/<id>/close` | MANUFACTURER | Close a recall |
| GET | `/recalls/check/<vin>` | Any auth | Check if a VIN has active recalls |
| POST | `/reconcile` | MANUFACTURER, SC | Blockchain integrity check — re-computes SHA-256, marks tampered records |

### Services (`/api/service`)
| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/submit` | SERVICE_CENTER | Submit service record (JSON or multipart with photos) |
| POST | `/verify` | OWNER | Verify (approve) a pending service record on-chain |
| POST | `/dispute` | OWNER | Dispute a pending service record on-chain |
| POST | `/dispute-response` | SERVICE_CENTER | Submit rebuttal to an owner dispute |
| POST | `/escalate-dispute` | SERVICE_CENTER | Formally escalate to manufacturer priority |
| POST | `/resolve-dispute` | MANUFACTURER | Resolve dispute (approve/reject/modify) on-chain |
| GET | `/pending/<vin>` | Any auth (scoped) | Pending records for a specific VIN |
| GET | `/history/<vin>` | Any auth | Finalized service history for a VIN |
| GET | `/owner/pending` | OWNER | All pending records across all owner's vehicles |
| GET | `/owner/history` | OWNER | All finalized history across all owner's vehicles (filterable) |
| GET | `/center/pending` | SERVICE_CENTER | All pending records submitted by this SC |
| POST | `/owner/verify` | OWNER | Owner verify (alias) |
| POST | `/owner/dispute` | OWNER | Owner dispute (alias, also emails manufacturers) |
| GET | `/dispute-messages/<vin>/<idx>` | Any auth (scoped) | Get dispute thread messages |
| POST | `/dispute-messages` | Any auth (scoped) | Post a message in a dispute thread |
| POST | `/void-request` | SERVICE_CENTER | Submit warranty void request (mileage gap evidence) |
| GET | `/void-requests/manufacturer` | MANUFACTURER | List void requests for own brand vehicles |
| GET | `/void-requests/owner` | OWNER | List void requests for own vehicles |
| POST | `/void-requests/<id>/resolve` | MANUFACTURER | Approve or deny a void request; if approved, calls `voidWarranty()` on-chain |
| POST | `/void-requests/<id>/dispute` | OWNER | Dispute a pending void request |
| POST | `/report` | OWNER, MANUFACTURER, SC | Report an independent workshop for abuse |

### Warranties (`/api/warranty`)
| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/check/<vin>` | Any auth | Check warranty status |
| GET | `/check-eligibility/<vin>` | Any auth | Check warranty claim eligibility (service history count included) |
| POST | `/submit-claim` | OWNER | Submit warranty claim (JSON or multipart with photos) |
| GET | `/claims/<vin>` | MANUFACTURER | View warranty claims for a VIN |
| POST | `/approve-claim` | MANUFACTURER | Approve a warranty claim on-chain |
| POST | `/deny-claim` | MANUFACTURER | Deny a warranty claim on-chain (reason required) |
| GET | `/owner/claims` | OWNER | Owner's own warranty claims |

### SC Management (`/api/sc`)
| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/service-centers` | MANUFACTURER | List brand's service centres (filtered by city/state/status/search) |
| GET | `/service-centers/<id>` | MANUFACTURER | Get SC detail + live ETH balance |
| POST | `/service-centers/<id>/activate` | MANUFACTURER | Activate a pending SC |
| POST | `/service-centers/<id>/suspend` | MANUFACTURER | Suspend a SC (revokes all sessions AND revokes SERVICE_CENTER_ROLE on-chain) |
| POST | `/service-centers/<id>/fund` | MANUFACTURER | Transfer ETH to a SC |
| POST | `/fund-all` | MANUFACTURER | Fund all active SCs with a fixed amount |
| POST | `/eth-request` | SERVICE_CENTER | SC requests ETH from manufacturer |
| GET | `/manufacturer/eth-requests` | MANUFACTURER | List pending ETH requests |
| GET | `/manufacturer/eth-requests/count` | MANUFACTURER | Count of pending ETH requests (badge) |
| POST | `/manufacturer/eth-requests/<id>/dismiss` | MANUFACTURER | Dismiss an ETH request |
| GET | `/authorized-licenses` | MANUFACTURER | List pre-registered SSM license numbers |
| POST | `/authorized-licenses` | MANUFACTURER | Add a new authorized SSM number |
| DELETE | `/authorized-licenses/<id>` | MANUFACTURER | Remove an authorized SSM number |

### Notifications (`/api/notifications`)
| Method | Path | Role | Description |
|---|---|---|---|
| GET | `` | Any auth | List notifications (unread first, max 100) |
| GET | `/count` | Any auth | Unread count (for badge polling) |
| POST | `/<id>/read` | Any auth | Mark one notification as read |
| POST | `/read-all` | Any auth | Mark all notifications as read |

### Uploads (`/api/upload`)
| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/upload` | Any auth | Upload an image file; returns filename |
| GET | `/uploads/<filename>` | Public | Serve an uploaded file |

### SC Self-Stats (`/api/sc`)
| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/my-stats` | SERVICE_CENTER | Own submission count, dispute rate, ETH balance |

### System (`/api`)
| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/health` | Public | DB + blockchain connectivity status; returns 503 if DB down |

---

## 5. Core Workflows

### Vehicle Registration & Ownership
1. Manufacturer registers vehicle with VIN, owner email, make/model/year, warranty years
2. Vehicle is created on-chain (VehicleRegistry), stored in DB (VehicleVINMapping)
3. Owner receives notification, claims vehicle via Flutter app (`POST /vehicle/claim`)
4. Ownership is transferred on-chain to the owner's blockchain address

### Service Record Lifecycle (Full State Machine)
```
SC submits → PENDING (on-chain)
    Owner FCM push notification sent
Owner verifies → VERIFIED (on-chain, immutable)
Owner disputes → DISPUTED (on-chain)
    SC submits rebuttal (DB only)
    SC optionally escalates
Manufacturer resolves → decision written to chain (approve / reject / modify)
    Owner FCM push + SC email notification
```

Dispute thread: owner, SC, and manufacturer can post messages (DisputeMessage table).
SC can only see disputes for records they submitted.

### Recall Workflow
1. Manufacturer issues recall with title + description
2. Saved to VehicleRecall table
3. FCM push sent to ALL owners with registered devices
4. Email sent to all active SCs of that brand
5. When SC services a recall vehicle: `POST /vehicle/recalls/<id>/service` with VIN
6. Owner sees recall status in Flutter recalls screen (serviced/pending)
7. Public verify page shows recall history for that VIN including serviced status
8. Manufacturer can close the recall when done

### Warranty Void Request Workflow
1. SC detects large mileage gap (configurable, default 50,000 km) — warns on submission
2. SC formally submits void request: `POST /service/void-request` with vin + reason + mileage evidence
3. Manufacturer email notification sent
4. Owner receives FCM push — goes to void requests screen in app
5. Owner can dispute: `POST /service/void-requests/<id>/dispute`
6. Manufacturer resolves: approved or denied
7. If approved: `WarrantyTracker.voidWarranty(vinHash)` is called on-chain — the warranty is permanently marked void in the smart contract. `isWarrantyValid()` returns false for that VIN. No further warranty claims can be submitted on-chain, not just in the backend.
8. Owner FCM push sent on resolution

### ETH Fund Request Flow
1. SC sees low ETH balance warning in dashboard
2. SC clicks "Request ETH from Manufacturer"
3. EthFundRequest record created
4. Bell badge appears on manufacturer's SC management page
5. Manufacturer reviews, funds via `POST /sc/service-centers/<id>/fund`
6. Fund request auto-fulfilled/dismissed after successful transfer

### SSM-Gated SC Registration
- **Manufacturer:** must supply valid SSM number + select brand from 37-brand dropdown; SSM is unique system-wide
- **Authorized SC:** must supply SSM number that manufacturer pre-registered in `AuthorizedSCLicense` table matching their brand; SSM is marked as used after registration
- **Independent SC:** no SSM required; self-registers; immediately active; no manufacturer linkage

### Blockchain Integrity Check (Reconciliation — Two-Layer)
1. Manufacturer (or SC) navigates to SC Network page — "Blockchain Integrity Check" panel
2. Enters optional VIN to scope check; leaves blank to check all brand vehicles
3. `POST /vehicle/reconcile` — backend re-computes SHA-256 from all stored DB fields (including ecu_modules, photos)
4. Layer 1 — DB field consistency: compares recomputed hash to stored `metadata_hash`. Catches naive tampering where fields are changed but hash is not updated.
5. Layer 2 — On-chain verification: confirms the stored `metadata_hash` actually appears in the on-chain pending/finalized record set. Catches sophisticated tampering where both fields AND metadata_hash are updated consistently in DB but the on-chain hash doesn't match.
6. Records marked `integrity_status = 'ok'` or `'tampered'` in DB with `db_fields_match` and `chain_match` diagnostics
7. Tampered records returned to UI; public verify page shows red "TAMPERED" badge

### Abuse Reporting (Independent Workshops)
1. Owner, manufacturer, or SC reports a workshop via `POST /service/report`
2. Non-owner reporters must supply a VIN as evidence (prevents coordinated false reporting)
3. Rate-limited: 1 report per reporter per target per 24 hours (DB-enforced)
4. Auto-suspend trigger: 3 or more reports AND at least 1 must be from an owner
5. On auto-suspend: admin email sent, workshop account suspended
6. Workshop can email admin to dispute suspension

---

## 6. Database Models (Key Tables)

| Model | Purpose |
|---|---|
| User | All roles; has role, brand, status, blockchain_address, ssm_number |
| VehicleVINMapping | Bridges VIN to owner address, registered_by, make/model/year, warranty_expiry, registration_status |
| ServiceMetadata | Full service record fields; metadata_hash, ecu_modules (JSON), integrity_status, integrity_checked_at, sc_brand, disputed |
| WarrantyClaimMetadata | Warranty claim records linked to VIN |
| DisputeMessage | Threaded messages for a dispute (sender_id, sender_role, message, vin, record_index) |
| EthFundRequest | SC ETH requests; status: pending/fulfilled/dismissed |
| VehicleRecall | Recall records; brand, title, description, status (active/closed) |
| RecallVINService | Junction: which VINs have been serviced under which recall |
| WarrantyVoidRequest | Void requests; status: pending/disputed/approved/denied |
| AuthorizedSCLicense | Manufacturer-pre-registered SSM numbers; used flag |
| AbuseReport | Reporter, target, category, reason, VIN evidence, timestamp |
| Notification | Persistent inbox: user_id, title, body, type, data (JSON), read, created_at |
| RefreshToken | JWT refresh tokens with revocation support |
| DeviceToken | FCM device tokens per user (platform: ios/android) |
| AuditLog | Security events (login, logout, password change, etc.) — auto-deleted after 365 days |
| PasswordResetToken | Password reset tokens; expires 60 minutes |
| EmailVerificationToken | Email verification tokens; expires 24 hours |

---

## 7. Smart Contracts

All contracts deployed to a private Hardhat Ethereum node.
Interactions go through web3.py adapters in `backend/blockchain/adapters/`.

### Role-Based Access Control (6 roles total)

| Role | Contract | Holder | Purpose |
|---|---|---|---|
| `DEFAULT_ADMIN_ROLE` | All 3 | Deployer EOA | Grant/revoke roles — system admin only |
| `MANUFACTURER_ROLE` | VehicleRegistry | Each manufacturer wallet | Register vehicles |
| `MANUFACTURER_ADMIN_ROLE` | ServiceLog + WarrantyTracker | Each manufacturer wallet | Resolve disputes, approve/deny claims, void warranties |
| `SERVICE_CENTER_ROLE` | ServiceLog | Each SC wallet | Submit service records; revoked on account suspension |
| `OWNER_ROLE` | VehicleRegistry | Each owner wallet | Verify/dispute services, submit claims |
| `SERVICE_LOG_ROLE` | VehicleRegistry | ServiceLog contract | Internal: write finalized service hashes |

`MANUFACTURER_ADMIN_ROLE` = `keccak256("MANUFACTURER_ADMIN_ROLE")` — intentionally NOT `DEFAULT_ADMIN_ROLE`. This prevents manufacturers from calling `grantRole()` to escalate privileges on either contract.

### VehicleRegistry
- `registerVehicle(vinHash, ownerAddress, warrantyExpiry)` — `MANUFACTURER_ROLE`
- `transferOwnership(vinHash, newOwner)` — owner or `OWNER_ROLE`
- `addServiceHash(vinHash, serviceHash)` — `SERVICE_LOG_ROLE` (called by ServiceLog only)
- `getVehicle(vinHash)` — read
- `getOwnedVehicles(ownerAddress)` — read

### ServiceLog
Key design: records are looked up by `metadataHash`, not array index. This eliminates the index-shifting race condition that swap-and-pop array removal would otherwise cause.

- `submitService(vinHash, metadataHash)` — `SERVICE_CENTER_ROLE`; includes duplicate hash check
- `verifyService(vinHash, metadataHash)` — owner; finds record by hash, finalizes, calls `addServiceHash`
- `disputeService(vinHash, metadataHash, reason)` — owner; finds record by hash, marks disputed
- `resolveDispute(vinHash, metadataHash, decision, resolutionHash)` — `MANUFACTURER_ADMIN_ROLE`; decision: APPROVE (finalize) / REJECT (remove) / MODIFY (keep disputed for further action)
- `getPendingServices(vinHash)` — read; returns array with `record_index` for display only
- `getFinalizedServices(vinHash)` — read

`disputeResolutions` mapping keyed by `(vin, metadataHash)` — stable even after array reordering.

### WarrantyTracker
- `isWarrantyValid(vinHash)` — checks expiry timestamp AND `voidedWarranties[vin]` mapping
- `voidWarranty(vinHash)` — `MANUFACTURER_ADMIN_ROLE`; permanently marks warranty void on-chain; called when manufacturer approves a void request. After this, `submitClaim` will revert.
- `submitClaim(vinHash, claimHash)` — owner; checks `isWarrantyValid` before accepting
- `approveClaim(vinHash, claimIndex)` — `MANUFACTURER_ADMIN_ROLE`
- `denyClaim(vinHash, claimIndex, reasonHash)` — `MANUFACTURER_ADMIN_ROLE`
- `getClaims(vinHash)` — read

### Hash computation (reproducible)
SHA-256 of the metadata dict with keys sorted alphabetically, then hex-encoded with `0x` prefix.
All 8 fields are included: `service_type`, `service_date`, `mileage`, `parts_replaced`, `technician_name`, `service_notes`, `ecu_modules`, `photos`.
`ecu_modules` is stored in the `ServiceMetadata` DB table so the reconcile can faithfully reproduce the original hash. The same function runs at submission time and at integrity-check time — any post-hoc DB modification produces a mismatch.

---

## 8. Notifications

### Persistent Notification Inbox (DB-backed)
Every call to `send_to_user()` in `core/notifications.py` persists a `Notification` row to the DB
before attempting FCM. This means notifications survive even when FCM is unavailable or the user has
no registered device. The `Notification` model stores: title, body, type, data (JSON), read flag, created_at.

### Web (Angular)
- Bell icon in both manufacturer and SC sidebar footers with real-time unread count badge
- Badge polls `GET /api/notifications/count` every 30 seconds
- Clicking the bell opens a panel showing the 20 most recent notifications (unread highlighted)
- "Mark all read" button; unread notifications highlighted with a blue tint
- Polling-based — no WebSocket; sufficient for a business dashboard usage pattern

### Email (Resend API)
Triggered for: new warranty claim, dispute filed, dispute resolved, recall alert to SCs,
void request to manufacturer, warranty void decision to owner, auto-suspend alert to admin,
password reset, email verification.
All email sends are in daemon threads — never block the API response.

### Mobile Push (FCM)
Triggered for: new pending service record, dispute resolved, recall issued, warranty void request,
warranty void resolved, service overdue reminder.
DeviceToken table stores per-user FCM tokens (upserted on app launch).
`broadcast_recall()` sends to all registered devices regardless of role.
`send_to_user(user_id, ...)` targets a specific user's devices and also persists to the DB inbox.

### Flutter Notification Inbox
Local SharedPreferences-based store (up to 50 notifications). Notifications are added when FCM
messages arrive (via `push_notification_service.dart`). Screen at `/notifications` shows the full
history with type-specific icons (wrench for service, shield for warranty, gavel for disputes).
"Mark all read" and "Clear all" actions available.

---

## 9. Resilience Patterns

### DB Write Retry
After a successful blockchain write (source of truth), the DB write is retried up to 3 times
with 0.15s / 0.30s backoff. If all 3 fail, a RuntimeError is raised explaining the on-chain record
is safe and to contact support with the VIN.

### Blockchain Fallback
`get_finalized_services()` catches blockchain exceptions and falls back to reading from PostgreSQL,
returning records with `status: 'cached'` to indicate verification state is unknown.
`get_owner_finalized_services()` similarly falls back to all DB records for that owner's vehicles.

### Dashboard Stats Cache
Manufacturer dashboard stats are cached in-process for 15 seconds per manufacturer address to avoid
hitting the DB and blockchain on every page refresh.

### Graceful ETH Balance Fetch
ETH balance fetch in SC detail view has a 2-second timeout in a daemon thread — never blocks the API.

---

## 10. Deployment

**Current:** Railway (PaaS)
- Backend: Python Flask app (Gunicorn)
- Database: PostgreSQL on Railway (managed)
- Blockchain node: **Ganache** hosted as a Railway service (not Hardhat Network — Ganache is the EVM; Hardhat is only the toolchain used to compile and deploy contracts)
- Frontend: Angular SPA (separate Railway service or any static host / CDN)

**Environment variables required:**
```
DATABASE_URL          PostgreSQL connection string
BLOCKCHAIN_URL        Hardhat/Geth RPC URL
DEPLOYER_ADDRESS      Ethereum address that deployed the contracts
DEPLOYER_PRIVATE_KEY  Private key of deployer (contract admin)
SECRET_KEY            Flask session secret
JWT_SECRET_KEY        JWT signing secret
RESEND_API_KEY        Resend email API key
MAIL_DEFAULT_SENDER   From address for emails
FRONTEND_URL          Frontend base URL (for password reset links)
FIREBASE_CREDENTIALS  Firebase service account JSON (for FCM)
ADMIN_CONTACT_EMAIL   Email address to receive auto-suspend alerts
```

**Configurable thresholds (no code change needed):**
- MILEAGE_GAP_THRESHOLD = 50,000 km
- ABUSE_AUTO_SUSPEND_THRESHOLD = 3 reports
- SC_DAILY_SUBMISSION_LIMIT = 100 (authorized SC)
- INDEP_SC_DAILY_LIMIT = 20 (independent workshop)
- PASSWORD_RESET_EXPIRY_MINUTES = 60

**Schema migration:** On startup, `app.py` runs `db.create_all()` plus explicit
`ALTER TABLE ADD COLUMN IF NOT EXISTS` for post-initial-deploy columns. Allows zero-downtime
column additions without a dedicated migration tool.

---

## 11. How to Scale

**Horizontal backend scaling:**
- Replace in-memory rate limiter storage with Redis (one-line config: `RATELIMIT_STORAGE_URI=redis://...`)
- Replace in-process stats cache dict with Redis
- Multiple Flask workers behind Railway load balancer — all state is in PostgreSQL so workers are stateless

**Database scaling:**
- Railway PostgreSQL can be upgraded to larger plans
- Add read replicas for dashboard/stats queries
- Add DB indexes on ServiceMetadata.vin, ServiceMetadata.service_center_address, VehicleVINMapping.registered_by

**Blockchain scaling:**
- Move from single Ganache node to multi-node consortium chain (Hyperledger Besu IBFT 2.0 or Polygon Edge)
- Minimum 4 nodes for Byzantine fault tolerance
- Flask adapters call the same JSON-RPC interface — no application code changes needed

**Push notifications:**
- FCM scales natively — no changes needed at current volume

---

## 12. Maintenance

**APScheduler jobs (run automatically on app startup):**
| Job | Schedule | What it does |
|---|---|---|
| warranty_expiry_reminders | Daily 08:00 UTC | Emails owners whose warranty expires in ~30 days |
| audit_log_purge | Daily 03:00 UTC | Deletes audit logs older than 365 days (PDPA retention) |
| service_overdue_reminders | Weekly Monday 09:00 UTC | FCM push + email to owners of vehicles with no service in 180+ days |
| notification_purge | Daily 04:00 UTC | Deletes notification inbox entries older than 90 days (prevents unbounded growth) |

**Operational monitoring:**
- Watch for `DB sync permanently failed` in logs — means service record is on-chain but not in DB
- Watch for `Blockchain unavailable` warnings — means records are being served from DB fallback cache
- `GET /api/health` returns JSON with `db.ok` and `blockchain.connected`; returns 503 if DB is down

**Database reset and demo seeding:**
```
python init_db.py          # drop all tables, recreate schema
python init_db.py --seed   # drop/recreate + load demo accounts, vehicles, service records, recall
```
Demo password for all seed accounts: `Demo@1234`

**Contract redeployment:**
1. Deploy new contracts via Hardhat
2. Update contract address environment variables
3. Restart backend — new addresses picked up at startup
4. Old records remain readable as long as old contract addresses are accessible

---

## 13. UI/UX Considerations

### Web Dashboard (Angular)
- Custom CSS variable design system with light/dark mode; theme preference persisted to DB
- Role-based routing with Angular Router guards
- Responsive layout — sidebar collapses on mobile
- Every async action shows a spinner; errors shown in inline alert divs
- Leaflet map on SC network page — colour-coded dots (green=active, amber=pending, red=suspended); uses divIcon to avoid webpack broken image issue
- Chart.js dashboard: service type pie, warranty claim trend line (6 months), fleet health score, top SCs bar
- Blockchain status badge on login: CSS gives proper colour contrast per state (green/red/grey)
- Mileage history line chart on public verify page
- QR code on public verify page linking back to the URL
- Tamper badge (red, "TAMPERED") and verified checkmark (green) on service records

### Mobile App (Flutter)
- GoRouter with ShellRoute — persistent bottom nav bar
- Service history: shows SC name, "Independent Workshop" label for brandless SCs
- "Report this Workshop" button on independent SC records — category dropdown + free-text reason
- Recalls screen: card list, green (serviced) / orange (pending) status
- Void requests screen: lists requests, "Dispute" button with reason dialog
- Notifications screen: full history with type-specific icons, mark-all-read, clear-all
- VIN claim screen: camera barcode/QR scanner via `mobile_scanner` package — no manual typing needed
- Push notification tap navigation: recall → recalls screen, void → void requests, pending service → pending list
- Biometric login (TouchID/FaceID) after first password login
- All network errors show snackbar; loading states on every button

### Registration Flow (Web)
- Three radio options: Manufacturer, Authorized Service Centre, Independent Workshop
- Dynamic form validators: SSM and brand shown/hidden based on selection
- Blue info banner on login page directing vehicle owners to the mobile app

---

## 14. Academic Gaps to Acknowledge

### Deliberate trade-offs — defend with technical argument

**Off-chain metadata (hash-on-chain pattern):**
Only SHA-256 hash is on-chain; full service metadata is in PostgreSQL.
Storing full JSON on Ethereum costs 20,000 gas per 32 bytes — prohibitive at scale.
This is the industry standard (IPFS-anchored NFT metadata, IBM Food Trust, Walmart Food Safety).
The integrity check re-derives hashes and detects any DB modification, demonstrating the blockchain value proposition.

**Private/permissioned chain (Ganache):**
A single Ganache node rather than public Ethereum. Ganache is a deterministic EVM simulator — chain state is predictable and gas is free. Contracts are compiled and deployed using the Hardhat toolchain targeting the Ganache network.
Mainnet ETH costs are prohibitive for per-record use (each service submission would cost real money). The integrity-guarantee properties — immutable hash anchoring, tamper detection — are identical on a private chain.
Production migration path: consortium chain (Hyperledger Besu IBFT 2.0 or Polygon Edge) with multiple nodes and real consensus. This mirrors how BMW, Volkswagen, Ford operate through the MOBI consortium.

**SSM regex-only validation:**
SSM number format validated by regex; no call to SSM Malaysia's official API.
SSM API access requires a registered business and formal approval — unavailable for an academic prototype.
The validation layer is designed to accept a real KYC adapter as a plug-in.

**Single blockchain node — no consensus:**
One Hardhat node means no Byzantine fault tolerance.
Multi-node consensus is infrastructure configuration, not application code.
Smart contract logic and hash anchoring work identically on a multi-node network.

### Acknowledged gaps — state honestly

**In-memory rate limiting:**
Flask-Limiter resets on every restart/redeploy.
Fix: `RATELIMIT_STORAGE_URI=redis://...` — one-line config change.
The DB-enforced 24-hour abuse report rate limit is persistent (does not reset on restart).

**Smart contract static analysis (Slither — DONE, not a gap):**
Slither 0.11.5 was run against all contracts. 9 contracts analysed (3 application + 6 OpenZeppelin library), 21 findings total. No high or critical severity issues. All application-code findings are low severity and justified:
- unused-return: intentional tuple destructuring (only needed fields captured)
- reentrancy-events: event emitted after external call, but no ETH transfer and no exploitable state — false positive for this pattern
- timestamp: block.timestamp used for warranty expiry; miner manipulation is at most a few seconds, irrelevant for warranties measured in years
The remaining findings are in OpenZeppelin library files and the Hardhat boilerplate Lock.sol — not application code.
Report phrasing: "Static analysis was performed using Slither 0.11.5. No high or critical severity vulnerabilities were identified in the application contracts."

**No longitudinal user study:**
System tested by developer; no pilot with real mechanics over time.
348 backend tests + 63 frontend tests; functional prototype demonstrates all workflows.
Future work: 3-month pilot with a real workshop, measuring time savings vs. paper-based processes.

**FCM and email are centralised:**
Decentralised push is an unsolved production problem — even Uniswap and OpenSea use centralised notifications.
PDPA implication: disclosed in Privacy Policy under Data Sharing and Disclosure.

**ecu_modules field has no hardware integration:**
The ecu_modules array is accepted in service submission, stored in DB, and included in the integrity hash. However, no OBD-II tool reads it automatically — a technician would have to type ECU module names manually.
Future work: ELM327 Bluetooth adapter integration in the Flutter app for automatic ECU module reading.

---

## 15. Security Evaluation — Complete Findings

This section is for the security evaluation chapter. All findings from a systematic penetration test of the system.

| # | Attack Vector | Severity | Status |
|---|---|---|---|
| 1 | X-Forwarded-For spoofing bypasses all rate limits | Critical | Fixed — XFF only trusted from known proxy IPs (`TRUSTED_PROXY_IPS`) |
| 2 | Recall endpoint had no rate limit — manufacturer could flood all owners with FCM | Medium | Fixed — 10/hour limit |
| 3 | Uploaded files served without authentication — unauthenticated enumeration | Medium | Fixed — `@token_required` on file serve endpoint |
| 4 | Email verification not enforced at login — unverified accounts fully functional | Medium | Fixed — login rejects unverified accounts |
| 5 | Warranty claim submission had no rate limit — spam manufacturer inbox | Medium | Fixed — 5/hour limit |
| 6 | Dispute message endpoint had no rate limit — flood dispute threads | Low | Fixed — 30/minute limit |
| 7 | Photos array in service submission accepted arbitrary strings (injection) | Medium | Fixed — validated as list of strings, max 20, 255 chars each |
| 8 | DB-only integrity check defeated by consistent metadata+hash tampering | Medium | Fixed — reconcile now also compares against on-chain hashes |
| 9 | SC suspension only revoked JWT — SC could still call contract directly | Critical | Fixed — suspension now revokes `SERVICE_CENTER_ROLE` on-chain |
| 10 | `ecu_modules` hashed at submission but not stored — integrity check produced false positives | High (Bug) | Fixed — `ecu_modules` column added, stored, included in reconcile |
| 11 | `WarrantyTracker.MANUFACTURER_ADMIN_ROLE = DEFAULT_ADMIN_ROLE` — manufacturers could call `grantRole()` | Medium | Fixed — contracts redeployed with distinct role hash |
| 12 | Swap-and-pop index shifting could cause wrong record to be verified/disputed | Medium | Fixed — contracts redeployed using `metadataHash` lookup instead of index |
| 13 | Admin secret compared with `!=` — timing attack enables brute-force | Low | Fixed — `hmac.compare_digest()` used |
| 14 | Notification inbox grew unbounded — no TTL | Low | Fixed — daily purge of entries older than 90 days |
| 15 | Warranty void only in DB — owner could still submit on-chain warranty claim after voiding | Medium | Fixed — `voidWarranty()` added to WarrantyTracker, called on approval |
| 16 | Keystore encryption key and data on same filesystem | High (Ops) | Acknowledged — production fix: AWS KMS or Railway secrets |
| 17 | JWT secret brute-forceable if weak | High (Ops) | Acknowledged — use 256-bit random secret; documented in deployment guide |
| 18 | Login timing oracle (bcrypt only runs if user exists — timing reveals email registration) | Low/Info | Acknowledged — inherent bcrypt limitation |
| 19 | SC suspension has 15-minute window (valid access token) | Low | Acknowledged — inherent short-lived JWT limitation |
| 20 | Multiple independent SC registrations bypass daily submission limits | Low | Acknowledged — needs phone/identity verification |
| 21 | SSM number squatting before legitimate SC registers | Low | Acknowledged — needs real SSM API integration |
| 22 | No certificate pinning in Flutter app | Medium | Acknowledged — 15-min token limits exposure window |
| 23 | Admin `/reset-db` destroys all data if ADMIN_SECRET leaks | Critical (Ops) | Acknowledged — Railway secret management is mitigation |
| 24 | `fix-ownership` temporarily grants OWNER_ROLE to deployer — dirty state if revoke fails | Low | Acknowledged — low probability edge case |
| 25 | Technician names and service notes publicly exposed via `/vehicle/public/<vin>` | Low (Privacy) | Acknowledged — disclosed in Privacy Policy; intentional for used car verification |
| 26 | IDOR on authorized licenses | Tested — NOT present | Already scoped by `manufacturer_user_id` in query |
| 27 | File path traversal in uploads | Tested — NOT present | `secure_filename()` + `send_from_directory()` |
| 28 | SQL injection | Tested — NOT present | ORM parameterised queries throughout |

**15 code-level vulnerabilities fixed. 13 acknowledged with documented mitigations. 3 tested and confirmed not present.**

---

## 16. System Strengths (for positive framing)

- Two-layer integrity check: DB field consistency AND on-chain hash verification — catches both naive and sophisticated DB tampering
- Warranty void is enforced on-chain: `voidWarranty()` in the smart contract prevents further warranty claims at the contract level, not just the API level
- SC suspension is complete: revokes JWT sessions AND `SERVICE_CENTER_ROLE` on-chain — suspended SC cannot bypass Flask by calling the contract directly
- Metadata-hash-based record lookup: eliminates the swap-and-pop index-shifting race condition entirely — a real correctness improvement over array-index-based contracts
- `MANUFACTURER_ADMIN_ROLE` is distinct from `DEFAULT_ADMIN_ROLE`: manufacturers cannot escalate privileges via `grantRole()`
- ecu_modules stored and hashed correctly: no false positives in integrity check
- Tamper detection is real and demonstrable live — two-layer check catches even a sophisticated DB attacker
- Full PDPA compliance: data export and account deletion are implemented, not just mentioned
- Persistent notification inbox: every notification stored in DB — survives FCM downtime, reviewable in both web panel and Flutter screen
- Proactive service reminders: APScheduler sends warranty expiry emails 30 days before expiry and weekly service-overdue push/email for vehicles idle 180+ days; notification inbox auto-purged after 90 days
- Static analysis completed: Slither 0.11.5 run on all contracts, no high/critical issues found
- Multi-channel notifications: FCM push (mobile), email (web), persistent DB inbox, in-app badge — four distinct delivery paths
- Graceful degradation: service history falls back to PostgreSQL if blockchain is unreachable
- Brand-scoped access control: every query is scoped to the requesting user's brand
- Dispute resolution is three-party: owner disputes, SC rebuts, manufacturer resolves — all on-chain with off-chain message thread
- Independent workshop lifecycle is complete: registration, ETH funding, submission, abuse reporting, auto-suspension (blockchain role also revoked)
- VIN barcode scan in Flutter: no manual 17-character entry; camera scans door-jamb barcode or QR code
- Public API is genuinely useful: warranty status + full service history with integrity badges + recall history
- PDF reports: per-vehicle and fleet-level exports with professional ReportLab layout
- Health check endpoint: `GET /api/health` returns DB and blockchain status; Railway uses this for uptime monitoring
- SC self-stats endpoint: dispute rate, submission count, ETH balance — SC can monitor their own performance
- 37-brand Malaysian dropdown: context-aware to the local market
- PDPA Privacy Policy and Terms of Service are real legal text served from the API and shown in-app
- Demo seed script: `python init_db.py --seed` creates a complete realistic dataset for presentations
