// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "./VehicleRegistry.sol";

contract WarrantyTracker is AccessControl {
    // Distinct role — does NOT equal DEFAULT_ADMIN_ROLE.
    // Prevents manufacturers from calling grantRole() to escalate privileges.
    bytes32 public constant MANUFACTURER_ADMIN_ROLE = keccak256("MANUFACTURER_ADMIN_ROLE");

    VehicleRegistry public immutable vehicleRegistry;

    struct WarrantyClaim {
        bytes32 vin;
        bytes32 claimDetailsHash;
        uint256 timestamp;
        address claimant;
        ClaimStatus status;
        bytes32 resolutionNotesHash;
    }

    enum ClaimStatus { PENDING, APPROVED, DENIED }

    mapping(bytes32 => WarrantyClaim[]) public claims;
    mapping(bytes32 => bool) public voidedWarranties;

    event ClaimSubmitted(bytes32 indexed vin, bytes32 claimDetailsHash, address claimant);
    event ClaimApproved(bytes32 indexed vin, uint256 claimIndex);
    event ClaimDenied(bytes32 indexed vin, uint256 claimIndex, bytes32 reasonHash);
    event WarrantyVoided(bytes32 indexed vin);

    constructor(address _vehicleRegistry) {
        vehicleRegistry = VehicleRegistry(_vehicleRegistry);
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MANUFACTURER_ADMIN_ROLE, msg.sender);
    }

    function isWarrantyValid(bytes32 vin) public view returns (bool valid, string memory reason) {
        (,, uint256 warrantyExpiry,, bool exists) = vehicleRegistry.getVehicle(vin);
        if (!exists) return (false, "Vehicle not registered");
        if (voidedWarranties[vin]) return (false, "Warranty has been voided");
        if (block.timestamp > warrantyExpiry) return (false, "Warranty has expired");
        return (true, "Warranty is valid");
    }

    function voidWarranty(bytes32 vin) external onlyRole(MANUFACTURER_ADMIN_ROLE) {
        (,,, , bool exists) = vehicleRegistry.getVehicle(vin);
        require(exists, "Vehicle not registered");
        voidedWarranties[vin] = true;
        emit WarrantyVoided(vin);
    }

    function submitClaim(bytes32 vin, bytes32 claimDetailsHash) external {
        (address owner,,,, bool exists) = vehicleRegistry.getVehicle(vin);
        require(exists, "Vehicle not registered");
        require(
            vehicleRegistry.hasRole(vehicleRegistry.OWNER_ROLE(), msg.sender) || owner == msg.sender,
            "Not the vehicle owner"
        );
        (bool valid, string memory reason) = isWarrantyValid(vin);
        require(valid, reason);

        claims[vin].push(WarrantyClaim({
            vin: vin,
            claimDetailsHash: claimDetailsHash,
            timestamp: block.timestamp,
            claimant: msg.sender,
            status: ClaimStatus.PENDING,
            resolutionNotesHash: bytes32(0)
        }));
        emit ClaimSubmitted(vin, claimDetailsHash, msg.sender);
    }

    function approveClaim(bytes32 vin, uint256 claimIndex) external onlyRole(MANUFACTURER_ADMIN_ROLE) {
        require(claimIndex < claims[vin].length, "Invalid claim index");
        require(claims[vin][claimIndex].status == ClaimStatus.PENDING, "Claim not pending");
        claims[vin][claimIndex].status = ClaimStatus.APPROVED;
        emit ClaimApproved(vin, claimIndex);
    }

    function denyClaim(bytes32 vin, uint256 claimIndex, bytes32 reasonHash) external onlyRole(MANUFACTURER_ADMIN_ROLE) {
        require(claimIndex < claims[vin].length, "Invalid claim index");
        require(claims[vin][claimIndex].status == ClaimStatus.PENDING, "Claim not pending");
        claims[vin][claimIndex].status = ClaimStatus.DENIED;
        claims[vin][claimIndex].resolutionNotesHash = reasonHash;
        emit ClaimDenied(vin, claimIndex, reasonHash);
    }

    function getWarrantyStatus(bytes32 vin) external view returns (uint256 expiry, bool isValid) {
        (,, uint256 warrantyExpiry,, bool exists) = vehicleRegistry.getVehicle(vin);
        if (!exists) return (0, false);
        if (voidedWarranties[vin]) return (warrantyExpiry, false);
        return (warrantyExpiry, block.timestamp <= warrantyExpiry);
    }

    function getClaims(bytes32 vin) external view returns (WarrantyClaim[] memory) {
        return claims[vin];
    }
}
