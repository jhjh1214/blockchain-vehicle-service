import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { VehicleService } from '../../../core/services/vehicle';
import { AuthService } from '../../../core/services/auth';

@Component({
  selector: 'app-register-vehicle',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './register-vehicle.html',
  styleUrls: ['./register-vehicle.css']
})
export class RegisterVehicleComponent {
  registerForm: FormGroup;
  loading = false;
  error = '';
  success = '';

  readonly currentMaxYear = new Date().getFullYear() + 1;
  readonly brand: string;

  constructor(
    private fb: FormBuilder,
    private vehicleService: VehicleService,
    private authService: AuthService,
  ) {
    this.brand = this.authService.currentUserValue?.brand ?? '';

    this.registerForm = this.fb.group({
      vin: ['', [Validators.required, Validators.pattern(/^[A-HJ-NPR-Z0-9]{17}$/i)]],
      owner_email: ['', [Validators.email]],
      warranty_years: ['', [Validators.required, Validators.min(1), Validators.max(10)]],
      make: [{ value: this.brand, disabled: true }],
      model: [''],
      year: ['', [Validators.min(1900), Validators.max(this.currentMaxYear)]]
    });
  }

  get f() { return this.registerForm.controls; }

  onSubmit(): void {
    if (this.registerForm.invalid) {
      this.registerForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.error = '';
    this.success = '';

    const data = { ...this.registerForm.getRawValue() };
    data.warranty_years = parseInt(data.warranty_years, 10);
    if (data.year) data.year = parseInt(data.year, 10);

    this.vehicleService.registerVehicle(data).subscribe({
      next: (response) => {
        const statusNote = response.registration_status === 'pending' ? ' (pending owner claim)' : '';
        this.success = `Vehicle registered${statusNote}. VIN: ${response.vin} — Transaction: ${(response.transaction?.tx_hash || '').slice(0, 18)}…`;
        this.loading = false;
        setTimeout(() => {
          this.registerForm.reset({ make: { value: this.brand, disabled: true } });
          this.success = '';
        }, 5000);
      },
      error: (err) => {
        this.error = err.error?.error || 'Failed to register vehicle.';
        this.loading = false;
      }
    });
  }

  onReset(): void {
    this.registerForm.reset({ make: { value: this.brand, disabled: true } });
    this.error = '';
    this.success = '';
  }
}
