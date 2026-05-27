import { Component } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ServiceService } from '../../../core/services/service';

interface DisputedRecord {
  record_index: number;
  vin: string;
  metadata_hash: string;
  timestamp: number;
  disputed: boolean;
  dispute_reason?: string;
  metadata?: {
    service_type: string;
    service_date: string;
    mileage: number;
    technician_name: string;
    parts_replaced: string;
    service_notes: string;
    rebuttal_notes?: string;
    rebuttal_submitted_at?: string;
  };
}

@Component({
  selector: 'app-dispute-resolution',
  standalone: true,
  imports: [CommonModule, DatePipe, ReactiveFormsModule],
  templateUrl: './dispute-resolution.html',
  styleUrl: './dispute-resolution.css'
})
export class DisputeResolutionComponent {
  searchForm: FormGroup;
  resolveForm: FormGroup;

  loading = false;
  actionLoading = false;
  error = '';
  actionSuccess = '';
  actionError = '';

  currentVin = '';
  disputedRecords: DisputedRecord[] = [];
  resolvingIndex: number | null = null;
  resolvingDecision: 'approve' | 'reject' | 'modify' | null = null;

  constructor(private fb: FormBuilder, private serviceService: ServiceService) {
    this.searchForm = this.fb.group({
      vin: ['', [Validators.required, Validators.pattern(/^[A-HJ-NPR-Z0-9]{17}$/i)]]
    });
    this.resolveForm = this.fb.group({
      resolution_notes: ['', Validators.required]
    });
  }

  get f() { return this.searchForm.controls; }

  onSearch(): void {
    if (this.searchForm.invalid) {
      this.searchForm.markAllAsTouched();
      return;
    }
    const vin = this.searchForm.value.vin.toUpperCase();
    this.loading = true;
    this.error = '';
    this.actionSuccess = '';
    this.actionError = '';
    this.disputedRecords = [];
    this.resolvingIndex = null;
    this.currentVin = vin;

    this.serviceService.getPendingServices(vin).subscribe({
      next: (res) => {
        this.disputedRecords = (res.pending_services || [])
          .map((r: any, i: number) => ({ ...r, record_index: i }))
          .filter((r: any) => r.disputed);
        this.loading = false;
      },
      error: (err) => {
        this.error = err.error?.error || 'Failed to load pending services';
        this.loading = false;
      }
    });
  }

  startResolve(index: number, decision: 'approve' | 'reject' | 'modify'): void {
    this.resolvingIndex = index;
    this.resolvingDecision = decision;
    this.resolveForm.reset();
    this.actionError = '';
  }

  cancelResolve(): void {
    this.resolvingIndex = null;
    this.resolvingDecision = null;
  }

  confirmResolve(): void {
    if (this.resolveForm.invalid) {
      this.resolveForm.markAllAsTouched();
      return;
    }
    if (this.resolvingIndex === null || !this.resolvingDecision) return;

    const record = this.disputedRecords[this.resolvingIndex];
    const decision = this.resolvingDecision === 'approve' ? 1 : this.resolvingDecision === 'reject' ? 2 : 3;
    const notes = this.resolveForm.value.resolution_notes;

    this.actionLoading = true;
    this.actionError = '';
    this.actionSuccess = '';

    this.serviceService.resolveDispute(record.vin, record.record_index, decision, notes).subscribe({
      next: () => {
        const label = this.resolvingDecision === 'approve' ? 'approved' : this.resolvingDecision === 'reject' ? 'rejected' : 'flagged for modification';
        this.actionSuccess = `Dispute ${label} successfully for ${record.metadata?.service_type || 'record'}.`;
        this.resolvingIndex = null;
        this.resolvingDecision = null;
        this.actionLoading = false;
        // Re-fetch from chain: swap-and-pop removal shifts indices so local state is stale
        this.refreshDisputed();
      },
      error: (err) => {
        this.actionError = err.error?.error || 'Failed to resolve dispute';
        this.actionLoading = false;
      }
    });
  }

  private refreshDisputed(): void {
    this.serviceService.getPendingServices(this.currentVin).subscribe({
      next: (res) => {
        this.disputedRecords = (res.pending_services || [])
          .map((r: any, i: number) => ({ ...r, record_index: i }))
          .filter((r: any) => r.disputed);
      },
      error: () => {}
    });
  }

  formatDate(ts: number): string {
    if (!ts) return '—';
    return new Date(ts * 1000).toLocaleDateString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric'
    });
  }

  formatDateTime(val: string): string {
    if (!val) return '—';
    return new Date(val).toLocaleDateString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric'
    });
  }
}
