// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "./VehicleRegistry.sol";

contract WarrantyTracker is AccessControl {
    bytes32 public constant MANUFACTURER_ADMIN_ROLE = DEFAULT_ADMIN_ROLE;

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

    event ClaimSubmitted(bytes32 indexed vin, bytes32 claimDetailsHash, address claimant);
    event ClaimApproved(bytes32 indexed vin, uint256 claimIndex);
    event ClaimDenied(bytes32 indexed vin, uint256 claimIndex, bytes32 reasonHash);

    constructor(address _vehicleRegistry) {
        vehicleRegistry = VehicleRegistry(_vehicleRegistry);
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    function isWarrantyValid(bytes32 vin) public view returns (bool valid, string memory reason) {
        (,, uint256 warrantyExpiry,, bool exists) = vehicleRegistry.getVehicle(vin);
        if (!exists) return (false, "Vehicle not registered");
        if (block.timestamp > warrantyExpiry) return (false, "Warranty has expired");
        return (true, "Warranty is valid");
    }

    // Called by Vehicle Owner (Mobile App)
    function submitClaim(bytes32 vin, bytes32 claimDetailsHash) external {
        (address owner,,,, bool exists) = vehicleRegistry.getVehicle(vin);
        require(exists, "Vehicle not registered");
        require(vehicleRegistry.hasRole(vehicleRegistry.OWNER_ROLE(), msg.sender) || owner == msg.sender, "Not the vehicle owner");

        (bool valid,) = isWarrantyValid(vin);
        require(valid, "Warranty is not valid");

        WarrantyClaim memory claim = WarrantyClaim({
            vin: vin,
            claimDetailsHash: claimDetailsHash,
            timestamp: block.timestamp,
            claimant: msg.sender,
            status: ClaimStatus.PENDING,
            resolutionNotesHash: bytes32(0)
        });

        claims[vin].push(claim);
        emit ClaimSubmitted(vin, claimDetailsHash, msg.sender);
    }

    function approveClaim(bytes32 vin, uint256 claimIndex) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(claimIndex < claims[vin].length, "Invalid claim index");
        require(claims[vin][claimIndex].status == ClaimStatus.PENDING, "Claim not pending");

        claims[vin][claimIndex].status = ClaimStatus.APPROVED;
        emit ClaimApproved(vin, claimIndex);
    }

    function denyClaim(bytes32 vin, uint256 claimIndex, bytes32 reasonHash) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(claimIndex < claims[vin].length, "Invalid claim index");
        require(claims[vin][claimIndex].status == ClaimStatus.PENDING, "Claim not pending");

        claims[vin][claimIndex].status = ClaimStatus.DENIED;
        claims[vin][claimIndex].resolutionNotesHash = reasonHash;
        emit ClaimDenied(vin, claimIndex, reasonHash);
    }

    function getWarrantyStatus(bytes32 vin) external view returns (uint256 expiry, bool isValid) {
        (,, uint256 warrantyExpiry,, bool exists) = vehicleRegistry.getVehicle(vin);
        if (!exists) return (0, false);
        return (warrantyExpiry, block.timestamp <= warrantyExpiry);
    }

    function getClaims(bytes32 vin) external view returns (WarrantyClaim[] memory) {
        return claims[vin];
    }
}