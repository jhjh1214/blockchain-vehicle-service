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

  if (signers.length < 14) {
    throw new Error(
      `Need at least 14 accounts, got ${signers.length}. Configure enough accounts in hardhat.config.js.`
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

  // ── Dispute scenarios ─────────────────────────────────────────────────────
  // After verifying the first 3 pending records, the remaining pending records
  // begin at index 0 (swap-and-pop keeps array compact). Dispute the first
  // remaining pending record on 5 vehicles.
  console.log("\nDisputing service records…");

  const DISPUTE_REASONS = [
    "Mileage recorded is higher than actual odometer reading",
    "Service was not authorised by vehicle owner",
    "Wrong service type listed — brake check not oil change",
    "Parts replaced do not match what was invoiced",
    "Service date is incorrect — car was not at this centre on that date",
  ];

  for (let i = 0; i < 5; i++) {
    const vin = VIN_LIST[i];
    const vinBytes = vinToBytes32(vin);
    const owner = signers[3 + i];
    await serviceLog.connect(owner).disputeService(vinBytes, 0, DISPUTE_REASONS[i]);
    console.log(`  VIN ${vin}: record disputed — "${DISPUTE_REASONS[i].slice(0, 50)}…"`);
  }

  // ── Resolve disputes ──────────────────────────────────────────────────────
  // Resolve disputes on VINs 0-2; leave VINs 3-4 unresolved (remain as open disputes).
  // DisputeDecision: 1 = APPROVE, 2 = REJECT, 3 = MODIFY
  console.log("\nResolving disputes…");

  const resolutions = [
    { decision: 1, notes: "Manufacturer review confirmed: mileage corrected in off-chain records, on-chain entry approved" },
    { decision: 2, notes: "SC provided service bay CCTV timestamps — dispute rejected, original record stands" },
    { decision: 3, notes: "Service type mislabelled; service centre to resubmit with correct metadata" },
  ];

  for (let i = 0; i < 3; i++) {
    const vin = VIN_LIST[i];
    const vinBytes = vinToBytes32(vin);
    const { decision, notes } = resolutions[i];
    await serviceLog.connect(deployer).resolveDispute(vinBytes, 0, decision, notes);
    const label = decision === 1 ? "APPROVED" : decision === 2 ? "REJECTED" : "MODIFY requested";
    console.log(`  VIN ${vin}: dispute ${label}`);
  }

  // ── Ownership transfer ────────────────────────────────────────────────────
  // Transfer VIN index 7 (signers[10]) to a new owner (signers[13])
  console.log("\nTransferring vehicle ownership…");

  const transferVin = VIN_LIST[7];
  const transferVinBytes = vinToBytes32(transferVin);
  const originalOwner = signers[10];
  const newOwner = signers[13];
  await registry.connect(originalOwner).transferOwnership(transferVinBytes, newOwner.address);
  console.log(`  VIN ${transferVin}: transferred ${originalOwner.address} → ${newOwner.address}`);

  // ── Resolve warranty claims ───────────────────────────────────────────────
  // Approve claims 0-2, deny claims 3-5, leave 6-7 pending for dashboard visibility
  console.log("\nResolving warranty claims…");

  let approvedClaims = 0;
  let deniedClaims = 0;

  for (let i = 0; i < 3; i++) {
    const vinBytes = vinToBytes32(VIN_LIST[i]);
    await warrantyTracker.connect(deployer).approveClaim(
      vinBytes, 0,
      `Claim approved: component failure within warranty window for VIN ${VIN_LIST[i]}`
    );
    approvedClaims++;
    console.log(`  VIN ${VIN_LIST[i]}: claim APPROVED`);
  }

  for (let i = 3; i < 6; i++) {
    const vinBytes = vinToBytes32(VIN_LIST[i]);
    await warrantyTracker.connect(deployer).denyClaim(
      vinBytes, 0,
      `Claim denied: damage caused by owner misuse, not covered under warranty`
    );
    deniedClaims++;
    console.log(`  VIN ${VIN_LIST[i]}: claim DENIED`);
  }

  // ── Summary ───────────────────────────────────────────────────────────────
  console.log("\n═══════════════ Seed complete ═══════════════");
  console.log(`VehicleRegistry:  ${registryAddr}`);
  console.log(`ServiceLog:       ${serviceLogAddr}`);
  console.log(`WarrantyTracker:  ${warrantyTrackerAddr}`);
  console.log(`Vehicles:         10 (6 active warranty, 2 expiring, 2 expired)`);
  console.log(`Service records:  ${totalServices}`);
  console.log(`Disputes raised:  5 (3 resolved: 1 approved, 1 rejected, 1 modify; 2 open)`);
  console.log(`Ownership xfers:  1 (VIN ${transferVin})`);
  console.log(`Warranty claims:  ${totalClaims} (${approvedClaims} approved, ${deniedClaims} denied, 2 pending)`);
  console.log("═════════════════════════════════════════════");
}

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
