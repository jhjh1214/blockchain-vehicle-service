# Slither Static Analysis Report

**Tool:** slither-analyzer v0.11.5  
**Date:** 2026-05-27  
**Contracts analysed:** ServiceLog, VehicleRegistry, WarrantyTracker (Lock.sol excluded)  
**Total detectors run:** 101  **Findings:** 6

---

## Finding 1 — `immutable-states` (Informational) ✅ Fixed

| Field | Detail |
|---|---|
| Severity | Informational |
| Detector | `immutable-states` |
| Contracts | `ServiceLog`, `WarrantyTracker` |

`vehicleRegistry` is set once in the constructor and never reassigned. Declaring it `immutable` saves gas on every read (SLOAD → inline constant).

**Resolution:** Added `immutable` keyword to both declarations.

---

## Finding 2 — `unused-return` (Low) ✅ Accepted / False-positive

| Field | Detail |
|---|---|
| Severity | Low |
| Detector | `unused-return` |
| Contracts | `ServiceLog`, `WarrantyTracker` |

Slither flags tuple destructuring such as `(vehicleOwner,,,, bool exists) = vehicleRegistry.getVehicle(vin)` because unnamed slots are discarded. This is intentional Solidity syntax; only `vehicleOwner` and `exists` are needed. There is no return value being silently ignored — the unnamed slots are documentation that the value is not used.

**Resolution:** Accepted as false-positive. No code change needed.

---

## Finding 3 — `reentrancy-events` (Low) ✅ Accepted / Not exploitable

| Field | Detail |
|---|---|
| Severity | Low |
| Detector | `reentrancy-events` |
| Contracts | `ServiceLog` |
| Functions | `verifyService`, `resolveDispute` |

An external call to `vehicleRegistry.addServiceHash()` is made before the `ServiceVerified` / `DisputeResolved` event is emitted. Slither classifies this as a potential reentrancy-event ordering issue.

**Why not exploitable:**
- The external call target is `VehicleRegistry`, a contract deployed and owned by the same admin.
- All state changes (record moved to finalized, swap-and-pop deletion) occur *before* the external call.
- The `addServiceHash` function on `VehicleRegistry` only pushes to a `bytes32[]` array and emits an event — it cannot re-enter `ServiceLog`.
- Standard checks-effects-interactions is satisfied for state mutations; only event emission follows the call.

**Resolution:** Accepted as not exploitable in this trust model. Added inline comment in code.

---

## Finding 4 — `timestamp` (Informational) ✅ Accepted / By design

| Field | Detail |
|---|---|
| Severity | Informational |
| Detector | `timestamp` |
| Contracts | `VehicleRegistry`, `WarrantyTracker` |

`block.timestamp` is used to compare warranty expiry (`block.timestamp > warrantyExpiry`). Miners can manipulate `block.timestamp` by a few seconds. For a warranty system where expiry is measured in months/years, a ±15-second miner manipulation is negligible.

**Resolution:** Accepted. Documented in system design section of FYP report.

---

## Finding 5 — `pragma` (Informational) ✅ Accepted / Dependency-only

| Field | Detail |
|---|---|
| Severity | Informational |
| Detector | `pragma` |

Four pragma versions appear across the dependency tree (OpenZeppelin uses `^0.8.20`, `>=0.8.4`, `>=0.4.16`). All our contracts use `^0.8.20`. The wider version ranges are in OZ library headers and cannot be changed.

**Resolution:** Accepted. No action required on application contracts.

---

## Finding 6 — `solc-version` (Informational) ✅ Accepted / Known OZ behaviour

| Field | Detail |
|---|---|
| Severity | Informational |
| Detector | `solc-version` |

Slither warns that `^0.8.20` encompasses historical compiler versions with known bugs. All listed bugs (`VerbatimInvalidDeduplication`, `FullInlinerNonExpressionSplitArgumentEvaluationOrder`, `MissingSideEffectsOnSelectorAccess`) were fixed in 0.8.21+. We compile with Hardhat's pinned `0.8.28` which is unaffected.

**Resolution:** Accepted. Compilation target is 0.8.28 (safe).

---

## Summary

| Finding | Severity | Action |
|---|---|---|
| `vehicleRegistry` should be `immutable` | Informational | **Fixed** |
| Unused tuple return slots | Low | Accepted (false-positive) |
| Reentrancy-events in `verifyService` / `resolveDispute` | Low | Accepted (not exploitable) |
| `block.timestamp` used for expiry | Informational | Accepted (by design) |
| Pragma version range | Informational | Accepted (dependency-only) |
| Compiler version range | Informational | Accepted (pinned to 0.8.28) |

**Conclusion:** No high or critical severity findings. The two low-severity findings are either false-positives or accepted risks with documented rationale. The `immutable` fix was applied.
