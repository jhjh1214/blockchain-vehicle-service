import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { VehicleService } from '../../../core/services/vehicle';
import { ServiceService } from '../../../core/services/service';
import { Vehicle } from '../../../core/models/vehicle.model';
import { ServiceRecord } from '../../../core/models/service.model';

@Component({
  selector: 'app-vehicle-lookup',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './vehicle-lookup.html',
  styleUrls: ['./vehicle-lookup.css']
})
export class VehicleLookupComponent {
  searchForm: FormGroup;
  loading = false;
  historyLoading = false;
  error = '';
  vehicle: Vehicle | null = null;
  serviceHistory: ServiceRecord[] = [];
  showHistory = false;

  constructor(
    private fb: FormBuilder,
    private vehicleService: VehicleService,
    private serviceService: ServiceService
  ) {
    this.searchForm = this.fb.group({
      vin: ['', [Validators.required, Validators.minLength(17), Validators.maxLength(17)]]
    });
  }

  get f() { return this.searchForm.controls; }

  onSearch(): void {
    if (this.searchForm.invalid) {
      this.searchForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.error = '';
    this.vehicle = null;
    this.serviceHistory = [];
    this.showHistory = false;

    this.vehicleService.getVehicle(this.searchForm.value.vin).subscribe({
      next: (data) => {
        this.vehicle = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = err.error?.error || 'Vehicle not found';
        this.loading = false;
      }
    });
  }

  loadServiceHistory(): void {
    if (!this.vehicle || this.historyLoading) return;

    this.historyLoading = true;
    this.serviceService.getServiceHistory(this.vehicle.vin).subscribe({
      next: (data) => {
        this.serviceHistory = data.service_history;
        this.showHistory = true;
        this.historyLoading = false;
      },
      error: () => {
        this.error = 'Failed to load service history';
        this.historyLoading = false;
      }
    });
  }

  formatDate(timestamp: number): string {
    if (!timestamp) return '—';
    return new Date(timestamp * 1000).toLocaleDateString('en-MY', {
      year: 'numeric', month: 'short', day: 'numeric'
    });
  }

  formatDateTime(iso: string): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-MY', {
      year: 'numeric', month: 'short', day: 'numeric'
    });
  }
}
