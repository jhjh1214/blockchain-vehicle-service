const { expect } = require("chai");
const { ethers } = require("hardhat");
const { anyValue } = require("@nomicfoundation/hardhat-chai-matchers/withArgs");

describe("Blockchain Vehicle Service & Warranty System", function () {
  let vehicleRegistry, serviceLog, warrantyTracker;
  let deployer, manufacturer, serviceCenter, owner, owner2;

  // Use keccak256 bytes for VIN (mirrors Python backend behaviour)
  const sampleVIN = ethers.keccak256(ethers.toUtf8Bytes("1HGCM82633A123456"));
  const sampleVIN2 = ethers.keccak256(ethers.toUtf8Bytes("2HGCM82633A654321"));
  const sampleMetadataHash = ethers.keccak256(ethers.toUtf8Bytes("service_metadata_hash_001"));
  const claimDetailsHash = ethers.keccak256(ethers.toUtf8Bytes("warranty_claim_details"));
  const resolutionHash = ethers.keccak256(ethers.toUtf8Bytes("Resolution notes"));

  const FAR_FUTURE = 9_999_999_999;
  const ONE_YEAR = Math.floor(Date.now() / 1000) + 365 * 24 * 60 * 60;

  beforeEach(async function () {
    [deployer, manufacturer, serviceCenter, owner, owner2] = await ethers.getSigners();

    // Deploy VehicleRegistry
    const VehicleRegistry = await ethers.getContractFactory("VehicleRegistry");
    vehicleRegistry = await VehicleRegistry.deploy();
    await vehicleRegistry.waitForDeployment();

    // Deploy ServiceLog (needs VehicleRegistry address)
    const ServiceLog = await ethers.getContractFactory("ServiceLog");
    serviceLog = await ServiceLog.deploy(await vehicleRegistry.getAddress());
    await serviceLog.waitForDeployment();

    // Deploy WarrantyTracker (needs VehicleRegistry address)
    const WarrantyTracker = await ethers.getContractFactory("WarrantyTracker");
    warrantyTracker = await WarrantyTracker.deploy(await vehicleRegistry.getAddress());
    await warrantyTracker.waitForDeployment();

    // ── Role setup ──────────────────────────────────────────────────────────
    // Grant MANUFACTURER_ROLE
    await vehicleRegistry.grantRole(
      await vehicleRegistry.MANUFACTURER_ROLE(),
      manufacturer.address
    );

    // Grant SERVICE_LOG_ROLE to ServiceLog contract so it can call addServiceHash
    await vehicleRegistry.grantRole(
      await vehicleRegistry.SERVICE_LOG_ROLE(),
      await serviceLog.getAddress()
    );

    // Grant SERVICE_CENTER_ROLE on ServiceLog
    await serviceLog.grantRole(
      await serviceLog.SERVICE_CENTER_ROLE(),
      serviceCenter.address
    );
  });

  // ── VehicleRegistry ────────────────────────────────────────────────────────

  describe("VehicleRegistry", function () {
    it("should register a vehicle by manufacturer", async function () {
      await vehicleRegistry.connect(manufacturer).registerVehicle(
        sampleVIN, owner.address, FAR_FUTURE
      );
      const v = await vehicleRegistry.getVehicle(sampleVIN);
      expect(v.exists).to.equal(true);
      expect(v.owner).to.equal(owner.address);
    });

    it("should reject registration by non-manufacturer", async function () {
      await expect(
        vehicleRegistry.connect(owner).registerVehicle(sampleVIN, owner.address, FAR_FUTURE)
      ).to.be.revertedWithCustomError(vehicleRegistry, "AccessControlUnauthorizedAccount");
    });

    it("should reject duplicate VIN registration", async function () {
      await vehicleRegistry.connect(manufacturer).registerVehicle(
        sampleVIN, owner.address, FAR_FUTURE
      );
      await expect(
        vehicleRegistry.connect(manufacturer).registerVehicle(
          sampleVIN, owner2.address, FAR_FUTURE
        )
      ).to.be.revertedWith("Vehicle already registered");
    });

    it("should grant OWNER_ROLE on vehicle registration", async function () {
      await vehicleRegistry.connect(manufacturer).registerVehicle(
        sampleVIN, owner.address, FAR_FUTURE
      );
      const OWNER_ROLE = await vehicleRegistry.OWNER_ROLE();
      expect(await vehicleRegistry.hasRole(OWNER_ROLE, owner.address)).to.equal(true);
    });

    it("should block addServiceHash without SERVICE_LOG_ROLE", async function () {
      await vehicleRegistry.connect(manufacturer).registerVehicle(
        sampleVIN, owner.address, FAR_FUTURE
      );
      await expect(
        vehicleRegistry.connect(owner).addServiceHash(sampleVIN, sampleMetadataHash)
      ).to.be.revertedWithCustomError(vehicleRegistry, "AccessControlUnauthorizedAccount");
    });

    it("should transfer vehicle ownership and update OWNER_ROLE correctly", async function () {
      await vehicleRegistry.connect(manufacturer).registerVehicle(
        sampleVIN, owner.address, FAR_FUTURE
      );

      await vehicleRegistry.connect(owner).transferOwnership(sampleVIN, owner2.address);

      const v = await vehicleRegistry.getVehicle(sampleVIN);
      expect(v.owner).to.equal(owner2.address);
      expect(await vehicleRegistry.hasRole(await vehicleRegistry.OWNER_ROLE(), owner2.address)).to.equal(true);
    });

    it("should NOT revoke OWNER_ROLE when previous owner still has other vehicles", async function () {
      // owner owns two vehicles; transfer only one — OWNER_ROLE should remain
      await vehicleRegistry.connect(manufacturer).registerVehicle(
        sampleVIN, owner.address, FAR_FUTURE
      );
      await vehicleRegistry.connect(manufacturer).registerVehicle(
        sampleVIN2, owner.address, FAR_FUTURE
      );

      await vehicleRegistry.connect(owner).transferOwnership(sampleVIN, owner2.address);

      const OWNER_ROLE = await vehicleRegistry.OWNER_ROLE();
      expect(await vehicleRegistry.hasRole(OWNER_ROLE, owner.address)).to.equal(true);
    });

    it("should revoke OWNER_ROLE when previous owner transfers their last vehicle", async function () {
      await vehicleRegistry.connect(manufacturer).registerVehicle(
        sampleVIN, owner.address, FAR_FUTURE
      );
      await vehicleRegistry.connect(owner).transferOwnership(sampleVIN, owner2.address);

      const OWNER_ROLE = await vehicleRegistry.OWNER_ROLE();
      expect(await vehicleRegistry.hasRole(OWNER_ROLE, owner.address)).to.equal(false);
    });

    it("should return owned VINs for an address", async function () {
      await vehicleRegistry.connect(manufacturer).registerVehicle(
        sampleVIN, owner.address, FAR_FUTURE
      );
      const owned = await vehicleRegistry.getOwnedVehicles(owner.address);
      expect(owned.length).to.equal(1);
    });

    it("should reject transfer of non-existent vehicle", async function () {
      await expect(
        vehicleRegistry.connect(owner).transferOwnership(sampleVIN, owner2.address)
      ).to.be.revertedWith("Vehicle does not exist");
    });

    it("should reject transfer by non-owner", async function () {
      await vehicleRegistry.connect(manufacturer).registerVehicle(
        sampleVIN, owner.address, FAR_FUTURE
      );
      await expect(
        vehicleRegistry.connect(owner2).transferOwnership(sampleVIN, owner2.address)
      ).to.be.revertedWith("Not the vehicle owner");
    });

    it("should reject transfer to zero address", async function () {
      await vehicleRegistry.connect(manufacturer).registerVehicle(
        sampleVIN, owner.address, FAR_FUTURE
      );
      await expect(
        vehicleRegistry.connect(owner).transferOwnership(sampleVIN, ethers.ZeroAddress)
      ).to.be.revertedWith("Invalid new owner");
    });

    it("should reject registerVehicle with zero address owner", async function () {
      await expect(
        vehicleRegistry.connect(manufacturer).registerVehicle(
          sampleVIN, ethers.ZeroAddress, FAR_FUTURE
        )
      ).to.be.revertedWith("Invalid owner address");
    });

    it("should reject addServiceHash for non-existent vehicle", async function () {
      await vehicleRegistry.grantRole(
        await vehicleRegistry.SERVICE_LOG_ROLE(),
        deployer.address
      );
      await expect(
        vehicleRegistry.connect(deployer).addServiceHash(sampleVIN, sampleMetadataHash)
      ).to.be.revertedWith("Vehicle does not exist");
    });
  });

  // ── ServiceLog ─────────────────────────────────────────────────────────────

  describe("ServiceLog", function () {
    beforeEach(async function () {
      await vehicleRegistry.connect(manufacturer).registerVehicle(
        sampleVIN, owner.address, FAR_FUTURE
      );
    });

    it("should allow service center to submit a service record", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      const pending = await serviceLog.getPendingServices(sampleVIN);
      expect(pending.length).to.equal(1);
      expect(pending[0].serviceCenter).to.equal(serviceCenter.address);
      expect(pending[0].verified).to.equal(false);
    });

    it("should reject service submission by non-service-center", async function () {
      await expect(
        serviceLog.connect(owner).submitService(sampleVIN, sampleMetadataHash)
      ).to.be.revertedWithCustomError(serviceLog, "AccessControlUnauthorizedAccount");
    });

    it("should allow vehicle owner to verify a service (two-stage)", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      await serviceLog.connect(owner).verifyService(sampleVIN, 0);

      const pending = await serviceLog.getPendingServices(sampleVIN);
      const finalized = await serviceLog.getFinalizedServices(sampleVIN);
      expect(pending.length).to.equal(0);
      expect(finalized.length).to.equal(1);
      expect(finalized[0].verified).to.equal(true);
    });

    it("should add service hash to VehicleRegistry on verification", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      await serviceLog.connect(owner).verifyService(sampleVIN, 0);

      const v = await vehicleRegistry.getVehicle(sampleVIN);
      expect(v.serviceHashes.length).to.equal(1);
    });

    it("should allow vehicle owner to dispute a service", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      await serviceLog.connect(owner).disputeService(sampleVIN, 0, "Wrong parts used");

      const pending = await serviceLog.getPendingServices(sampleVIN);
      expect(pending[0].disputed).to.equal(true);
      expect(pending[0].disputeReason).to.equal("Wrong parts used");
    });

    it("should allow admin to approve a disputed record", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      await serviceLog.connect(owner).disputeService(sampleVIN, 0, "Wrong parts");
      await serviceLog.connect(deployer).resolveDispute(sampleVIN, 0, 1, resolutionHash); // APPROVE

      const finalized = await serviceLog.getFinalizedServices(sampleVIN);
      expect(finalized.length).to.equal(1);
    });

    it("should allow admin to reject a disputed record", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      await serviceLog.connect(owner).disputeService(sampleVIN, 0, "Fake service");
      await serviceLog.connect(deployer).resolveDispute(sampleVIN, 0, 2, resolutionHash); // REJECT

      const pending = await serviceLog.getPendingServices(sampleVIN);
      const finalized = await serviceLog.getFinalizedServices(sampleVIN);
      expect(pending.length).to.equal(0);
      expect(finalized.length).to.equal(0);
    });

    it("should reject resolving a non-disputed record", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      await expect(
        serviceLog.connect(deployer).resolveDispute(sampleVIN, 0, 1, resolutionHash)
      ).to.be.revertedWith("Not a disputed record");
    });

    it("should store resolution notes hash on-chain", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      await serviceLog.connect(owner).disputeService(sampleVIN, 0, "Bad service");
      await serviceLog.connect(deployer).resolveDispute(sampleVIN, 0, 1, resolutionHash);

      const resolution = await serviceLog.disputeResolutions(sampleVIN, 0);
      expect(resolution.resolutionNotesHash).to.equal(resolutionHash);
      expect(resolution.resolver).to.equal(deployer.address);
    });

    it("should keep record in pending on MODIFY resolution", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      await serviceLog.connect(owner).disputeService(sampleVIN, 0, "Partially wrong");
      await serviceLog.connect(deployer).resolveDispute(sampleVIN, 0, 3, resolutionHash); // MODIFY

      const pending = await serviceLog.getPendingServices(sampleVIN);
      const finalized = await serviceLog.getFinalizedServices(sampleVIN);
      expect(pending.length).to.equal(1);
      expect(finalized.length).to.equal(0);
    });

    it("should increment disputeCount when owner disputes", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      const before = await serviceLog.disputeCount(owner.address);
      await serviceLog.connect(owner).disputeService(sampleVIN, 0, "Wrong parts");
      const after = await serviceLog.disputeCount(owner.address);
      expect(after).to.equal(before + 1n);
    });

    it("should emit DisputeEscalated event with service center address", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      await expect(
        serviceLog.connect(owner).disputeService(sampleVIN, 0, "Wrong parts")
      )
        .to.emit(serviceLog, "DisputeEscalated")
        .withArgs(sampleVIN, 0, serviceCenter.address, anyValue);
    });

    it("should reject submitService for non-existent vehicle", async function () {
      const unknownVIN = ethers.keccak256(ethers.toUtf8Bytes("UNKNOWN_VIN_000000"));
      await expect(
        serviceLog.connect(serviceCenter).submitService(unknownVIN, sampleMetadataHash)
      ).to.be.revertedWith("Vehicle not registered");
    });

    it("should reject verifyService with out-of-range index", async function () {
      await expect(
        serviceLog.connect(owner).verifyService(sampleVIN, 99)
      ).to.be.revertedWith("Invalid record index");
    });

    it("should reject verifyService by non-owner", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      await expect(
        serviceLog.connect(owner2).verifyService(sampleVIN, 0)
      ).to.be.revertedWith("Not the vehicle owner");
    });

    it("should reject verifying an already-disputed record", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      await serviceLog.connect(owner).disputeService(sampleVIN, 0, "Bad service");
      await expect(
        serviceLog.connect(owner).verifyService(sampleVIN, 0)
      ).to.be.revertedWith("Record is disputed");
    });

    it("should reject double-dispute on same record", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      await serviceLog.connect(owner).disputeService(sampleVIN, 0, "First dispute");
      await expect(
        serviceLog.connect(owner).disputeService(sampleVIN, 0, "Second dispute")
      ).to.be.revertedWith("Already disputed");
    });

    it("should reject disputeService with out-of-range index", async function () {
      await expect(
        serviceLog.connect(owner).disputeService(sampleVIN, 99, "Bad")
      ).to.be.revertedWith("Invalid record index");
    });

    it("should reject resolveDispute by non-admin", async function () {
      await serviceLog.connect(serviceCenter).submitService(sampleVIN, sampleMetadataHash);
      await serviceLog.connect(owner).disputeService(sampleVIN, 0, "Bad service");
      await expect(
        serviceLog.connect(owner).resolveDispute(sampleVIN, 0, 1, resolutionHash)
      ).to.be.revertedWithCustomError(serviceLog, "AccessControlUnauthorizedAccount");
    });
  });

  // ── WarrantyTracker ────────────────────────────────────────────────────────

  describe("WarrantyTracker", function () {
    beforeEach(async function () {
      await vehicleRegistry.connect(manufacturer).registerVehicle(
        sampleVIN, owner.address, FAR_FUTURE
      );
    });

    it("should report warranty as valid within expiry", async function () {
      const [valid] = await warrantyTracker.isWarrantyValid(sampleVIN);
      expect(valid).to.equal(true);
    });

    it("should report warranty as invalid for unregistered VIN", async function () {
      const unknownVIN = ethers.keccak256(ethers.toUtf8Bytes("UNKNOWN00000000000"));
      const [valid, reason] = await warrantyTracker.isWarrantyValid(unknownVIN);
      expect(valid).to.equal(false);
      expect(reason).to.include("not registered");
    });

    it("should allow vehicle owner to submit a warranty claim", async function () {
      await warrantyTracker.connect(owner).submitClaim(sampleVIN, claimDetailsHash);
      const claims = await warrantyTracker.getClaims(sampleVIN);
      expect(claims.length).to.equal(1);
      expect(claims[0].status).to.equal(0); // PENDING
      expect(claims[0].claimant).to.equal(owner.address);
    });

    it("should reject warranty claim from non-owner", async function () {
      await expect(
        warrantyTracker.connect(serviceCenter).submitClaim(sampleVIN, claimDetailsHash)
      ).to.be.revertedWith("Not the vehicle owner");
    });

    it("should allow admin to approve a warranty claim", async function () {
      await warrantyTracker.connect(owner).submitClaim(sampleVIN, claimDetailsHash);
      await warrantyTracker.connect(deployer).approveClaim(sampleVIN, 0);

      const claims = await warrantyTracker.getClaims(sampleVIN);
      expect(claims[0].status).to.equal(1); // APPROVED
    });

    it("should allow admin to deny a warranty claim with reason hash", async function () {
      await warrantyTracker.connect(owner).submitClaim(sampleVIN, claimDetailsHash);
      await warrantyTracker.connect(deployer).denyClaim(sampleVIN, 0, resolutionHash);

      const claims = await warrantyTracker.getClaims(sampleVIN);
      expect(claims[0].status).to.equal(2); // DENIED
      expect(claims[0].resolutionNotesHash).to.equal(resolutionHash);
    });

    it("should reject approval of an already-approved claim", async function () {
      await warrantyTracker.connect(owner).submitClaim(sampleVIN, claimDetailsHash);
      await warrantyTracker.connect(deployer).approveClaim(sampleVIN, 0);
      await expect(
        warrantyTracker.connect(deployer).approveClaim(sampleVIN, 0)
      ).to.be.revertedWith("Claim not pending");
    });

    it("should reject non-admin claim actions", async function () {
      await warrantyTracker.connect(owner).submitClaim(sampleVIN, claimDetailsHash);
      await expect(
        warrantyTracker.connect(manufacturer).approveClaim(sampleVIN, 0)
      ).to.be.revertedWithCustomError(warrantyTracker, "AccessControlUnauthorizedAccount");
    });

    it("should return (expiry, true) from getWarrantyStatus for active warranty", async function () {
      const [expiry, isValid] = await warrantyTracker.getWarrantyStatus(sampleVIN);
      expect(isValid).to.equal(true);
      expect(expiry).to.equal(FAR_FUTURE);
    });

    it("should return (0, false) from getWarrantyStatus for unregistered VIN", async function () {
      const unknownVIN = ethers.keccak256(ethers.toUtf8Bytes("UNREGISTERED_VIN00"));
      const [expiry, isValid] = await warrantyTracker.getWarrantyStatus(unknownVIN);
      expect(expiry).to.equal(0);
      expect(isValid).to.equal(false);
    });

    it("should return (expiry, false) from getWarrantyStatus for expired warranty", async function () {
      const PAST = 1;
      await vehicleRegistry.connect(manufacturer).registerVehicle(sampleVIN2, owner.address, PAST);
      const [expiry, isValid] = await warrantyTracker.getWarrantyStatus(sampleVIN2);
      expect(isValid).to.equal(false);
      expect(expiry).to.equal(PAST);
    });

    it("should reject submitClaim when warranty has expired", async function () {
      const PAST = 1;
      await vehicleRegistry.connect(manufacturer).registerVehicle(sampleVIN2, owner.address, PAST);
      await expect(
        warrantyTracker.connect(owner).submitClaim(sampleVIN2, claimDetailsHash)
      ).to.be.revertedWith("Warranty is not valid");
    });

    it("should reject approveClaim with out-of-range index", async function () {
      await expect(
        warrantyTracker.connect(deployer).approveClaim(sampleVIN, 99)
      ).to.be.revertedWith("Invalid claim index");
    });

    it("should reject denyClaim with out-of-range index", async function () {
      await expect(
        warrantyTracker.connect(deployer).denyClaim(sampleVIN, 99, resolutionHash)
      ).to.be.revertedWith("Invalid claim index");
    });

    it("should reject deny on already-denied claim", async function () {
      await warrantyTracker.connect(owner).submitClaim(sampleVIN, claimDetailsHash);
      await warrantyTracker.connect(deployer).denyClaim(sampleVIN, 0, resolutionHash);
      await expect(
        warrantyTracker.connect(deployer).denyClaim(sampleVIN, 0, resolutionHash)
      ).to.be.revertedWith("Claim not pending");
    });
  });
});
