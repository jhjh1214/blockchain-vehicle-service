# Smart Contracts — Blockchain Vehicle Service

Solidity smart contracts for vehicle registration, service verification, and warranty claim management. Built with Hardhat and OpenZeppelin.

---

## Overview

Three contracts form the on-chain layer of the vehicle service system:

| Contract | Purpose |
|---|---|
| `VehicleRegistry` | Core registry — vehicle ownership, warranty expiry, finalized service hashes |
| `ServiceLog` | Two-stage service verification pipeline (submit → verify/dispute → resolve) |
| `WarrantyTracker` | Warranty validity checks and claim lifecycle management |

All contracts use OpenZeppelin `AccessControl` for role-based permissions. No raw strings are stored on-chain — all sensitive data is represented as `bytes32` hashes.

---

## Contracts

### VehicleRegistry

The authoritative source of truth for vehicle ownership and warranty status.

**State per VIN:**
- `owner` — current owner address
- `warrantyStart` / `warrantyExpiry` — Unix timestamps
- `serviceHashes` — array of SHA-256 service record hashes (written on finalization)

**Key methods:**

| Method | Required role | Description |
|---|---|---|
| `registerVehicle(vin, owner, warrantyExpiry)` | MANUFACTURER_ROLE | Register a new vehicle |
| `transferOwnership(vin, newOwner)` | OWNER_ROLE | Transfer vehicle to a new owner |
| `adminTransferOwnership(vin, newOwner)` | DEFAULT_ADMIN_ROLE | Admin transfer (used for vehicle claim flow) |
| `addServiceHash(vin, serviceHash)` | SERVICE_LOG_ROLE | Append a finalized service hash (called by ServiceLog) |
| `getVehicle(vin)` | anyone | Read all vehicle fields |
| `getOwnedVehicles(owner)` | anyone | List all VIN hashes owned by an address |

**Events:** `VehicleRegistered`, `OwnershipTransferred`, `ServiceHashAdded`

---

### ServiceLog

Manages the lifecycle of service records from submission to on-chain finalization.

**Record states:**
- **Pending** — submitted by service centre, awaiting owner action
- **Verified** (finalized) — approved by owner, hash written to VehicleRegistry
- **Disputed** — flagged by owner, awaiting manufacturer resolution

**Key methods:**

| Method | Required role | Description |
|---|---|---|
| `submitService(vin, metadataHash)` | SERVICE_CENTER_ROLE | Submit a new pending service record |
| `verifyService(vin, recordIndex)` | OWNER_ROLE | Approve record → finalize on-chain |
| `disputeService(vin, recordIndex, reason)` | OWNER_ROLE | Flag a record for review |
| `resolveDispute(vin, recordIndex, decision, resolutionHash)` | DEFAULT_ADMIN_ROLE | Approve (1) or reject (2) a disputed record |
| `getPendingServices(vin)` | anyone | Array of pending `ServiceRecord` structs |
| `getFinalizedServices(vin)` | anyone | Array of finalized `ServiceRecord` structs |

**Enum `DisputeDecision`:** `PENDING=0`, `APPROVE=1`, `REJECT=2`

> **Important — swap-and-pop:** Pending record removal uses swap-and-pop for O(1) gas cost. Record indices shift after any removal. Always re-fetch from the chain after mutating operations; never cache indices.

**Events:** `ServiceSubmitted`, `ServiceVerified`, `ServiceDisputed`, `DisputeResolved`

---

### WarrantyTracker

Reads warranty expiry from `VehicleRegistry` and manages the claim lifecycle.

**Key methods:**

| Method | Required role | Description |
|---|---|---|
| `isWarrantyValid(vin)` | anyone | Returns `{ valid, reason }` vs current timestamp |
| `submitClaim(vin, claimDetailsHash)` | OWNER_ROLE | Submit a new warranty claim |
| `approveClaim(vin, claimIndex)` | DEFAULT_ADMIN_ROLE | Approve a pending claim |
| `denyClaim(vin, claimIndex, reasonHash)` | DEFAULT_ADMIN_ROLE | Deny a claim with reason hash |
| `getClaims(vin)` | anyone | Array of all `WarrantyClaim` structs for a VIN |

**Enum `ClaimStatus`:** `PENDING=0`, `APPROVED=1`, `DENIED=2`

**Events:** `ClaimSubmitted`, `ClaimApproved`, `ClaimDenied`

---

## Role Summary

| Role | Assigned to | Rights |
|---|---|---|
| `DEFAULT_ADMIN_ROLE` | Deployer EOA | Grant/revoke all roles, dispute resolution, claim approval/denial, admin transfers |
| `MANUFACTURER_ROLE` | Manufacturer wallet | Register vehicles |
| `SERVICE_CENTER_ROLE` | Service centre wallet | Submit service records |
| `OWNER_ROLE` | Vehicle owner wallet | Transfer ownership, verify/dispute services, submit warranty claims |
| `SERVICE_LOG_ROLE` | ServiceLog contract address | Write service hashes to VehicleRegistry (granted automatically by deploy script) |

---

## Prerequisites

- Node.js 18+ and npm
- Ganache for local network deployment: `npm install -g ganache`

---

## Setup

```bash
cd smart-contracts
npm install
```

---

## Compile

```bash
npx hardhat compile
```

Compiled artifacts land in `artifacts/contracts/`. The backend requires three ABI JSON files:

```powershell
# Windows — run from smart-contracts/
Copy-Item "artifacts\contracts\VehicleRegistry.sol\VehicleRegistry.json" "..\backend\abis\"
Copy-Item "artifacts\contracts\ServiceLog.sol\ServiceLog.json"           "..\backend\abis\"
Copy-Item "artifacts\contracts\WarrantyTracker.sol\WarrantyTracker.json" "..\backend\abis\"
```

---

## Test

Tests run against Hardhat's in-memory EVM — no Ganache required.

```bash
npx hardhat test
```

| Area | What is tested |
|---|---|
| VehicleRegistry — register | VIN registration, duplicate rejection, event emission |
| VehicleRegistry — roles | MANUFACTURER_ROLE enforcement, unauthorised caller rejection |
| VehicleRegistry — ownership | transferOwnership, adminTransferOwnership |
| ServiceLog — submit | SERVICE_CENTER_ROLE enforcement |
| ServiceLog — verify | OWNER_ROLE enforcement, service hash written to VehicleRegistry |
| ServiceLog — dispute & resolve | Full dispute flow, approve and reject outcomes |
| WarrantyTracker — validity | Active and expired warranty checks |
| WarrantyTracker — claims | Submit, approve, deny lifecycle |
| Multi-vehicle | Owner retains OWNER_ROLE across multiple registered VINs |

**Expected: 20+ passing**

---

## Deploy to Ganache

Start Ganache in a dedicated terminal:

```bash
ganache --port 8545 --chainId 1337 --deterministic
```

`--deterministic` produces the same 10 HD-wallet accounts every restart, which keeps `backend/.env` stable.

Deploy all contracts:

```bash
npx hardhat run scripts/deploy.js --network ganache
```

Output:

```
VehicleRegistry deployed to: 0x...
ServiceLog deployed to:      0x...
WarrantyTracker deployed to: 0x...
SERVICE_LOG_ROLE granted to ServiceLog
```

Copy the three addresses into `backend/.env`. The deploy script automatically grants `SERVICE_LOG_ROLE` to the ServiceLog contract so it can write service hashes to VehicleRegistry.

---

## Network Configuration

```javascript
// hardhat.config.js
module.exports = {
  solidity: "0.8.28",
  networks: {
    ganache: {
      url: "http://127.0.0.1:8545",
      chainId: 1337
    }
  }
};
```

For a testnet or mainnet, add the network configuration with an RPC URL and pass `--network <name>` to the deploy command.

---

## Hashing Convention

The backend pre-hashes all data before sending to contracts:

| Data | Hash algorithm | Notes |
|---|---|---|
| VIN string | `keccak256(abi.encodePacked(vin))` | Used as the on-chain vehicle key (`bytes32`) |
| Service metadata | SHA-256 of key-sorted JSON | Computed in `backend/blockchain/utils.py` |
| Warranty claim details | SHA-256 | Same utility |
| Dispute reason / resolution notes | SHA-256 | Stored on-chain as `bytes32` |

Raw strings never appear in contract storage. SQLite holds the originals, which can be independently verified by recomputing the hash and comparing.

---

## Dependencies

```json
{
  "hardhat": "^2.28.6",
  "@nomicfoundation/hardhat-toolbox": "^5.0.0",
  "@openzeppelin/contracts": "^5.0.0"
}
```
