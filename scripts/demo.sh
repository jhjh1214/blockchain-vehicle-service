#!/usr/bin/env bash
# ==============================================================================
# VehicleChain End-to-End Demo Script
# ==============================================================================
# Prerequisites:
#   1. Ganache running:  npx hardhat node --port 8545
#   2. Contracts deployed + seeded: cd smart-contracts && npx hardhat run scripts/deploy.js --network localhost && npx hardhat run scripts/seed.js --network localhost
#   3. Backend running:  cd backend && python app.py
#   4. Set BASE_URL below if different

BASE_URL="${BASE_URL:-http://localhost:5000/api}"
echo "================================================================"
echo "  VehicleChain Demo — Backend: $BASE_URL"
echo "================================================================"

# ── helpers ──────────────────────────────────────────────────────────────────
header() { echo; echo "── $1 ──────────────────────────────────────────────────"; }
check() { [ $? -eq 0 ] && echo "  ✓ OK" || echo "  ✗ FAIL"; }

# ── 1. Health check ───────────────────────────────────────────────────────────
header "1. Blockchain health check"
curl -s "$BASE_URL/health" | python3 -m json.tool
check

# ── 2. Manufacturer login ─────────────────────────────────────────────────────
header "2. Manufacturer login"
MFR_RESP=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"manufacturer@toyota.com","password":"password123"}')
echo "$MFR_RESP" | python3 -m json.tool
MFR_TOKEN=$(echo "$MFR_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
[ -n "$MFR_TOKEN" ] && echo "  ✓ Token acquired" || echo "  ✗ No token — check credentials"

# ── 3. Register a vehicle ─────────────────────────────────────────────────────
header "3. Register vehicle (Toyota Camry 2024)"
EXPIRY=$(($(date +%s) + 31536000 * 3))   # 3 years
curl -s -X POST "$BASE_URL/vehicle/register" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MFR_TOKEN" \
  -d "{\"vin\":\"DEMO00000000000001\",\"make\":\"Toyota\",\"model\":\"Camry\",\"year\":2024,\"warranty_years\":3}" | python3 -m json.tool
check

# ── 4. Service Centre login ───────────────────────────────────────────────────
header "4. Service Centre login"
SC_RESP=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"sc1@toyota.com","password":"password123"}')
SC_TOKEN=$(echo "$SC_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
[ -n "$SC_TOKEN" ] && echo "  ✓ SC token acquired" || echo "  ✗ No SC token"

# ── 5. Submit a service record ────────────────────────────────────────────────
header "5. Submit service record (Oil Change)"
SUBMIT_RESP=$(curl -s -X POST "$BASE_URL/service/submit" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SC_TOKEN" \
  -d "{
    \"vin\":\"DEMO00000000000001\",
    \"service_type\":\"Oil Change\",
    \"service_date\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"mileage\":15000,
    \"technician_name\":\"John Doe\",
    \"parts_replaced\":\"Engine oil 5W-30, Oil filter\",
    \"service_notes\":\"Routine oil change at 15,000 km\"
  }")
echo "$SUBMIT_RESP" | python3 -m json.tool
METADATA_HASH=$(echo "$SUBMIT_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('metadata_hash',''))" 2>/dev/null)
echo "  Metadata hash: $METADATA_HASH"
check

# ── 6. Check warranty status ──────────────────────────────────────────────────
header "6. Check warranty status"
curl -s "$BASE_URL/warranty/check/DEMO00000000000001" \
  -H "Authorization: Bearer $MFR_TOKEN" | python3 -m json.tool
check

# ── 7. Check warranty eligibility ────────────────────────────────────────────
header "7. Warranty claim eligibility check"
curl -s "$BASE_URL/warranty/check-eligibility/DEMO00000000000001" \
  -H "Authorization: Bearer $MFR_TOKEN" | python3 -m json.tool
check

# ── 8. Manufacturer dashboard stats ──────────────────────────────────────────
header "8. Manufacturer dashboard stats"
curl -s "$BASE_URL/vehicle/dashboard-stats" \
  -H "Authorization: Bearer $MFR_TOKEN" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  Registered vehicles : {d.get('total_vehicles')}\")
print(f\"  Active warranties   : {d.get('active_warranties')}\")
print(f\"  Warranty claims     : {d.get('warranty_claims')}\")
print(f\"  Services this month : {d.get('services_this_month')}\")
"
check

# ── 9. Activity feed ──────────────────────────────────────────────────────────
header "9. Recent activity feed"
curl -s "$BASE_URL/vehicle/activity-feed" \
  -H "Authorization: Bearer $MFR_TOKEN" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
for item in d.get('feed', [])[:5]:
    print(f\"  [{item['type']:15s}] {item['vin']} — {item['description'][:50]}\")
"
check

echo
echo "================================================================"
echo "  Demo complete. Open http://localhost:4200 to view the web app."
echo "================================================================"
