import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth-guard';

import { LoginComponent } from './features/auth/login/login';
import { RegisterComponent } from './features/auth/register/register';
import { ForgotPasswordComponent } from './features/auth/forgot-password/forgot-password';
import { ResetPasswordComponent } from './features/auth/reset-password/reset-password';

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
import { ServiceCentersComponent } from './features/manufacturer/service-centers/service-centers';
import { ScDetailComponent } from './features/manufacturer/service-centers/detail/sc-detail';
import { FleetComponent } from './features/manufacturer/fleet/fleet';
import { ProfileComponent } from './features/shared/profile/profile';
import { VerifyComponent } from './features/public/verify/verify';

export const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: 'forgot-password', component: ForgotPasswordComponent },
  { path: 'reset-password', component: ResetPasswordComponent },
  { path: 'verify/:vin', component: VerifyComponent },
  { path: 'verify', component: VerifyComponent },

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
      { path: 'pending-records', component: PendingRecordsComponent },
      { path: 'profile', component: ProfileComponent },
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
      { path: 'fleet', component: FleetComponent },
      { path: 'warranty-claims', component: WarrantyClaimsComponent },
      { path: 'dispute-resolution', component: DisputeResolutionComponent },
      { path: 'service-centers', component: ServiceCentersComponent },
      { path: 'service-centers/:id', component: ScDetailComponent },
      { path: 'profile', component: ProfileComponent },
    ]
  },

  { path: '**', redirectTo: '/login' }
];
