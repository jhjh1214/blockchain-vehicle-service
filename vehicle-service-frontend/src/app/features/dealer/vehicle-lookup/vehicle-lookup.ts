import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { VehicleService } from '../../../core/services/vehicle';
import { ServiceService } from '../../../core/services/service';
import { Vehicle } from '../../../core/models/vehicle.model';
import { ServiceRecord } from '../../../core/models/service.model';

@Component({
  selector: 'app-vehicle-lookup',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule, RouterModule],
  templateUrl: './vehicle-lookup.html',
  styleUrls: ['./vehicle-lookup.css']
})
export class VehicleLookupComponent implements OnInit {
  searchForm: FormGroup;
  loading = false;
  historyLoading = false;
  error = '';
  vehicle: Vehicle | null = null;
  serviceHistory: ServiceRecord[] = [];
  showHistory = false;

  showVoidForm = false;
  voidReason = '';
  voidLoading = false;
  voidSuccess = '';
  voidError = '';

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private vehicleService: VehicleService,
    private serviceService: ServiceService
  ) {
    this.searchForm = this.fb.group({
      vin: ['', [Validators.required, Validators.pattern(/^[A-HJ-NPR-Z0-9]{17}$/i)]]
    });
  }

  ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      const vin = (params['vin'] || '').toUpperCase();
      if (vin.length === 17) {
        this.searchForm.patchValue({ vin });
        this.onSearch();
      }
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

    this.showVoidForm = false;
    this.voidReason = '';
    this.voidSuccess = '';
    this.voidError = '';

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

  submitVoidRequest(): void {
    if (!this.vehicle || !this.voidReason.trim() || this.voidLoading) return;
    this.voidLoading = true;
    this.voidError = '';
    this.serviceService.createVoidRequest(this.vehicle.vin, this.voidReason.trim()).subscribe({
      next: () => {
        this.voidLoading = false;
        this.showVoidForm = false;
        this.voidSuccess = 'Warranty void request submitted. The manufacturer will be notified.';
        this.voidReason = '';
      },
      error: (err) => {
        this.voidLoading = false;
        this.voidError = err.error?.error || 'Failed to submit void request';
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

  exportCsv(): void {
    const headers = ['Service Type', 'Service Date', 'Mileage (km)', 'Technician', 'Parts Replaced', 'Notes'];
    const rows = this.serviceHistory.map(s => [
      s.metadata?.service_type ?? '',
      s.metadata?.service_date ?? '',
      s.metadata?.mileage?.toString() ?? '',
      s.metadata?.technician_name ?? '',
      s.metadata?.parts_replaced ?? '',
      s.metadata?.service_notes ?? '',
    ].map(v => `"${v.replace(/"/g, '""')}"`).join(','));

    const csv = [headers.join(','), ...rows].join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `service-history-${this.vehicle?.vin ?? 'export'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
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
