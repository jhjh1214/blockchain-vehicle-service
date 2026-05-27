# FYP2 Codebase Audit — Blockchain Vehicle Service & Warranty Management System

**Audit date:** 2026-05-27  
**Audited against:** FYP1 implementation checklist (fyp2_audit_checklist.html)  
**Codebase branch:** `main`

---

## Score Dashboard

| Section | Items | ✅ Met / Exceeded | ⚠️ Partial | ❌ Not Met |
|---|---|---|---|---|
| Smart Contracts (Solidity) | 35 | 23 (66%) | 7 (20%) | 5 (14%) |
| REST API Endpoints | 17 | 12 (71%) | 2 (12%) | 3 (18%) |
| Backend Infrastructure | 17 | 7 (41%) | 6 (35%) | 4 (24%) |
| Web App UI (Angular) | 15 | 3 (20%) | 9 (60%) | 3 (20%) |
| Mobile App UI (Flutter) | 13 | 2 (15%) | 9 (69%) | 2 (15%) |
| Ganache / Deployment | 13 | 4 (31%) | 2 (15%) | 7 (54%) |
| Testing | 13 | 4 (31%) | 2 (15%) | 7 (54%) |
| **TOTAL** | **123** | **55 (45%)** | **37 (30%)** | **31 (25%)** |

> **Weighted score** (partials = 0.5): **73.5 / 123 = 60%** of FYP1 scope implemented.

Key insight: the technical core (smart contracts, API, backend) is in strong shape. The gaps concentrate in **simulation/demo scripts**, **formal testing** (Slither, usability), and **UI polish** (photos, export PDF, timeline layout, biometrics).

---

## What Was Built Beyond FYP1 Scope

The following features were **not in the FYP1 plan** but are now implemented — these can strengthen the FYP2 report:

| Feature | Layer | Notes |
|---|---|---|
| Refresh token rotation with per-device tracking | Backend | Full 30-day refresh cycle; old token revoked on rotation |
| Multi-device session management + `POST /api/auth/logout-all` | Backend | Device tokens tracked in DB |
| Rate limiting on all auth endpoints | Backend | 10/min login, 20/min register, 30/min refresh |
| Security headers (CSP, X-Frame-Options, HSTS, etc.) | Backend | Applied globally to all responses |
| Account lockout after 5 failed login attempts | Backend | 15-minute lockout, failed attempts reset on success |
| Encrypted keystore (Fernet symmetric encryption) | Backend | Private keys never stored plaintext |
| Service centre management workflow (activate / suspend / fund) | Backend + Web | Manufacturer can activate/suspend SCs and fund them with ETH |
| ETH auto-funding on registration and bulk `fund-all` | Backend | New SC accounts automatically funded; manufacturer can top-up |
| Manufacturer brand validation | Backend | Manufacturer can only register vehicles of their own brand |
| Vehicle pre-registration without owner + owner claim flow | Smart contract + Backend + Mobile | Owner claims a pre-registered vehicle using VIN; `adminTransferOwnership` for handoff |
| `adminTransferOwnership` via `DEFAULT_ADMIN_ROLE` | Smart contract | Needed for the claim flow |
| `OWNER_ROLE` conditional revocation | Smart contract | Role only revoked on transfer if owner has no remaining vehicles |
| Swap-and-pop O(1) pending record removal | Smart contract | Gas-efficient; documented in README |
| `isWarrantyValid` returns `(bool, string reason)` | Smart contract | More informative than just `bool` |
| Input sanitisation with `bleach` + VIN format validation | Backend | VIN must be 17 chars, no I/O/Q |
| Public vehicle verify page (no auth) | Angular | Anyone can verify a VIN's registration and warranty |
| Leaflet map for service centre visualisation | Angular | Pins coloured by status; state/text filters |
| Angular profile page with editable fields | Angular | Profile update + change password for web users |
| Angular register with real-time password strength indicator | Angular | Five criteria displayed live |
| Flutter transfer vehicle — two-stage confirmation UI | Flutter | Requires explicit confirmation with red warning box |
| Flutter profile, change-password, and claim vehicle screens | Flutter | Not in FYP1 screen list |
| Blockchain event listener daemon thread | Backend | Monitors 4 events at 5-second intervals; auto-reconnects |

---

## Section 1: Smart Contracts (Solidity)

35 items · **✅ 23 · ⚠️ 7 · ❌ 5**

| # | Checklist Item | Status | Notes |
|---|---|---|---|
| 1 | `registerVehicle(bytes32 vin, address owner, uint256 warrantyExpiry)` — MANUFACTURER_ROLE | ✅ Met | Signature matches; `initialOwner` parameter name only |
| 2 | `transferOwnership(bytes32 vin, address newOwner)` — current owner | ✅ Exceeded | Also added `adminTransferOwnership` via `DEFAULT_ADMIN_ROLE` for vehicle claim flow |
| 3 | Vehicle struct: `owner, warrantyStart, warrantyExpiry, serviceHashes[], pendingServices[]` | ⚠️ Partial | Has all fields except `pendingServices[]`. Pending records live in `ServiceLog` (better separation of concerns — VehicleRegistry only holds finalized hashes) |
| 4 | `mapping(bytes32 => Vehicle) vehicles` | ✅ Met | Public mapping, matches spec |
| 5 | `mapping(address => bytes32[]) ownedVINs` | ✅ Met | Public mapping, matches spec |
| 6 | `submitService(bytes32 vin, bytes32 metadataHash)` — SERVICE_CENTER_ROLE | ✅ Met | Exact match |
| 7 | `verifyService(bytes32 vin, uint256 recordIndex)` — vehicle owner | ✅ Met | OWNER_ROLE enforced |
| 8 | `disputeService(bytes32 vin, uint256 recordIndex, string reason)` — owner | ✅ Met | Exact match |
| 9 | `getPendingServices(bytes32 vin)` returns `ServiceRecord[]` | ✅ Met | View function, exact match |
| 10 | `getServiceHistory(bytes32 vin)` filtering verified | ✅ Met | Named `getFinalizedServices()` — same semantics |
| 11 | `resolveDispute(vin, recordIndex, decision, resolutionNotes)` — MANUFACTURER_ADMIN_ROLE | ✅ Met | Uses `DEFAULT_ADMIN_ROLE` (see item 31); resolutionNotes stored as `bytes32` hash |
| 12 | ServiceRecord struct: `vin, metadataHash, timestamp, technician, serviceCenter, verified, disputed` | ⚠️ Partial | Has all fields except `technician`. Technician stored off-chain in `ServiceMetadata` SQLite table (gas saving decision) |
| 13 | DisputeResolution struct + `DisputeDecision` enum (APPROVE/REJECT/MODIFY) | ⚠️ Partial | Struct fully implemented. Enum has `PENDING/APPROVE/REJECT` — **`MODIFY` variant missing** |
| 14 | `event ServiceSubmitted(bytes32 vin, bytes32 metadataHash, uint256 timestamp, address serviceCenter)` | ✅ Met | Exact match |
| 15 | `event ServiceVerified(bytes32 vin, bytes32 metadataHash, address owner)` | ✅ Exceeded | Emits extra `recordIndex` parameter |
| 16 | `event ServiceDisputed(bytes32 vin, bytes32 metadataHash, address owner, string reason)` | ✅ Exceeded | Emits extra `recordIndex` parameter |
| 17 | `event DisputeResolved` on-chain | ✅ Met | Emits `(bytes32 vin, uint256 recordIndex, DisputeDecision decision)` |
| 18 | `event ManualReviewRequired` for major repairs after 90-day timeout | ❌ Not Met | No timeout mechanism implemented. No scheduled task or block-timestamp deadline logic in contracts |
| 19 | `event DisputeEscalated(bytes32 vin, uint256 recordIndex, address serviceCenter, uint256 timestamp)` | ❌ Not Met | No escalation event; dispute goes directly owner → admin resolution |
| 20 | `mapping(address => uint256) disputeCount` for abuse prevention | ❌ Not Met | No per-owner dispute counter. Each record has a `disputed` bool flag |
| 21 | `verifiedByTimeout: true` flag for auto-finalized routine maintenance | ❌ Not Met | No timeout auto-verification. All verification is owner-initiated |
| 22 | `isWarrantyValid(bytes32 vin)` returns `bool` | ✅ Exceeded | Returns `(bool valid, string reason)` — more informative |
| 23 | `submitClaim(bytes32 vin, bytes32 claimDetailsHash)` checks warranty validity AND service history | ⚠️ Partial | On-chain checks warranty validity via `VehicleRegistry`. Service history compliance is enforced in the backend before calling the contract, not on-chain |
| 24 | `getWarrantyStatus(bytes32 vin)` returns `(uint256 expiry, bool isValid)` | ⚠️ Partial | No dedicated `getWarrantyStatus` function. Expiry read from `VehicleRegistry.getVehicle()`; validity from `isWarrantyValid()`. Two calls instead of one |
| 25 | `ClaimSubmitted` event on-chain | ✅ Met | Exact match |
| 26 | `ClaimApproved` event on-chain | ✅ Met | Exact match |
| 27 | `ClaimDenied` event on-chain | ✅ Met | Emits `reasonHash` — matches spec |
| 28 | `MANUFACTURER_ROLE` via OpenZeppelin AccessControl | ✅ Met | Granted on registration and in deploy script |
| 29 | `SERVICE_CENTER_ROLE` via OpenZeppelin AccessControl | ✅ Met | Granted on registration by backend |
| 30 | `OWNER_ROLE` via OpenZeppelin AccessControl | ✅ Met | Granted on vehicle registration; conditionally revoked on transfer |
| 31 | `MANUFACTURER_ADMIN_ROLE` for dispute resolution | ⚠️ Partial | FYP1 specified a dedicated `MANUFACTURER_ADMIN_ROLE`. Current implementation uses `DEFAULT_ADMIN_ROLE` instead. Functionally identical but role name differs from spec |
| 32 | SHA-256 metadata hashing | ✅ Met | `compute_metadata_hash()` in `backend/blockchain/utils.py` uses SHA-256 of key-sorted JSON |
| 33 | OpenZeppelin Ownable base for system admin | ✅ Exceeded | Uses `AccessControl` (OZ) instead of `Ownable`. `AccessControl` is strictly more powerful and appropriate for a multi-role system |
| 34 | Gas optimization via events instead of storage | ✅ Exceeded | Events used throughout; additionally, swap-and-pop O(1) deletion for pending records |
| 35 | Security audit via Slither/MythX static analysis | ❌ Not Met | No static analysis tools run; no audit reports in repo |

---

## Section 2: REST API Endpoints

17 items · **✅ 12 · ⚠️ 2 · ❌ 3**

> Note: FYP1 spec used flat paths (`/api/login`). Actual implementation uses blueprint-prefixed paths (`/api/auth/login`). All functional mappings below note both.

| # | Checklist Item | Status | Notes |
|---|---|---|---|
| 1 | `POST /api/login` | ✅ Met | Implemented as `POST /api/auth/login`. Returns JWT access + refresh tokens |
| 2 | `POST /api/register-vehicle` | ✅ Met | `POST /api/vehicle/register`. MANUFACTURER role required |
| 3 | `GET /api/vehicle/{VIN}` — aggregated blockchain + service data | ✅ Met | `GET /api/vehicle/<vin>`. Enriched with SQLite metadata |
| 4 | `POST /api/submit-service` | ✅ Met | `POST /api/service/submit`. SERVICE_CENTER role required |
| 5 | `GET /api/pending-services/{VIN}` | ✅ Met | `GET /api/service/pending/<vin>` |
| 6 | `POST /api/verify-service` | ✅ Met | `POST /api/service/owner/verify`. OWNER role required |
| 7 | `POST /api/dispute-service` | ✅ Met | `POST /api/service/owner/dispute`. OWNER role required |
| 8 | `GET /api/service-history/{VIN}` | ✅ Met | `GET /api/service/history/<vin>` |
| 9 | `GET /api/check-warranty/{VIN}` | ✅ Met | `GET /api/warranty/check/<vin>`. Returns validity + days remaining |
| 10 | `POST /api/check-warranty-eligibility/{VIN}` | ❌ Not Met | No dedicated eligibility pre-check endpoint. Validity is bundled into the warranty check response |
| 11 | `POST /api/submit-claim` | ✅ Met | `POST /api/warranty/submit-claim`. OWNER role required |
| 12 | `GET /api/claims/{VIN}` | ✅ Met | `GET /api/warranty/claims/<vin>` |
| 13 | `GET /api/owner/vehicles` | ✅ Met | `GET /api/vehicle/owner/vehicles`. OWNER role required |
| 14 | `GET /api/service-center/pending-records` (all SC's records) | ⚠️ Partial | `GET /api/service/pending/<vin>` requires a VIN. There is no "all my pending records across all VINs" endpoint without specifying a VIN. Dealer UI searches per-VIN |
| 15 | `GET /api/manufacturer/dashboard-stats` | ⚠️ Partial | Stats spread across `GET /api/vehicle/stats` (vehicle counts, warranty counts) and `GET /api/sc/my-stats`. Not a single aggregated endpoint matching spec |
| 16 | `POST /api/dispute-response` (SC uploads rebuttal evidence) | ❌ Not Met | Not implemented. Disputes go directly to manufacturer resolution |
| 17 | `POST /api/escalate-dispute` | ❌ Not Met | Not implemented. No escalation step |

**Implemented beyond FYP1 spec:**
- `POST /api/auth/refresh` — token rotation
- `POST /api/auth/logout-all` — revoke all sessions
- `POST /api/auth/device-token` — push notification registration
- `POST /api/vehicle/claim` — owner claims pre-registered vehicle
- `GET /api/vehicle/fleet` — manufacturer's full vehicle list
- `POST /api/service/resolve-dispute` — manufacturer resolves dispute
- `POST /api/warranty/approve-claim` / `POST /api/warranty/deny-claim`
- `GET /api/warranty/owner/claims`
- Full SC management: `GET/POST /api/sc/service-centers`, activate, suspend, fund
- `GET /api/vehicle/public/<vin>` — no-auth public verification
- `GET /api/health` — blockchain connectivity check

---

## Section 3: Backend Infrastructure & Logic

17 items · **✅ 7 · ⚠️ 6 · ❌ 4**

| # | Checklist Item | Status | Notes |
|---|---|---|---|
| 1 | User auth DB — credentials mapped to blockchain addresses | ✅ Met | `User` model: email, bcrypt password_hash, role, blockchain_address |
| 2 | JWT session token generation and validation | ✅ Exceeded | 60-min access tokens + 30-day refresh tokens with rotation. NIST-compliant password policy. Account lockout after 5 failures |
| 3 | Encrypted keystore for private keys | ✅ Met | Fernet symmetric encryption. Keys stored in `backend/keystore/keys.json` |
| 4 | Key rotation policies and access logging | ⚠️ Partial | Encryption key is configurable via env var (rotation possible). No formal key rotation schedule or access audit log implemented |
| 5 | Web3.py transaction signing (load key → sign → submit → receipt) | ✅ Met | `sign_and_send()` in `blockchain/client.py`. Nonce management included |
| 6 | User-friendly error translation | ✅ Met | Blockchain revert errors translated to human messages throughout service layer |
| 7 | Event listener: `ServiceSubmitted` → push notification to owner | ⚠️ Partial | Daemon thread monitors the event. Device tokens stored in DB. **No actual push delivery** (no Firebase/APNs integration) |
| 8 | Event listener: `ServiceVerified` → notify service centre | ⚠️ Partial | Event monitored. No delivery backend |
| 9 | Event listener: `ServiceDisputed` → escalation notification to manufacturer | ⚠️ Partial | Event monitored. No delivery backend |
| 10 | Off-chain metadata storage (photos + service data) via SHA-256 hash | ✅ Met | `ServiceMetadata` table + `uploads/` directory. Files up to 16 MB |
| 11 | IPFS hash storage for large files | ❌ Not Met | Files stored locally in `uploads/`. No IPFS integration |
| 12 | Pending record timeout logic (30/60/90-day reminders + auto-finalize) | ❌ Not Met | No scheduled tasks or cron jobs. No timeout logic in contracts or backend |
| 13 | Service centre dispute rate tracking (flag >10%) | ❌ Not Met | No per-SC dispute rate calculation |
| 14 | Manufacturer dashboard cache | ⚠️ Partial | Stats computed on-demand from blockchain. No explicit cache layer (Redis etc.) |
| 15 | Biometric auth mapping to email/password account | ❌ Not Met | Not implemented anywhere in the stack |
| 16 | Push notification system for mobile (pending verifications) | ⚠️ Partial | Infrastructure complete: `POST /api/auth/device-token`, `DeviceToken` model, platform field. **No FCM/APNs delivery** |
| 17 | Off-chain claim data + photo storage + `claimDetailsHash` generation | ✅ Met | `WarrantyClaimMetadata` table + `compute_metadata_hash()` |

---

## Section 4: Web App UI — Service Centre & Manufacturer

15 items · **✅ 3 · ⚠️ 9 · ❌ 3**

| # | Checklist Item | Status | Notes |
|---|---|---|---|
| 1 | Login: email/password + "remember me" + "forgot password" + blockchain green dot indicator | ⚠️ Partial | Email/password + visibility toggle: ✓. Blockchain status dot: ✓ (on dashboards, not login page). **"Remember me" and "Forgot password": not implemented** |
| 2 | JWT in localStorage, redirect to role-specific dashboard | ✅ Met | Stored under key `token`. Redirects to `/manufacturer/dashboard` or `/dealer/dashboard` |
| 3 | VIN search results card with Make/Model/Year, Owner, Warranty badge, service count, "Blockchain Verified" badge | ⚠️ Partial | Vehicle lookup shows Make/Model/Year, owner address, status. **No service count in results. No "Blockchain Verified" checkmark badge on dealer lookup** (present on public verify page) |
| 4 | "Submit New Service" button inline on vehicle lookup | ⚠️ Partial | Separate submit-service page exists. No inline CTA on the lookup results card |
| 5 | Service submission form: VIN (read-only), date, mileage, service type, ECU, parts, technician dropdown, notes, photo upload (up to 5) | ⚠️ Partial | Has all text fields. **Photo upload absent. VIN is editable, not read-only. Technician is a free-text field, not a dropdown** |
| 6 | Auto-calculated SHA-256 hash display (collapsible "Advanced" section) | ⚠️ Partial | Hash shown in the success message after submission. **Not displayed in the form itself. No collapsible "Advanced" section** |
| 7 | "Submit for Owner Verification" CTA with confirmation message | ✅ Met | "Submit Record" button with success confirmation showing hash and verification note |
| 8 | Pending records table: Record ID, VIN (last 6), date, type, status badge, days pending, "View Details" | ⚠️ Partial | Shows type, VIN, date, mileage, days pending with colour-coded age badges. **No Record ID column. No "View Details" link per row** |
| 9 | Filter by All/Pending/Verified/Disputed and search by VIN | ⚠️ Partial | VIN search is implemented. **No filter tabs for status (All/Pending/Verified/Disputed)** |
| 10 | Escalation warning highlighting for records pending 30+ days | ✅ Met | Age-based badge styling: fresh < 7 days (green), warning < 30 days (amber), old ≥ 30 days (red) |
| 11 | Manufacturer overview cards: total vehicles, active warranties, pending claims, verified services this month | ⚠️ Partial | Cards show: Total vehicles, Active service centres, Pending approvals, Warranty claims. **"Verified services this month" card is missing** |
| 12 | Charts: warranty claim trend (line), service type distribution (pie), top SCs by volume (bar) | ❌ Not Met | No charts on manufacturer dashboard. `ng2-charts` + `Chart.js` included in dependencies but not wired up on dashboard |
| 13 | Recent activity feed (registrations, claims, disputes) | ❌ Not Met | Not implemented |
| 14 | "Export Audit Report" PDF button | ❌ Not Met | Not implemented anywhere in web app |
| 15 | Transaction hash / block number viewable (hidden by default) | ⚠️ Partial | Transaction hashes shown in success messages (truncated to 18 chars). Not persistently displayed per record |

---

## Section 5: Mobile App UI — Vehicle Owner

13 items · **✅ 2 · ⚠️ 9 · ❌ 2**

> FYP1 referenced "5 screens". The Flutter app implements **11 distinct screens**: Login, Register, My Vehicles, Vehicle Detail, Claim Vehicle, Transfer Vehicle, Pending Services, Service History, Warranty Claims, Submit Claim, Profile, Change Password.

| # | Checklist Item | Status | Notes |
|---|---|---|---|
| 1 | Owner login: email/phone + password, fingerprint/Face ID biometric option | ⚠️ Partial | Email + password login: ✓. **No biometric option** |
| 2 | JWT in secure mobile storage, push notification permission after login | ⚠️ Partial | `flutter_secure_storage` used for JWT: ✓. **No push notification permission dialog after login** |
| 3 | My Vehicles: vehicle photo, Make/Model/Year, VIN (last 6), warranty badge, pending verification red dot badge | ⚠️ Partial | Cards with display name, VIN, warranty icon badge: ✓. **No vehicle photo. No pending verification red dot badge** |
| 4 | Vehicle detail: full VIN with copy button, warranty coverage, "View Service History" + "File Warranty Claim" buttons | ⚠️ Partial | Detail screen with VIN, warranty status, warranty claim button: ✓. **No copy-to-clipboard on VIN. No "View Service History" button on detail screen** |
| 5 | Pending service card: SC name, date, type, mileage, parts, technician, expandable notes, swipeable photo gallery | ⚠️ Partial | Shows type, date, mileage, technician, parts, notes: ✓. **No service centre name (address shown). No photo gallery. Notes shown directly, not in expand** |
| 6 | Metadata hash in collapsible "Technical Details" section | ❌ Not Met | No hash displayed on pending services screen |
| 7 | "✓ Approve Service" (green) and "✗ Dispute Service" (red) buttons with "permanently recorded" helper text | ✅ Met | "Verify" (green) and "Dispute" (red) buttons on every pending service card |
| 8 | Dispute modal with reason textarea and "Submit Dispute" button | ✅ Met | `AlertDialog` with required `TextField` (max 3 lines), validated before submission |
| 9 | Service history timeline — vertical, date, type icon, SC name, mileage, "✓ Verified" badge, expandable details | ⚠️ Partial | `ExpansionTile` list with date, type, status badge, expandable details: ✓. **No vertical timeline connector. No service centre name. No type icon** |
| 10 | "Export History" PDF generation button | ❌ Not Met | Not implemented |
| 11 | Warranty eligibility auto-check: status badge + required maintenance checklist | ⚠️ Partial | Warranty status badge shown on vehicle detail: ✓. **No dedicated eligibility checklist screen** |
| 12 | Warranty claim form: issue description textarea + photo upload | ⚠️ Partial | Issue description textarea (min 20 chars) on submit claim screen: ✓. **No photo upload** |
| 13 | Claims history: Claim ID, date filed, status badge, denial reason, "View Details" link | ⚠️ Partial | VIN, issue description, date, status badge, denial reason in red box: ✓. **No Claim ID. No "View Details" link** |

---

## Section 6: Ganache Setup & Deployment Simulation

13 items · **✅ 4 · ⚠️ 2 · ❌ 7**

| # | Checklist Item | Status | Notes |
|---|---|---|---|
| 1 | Ganache private network with pre-funded accounts per role | ✅ Met | `ganache --port 8545 --chainId 1337 --deterministic` gives reproducible accounts |
| 2 | Deploy VehicleRegistry, ServiceLog, WarrantyTracker to Ganache | ✅ Met | `scripts/deploy.js` deploys all three and grants `SERVICE_LOG_ROLE` |
| 3 | Grant MANUFACTURER_ROLE, SERVICE_CENTER_ROLE, OWNER_ROLE to designated addresses | ✅ Met | Roles granted in deploy script + backend `auth_service.register_user()` |
| 4 | Register 10 test vehicles with varying warranty periods | ❌ Not Met | No seed/fixture script for pre-populating test data |
| 5 | Log 50+ service events (routine + major repairs) | ❌ Not Met | No simulation script |
| 6 | Simulate 80% owner approvals, 5% disputes, remainder auto-timeout | ❌ Not Met | No simulation script; auto-timeout not implemented |
| 7 | Submit warranty claims and test eligibility and approval flows | ⚠️ Partial | Backend test suite covers claim submission, approval, denial. No standalone simulation script for a full demo run |
| 8 | Simulate timeout scenarios (30/60/90-day marks) | ❌ Not Met | Timeout mechanism not implemented |
| 9 | Simulate fraudulent claim rejection scenario | ❌ Not Met | No simulation script |
| 10 | Simulate ownership transfer scenario | ⚠️ Partial | Transfer fully implemented and tested. No standalone demonstration script |
| 11 | Record transaction times, gas consumption, throughput metrics | ❌ Not Met | No benchmarking or performance profiling scripts |
| 12 | Angular web app + Flutter app running locally, connected to backend | ✅ Met | Both apps run. Flutter confirmed on Android emulator |
| 13 | End-to-end demo video/scripts covering all core flows | ❌ Not Met | No demo scripts or recorded walkthroughs |

---

## Section 7: Testing Requirements

13 items · **✅ 4 · ⚠️ 2 · ❌ 7**

| # | Checklist Item | Status | Notes |
|---|---|---|---|
| 1 | Smart contract unit tests: RBAC enforcement (non-manufacturer cannot register) | ✅ Met | Hardhat tests verify role enforcement for all three contracts |
| 2 | Smart contract unit tests: pending-to-verified state transitions | ✅ Met | Full submit → verify flow tested; service hash written to VehicleRegistry verified |
| 3 | Smart contract unit tests: dispute escalation workflows | ✅ Met | Dispute → approve and dispute → reject both covered |
| 4 | Smart contract unit tests: warranty validity calculations | ⚠️ Partial | Expiry-based validity tested. **No mileage or service-compliance tests** (those are enforced in backend, not on-chain) |
| 5 | Smart contract unit tests: edge cases (timeouts, duplicate submissions, invalid VINs) | ⚠️ Partial | Duplicate VIN registration rejection tested. **No timeout tests** (feature unimplemented). Invalid VIN edge cases not explicitly tested (VINs are keccak-hashed before reaching contracts) |
| 6 | >90% smart contract line coverage | ❌ Not Met | No coverage report generated. 20+ tests across 3 contracts are present but coverage percentage unmeasured |
| 7 | Integration / end-to-end tests: register → submit → verify → view history | ✅ Met | `backend/tests/test_integration.py` covers the full flow. Backend suite: 142 tests all passing |
| 8 | Security analysis with Slither | ❌ Not Met | Not run |
| 9 | Security analysis with MythX | ❌ Not Met | Not run |
| 10 | Usability testing: 5–10 participants per stakeholder group | ❌ Not Met | Academic activity, not yet conducted |
| 11 | Usability tasks: log oil change, verify service, dispute entry, review warranty claim | ❌ Not Met | Not conducted |
| 12 | SUS questionnaire, target score > 70 | ❌ Not Met | Not conducted |
| 13 | UI iteration based on usability findings | ❌ Not Met | Not conducted |

**Current test counts:**
- Smart contract tests: 22 passing (Hardhat/Chai)
- Backend tests: 142 passing (pytest)
- Flutter unit tests: 88 passing (Mockito + flutter_test)

---

## Architecture Decisions That Diverge From FYP1 Spec

These are intentional design improvements, not omissions. They should be documented as design evolutions in the FYP2 report.

### 1. `pendingServices[]` moved out of `VehicleRegistry`
FYP1 placed pending services in the `Vehicle` struct inside `VehicleRegistry`. The implementation keeps them in `ServiceLog`. This is architecturally cleaner — `VehicleRegistry` is the ownership and finalized-hash store; `ServiceLog` owns the mutable pending state. The on-chain separation reduces coupling and avoids VehicleRegistry becoming a god contract.

### 2. `MANUFACTURER_ADMIN_ROLE` → `DEFAULT_ADMIN_ROLE`
FYP1 specified a separate `MANUFACTURER_ADMIN_ROLE`. Using `DEFAULT_ADMIN_ROLE` is functionally equivalent for a single-admin deployment (Ganache) and avoids an extra role grant in the deploy script. If the system scales to multiple manufacturers, a dedicated role should be added.

### 3. `OpenZeppelin Ownable` → `AccessControl`
FYP1 specified `Ownable` as the admin base. `AccessControl` is strictly more powerful: it supports multiple roles, role-based revocation, and role hierarchies. This was the right call for a multi-role system.

### 4. `getServiceHistory` → `getFinalizedServices`
Renamed for semantic clarity. Finalized records are those that completed the verification pipeline. The name `getServiceHistory` was too generic.

### 5. Technician field off-chain
The `ServiceRecord` struct on-chain doesn't include `technician`. Technician data is stored in `ServiceMetadata` SQLite and linked by `metadataHash`. This saves gas — only the hash is immutable; the human-readable metadata is verifiable by recomputing the hash.

### 6. Service eligibility check in backend, not on-chain
FYP1 specified `submitClaim` should check service history compliance on-chain. Doing this on-chain would require expensive iteration over the `serviceHashes` array. The backend validates compliance before calling the contract, which is the standard pattern (oracle pattern).

---

## Priority Gap Analysis for FYP2

### High Priority (Core Demo / Submission Requirements)

| Gap | Effort | Why Important |
|---|---|---|
| Charts on manufacturer dashboard (line, pie, bar) | Medium | Explicitly in FYP1 spec; visually prominent in report |
| Simulation/seed scripts (10 vehicles, 50+ services) | Medium | Required for the Ganache demo section of FYP2 |
| Transaction times + gas consumption metrics | Low | Required for performance evaluation in FYP2 report |
| End-to-end demo script covering all core flows | Low | Needed for evaluation/demonstration |
| Service type distribution and warranty trend data in dashboard | Medium | Ties into charts gap |

### Medium Priority (Feature Completeness)

| Gap | Effort | Why Important |
|---|---|---|
| Photo upload in service submission form (web) | Medium | Listed in FYP1 spec; improves demo quality |
| Photo upload in Flutter claim submission | Medium | Listed in FYP1 spec |
| Timeline UI for service history (Flutter) | Low | Visual polish; FYP1 explicitly described vertical timeline |
| Metadata hash display in Flutter pending services ("Technical Details") | Low | Shows blockchain transparency to owner |
| VIN copy button on vehicle detail (Flutter) | Low | Mentioned in FYP1 spec |
| "View Service History" button on vehicle detail → service history tab | Low | Navigation gap |
| Claim ID in warranty claims list | Low | Referenced in FYP1 spec |
| Filter tabs on dealer pending records (All/Pending/Verified/Disputed) | Low | Mentioned in FYP1 spec |
| SHA-256 hash in service submission form (collapsible) | Low | FYP1 spec shows this in the form, not the success message |
| `getWarrantyStatus` returning `(uint256 expiry, bool isValid)` | Low | Minor contract addition |
| Hardhat coverage report | Low | Required for ">90% coverage" claim |

### Lower Priority (Research/Formal Requirements)

| Gap | Effort | Why Important |
|---|---|---|
| Slither static analysis | Low | FYP2 report security section |
| `disputeCount` mapping for abuse prevention | Medium | Described in FYP1; improves system integrity |
| `DisputeEscalated` event | Low | Adds escalation audit trail |
| Separate `MANUFACTURER_ADMIN_ROLE` | Low | Matches FYP1 spec exactly |
| `MODIFY` variant in `DisputeDecision` enum | Low | Contract change; backend + frontend support needed |
| Usability study (5–10 participants, SUS) | High | Academic requirement for FYP2 |
| "Forgot password" flow on login | Medium | UX gap noted in FYP1 |
| Push notification delivery (Firebase) | High | Significant integration; device token infra already done |
| 30/60/90-day timeout backend logic | High | Complex scheduled task; significant backend work |

---

## Summary

The blockchain core of the system — three Solidity contracts, a 40-endpoint Flask API, and a 122-test suite — is **production-ready as a proof of concept**. The smart contract layer implements all primary on-chain operations with OpenZeppelin AccessControl, proper event emission, and gas-efficient patterns. The backend exceeds FYP1 in authentication security (refresh token rotation, rate limiting, account lockout, encrypted keystore, security headers) and in role/workflow management (service centre lifecycle, vehicle claim flow, brand validation).

The gaps fall into three clear categories:
1. **Demo/simulation scripts** — no Ganache seeder or performance benchmarks (straightforward to add before FYP2 submission)
2. **UI polish** — photo upload, PDF export, timeline view, charts (scoped work, each self-contained)
3. **Formal academic requirements** — usability study, SUS questionnaire, Slither analysis (planned activities, not code gaps)

The 22 features built beyond FYP1 scope — especially service centre management, vehicle claim flow, encrypted keystore, token rotation, and the Leaflet map — represent a genuine improvement over the original plan and should be highlighted in the FYP2 report as system enhancements.
