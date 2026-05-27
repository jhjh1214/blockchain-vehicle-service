import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ServiceService } from '../../../core/services/service';
import { ServiceRecord } from '../../../core/models/service.model';

type FilterTab = 'all' | 'pending' | 'disputed';

@Component({
  selector: 'app-pending-records',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './pending-records.html',
  styleUrls: ['./pending-records.css']
})
export class PendingRecordsComponent {
  searchForm: FormGroup;
  loading = false;
  error = '';
  pendingRecords: ServiceRecord[] = [];
  currentVin = '';
  activeFilter: FilterTab = 'all';

  constructor(private fb: FormBuilder, private serviceService: ServiceService) {
    this.searchForm = this.fb.group({
      vin: ['', [Validators.required, Validators.pattern(/^[A-HJ-NPR-Z0-9]{17}$/i)]]
    });
  }

  get f() { return this.searchForm.controls; }

  get filteredRecords(): ServiceRecord[] {
    if (this.activeFilter === 'disputed') return this.pendingRecords.filter(r => r.disputed);
    if (this.activeFilter === 'pending') return this.pendingRecords.filter(r => !r.disputed);
    return this.pendingRecords;
  }

  get pendingCount(): number { return this.pendingRecords.filter(r => !r.disputed).length; }
  get disputedCount(): number { return this.pendingRecords.filter(r => r.disputed).length; }

  setFilter(tab: FilterTab): void { this.activeFilter = tab; }

  onSearch(): void {
    if (this.searchForm.invalid) {
      this.searchForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.error = '';
    this.pendingRecords = [];
    this.activeFilter = 'all';
    this.currentVin = this.searchForm.value.vin;

    this.serviceService.getPendingServices(this.currentVin).subscribe({
      next: (data) => {
        this.pendingRecords = data.pending_services;
        this.loading = false;
      },
      error: (err) => {
        this.error = err.error?.error || 'Failed to load pending services';
        this.loading = false;
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

  getDaysPending(timestamp: number): number {
    return Math.floor((Date.now() - timestamp * 1000) / 86_400_000);
  }

  ageBadgeClass(days: number): string {
    if (days < 7) return 'badge badge-verified';
    if (days < 30) return 'badge badge-pending';
    return 'badge badge-disputed';
  }

  ageLabel(days: number): string {
    if (days === 0) return 'Today';
    if (days === 1) return '1 day ago';
    return `${days} days ago`;
  }
}
