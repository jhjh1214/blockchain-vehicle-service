// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";

contract VehicleRegistry is AccessControl {
    bytes32 public constant MANUFACTURER_ROLE = keccak256("MANUFACTURER_ROLE");
    bytes32 public constant OWNER_ROLE = keccak256("OWNER_ROLE");
    bytes32 public constant SERVICE_LOG_ROLE = keccak256("SERVICE_LOG_ROLE");

    struct Vehicle {
        address owner;
        uint256 warrantyStart;
        uint256 warrantyExpiry;
        bytes32[] serviceHashes;
        bool exists;
    }

    mapping(bytes32 => Vehicle) public vehicles;
    mapping(address => bytes32[]) public ownedVINs;

    event VehicleRegistered(bytes32 indexed vin, address indexed owner, uint256 warrantyExpiry);
    event OwnershipTransferred(bytes32 indexed vin, address indexed previousOwner, address indexed newOwner);
    event ServiceHashAdded(bytes32 indexed vin, bytes32 serviceHash);

    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MANUFACTURER_ROLE, msg.sender);
    }

    function registerVehicle(
        bytes32 vin,
        address initialOwner,
        uint256 warrantyExpiry
    ) external onlyRole(MANUFACTURER_ROLE) {
        require(!vehicles[vin].exists, "Vehicle already registered");
        require(initialOwner != address(0), "Invalid owner address");

        vehicles[vin] = Vehicle({
            owner: initialOwner,
            warrantyStart: block.timestamp,
            warrantyExpiry: warrantyExpiry,
            serviceHashes: new bytes32[](0),
            exists: true
        });

        ownedVINs[initialOwner].push(vin);
        _grantRole(OWNER_ROLE, initialOwner);

        emit VehicleRegistered(vin, initialOwner, warrantyExpiry);
    }

    function transferOwnership(bytes32 vin, address newOwner) external {
        require(vehicles[vin].exists, "Vehicle does not exist");
        require(hasRole(OWNER_ROLE, msg.sender) || vehicles[vin].owner == msg.sender, "Not the vehicle owner");
        require(newOwner != address(0), "Invalid new owner");

        address previousOwner = vehicles[vin].owner;

        vehicles[vin].owner = newOwner;
        _grantRole(OWNER_ROLE, newOwner);

        ownedVINs[newOwner].push(vin);
        _removeVinFromOwner(previousOwner, vin);

        // Only revoke OWNER_ROLE when the previous owner has no remaining vehicles
        if (ownedVINs[previousOwner].length == 0) {
            _revokeRole(OWNER_ROLE, previousOwner);
        }

        emit OwnershipTransferred(vin, previousOwner, newOwner);
    }

    function addServiceHash(bytes32 vin, bytes32 serviceHash) external onlyRole(SERVICE_LOG_ROLE) {
        require(vehicles[vin].exists, "Vehicle does not exist");
        vehicles[vin].serviceHashes.push(serviceHash);
        emit ServiceHashAdded(vin, serviceHash);
    }

    function getVehicle(bytes32 vin) external view returns (
        address owner,
        uint256 warrantyStart,
        uint256 warrantyExpiry,
        bytes32[] memory serviceHashes,
        bool exists
    ) {
        Vehicle memory v = vehicles[vin];
        return (v.owner, v.warrantyStart, v.warrantyExpiry, v.serviceHashes, v.exists);
    }

    function getOwnedVehicles(address ownerAddr) external view returns (bytes32[] memory) {
        return ownedVINs[ownerAddr];
    }

    function _removeVinFromOwner(address ownerAddr, bytes32 vin) internal {
        bytes32[] storage vins = ownedVINs[ownerAddr];
        for (uint256 i = 0; i < vins.length; i++) {
            if (vins[i] == vin) {
                vins[i] = vins[vins.length - 1];
                vins.pop();
                break;
            }
        }
    }
}