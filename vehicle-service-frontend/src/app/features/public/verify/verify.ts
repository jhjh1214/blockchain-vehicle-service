import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { VehicleService } from '../../../core/services/vehicle';

@Component({
  selector: 'app-verify',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './verify.html',
})
export class VerifyComponent {
  vin = '';
  result: any = null;
  loading = false;
  error = '';

  constructor(private vehicleService: VehicleService) {}

  lookup(): void {
    const v = this.vin.trim().toUpperCase();
    if (!v || v.length !== 17) { this.error = 'Please enter a valid 17-character VIN'; return; }
    this.loading = true;
    this.error = '';
    this.result = null;
    this.vehicleService.getPublicVehicle(v).subscribe({
      next: r => { this.result = r; this.loading = false; },
      error: e => {
        this.error = e.error?.error || 'Vehicle not found';
        this.loading = false;
      }
    });
  }

  warrantyDate(ts: number): string {
    if (!ts) return '—';
    return new Date(ts * 1000).toLocaleDateString('en-MY', { year: 'numeric', month: 'long', day: 'numeric' });
  }
}
