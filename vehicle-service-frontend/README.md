# Vehicle Service Frontend

Angular 21 web application for the Blockchain Vehicle Service system. Provides dashboards for **Manufacturers** and **Service Centres** (Dealers). Vehicle Owners use the Flutter mobile app instead.

---

## Features

### Manufacturer Dashboard
- Register new vehicles on-chain (VIN, owner email, warranty period, make/model/year); Make is locked to the manufacturer's registered brand
- Pre-register vehicles without an owner (owner claims via mobile app later)
- View all vehicles registered under the manufacturer's brand
- Manage authorised service centres (list, activate, suspend, view detail)
- Pre-register SSM license numbers that service centres must supply during account registration
- Review and approve or deny warranty claims submitted by owners
- Resolve disputed service records (approve or reject with resolution notes)
- View dashboard statistics: total vehicles, active warranties, pending claims, dispute rate

### Service Centre (Dealer) Dashboard
- Submit service records for a vehicle (metadata hashed SHA-256, hash anchored on-chain)
- View pending (unverified) and finalized service history for any VIN
- Look up vehicle details and warranty status by VIN
- View and manage disputed records submitted against this service centre

### Shared (Both Roles)
- Update profile (name, phone, city, state)
- Change password

### Auth
- Login with email and password
- Registration (role selection: Manufacturer or Service Centre)
- Forgot password — sends a reset link via email
- Reset password with token from email link

### Public
- Verify any vehicle by VIN — ownership, warranty status, service hash count
- Privacy Policy page

---

## Tech Stack

| Technology | Version |
|---|---|
| Angular | 21.2.x |
| Angular Material | 21.2.x |
| TypeScript | ~5.7 |
| RxJS | ~7.8 |
| ng2-charts + Chart.js | 10.0 / 4.5 |
| Leaflet | 1.9.4 |
| jwt-decode | 4.0.0 |

Architecture: standalone components throughout (no NgModules), lazy-loaded feature routes, HTTP interceptor for Bearer token injection, Angular signals for reactive state.

---

## Project Structure

```
vehicle-service-frontend/
└── src/
    └── app/
        ├── core/
        │   ├── guards/
        │   │   └── auth-guard.ts              # Redirects to /login if no JWT
        │   ├── interceptors/
        │   │   └── auth-interceptor.ts        # Attaches Authorization: Bearer <token>
        │   ├── services/
        │   │   ├── auth.ts                    # Login, register, logout, currentUser signal
        │   │   ├── vehicle.ts                 # Register, getVehicle, getMyVehicles
        │   │   ├── service.ts                 # Submit, pending, history, verify, dispute, resolve
        │   │   ├── warranty.ts                # Check, submitClaim, approveClaim, denyClaim
        │   │   ├── sc-management.service.ts   # Service centre listing, activation, SSM licenses
        │   │   ├── inactivity.service.ts      # 30-minute session inactivity timeout
        │   │   ├── blockchain.service.ts      # Public VIN lookup
        │   │   └── theme.service.ts
        │   └── models/
        │       ├── service.model.ts
        │       ├── user.model.ts
        │       └── vehicle.model.ts
        │
        ├── features/
        │   ├── auth/
        │   │   ├── login/                     # Login form
        │   │   ├── register/                  # Role selection + registration form
        │   │   ├── forgot-password/           # Forgot password — sends reset email
        │   │   └── reset-password/            # Reset password with token from email
        │   │
        │   ├── manufacturer/
        │   │   ├── dashboard/                 # Overview cards, quick links, charts
        │   │   ├── register-vehicle/          # New vehicle registration form (Make locked to brand)
        │   │   ├── dispute-resolution/        # Search VIN, view and resolve disputes
        │   │   ├── warranty-claims/           # List and approve/deny warranty claims
        │   │   ├── fleet/                     # Vehicle fleet view
        │   │   └── service-centers/           # Manage authorised service centres + SSM licenses
        │   │       └── detail/                # Service centre detail view
        │   │
        │   ├── dealer/
        │   │   ├── dashboard/                 # Overview cards, quick links
        │   │   ├── vehicle-lookup/            # Search VIN, view history
        │   │   ├── pending-records/           # List pending service records
        │   │   ├── disputes/                  # View and respond to disputed records
        │   │   └── submit-service/            # New service submission form
        │   │
        │   ├── shared/
        │   │   └── profile/                   # Update name/phone/city/state; change password
        │   │
        │   └── public/
        │       ├── verify/                    # Public VIN verification page
        │       └── privacy-policy/            # PDPA privacy policy page
        │
        ├── shared/
        │   ├── constants/
        │   │   └── my-cities.ts               # Malaysian city list for profile form
        │   └── shell/
        │       ├── manufacturer-shell.ts      # Manufacturer nav layout + inactivity timeout
        │       └── dealer-shell.ts            # Dealer nav layout + inactivity timeout
        │
        ├── app.routes.ts                      # Root routes (lazy loads shells)
        └── app.ts                             # Root standalone component
```

---

## Prerequisites

- Node.js 18+ and npm

---

## Setup

```bash
cd vehicle-service-frontend
npm install
```

---

## Development Server

```bash
npx ng serve
```

App is available at `http://localhost:4200`. The backend must be running at `http://localhost:5000` (see root README for backend setup). The dev environment reads `src/environments/environment.ts` which points to `http://localhost:5000/api`.

---

## Build

```bash
# Development build (type-check only)
npx ng build --configuration development

# Production build
npx ng build --configuration production
```

Production output lands in `dist/vehicle-service-frontend/`. Serve it with Nginx or any static file server.

---

## Environment Configuration

Edit `src/environments/environment.ts` for development:

```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:5000/api'
};
```

Edit `src/environments/environment.prod.ts` for production. The auth interceptor appends `Authorization: Bearer <token>` from `localStorage` to every outgoing HTTP request.

---

## Authentication

- JWT is stored in `localStorage` under the key `token`
- `auth-guard.ts` checks for a valid token before allowing access to protected routes
- `auth-interceptor.ts` attaches the token to all HTTP requests automatically
- Roles (`MANUFACTURER`, `SERVICE_CENTER`) determine which shell layout and feature routes are accessible
- Login redirects to the appropriate dashboard based on the user's role
- **Session inactivity timeout:** `inactivity.service.ts` shows a warning dialog at 25 minutes of inactivity and auto-logs out at 30 minutes

---

## API Integration

All API calls go to the Flask backend at `/api`. The services in `core/services/` map to backend blueprints:

| Angular service | Backend blueprint | URL prefix |
|---|---|---|
| `auth.ts` | `auth` | `/api/auth` |
| `vehicle.ts` | `vehicles` | `/api/vehicle` |
| `service.ts` | `services` | `/api/service` |
| `warranty.ts` | `warranties` | `/api/warranty` |
| `sc-management.service.ts` | `sc_management` | `/api/sc` |

---

## Type Check

```bash
npx ng build --configuration development
```

A clean build with no TypeScript or template errors confirms the frontend is type-safe.

---

## Dependencies

Key packages (see `package.json` for full list):

```json
{
  "@angular/core": "^21.2.0",
  "@angular/material": "^21.2.10",
  "rxjs": "~7.8.0",
  "ng2-charts": "^10.0.0",
  "chart.js": "^4.5.1",
  "leaflet": "^1.9.4",
  "jwt-decode": "^4.0.0"
}
```
