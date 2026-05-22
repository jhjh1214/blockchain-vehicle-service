# setup.ps1 — Full project setup for blockchain-vehicle-service
# Run from the project root: .\setup.ps1
# Requires: Python 3.10+, Node.js 18+, npm

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

function Write-Step($msg) { Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "   OK  $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "   WARN $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "   FAIL $msg" -ForegroundColor Red; exit 1 }

# ─────────────────────────────────────────────────────────────────────────────
# 1. Python version check
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Checking Python version"
try {
    $pyver = python --version 2>&1
    Write-OK $pyver
    if ($pyver -notmatch "Python 3\.(1[0-9]|[2-9][0-9])") {
        Write-Warn "Python 3.10+ is recommended. Detected: $pyver"
    }
} catch {
    Write-Fail "Python not found. Install from https://python.org"
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. Backend — create venv and install dependencies
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Setting up Python virtual environment (backend/venv)"
$BackendDir = Join-Path $Root "backend"
$VenvDir    = Join-Path $BackendDir "venv"

if (-not (Test-Path $VenvDir)) {
    python -m venv $VenvDir
    Write-OK "Created venv at $VenvDir"
} else {
    Write-OK "venv already exists — skipping creation"
}

$PipExe = Join-Path $VenvDir "Scripts\pip.exe"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

Write-Step "Installing backend Python dependencies"
& $PipExe install --upgrade pip --quiet
& $PipExe install -r (Join-Path $BackendDir "requirements.txt")
Write-OK "Backend dependencies installed"

# ─────────────────────────────────────────────────────────────────────────────
# 3. Check .env exists
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Checking backend .env file"
$EnvFile = Join-Path $BackendDir ".env"
if (-not (Test-Path $EnvFile)) {
    $ExampleEnv = Join-Path $BackendDir ".env.example"
    if (Test-Path $ExampleEnv) {
        Copy-Item $ExampleEnv $EnvFile
        Write-Warn ".env created from .env.example — update contract addresses before running"
    } else {
        Write-Warn ".env not found. Create backend/.env with your contract addresses."
    }
} else {
    Write-OK ".env found"
}

# ─────────────────────────────────────────────────────────────────────────────
# 4. Node.js version check
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Checking Node.js version"
try {
    $nodever = node --version 2>&1
    Write-OK "Node.js $nodever"
    if ($nodever -match "v(\d+)" -and [int]$Matches[1] -lt 18) {
        Write-Warn "Node.js 18+ is recommended. Detected: $nodever"
    }
} catch {
    Write-Fail "Node.js not found. Install from https://nodejs.org"
}

# ─────────────────────────────────────────────────────────────────────────────
# 5. Smart contracts — npm install + compile
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Installing smart contract dependencies (Hardhat)"
$ContractsDir = Join-Path $Root "smart-contracts"
Push-Location $ContractsDir
try {
    npm install --silent
    Write-OK "npm install complete"

    Write-Step "Compiling smart contracts"
    npx hardhat compile
    Write-OK "Contracts compiled"
} finally {
    Pop-Location
}

# ─────────────────────────────────────────────────────────────────────────────
# 6. Frontend — npm install
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Installing Angular frontend dependencies"
$FrontendDir = Join-Path $Root "vehicle-service-frontend"
Push-Location $FrontendDir
try {
    npm install --silent
    Write-OK "Frontend npm install complete"

    # Check Angular CLI
    $ngVersion = npx ng version 2>&1 | Select-String "Angular CLI"
    if ($ngVersion) {
        Write-OK $ngVersion
    }
} finally {
    Pop-Location
}

# ─────────────────────────────────────────────────────────────────────────────
# 7. ABI copy (if contracts were just compiled and abis dir is empty)
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Checking ABI files in backend/abis"
$AbiDir = Join-Path $BackendDir "abis"
if (-not (Test-Path $AbiDir)) { New-Item -ItemType Directory -Path $AbiDir | Out-Null }

$artifactsDir = Join-Path $ContractsDir "artifacts\contracts"
$contracts = @("VehicleRegistry", "ServiceLog", "WarrantyTracker")

foreach ($c in $contracts) {
    $src = Join-Path $artifactsDir "$c.sol\$c.json"
    $dst = Join-Path $AbiDir "$c.json"
    if (Test-Path $src) {
        Copy-Item $src $dst -Force
        Write-OK "Copied $c.json"
    } else {
        if (Test-Path $dst) {
            Write-OK "$c.json already in abis/ (compile first to refresh)"
        } else {
            Write-Warn "$c.json not found — run 'npx hardhat compile' in smart-contracts/"
        }
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# 8. Initialise database (only if it doesn't exist)
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Initialising SQLite database"
$DbFile = Join-Path $BackendDir "instance\vehicle_service.db"
if (-not (Test-Path $DbFile)) {
    Push-Location $BackendDir
    try {
        & $PythonExe init_db.py
        Write-OK "Database initialised"
    } catch {
        Write-Warn "Database init failed — run manually: cd backend && python init_db.py"
    } finally {
        Pop-Location
    }
} else {
    Write-OK "Database already exists"
}

# ─────────────────────────────────────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host " Setup complete!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host " Next steps:" -ForegroundColor White
Write-Host "  1. Start Ganache (port 8545, chain ID 1337)"
Write-Host "  2. Deploy contracts:"
Write-Host "       cd smart-contracts"
Write-Host "       npx hardhat run scripts/deploy.js --network ganache"
Write-Host "  3. Update backend/.env with the printed contract addresses"
Write-Host "  4. Copy ABIs:  .\setup.ps1   (re-run — copies compiled ABIs)"
Write-Host "  5. Start backend:"
Write-Host "       cd backend"
Write-Host "       .\venv\Scripts\Activate.ps1"
Write-Host "       python app.py"
Write-Host "  6. Start frontend:"
Write-Host "       cd vehicle-service-frontend"
Write-Host "       npx ng serve"
Write-Host ""
Write-Host " Run tests:" -ForegroundColor White
Write-Host "  Unit + API tests (no Ganache needed):"
Write-Host "       cd backend && .\venv\Scripts\Activate.ps1 && pytest"
Write-Host "  Smart contract tests:"
Write-Host "       cd smart-contracts && npx hardhat test"
Write-Host "  End-to-end tests (requires running backend + Ganache):"
Write-Host "       cd backend && pytest -m e2e"
Write-Host ""
