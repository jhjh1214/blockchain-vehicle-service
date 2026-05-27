/**
 * Gas & latency benchmark for all key on-chain operations.
 *
 * Usage:
 *   npx hardhat run scripts/benchmark.js --network hardhat
 *   npx hardhat run scripts/benchmark.js --network ganache
 *
 * Outputs a table of gas used, estimated ETH cost (at 20 Gwei),
 * and wall-clock latency for each operation.
 */

const hre = require("hardhat");
const { ethers } = hre;

const GAS_PRICE_GWEI = 20n;
const ETH_USD = 3000; // approximate; update as needed

function vinToBytes32(vin) {
  const buf = Buffer.alloc(32);
  Buffer.from(vin, "ascii").copy(buf);
  return "0x" + buf.toString("hex");
}

function makeHash(data) {
  return ethers.keccak256(ethers.toUtf8Bytes(JSON.stringify(data)));
}

function formatGas(gas, latencyMs) {
  const gasN = BigInt(gas);
  const weiCost = gasN * GAS_PRICE_GWEI * 1_000_000_000n;
  const ethCost = Number(weiCost) / 1e18;
  const usdCost = ethCost * ETH_USD;
  return {
    gas: gas.toString(),
    ethCost: ethCost.toFixed(6),
    usdCost: usdCost.toFixed(4),
    latencyMs: latencyMs.toFixed(0),
  };
}

async function measure(label, txPromise) {
  const t0 = Date.now();
  const tx = await txPromise;
  const receipt = await tx.wait();
  const latency = Date.now() - t0;
  return { label, ...formatGas(receipt.gasUsed, latency) };
}

async function main() {
  const signers = await ethers.getSigners();
  const [deployer, sc1, owner1, owner2] = signers;

  // ── Deploy ────────────────────────────────────────────────────────────────
  const VehicleRegistry = await ethers.getContractFactory("VehicleRegistry");
  const registry = await VehicleRegistry.deploy();
  await registry.waitForDeployment();

  const ServiceLog = await ethers.getContractFactory("ServiceLog");
  const serviceLog = await ServiceLog.deploy(await registry.getAddress());
  await serviceLog.waitForDeployment();

  const WarrantyTracker = await ethers.getContractFactory("WarrantyTracker");
  const warrantyTracker = await WarrantyTracker.deploy(await registry.getAddress());
  await warrantyTracker.waitForDeployment();

  // Setup roles
  await registry.grantRole(await registry.SERVICE_LOG_ROLE(), await serviceLog.getAddress());
  await serviceLog.grantRole(await serviceLog.SERVICE_CENTER_ROLE(), sc1.address);

  const vin1 = vinToBytes32("1HGBH41JXMN109186");
  const vin2 = vinToBytes32("2T1BURHE0JC023455");
  const now = Math.floor(Date.now() / 1000);
  const oneYear = 365 * 24 * 3600;
  const hash1 = makeHash({ type: "Oil Change", mileage: 10000 });
  const hash2 = makeHash({ type: "Brake Service", mileage: 15000 });
  const claimHash = makeHash({ issue: "Engine noise" });
  const resolutionHash = makeHash({ notes: "Claim verified" });

  const results = [];

  // ── Benchmark each operation ──────────────────────────────────────────────

  results.push(await measure(
    "registerVehicle (MANUFACTURER_ROLE)",
    registry.registerVehicle(vin1, owner1.address, now + oneYear)
  ));

  results.push(await measure(
    "registerVehicle (with existing owner, 2nd vehicle)",
    registry.registerVehicle(vin2, owner1.address, now + oneYear)
  ));

  results.push(await measure(
    "submitService (SERVICE_CENTER_ROLE)",
    serviceLog.connect(sc1).submitService(vin1, hash1)
  ));

  results.push(await measure(
    "submitService (2nd record, same VIN)",
    serviceLog.connect(sc1).submitService(vin1, hash2)
  ));

  results.push(await measure(
    "verifyService (OWNER — happy path)",
    serviceLog.connect(owner1).verifyService(vin1, 0)
  ));

  results.push(await measure(
    "disputeService (OWNER — dispute 2nd record)",
    serviceLog.connect(owner1).disputeService(vin1, 0, "Wrong parts installed")
  ));

  results.push(await measure(
    "resolveDispute — APPROVE",
    serviceLog.connect(deployer).resolveDispute(vin1, 0, 1, resolutionHash)
  ));

  // Submit a new record to resolve with REJECT
  await serviceLog.connect(sc1).submitService(vin1, hash1);
  await serviceLog.connect(owner1).disputeService(vin1, 0, "Fake service");
  results.push(await measure(
    "resolveDispute — REJECT",
    serviceLog.connect(deployer).resolveDispute(vin1, 0, 2, resolutionHash)
  ));

  // Submit a new record to resolve with MODIFY
  await serviceLog.connect(sc1).submitService(vin1, hash2);
  await serviceLog.connect(owner1).disputeService(vin1, 0, "Partial issue");
  results.push(await measure(
    "resolveDispute — MODIFY (keep pending)",
    serviceLog.connect(deployer).resolveDispute(vin1, 0, 3, resolutionHash)
  ));

  results.push(await measure(
    "submitClaim (WarrantyTracker)",
    warrantyTracker.connect(owner1).submitClaim(vin1, claimHash)
  ));

  results.push(await measure(
    "approveClaim (MANUFACTURER_ADMIN_ROLE)",
    warrantyTracker.connect(deployer).approveClaim(vin1, 0)
  ));

  // Submit second claim to deny (index 1 — index 0 was approved above)
  await warrantyTracker.connect(owner1).submitClaim(vin1, claimHash);
  results.push(await measure(
    "denyClaim (MANUFACTURER_ADMIN_ROLE)",
    warrantyTracker.connect(deployer).denyClaim(vin1, 1, resolutionHash)
  ));

  results.push(await measure(
    "transferOwnership (vehicle owner)",
    registry.connect(owner1).transferOwnership(vin2, owner2.address)
  ));

  // ── Print table ───────────────────────────────────────────────────────────
  const PAD = {
    label: 48,
    gas: 10,
    ethCost: 12,
    usdCost: 10,
    latencyMs: 12,
  };

  const header = [
    "Operation".padEnd(PAD.label),
    "Gas Used".padStart(PAD.gas),
    "ETH Cost".padStart(PAD.ethCost),
    "USD Cost".padStart(PAD.usdCost),
    "Latency (ms)".padStart(PAD.latencyMs),
  ].join("  ");

  const sep = "-".repeat(header.length);

  console.log("\n" + sep);
  console.log("  Gas & Latency Benchmark — Blockchain Vehicle Service System");
  console.log(`  Gas price: ${GAS_PRICE_GWEI} Gwei   ETH/USD: $${ETH_USD}`);
  console.log(sep);
  console.log(header);
  console.log(sep);

  for (const r of results) {
    const row = [
      r.label.padEnd(PAD.label),
      r.gas.padStart(PAD.gas),
      r.ethCost.padStart(PAD.ethCost),
      `$${r.usdCost}`.padStart(PAD.usdCost),
      `${r.latencyMs}ms`.padStart(PAD.latencyMs),
    ].join("  ");
    console.log(row);
  }

  console.log(sep);

  const totalGas = results.reduce((s, r) => s + BigInt(r.gas), 0n);
  const avgLatency =
    results.reduce((s, r) => s + Number(r.latencyMs), 0) / results.length;

  console.log(`  Total gas (all ops): ${totalGas.toString()}`);
  console.log(`  Average latency:     ${avgLatency.toFixed(0)}ms`);
  console.log(sep + "\n");
}

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
