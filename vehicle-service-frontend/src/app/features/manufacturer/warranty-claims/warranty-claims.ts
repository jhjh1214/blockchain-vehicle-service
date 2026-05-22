import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { WarrantyService, WarrantyClaim, WarrantyStatus } from '../../../core/services/warranty';

@Component({
  selector: 'app-warranty-claims',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './warranty-claims.html',
  styleUrls: ['./warranty-claims.css']
})
export class WarrantyClaimsComponent {
  searchForm: FormGroup;
  denyForm: FormGroup;

  loading = false;
  actionLoading = false;
  error = '';
  actionError = '';
  actionSuccess = '';

  currentVin = '';
  warrantyStatus: WarrantyStatus | null = null;
  claims: WarrantyClaim[] = [];

  denyingIndex: number | null = null;

  constructor(private fb: FormBuilder, private warrantyService: WarrantyService) {
    this.searchForm = this.fb.group({
      vin: ['', [Validators.required, Validators.pattern(/^[A-HJ-NPR-Z0-9]{17}$/i)]]
    });
    this.denyForm = this.fb.group({
      reason: ['', Validators.required]
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
    this.claims = [];
    this.warrantyStatus = null;
    this.actionSuccess = '';
    this.actionError = '';
    this.currentVin = this.searchForm.value.vin;

    // Load warranty status and claims in parallel
    this.warrantyService.checkWarranty(this.currentVin).subscribe({
      next: (status) => {
        this.warrantyStatus = status;
        this.loading = false;
      },
      error: (err) => {
        this.error = err.error?.error || 'Failed to load warranty data';
        this.loading = false;
      }
    });

    this.warrantyService.getClaims(this.currentVin).subscribe({
      next: (data) => {
        this.claims = data.claims;
      },
      error: () => {
        // Non-fatal — still show warranty status
      }
    });
  }

  approveClaim(index: number): void {
    this.actionLoading = true;
    this.actionError = '';
    this.actionSuccess = '';

    this.warrantyService.approveClaim(this.currentVin, index).subscribe({
      next: () => {
        this.actionSuccess = `Claim #${index + 1} approved.`;
        this.claims[index] = { ...this.claims[index], status: 'approved' };
        this.actionLoading = false;
      },
      error: (err) => {
        this.actionError = err.error?.error || 'Failed to approve claim';
        this.actionLoading = false;
      }
    });
  }

  startDeny(index: number): void {
    this.denyingIndex = index;
    this.denyForm.reset();
    this.actionError = '';
  }

  cancelDeny(): void {
    this.denyingIndex = null;
  }

  confirmDeny(): void {
    if (this.denyForm.invalid || this.denyingIndex === null) {
      this.denyForm.markAllAsTouched();
      return;
    }

    const index = this.denyingIndex;
    const reason = this.denyForm.value.reason;
    this.actionLoading = true;
    this.actionError = '';

    this.warrantyService.denyClaim(this.currentVin, index, reason).subscribe({
      next: () => {
        this.actionSuccess = `Claim #${index + 1} denied.`;
        this.claims[index] = { ...this.claims[index], status: 'denied' };
        this.denyingIndex = null;
        this.actionLoading = false;
      },
      error: (err) => {
        this.actionError = err.error?.error || 'Failed to deny claim';
        this.actionLoading = false;
      }
    });
  }

  formatDate(timestamp: number): string {
    if (!timestamp) return '—';
    return new Date(timestamp * 1000).toLocaleDateString('en-MY', {
      year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  }

  statusBadge(status: string): string {
    const map: Record<string, string> = {
      pending: 'badge badge-pending',
      approved: 'badge badge-approved',
      denied: 'badge badge-denied'
    };
    return map[status] || 'badge';
  }
}
