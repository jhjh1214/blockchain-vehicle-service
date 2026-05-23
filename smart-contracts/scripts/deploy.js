const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  const VehicleRegistry = await hre.ethers.getContractFactory("VehicleRegistry");
  const vehicleRegistry = await VehicleRegistry.deploy();
  await vehicleRegistry.waitForDeployment();
  const vehicleRegistryAddress = await vehicleRegistry.getAddress();

  const ServiceLog = await hre.ethers.getContractFactory("ServiceLog");
  const serviceLog = await ServiceLog.deploy(vehicleRegistryAddress);
  await serviceLog.waitForDeployment();
  const serviceLogAddress = await serviceLog.getAddress();

  const WarrantyTracker = await hre.ethers.getContractFactory("WarrantyTracker");
  const warrantyTracker = await WarrantyTracker.deploy(vehicleRegistryAddress);
  await warrantyTracker.waitForDeployment();
  const warrantyTrackerAddress = await warrantyTracker.getAddress();

  // Required: allow ServiceLog to write service hashes to VehicleRegistry
  const SERVICE_LOG_ROLE = await vehicleRegistry.SERVICE_LOG_ROLE();
  await vehicleRegistry.grantRole(SERVICE_LOG_ROLE, serviceLogAddress);

  console.log(`DEPLOYER_ADDRESS=${deployer.address}`);
  console.log(`VEHICLE_REGISTRY_ADDRESS=${vehicleRegistryAddress}`);
  console.log(`SERVICE_LOG_ADDRESS=${serviceLogAddress}`);
  console.log(`WARRANTY_TRACKER_ADDRESS=${warrantyTrackerAddress}`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
