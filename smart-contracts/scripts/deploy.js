const hre = require("hardhat");
const fs = require('fs');
const path = require('path');

async function main() {
  console.log("🚀 Starting deployment...\n");
  
  // Get accounts
  const [deployer, manufacturer, serviceCenter, owner1, owner2] = await hre.ethers.getSigners();
  
  console.log("📋 Account Setup:");
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log(`Deployer:        ${deployer.address}`);
  console.log(`Manufacturer:    ${manufacturer.address}`);
  console.log(`Service Center:  ${serviceCenter.address}`);
  console.log(`Owner 1:         ${owner1.address}`);
  console.log(`Owner 2:         ${owner2.address}`);
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");

  // ==================== DEPLOY CONTRACTS ====================
  
  console.log("📦 Deploying Smart Contracts...\n");
  
  // 1. Deploy VehicleRegistry
  console.log("1️⃣ Deploying VehicleRegistry...");
  const VehicleRegistry = await hre.ethers.getContractFactory("VehicleRegistry");
  const vehicleRegistry = await VehicleRegistry.deploy();
  await vehicleRegistry.waitForDeployment();
  const vehicleRegistryAddress = await vehicleRegistry.getAddress();
  console.log(`   ✅ VehicleRegistry: ${vehicleRegistryAddress}\n`);

  // 2. Deploy ServiceLog
  console.log("2️⃣ Deploying ServiceLog...");
  const ServiceLog = await hre.ethers.getContractFactory("ServiceLog");
  const serviceLog = await ServiceLog.deploy(vehicleRegistryAddress);
  await serviceLog.waitForDeployment();
  const serviceLogAddress = await serviceLog.getAddress();
  console.log(`   ✅ ServiceLog: ${serviceLogAddress}\n`);

  // 3. Deploy WarrantyTracker
  console.log("3️⃣ Deploying WarrantyTracker...");
  const WarrantyTracker = await hre.ethers.getContractFactory("WarrantyTracker");
  const warrantyTracker = await WarrantyTracker.deploy(vehicleRegistryAddress);
  await warrantyTracker.waitForDeployment();
  const warrantyTrackerAddress = await warrantyTracker.getAddress();
  console.log(`   ✅ WarrantyTracker: ${warrantyTrackerAddress}\n`);

  // ==================== GRANT ROLES ====================
  
  console.log("🔐 Setting up roles...\n");

  // Grant Manufacturer Role
  const MANUFACTURER_ROLE = await vehicleRegistry.MANUFACTURER_ROLE();
  await vehicleRegistry.grantRole(MANUFACTURER_ROLE, manufacturer.address);
  console.log(`✅ MANUFACTURER_ROLE granted to: ${manufacturer.address}`);

  // Grant SERVICE_LOG_ROLE to ServiceLog contract on VehicleRegistry
  // This allows ServiceLog to call addServiceHash when records are finalized
  const SERVICE_LOG_ROLE = await vehicleRegistry.SERVICE_LOG_ROLE();
  await vehicleRegistry.grantRole(SERVICE_LOG_ROLE, serviceLogAddress);
  console.log(`✅ SERVICE_LOG_ROLE granted to ServiceLog contract: ${serviceLogAddress}`);

  // Grant Service Center Role
  const SERVICE_CENTER_ROLE = await serviceLog.SERVICE_CENTER_ROLE();
  await serviceLog.grantRole(SERVICE_CENTER_ROLE, serviceCenter.address);
  console.log(`✅ SERVICE_CENTER_ROLE granted to: ${serviceCenter.address}`);

  console.log(`ℹ️  OWNER_ROLE will be auto-granted when vehicles are registered\n`);

  // ==================== OPTIONAL: REGISTER TEST VEHICLE ====================
  
  console.log("🚗 Registering test vehicle (optional)...\n");
  
  try {
    // Calculate warranty expiry (3 years from now)
    const currentBlock = await hre.ethers.provider.getBlock('latest');
    const warrantyExpiry = currentBlock.timestamp + (3 * 365 * 24 * 60 * 60);
    
    // Sample VIN
    const testVIN = hre.ethers.encodeBytes32String("1HGCM82633A123456");
    
    // Register vehicle
    await vehicleRegistry.connect(manufacturer).registerVehicle(
      testVIN,
      owner1.address,
      warrantyExpiry
    );
    
    console.log(`✅ Test vehicle registered:`);
    console.log(`   VIN (bytes32): ${testVIN}`);
    console.log(`   VIN (string):  1HGCM82633A123456`);
    console.log(`   Owner:         ${owner1.address}`);
    console.log(`   Warranty:      ${new Date(warrantyExpiry * 1000).toLocaleDateString()}`);
    console.log(`   (OWNER_ROLE auto-granted to owner)\n`);
    
  } catch (error) {
    console.log(`⚠️  Test vehicle registration skipped: ${error.message}\n`);
  }

  // ==================== SAVE DEPLOYMENT INFO ====================
  
  const deploymentInfo = {
    network: hre.network.name,
    timestamp: new Date().toISOString(),
    contracts: {
      VehicleRegistry: vehicleRegistryAddress,
      ServiceLog: serviceLogAddress,
      WarrantyTracker: warrantyTrackerAddress
    },
    accounts: {
      deployer: deployer.address,
      manufacturer: manufacturer.address,
      serviceCenter: serviceCenter.address,
      owner1: owner1.address,
      owner2: owner2.address
    },
    roles: {
      MANUFACTURER_ROLE: manufacturer.address,
      SERVICE_CENTER_ROLE: serviceCenter.address,
      SERVICE_LOG_ROLE: serviceLogAddress,
      OWNER_ROLE: "Auto-granted on vehicle registration"
    }
  };

  // Save to JSON
  const deploymentPath = path.join(__dirname, '..', 'deployed_addresses.json');
  fs.writeFileSync(deploymentPath, JSON.stringify(deploymentInfo, null, 2));
  console.log(`📄 Deployment info saved to: deployed_addresses.json\n`);

  // ==================== GENERATE .env TEMPLATE ====================
  
  const envTemplate = `# Blockchain Configuration
GANACHE_URL=http://127.0.0.1:8545

# Contract Addresses (deployed on ${new Date().toLocaleDateString()})
VEHICLE_REGISTRY_ADDRESS=${vehicleRegistryAddress}
SERVICE_LOG_ADDRESS=${serviceLogAddress}
WARRANTY_TRACKER_ADDRESS=${warrantyTrackerAddress}

# Test Accounts (for development only - DO NOT USE IN PRODUCTION)
DEPLOYER_ADDRESS=${deployer.address}
MANUFACTURER_ADDRESS=${manufacturer.address}
SERVICE_CENTER_ADDRESS=${serviceCenter.address}
OWNER1_ADDRESS=${owner1.address}
OWNER2_ADDRESS=${owner2.address}

# Flask Configuration
SECRET_KEY=your-secret-key-change-this-in-production
DATABASE_URI=sqlite:///vehicle_service.db

# Keystore Configuration
KEYSTORE_DIR=keystore
KEYSTORE_ENCRYPTION_KEY=your-encryption-key-change-this-in-production

# Upload Configuration
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216
`;

  const envPath = path.join(__dirname, '..', '..', 'backend', '.env.example');
  fs.writeFileSync(envPath, envTemplate);
  console.log(`📝 .env template saved to: backend/.env.example\n`);

  // ==================== SUMMARY ====================
  
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log("🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!");
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
  
  console.log("📋 Next Steps:\n");
  console.log("1️⃣  Copy contract addresses to backend/.env:");
  console.log(`   VEHICLE_REGISTRY_ADDRESS=${vehicleRegistryAddress}`);
  console.log(`   SERVICE_LOG_ADDRESS=${serviceLogAddress}`);
  console.log(`   WARRANTY_TRACKER_ADDRESS=${warrantyTrackerAddress}\n`);
  
  console.log("2️⃣  Copy ABIs to backend:");
  console.log("   cd backend");
  console.log("   mkdir -p abis");
  console.log("   cp ../smart-contracts/artifacts/contracts/VehicleRegistry.sol/VehicleRegistry.json abis/");
  console.log("   cp ../smart-contracts/artifacts/contracts/ServiceLog.sol/ServiceLog.json abis/");
  console.log("   cp ../smart-contracts/artifacts/contracts/WarrantyTracker.sol/WarrantyTracker.json abis/\n");
  
  console.log("3️⃣  Initialize database:");
  console.log("   cd backend");
  console.log("   python init_db.py\n");
  
  console.log("4️⃣  Start backend:");
  console.log("   python app.py\n");
  
  console.log("5️⃣  Test the system:");
  console.log("   python test_blockchain.py\n");
  
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  });