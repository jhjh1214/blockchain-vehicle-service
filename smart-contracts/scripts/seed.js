const hre = require("hardhat");
const { ethers } = hre;

const VIN_LIST = [
  "1HGBH41JXMN109186",
  "2T1BURHE0JC023455",
  "3VWFE21C04M000001",
  "1G1AF5S33H7148472",
  "5FNRL5H90GB123456",
  "JH4KA7650MC000002",
  "WBANE53551CT12345",
  "1FAHP3K27CL123456",
  "KNDJN2A29G7234567",
  "1N4AL3AP8JC234567",
];

const SERVICE_TYPES = [
  "Oil Change",
  "Brake Service",
  "Tire Rotation",
  "Engine Repair",
  "Battery Replacement",
  "Air Filter Replacement",
  "Coolant Flush",
  "General Inspection",
];

function vinToBytes32(vin) {
  const buf = Buffer.alloc(32);
  Buffer.from(vin, "ascii").copy(buf);
  return "0x" + buf.toString("hex");
}

function makeHash(data) {
  return ethers.keccak256(ethers.toUtf8Bytes(JSON.stringify(data)));
}

async function main() {
  const signers = await ethers.getSigners();
  // signers[0]     = deployer / manufacturer admin
  // signers[1..2]  = service centers
  // signers[3..12] = vehicle owners (one per vehicle)

  if (signers.length < 13) {
    throw new Error(
      `Need at least 13 accounts, got ${signers.length}. Configure enough accounts in hardhat.config.js.`
    );
  }

  const [deployer] = signers;
  console.log(`Deployer: ${deployer.address}`);

  // ── Deploy ────────────────────────────────────────────────────────────────
  console.log("\nDeploying contracts…");

  const VehicleRegistry = await ethers.getContractFactory("VehicleRegistry");
  const registry = await VehicleRegistry.deploy();
  await registry.waitForDeployment();
  const registryAddr = await registry.getAddress();

  const ServiceLog = await ethers.getContractFactory("ServiceLog");
  const serviceLog = await ServiceLog.deploy(registryAddr);
  await serviceLog.waitForDeployment();
  const serviceLogAddr = await serviceLog.getAddress();

  const WarrantyTracker = await ethers.getContractFactory("WarrantyTracker");
  const warrantyTracker = await WarrantyTracker.deploy(registryAddr);
  await warrantyTracker.waitForDeployment();
  const warrantyTrackerAddr = await warrantyTracker.getAddress();

  // Allow ServiceLog to write service hashes to VehicleRegistry
  const SERVICE_LOG_ROLE = await registry.SERVICE_LOG_ROLE();
  await registry.grantRole(SERVICE_LOG_ROLE, serviceLogAddr);

  // Grant SERVICE_CENTER_ROLE to two service center accounts
  const SC_ROLE = await serviceLog.SERVICE_CENTER_ROLE();
  await serviceLog.grantRole(SC_ROLE, signers[1].address);
  await serviceLog.grantRole(SC_ROLE, signers[2].address);
  console.log(`Service center 1: ${signers[1].address}`);
  console.log(`Service center 2: ${signers[2].address}`);

  // ── Register vehicles ─────────────────────────────────────────────────────
  console.log("\nRegistering 10 vehicles…");

  const now = Math.floor(Date.now() / 1000);
  const oneYear = 365 * 24 * 3600;
  const thirtyDays = 30 * 24 * 3600;

  for (let i = 0; i < 10; i++) {
    const vin = VIN_LIST[i];
    const owner = signers[3 + i];

    // i 0-5: active warranty (1 year)
    // i 6-7: expiring soon (30 days)
    // i 8-9: already expired
    let warrantyExpiry;
    if (i < 6) warrantyExpiry = now + oneYear;
    else if (i < 8) warrantyExpiry = now + thirtyDays;
    else warrantyExpiry = now - thirtyDays;

    await registry.registerVehicle(vinToBytes32(vin), owner.address, warrantyExpiry);
    console.log(`  Registered VIN ${vin} → owner ${owner.address}`);
  }

  // ── Submit service records ────────────────────────────────────────────────
  console.log("\nSubmitting service records…");

  let totalServices = 0;
  const verifiedPerVehicle = {};

  for (let i = 0; i < 10; i++) {
    const vin = VIN_LIST[i];
    const vinBytes = vinToBytes32(vin);
    const sc = signers[i % 2 === 0 ? 1 : 2]; // alternate between SC1 and SC2
    const owner = signers[3 + i];

    const count = 5 + (i % 3); // 5, 6, or 7 services per vehicle → total ≥ 57

    for (let j = 0; j < count; j++) {
      const serviceType = SERVICE_TYPES[(i * 3 + j) % SERVICE_TYPES.length];
      const mileage = 10000 + i * 5000 + j * 1500;
      const hash = makeHash({ vin, serviceType, mileage, seq: j });
      await serviceLog.connect(sc).submitService(vinBytes, hash);
      totalServices++;
    }

    // Owner verifies first 2–3 records on each vehicle
    const toVerify = Math.min(3, count);
    for (let j = 0; j < toVerify; j++) {
      await serviceLog.connect(owner).verifyService(vinBytes, j);
    }
    verifiedPerVehicle[vin] = toVerify;

    console.log(`  VIN ${vin}: ${count} submitted, ${toVerify} verified`);
  }

  console.log(`Total service records submitted: ${totalServices}`);

  // ── Submit warranty claims ────────────────────────────────────────────────
  console.log("\nSubmitting warranty claims…");

  let totalClaims = 0;
  // Only vehicles with active or expiring warranty (i 0–7) can submit claims
  for (let i = 0; i < 8; i++) {
    const vin = VIN_LIST[i];
    const vinBytes = vinToBytes32(vin);
    const owner = signers[3 + i];

    const claimHash = makeHash({
      vin,
      issue: `Warranty claim ${i + 1}: component malfunction`,
      claimant: owner.address,
    });
    await warrantyTracker.connect(owner).submitClaim(vinBytes, claimHash);
    totalClaims++;
    console.log(`  Claim submitted for VIN ${vin}`);
  }

  // ── Summary ───────────────────────────────────────────────────────────────
  console.log("\n═══════════════ Seed complete ═══════════════");
  console.log(`VehicleRegistry:  ${registryAddr}`);
  console.log(`ServiceLog:       ${serviceLogAddr}`);
  console.log(`WarrantyTracker:  ${warrantyTrackerAddr}`);
  console.log(`Vehicles:         10 (6 active warranty, 2 expiring, 2 expired)`);
  console.log(`Service records:  ${totalServices}`);
  console.log(`Warranty claims:  ${totalClaims}`);
  console.log("═════════════════════════════════════════════");
}

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
