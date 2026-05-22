import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth-guard';

import { LoginComponent } from './features/auth/login/login';
import { RegisterComponent } from './features/auth/register/register';

import { DealerShellComponent } from './shared/shell/dealer-shell';
import { DashboardComponent } from './features/dealer/dashboard/dashboard';
import { VehicleLookupComponent } from './features/dealer/vehicle-lookup/vehicle-lookup';
import { SubmitServiceComponent } from './features/dealer/submit-service/submit-service';
import { PendingRecordsComponent } from './features/dealer/pending-records/pending-records';

import { ManufacturerShellComponent } from './shared/shell/manufacturer-shell';
import { ManufacturerDashboardComponent } from './features/manufacturer/dashboard/dashboard';
import { RegisterVehicleComponent } from './features/manufacturer/register-vehicle/register-vehicle';
import { WarrantyClaimsComponent } from './features/manufacturer/warranty-claims/warranty-claims';
import { DisputeResolutionComponent } from './features/manufacturer/dispute-resolution/dispute-resolution';

export const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },

  // Service Center routes
  {
    path: 'dealer',
    component: DealerShellComponent,
    canActivate: [authGuard],
    data: { role: 'SERVICE_CENTER' },
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      { path: 'dashboard', component: DashboardComponent },
      { path: 'vehicle-lookup', component: VehicleLookupComponent },
      { path: 'submit-service', component: SubmitServiceComponent },
      { path: 'pending-records', component: PendingRecordsComponent }
    ]
  },

  // Manufacturer routes
  {
    path: 'manufacturer',
    component: ManufacturerShellComponent,
    canActivate: [authGuard],
    data: { role: 'MANUFACTURER' },
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      { path: 'dashboard', component: ManufacturerDashboardComponent },
      { path: 'register-vehicle', component: RegisterVehicleComponent },
      { path: 'warranty-claims', component: WarrantyClaimsComponent },
      { path: 'dispute-resolution', component: DisputeResolutionComponent }
    ]
  },

  { path: '**', redirectTo: '/login' }
];
