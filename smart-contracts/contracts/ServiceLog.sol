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
    mapping(bytes32 => mapping(uint256 => DisputeResolution)) public disputeResolutions;
    mapping(address => uint256) public disputeCount;

    event ServiceSubmitted(bytes32 indexed vin, bytes32 metadataHash, uint256 timestamp, address serviceCenter);
    event ServiceVerified(bytes32 indexed vin, bytes32 metadataHash, address owner, uint256 recordIndex);
    event ServiceDisputed(bytes32 indexed vin, bytes32 metadataHash, address owner, string reason, uint256 recordIndex);
    event DisputeResolved(bytes32 indexed vin, uint256 recordIndex, DisputeDecision decision);
    event DisputeEscalated(bytes32 indexed vin, uint256 recordIndex, address indexed serviceCenter, uint256 timestamp);

    constructor(address _vehicleRegistry) {
        vehicleRegistry = VehicleRegistry(_vehicleRegistry);
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MANUFACTURER_ADMIN_ROLE, msg.sender);
    }

    // Called by Service Center (Web Dashboard)
    function submitService(
        bytes32 vin,
        bytes32 metadataHash
    ) external onlyRole(SERVICE_CENTER_ROLE) {
        (,,,, bool exists) = vehicleRegistry.getVehicle(vin);
        require(exists, "Vehicle not registered");

        ServiceRecord memory record = ServiceRecord({
            vin: vin,
            metadataHash: metadataHash,
            timestamp: block.timestamp,
            serviceCenter: msg.sender,
            verified: false,
            disputed: false,
            disputeReason: ""
        });

        pendingServices[vin].push(record);
        emit ServiceSubmitted(vin, metadataHash, block.timestamp, msg.sender);
    }

    // Called by Vehicle Owner (Mobile App)
    function verifyService(bytes32 vin, uint256 recordIndex) external {
        (address vehicleOwner,,,, bool exists) = vehicleRegistry.getVehicle(vin);
        require(exists, "Vehicle not registered");
        require(vehicleRegistry.hasRole(vehicleRegistry.OWNER_ROLE(), msg.sender) || vehicleOwner == msg.sender, "Not the vehicle owner");

        require(recordIndex < pendingServices[vin].length, "Invalid record index");
        require(!pendingServices[vin][recordIndex].verified, "Already verified");
        require(!pendingServices[vin][recordIndex].disputed, "Record is disputed");

        ServiceRecord storage record = pendingServices[vin][recordIndex];
        record.verified = true;
        bytes32 capturedHash = record.metadataHash;

        finalizedServices[vin].push(record);
        vehicleRegistry.addServiceHash(vin, capturedHash);

        _removePendingService(vin, recordIndex);

        emit ServiceVerified(vin, capturedHash, msg.sender, finalizedServices[vin].length - 1);
    }

    // Called by Vehicle Owner (Mobile App)
    function disputeService(bytes32 vin, uint256 recordIndex, string memory reason) external {
        (address vehicleOwner,,,, bool exists) = vehicleRegistry.getVehicle(vin);
        require(exists, "Vehicle not registered");
        require(vehicleRegistry.hasRole(vehicleRegistry.OWNER_ROLE(), msg.sender) || vehicleOwner == msg.sender, "Not the vehicle owner");

        require(recordIndex < pendingServices[vin].length, "Invalid record index");
        require(!pendingServices[vin][recordIndex].disputed, "Already disputed");

        pendingServices[vin][recordIndex].disputed = true;
        pendingServices[vin][recordIndex].disputeReason = reason;

        address sc = pendingServices[vin][recordIndex].serviceCenter;
        disputeCount[msg.sender] += 1;

        emit ServiceDisputed(vin, pendingServices[vin][recordIndex].metadataHash, msg.sender, reason, recordIndex);
        emit DisputeEscalated(vin, recordIndex, sc, block.timestamp);
    }

    function resolveDispute(
        bytes32 vin,
        uint256 recordIndex,
        DisputeDecision decision,
        bytes32 resolutionNotesHash
    ) external onlyRole(MANUFACTURER_ADMIN_ROLE) {
        require(recordIndex < pendingServices[vin].length, "Invalid record index");
        require(pendingServices[vin][recordIndex].disputed, "Not a disputed record");

        disputeResolutions[vin][recordIndex] = DisputeResolution({
            resolver: msg.sender,
            timestamp: block.timestamp,
            decision: decision,
            resolutionNotesHash: resolutionNotesHash
        });

        if (decision == DisputeDecision.APPROVE) {
            ServiceRecord storage record = pendingServices[vin][recordIndex];
            record.verified = true;
            bytes32 capturedHash = record.metadataHash;
            finalizedServices[vin].push(record);
            vehicleRegistry.addServiceHash(vin, capturedHash);
            _removePendingService(vin, recordIndex);
        } else if (decision == DisputeDecision.REJECT) {
            _removePendingService(vin, recordIndex);
        }

        emit DisputeResolved(vin, recordIndex, decision);
    }

    function _removePendingService(bytes32 vin, uint256 index) internal {
        ServiceRecord[] storage records = pendingServices[vin];
        records[index] = records[records.length - 1];
        records.pop();
    }

    function getPendingServices(bytes32 vin) external view returns (ServiceRecord[] memory) {
        return pendingServices[vin];
    }

    function getFinalizedServices(bytes32 vin) external view returns (ServiceRecord[] memory) {
        return finalizedServices[vin];
    }
}