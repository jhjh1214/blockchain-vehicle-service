// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "./VehicleRegistry.sol";

contract ServiceLog is AccessControl {
    bytes32 public constant SERVICE_CENTER_ROLE = keccak256("SERVICE_CENTER_ROLE");
    bytes32 public constant MANUFACTURER_ADMIN_ROLE = keccak256("MANUFACTURER_ADMIN_ROLE");

    VehicleRegistry public immutable vehicleRegistry;

    struct ServiceRecord {
        bytes32 vin;
        bytes32 metadataHash;
        uint256 timestamp;
        address serviceCenter;
        bool verified;
        bool disputed;
        string disputeReason;
    }

    struct DisputeResolution {
        address resolver;
        uint256 timestamp;
        DisputeDecision decision;
        bytes32 resolutionNotesHash;
    }

    enum DisputeDecision { PENDING, APPROVE, REJECT, MODIFY }

    mapping(bytes32 => ServiceRecord[]) public pendingServices;
    mapping(bytes32 => ServiceRecord[]) public finalizedServices;
    // vin => metadataHash => resolution (stable key, unaffected by array reordering)
    mapping(bytes32 => mapping(bytes32 => DisputeResolution)) public disputeResolutions;
    mapping(address => uint256) public disputeCount;

    event ServiceSubmitted(bytes32 indexed vin, bytes32 metadataHash, uint256 timestamp, address serviceCenter);
    event ServiceVerified(bytes32 indexed vin, bytes32 metadataHash, address owner, uint256 finalizedIndex);
    event ServiceDisputed(bytes32 indexed vin, bytes32 metadataHash, address owner, string reason);
    event DisputeResolved(bytes32 indexed vin, bytes32 metadataHash, DisputeDecision decision);

    constructor(address _vehicleRegistry) {
        vehicleRegistry = VehicleRegistry(_vehicleRegistry);
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MANUFACTURER_ADMIN_ROLE, msg.sender);
    }

    // ── Internal helpers ──────────────────────────────────────────────────────

    function _findPending(bytes32 vin, bytes32 metadataHash)
        internal view returns (uint256 index, bool found)
    {
        ServiceRecord[] storage records = pendingServices[vin];
        for (uint256 i = 0; i < records.length; i++) {
            if (records[i].metadataHash == metadataHash) {
                return (i, true);
            }
        }
        return (0, false);
    }

    function _removePendingAt(bytes32 vin, uint256 index) internal {
        ServiceRecord[] storage records = pendingServices[vin];
        records[index] = records[records.length - 1];
        records.pop();
    }

    // ── Write functions ───────────────────────────────────────────────────────

    function submitService(bytes32 vin, bytes32 metadataHash)
        external onlyRole(SERVICE_CENTER_ROLE)
    {
        (,,,, bool exists) = vehicleRegistry.getVehicle(vin);
        require(exists, "Vehicle not registered");
        require(!_isDuplicate(vin, metadataHash), "Duplicate service record");

        pendingServices[vin].push(ServiceRecord({
            vin: vin,
            metadataHash: metadataHash,
            timestamp: block.timestamp,
            serviceCenter: msg.sender,
            verified: false,
            disputed: false,
            disputeReason: ""
        }));
        emit ServiceSubmitted(vin, metadataHash, block.timestamp, msg.sender);
    }

    function verifyService(bytes32 vin, bytes32 metadataHash) external {
        (address vehicleOwner,,,, bool exists) = vehicleRegistry.getVehicle(vin);
        require(exists, "Vehicle not registered");
        require(
            vehicleRegistry.hasRole(vehicleRegistry.OWNER_ROLE(), msg.sender) || vehicleOwner == msg.sender,
            "Not the vehicle owner"
        );

        (uint256 idx, bool found) = _findPending(vin, metadataHash);
        require(found, "Service record not found");
        require(!pendingServices[vin][idx].verified, "Already verified");
        require(!pendingServices[vin][idx].disputed, "Record is disputed");

        pendingServices[vin][idx].verified = true;
        bytes32 capturedHash = pendingServices[vin][idx].metadataHash;

        finalizedServices[vin].push(pendingServices[vin][idx]);
        vehicleRegistry.addServiceHash(vin, capturedHash);
        _removePendingAt(vin, idx);

        emit ServiceVerified(vin, capturedHash, msg.sender, finalizedServices[vin].length - 1);
    }

    function disputeService(bytes32 vin, bytes32 metadataHash, string memory reason) external {
        (address vehicleOwner,,,, bool exists) = vehicleRegistry.getVehicle(vin);
        require(exists, "Vehicle not registered");
        require(
            vehicleRegistry.hasRole(vehicleRegistry.OWNER_ROLE(), msg.sender) || vehicleOwner == msg.sender,
            "Not the vehicle owner"
        );

        (uint256 idx, bool found) = _findPending(vin, metadataHash);
        require(found, "Service record not found");
        require(!pendingServices[vin][idx].disputed, "Already disputed");

        pendingServices[vin][idx].disputed = true;
        pendingServices[vin][idx].disputeReason = reason;
        disputeCount[msg.sender] += 1;

        emit ServiceDisputed(vin, metadataHash, msg.sender, reason);
    }

    function resolveDispute(
        bytes32 vin,
        bytes32 metadataHash,
        DisputeDecision decision,
        bytes32 resolutionNotesHash
    ) external onlyRole(MANUFACTURER_ADMIN_ROLE) {
        (uint256 idx, bool found) = _findPending(vin, metadataHash);
        require(found, "Service record not found");
        require(pendingServices[vin][idx].disputed, "Not a disputed record");

        disputeResolutions[vin][metadataHash] = DisputeResolution({
            resolver: msg.sender,
            timestamp: block.timestamp,
            decision: decision,
            resolutionNotesHash: resolutionNotesHash
        });

        if (decision == DisputeDecision.APPROVE) {
            pendingServices[vin][idx].verified = true;
            bytes32 capturedHash = pendingServices[vin][idx].metadataHash;
            finalizedServices[vin].push(pendingServices[vin][idx]);
            vehicleRegistry.addServiceHash(vin, capturedHash);
            _removePendingAt(vin, idx);
        } else if (decision == DisputeDecision.REJECT) {
            _removePendingAt(vin, idx);
        }

        emit DisputeResolved(vin, metadataHash, decision);
    }

    // ── Read functions ────────────────────────────────────────────────────────

    function getPendingServices(bytes32 vin) external view returns (ServiceRecord[] memory) {
        return pendingServices[vin];
    }

    function getFinalizedServices(bytes32 vin) external view returns (ServiceRecord[] memory) {
        return finalizedServices[vin];
    }

    // ── Internal utils ────────────────────────────────────────────────────────

    function _isDuplicate(bytes32 vin, bytes32 metadataHash) internal view returns (bool) {
        ServiceRecord[] storage records = pendingServices[vin];
        for (uint256 i = 0; i < records.length; i++) {
            if (records[i].metadataHash == metadataHash) return true;
        }
        return false;
    }
}
