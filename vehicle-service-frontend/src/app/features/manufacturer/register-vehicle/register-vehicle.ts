import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { VehicleService } from '../../../core/services/vehicle';

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

  constructor(private fb: FormBuilder, private vehicleService: VehicleService) {
    this.registerForm = this.fb.group({
      vin: ['', [Validators.required, Validators.pattern(/^[A-HJ-NPR-Z0-9]{17}$/i)]],
      owner_email: ['', [Validators.required, Validators.email]],
      warranty_years: ['', [Validators.required, Validators.min(1), Validators.max(10)]],
      make: [''],
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

    const data = { ...this.registerForm.value };
    data.warranty_years = parseInt(data.warranty_years, 10);
    if (data.year) data.year = parseInt(data.year, 10);

    this.vehicleService.registerVehicle(data).subscribe({
      next: (response) => {
        this.success = `Vehicle registered. VIN: ${response.vin} — Transaction: ${(response.transaction?.tx_hash || '').slice(0, 18)}…`;
        this.loading = false;
        setTimeout(() => {
          this.registerForm.reset();
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
    this.registerForm.reset();
    this.error = '';
    this.success = '';
  }
}
