#!/usr/bin/env python3
"""
VehicleChain seed script
Creates test accounts, vehicles, service records, and warranty claims
so all dashboard features can be exercised immediately.

Usage:
    python seed.py                           # default http://localhost:5000
    python seed.py --url http://HOST:5000    # custom backend URL

What gets created
─────────────────
Accounts
  manufacturer@vehiclechain.com  /  Password1!   (MANUFACTURER)
  service@autofix.com            /  Password1!   (SERVICE_CENTER)
  alice@owner.com                /  Password1!   (OWNER)
  bob@owner.com                  /  Password1!   (OWNER)

Vehicles  (registered by manufacturer)
  1HGCM82633A004352  Toyota Camry    2023  → alice
  2T1BURHE0JC050012  Honda Civic     2022  → alice
  JN1AZ4EH7FM730548  Nissan Altima   2021  → alice
  3VWFE21C04M000001  Volkswagen Golf 2020  → bob
  5YJSA1E26MF000001  Tesla Model 3   2021  → bob

Service records  (submitted by service center)
  Camry   – Oil Change          → alice verifies   [FINALIZED]
  Camry   – Brake Pad Replace   → left pending     [PENDING]
  Civic   – Tire Rotation       → alice verifies   [FINALIZED]
  Altima  – Transmission Flush  → alice disputes   [DISPUTED]
  Golf    – Full Service Check  → left pending     [PENDING]

Warranty claims  (submitted by owners)
  Camry  – Alternator failure   → manufacturer approves  [APPROVED]
  Civic  – Engine noise         → left pending           [PENDING]
  Altima – Airbag sensor fault  → manufacturer denies    [DENIED]
"""

import sys
import json
import argparse
import time

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests")
    sys.exit(1)

# ── ANSI colours ─────────────────────────────────────────────
G  = "\033[92m"   # green
Y  = "\033[93m"   # yellow
R  = "\033[91m"   # red
B  = "\033[94m"   # blue
DIM = "\033[2m"
BOLD = "\033[1m"
NC = "\033[0m"    # reset

def ok(msg):   print(f"  {G}✓{NC} {msg}")
def skip(msg): print(f"  {Y}→{NC} {DIM}{msg}{NC}")
def err(msg):  print(f"  {R}✗{NC} {msg}")
def hdr(msg):  print(f"\n{BOLD}{B}{msg}{NC}")
def sub(msg):  print(f"  {DIM}{msg}{NC}")

# ── Seed data ─────────────────────────────────────────────────
PASSWORD = "Password1!"

ACCOUNTS = [
    {"email": "manufacturer@vehiclechain.com", "role": "MANUFACTURER",    "label": "Manufacturer"},
    {"email": "service@autofix.com",           "role": "SERVICE_CENTER",  "label": "Service Center"},
    {"email": "alice@owner.com",               "role": "OWNER",           "label": "Owner (alice)"},
    {"email": "bob@owner.com",                 "role": "OWNER",           "label": "Owner (bob)"},
]

VEHICLES = [
    {"vin": "1HGCM82633A004352", "make": "Toyota",     "model": "Camry",    "year": 2023, "warranty_years": 5, "owner": "alice@owner.com"},
    {"vin": "2T1BURHE0JC050012", "make": "Honda",      "model": "Civic",    "year": 2022, "warranty_years": 4, "owner": "alice@owner.com"},
    {"vin": "JN1AZ4EH7FM730548", "make": "Nissan",     "model": "Altima",   "year": 2021, "warranty_years": 3, "owner": "alice@owner.com"},
    {"vin": "3VWFE21C04M000001", "make": "Volkswagen", "model": "Golf",     "year": 2020, "warranty_years": 3, "owner": "bob@owner.com"},
    {"vin": "5YJSA1E26MF000001", "make": "Tesla",      "model": "Model 3",  "year": 2021, "warranty_years": 5, "owner": "bob@owner.com"},
]

SERVICE_RECORDS = [
    # (vin, service_type, mileage, parts, technician, notes, action, owner_email)
    ("1HGCM82633A004352", "Oil Change",         32000, "Engine oil, oil filter",      "John Tan",   "Full synthetic 5W-30",        "verify",  "alice@owner.com"),
    ("1HGCM82633A004352", "Brake Pad Replacement", 32500, "Front brake pads, rotors", "John Tan",   "OEM brake pads installed",    "pending", None),
    ("2T1BURHE0JC050012", "Tire Rotation",      18000, "",                            "Siti Rahma", "Rotated all 4 tires",         "verify",  "alice@owner.com"),
    ("JN1AZ4EH7FM730548", "Transmission Flush", 45000, "ATF fluid",                  "Ravi Kumar", "Replaced with Nissan NS-3",   "dispute", "alice@owner.com"),
    ("3VWFE21C04M000001", "Full Service Check", 28000, "Air filter, spark plugs",    "John Tan",   "Annual full service completed","pending", None),
]

WARRANTY_CLAIMS = [
    # (vin, issue, action, owner_email, deny_reason)
    ("1HGCM82633A004352", "Alternator failure — battery warning light appeared at 31500km",   "approve", "alice@owner.com", None),
    ("2T1BURHE0JC050012", "Engine making unusual knocking noise at cold start since 17000km",  "pending", "alice@owner.com", None),
    ("JN1AZ4EH7FM730548", "Airbag warning sensor fault — SRS light on dashboard",             "deny",    "alice@owner.com", "Fault caused by aftermarket modification to steering column — not covered under warranty"),
]

# ── API helpers ───────────────────────────────────────────────
def api(base, method, path, token=None, **kwargs):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{base}{path}"
    resp = getattr(requests, method)(url, headers=headers, timeout=15, **kwargs)
    return resp

def register_or_login(base, email, role, label):
    r = api(base, "post", "/api/auth/register", json={"email": email, "password": PASSWORD, "role": role})
    if r.status_code == 200:
        token = r.json()["token"]
        ok(f"Registered {label} ({email})")
        return token
    body = r.json()
    if "already exists" in body.get("error", "").lower():
        r2 = api(base, "post", "/api/auth/login", json={"email": email, "password": PASSWORD})
        if r2.status_code == 200:
            skip(f"{label} already exists — logged in ({email})")
            return r2.json()["token"]
        err(f"Login failed for {email}: {r2.json()}")
        return None
    err(f"Register failed for {email}: {body}")
    return None

# ── Main ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Seed VehicleChain with test data")
    parser.add_argument("--url", default="http://localhost:5000", help="Backend base URL")
    args = parser.parse_args()
    BASE = args.url.rstrip("/")

    print(f"\n{BOLD}VehicleChain Seed Script{NC}")
    print(f"{DIM}Target: {BASE}{NC}")

    # ── Health check ──────────────────────────────────────────
    hdr("0 / Checking backend + blockchain")
    try:
        h = api(BASE, "get", "/api/health")
        data = h.json()
        if data.get("blockchain", {}).get("connected"):
            ok("Backend reachable, Ganache connected")
        else:
            err("Backend reachable but Ganache is NOT connected")
            print(f"\n  {Y}Make sure Ganache is running on port 8545 and contracts are deployed.{NC}")
            print(f"  Run:  cd smart-contracts && npx hardhat run scripts/deploy.js --network localhost\n")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        err(f"Cannot reach backend at {BASE}")
        print(f"\n  {Y}Start the Flask server first:  cd backend && python app.py{NC}\n")
        sys.exit(1)

    # ── Step 1 — Accounts ─────────────────────────────────────
    hdr("1 / Registering accounts")
    tokens = {}
    for acc in ACCOUNTS:
        t = register_or_login(BASE, acc["email"], acc["role"], acc["label"])
        if t is None:
            err(f"Cannot continue without a token for {acc['email']}")
            sys.exit(1)
        tokens[acc["email"]] = t
        time.sleep(0.3)   # give blockchain a moment between account creations

    mfr_token = tokens["manufacturer@vehiclechain.com"]
    sc_token   = tokens["service@autofix.com"]
    alice_tok  = tokens["alice@owner.com"]
    bob_tok    = tokens["bob@owner.com"]
    owner_tokens = {"alice@owner.com": alice_tok, "bob@owner.com": bob_tok}

    # ── Step 2 — Vehicles ─────────────────────────────────────
    hdr("2 / Registering vehicles")
    registered_vins = set()
    for v in VEHICLES:
        label = f"{v['year']} {v['make']} {v['model']} ({v['vin']})"
        r = api(BASE, "post", "/api/vehicle/register", token=mfr_token, json={
            "vin":           v["vin"],
            "owner_email":   v["owner"],
            "warranty_years": v["warranty_years"],
            "make":          v["make"],
            "model":         v["model"],
            "year":          v["year"],
        })
        if r.status_code == 200:
            ok(f"Registered {label} → {v['owner']}")
            registered_vins.add(v["vin"])
        elif "already" in r.text.lower() or "exists" in r.text.lower():
            skip(f"{label} already on-chain")
            registered_vins.add(v["vin"])
        else:
            err(f"Failed to register {label}: {r.json()}")
        time.sleep(0.5)

    # ── Step 3 — Service records ──────────────────────────────
    hdr("3 / Submitting service records")
    today = time.strftime("%Y-%m-%d")
    service_indices = {}   # vin -> list of submitted record indices

    for (vin, stype, mileage, parts, tech, notes, action, owner_email) in SERVICE_RECORDS:
        # Get current count before submitting so we know the index
        pending_r = api(BASE, "get", f"/api/service/pending/{vin}", token=sc_token)
        idx_before = len(pending_r.json().get("pending_services", [])) if pending_r.ok else 0

        r = api(BASE, "post", "/api/service/submit", token=sc_token, json={
            "vin":              vin,
            "service_type":     stype,
            "service_date":     today,
            "mileage":          mileage,
            "parts_replaced":   parts,
            "technician_name":  tech,
            "service_notes":    notes,
        })
        if r.status_code == 200:
            ok(f"Submitted: {stype} on {vin}")
            service_indices.setdefault(vin, []).append((idx_before, action, owner_email, stype))
        else:
            body = r.json()
            if "duplicate" in str(body).lower() or "already" in str(body).lower():
                skip(f"{stype} on {vin} — already submitted")
            else:
                err(f"Failed to submit {stype} on {vin}: {body}")
        time.sleep(0.4)

    # ── Step 4 — Owner verify / dispute ───────────────────────
    hdr("4 / Owner actions on service records (verify / dispute)")
    for vin, records in service_indices.items():
        # Fetch the fresh pending list once for this VIN
        for (idx_before, action, owner_email, stype) in records:
            if action == "pending":
                sub(f"Leaving '{stype}' on {vin} as PENDING (test data for dashboard)")
                continue
            if owner_email is None:
                continue
            owner_tok = owner_tokens.get(owner_email)
            if not owner_tok:
                continue

            # The newly submitted record is at index idx_before in the pending list
            record_index = idx_before
            if action == "verify":
                r = api(BASE, "post", "/api/service/owner/verify", token=owner_tok,
                        json={"vin": vin, "record_index": record_index})
                if r.status_code == 200:
                    ok(f"Owner verified '{stype}' on {vin}")
                else:
                    err(f"Verify failed for '{stype}' on {vin}: {r.json()}")
            elif action == "dispute":
                r = api(BASE, "post", "/api/service/owner/dispute", token=owner_tok,
                        json={"vin": vin, "record_index": record_index,
                              "reason": "Service was performed without my knowledge and the mileage recorded is incorrect"})
                if r.status_code == 200:
                    ok(f"Owner DISPUTED '{stype}' on {vin}")
                else:
                    err(f"Dispute failed for '{stype}' on {vin}: {r.json()}")
            time.sleep(0.4)

    # ── Step 5 — Warranty claims ──────────────────────────────
    hdr("5 / Submitting warranty claims")
    claim_indices = {}   # vin -> index of submitted claim

    for (vin, issue, action, owner_email, _) in WARRANTY_CLAIMS:
        owner_tok = owner_tokens.get(owner_email)
        if not owner_tok:
            err(f"No token for {owner_email}, skipping warranty claim")
            continue

        # Count existing claims to find new index
        existing_r = api(BASE, "get", f"/api/warranty/claims/{vin}", token=owner_tok)
        idx = len(existing_r.json().get("claims", [])) if existing_r.ok else 0

        r = api(BASE, "post", "/api/warranty/submit-claim", token=owner_tok,
                json={"vin": vin, "issue_description": issue})
        if r.status_code == 200:
            ok(f"Warranty claim submitted for {vin}")
            claim_indices[vin] = idx
        else:
            body = r.json()
            if "already" in str(body).lower() or "duplicate" in str(body).lower():
                skip(f"Claim for {vin} already exists")
                claim_indices[vin] = 0
            else:
                err(f"Failed warranty claim for {vin}: {body}")
        time.sleep(0.4)

    # ── Step 6 — Manufacturer approve / deny claims ───────────
    hdr("6 / Manufacturer actions on warranty claims")
    for (vin, issue, action, owner_email, deny_reason) in WARRANTY_CLAIMS:
        if action == "pending":
            sub(f"Leaving claim for {vin} as PENDING (test data for dashboard)")
            continue
        claim_idx = claim_indices.get(vin)
        if claim_idx is None:
            continue

        if action == "approve":
            r = api(BASE, "post", "/api/warranty/approve-claim", token=mfr_token,
                    json={"vin": vin, "claim_index": claim_idx})
            if r.status_code == 200:
                ok(f"Manufacturer APPROVED warranty claim for {vin}")
            else:
                err(f"Approve failed for {vin}: {r.json()}")
        elif action == "deny":
            r = api(BASE, "post", "/api/warranty/deny-claim", token=mfr_token,
                    json={"vin": vin, "claim_index": claim_idx, "reason": deny_reason})
            if r.status_code == 200:
                ok(f"Manufacturer DENIED warranty claim for {vin}")
            else:
                err(f"Deny failed for {vin}: {r.json()}")
        time.sleep(0.4)

    # ── Summary ───────────────────────────────────────────────
    print(f"\n{'─'*58}")
    print(f"{BOLD}Seed complete — login credentials{NC}")
    print(f"{'─'*58}")
    rows = [
        ("Role",            "Email",                          "Password"),
        ("─"*15,            "─"*32,                          "─"*10),
        ("Manufacturer",    "manufacturer@vehiclechain.com",  PASSWORD),
        ("Service Center",  "service@autofix.com",            PASSWORD),
        ("Owner (alice)",   "alice@owner.com",                PASSWORD),
        ("Owner (bob)",     "bob@owner.com",                  PASSWORD),
    ]
    for role, email, pw in rows:
        print(f"  {role:<16}  {email:<33}  {pw}")
    print(f"\n{BOLD}VINs to test with{NC}")
    print(f"{'─'*58}")
    for v in VEHICLES:
        print(f"  {v['vin']}  {v['year']} {v['make']} {v['model']:<12}  owner: {v['owner']}")
    print(f"\n{BOLD}Dashboard test coverage{NC}")
    print(f"{'─'*58}")
    print(f"  Manufacturer  — 1 pending claim, 1 approved, 1 denied, 1 disputed record")
    print(f"  Service Center — 2 pending records, 2 finalized, 1 disputed")
    print(f"  Vehicle lookup — all 5 VINs above are registered on-chain")
    print()

if __name__ == "__main__":
    main()
