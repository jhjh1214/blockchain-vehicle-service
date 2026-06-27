import { Component, OnInit } from '@angular/core';
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
export class WarrantyClaimsComponent implements OnInit {
  searchForm: FormGroup;
  denyForm: FormGroup;

  loading = false;
  actionLoading = false;
  error = '';
  actionError = '';
  actionSuccess = '';

  /** 'all' = every claim across vehicles this manufacturer registered; 'vin' = a specific VIN search. */
  viewMode: 'all' | 'vin' = 'all';
  currentVin = '';
  warrantyStatus: WarrantyStatus | null = null;
  claims: WarrantyClaim[] = [];

  denyingClaim: WarrantyClaim | null = null;

  constructor(private fb: FormBuilder, private warrantyService: WarrantyService) {
    this.searchForm = this.fb.group({
      vin: ['', [Validators.required, Validators.pattern(/^[A-HJ-NPR-Z0-9]{17}$/i)]]
    });
    this.denyForm = this.fb.group({
      reason: ['', Validators.required]
    });
  }

  ngOnInit(): void {
    this.loadAllClaims();
  }

  get f() { return this.searchForm.controls; }

  loadAllClaims(): void {
    this.viewMode = 'all';
    this.loading = true;
    this.error = '';
    this.claims = [];
    this.warrantyStatus = null;
    this.actionSuccess = '';
    this.actionError = '';
    this.currentVin = '';

    this.warrantyService.getMfrClaims().subscribe({
      next: (data) => {
        this.claims = data.claims || [];
        this.loading = false;
      },
      error: (err) => {
        this.error = err.error?.error || 'Failed to load warranty claims';
        this.loading = false;
      }
    });
  }

  onSearch(): void {
    if (this.searchForm.invalid) {
      this.searchForm.markAllAsTouched();
      return;
    }

    this.viewMode = 'vin';
    this.loading = true;
    this.error = '';
    this.claims = [];
    this.warrantyStatus = null;
    this.actionSuccess = '';
    this.actionError = '';
    const vin = this.searchForm.value.vin.toUpperCase();
    this.currentVin = vin;

    // Load warranty status and claims in parallel
    this.warrantyService.checkWarranty(vin).subscribe({
      next: (status) => {
        this.warrantyStatus = status;
        this.loading = false;
      },
      error: (err) => {
        this.error = err.error?.error || 'Failed to load warranty data';
        this.loading = false;
      }
    });

    this.warrantyService.getClaims(vin).subscribe({
      next: (data) => {
        this.claims = (data.claims || []).map((c, i) => ({ ...c, vin, claim_index: i }));
      },
      error: () => {
        // Non-fatal — still show warranty status
      }
    });
  }

  approveClaim(claim: WarrantyClaim): void {
    this.actionLoading = true;
    this.actionError = '';
    this.actionSuccess = '';

    this.warrantyService.approveClaim(claim.vin, claim.claim_index!).subscribe({
      next: () => {
        this.actionSuccess = `Claim for ${claim.vin} approved.`;
        claim.status = 'approved';
        this.actionLoading = false;
      },
      error: (err) => {
        this.actionError = err.error?.error || 'Failed to approve claim';
        this.actionLoading = false;
      }
    });
  }

  startDeny(claim: WarrantyClaim): void {
    this.denyingClaim = claim;
    this.denyForm.reset();
    this.actionError = '';
  }

  cancelDeny(): void {
    this.denyingClaim = null;
  }

  confirmDeny(): void {
    if (this.denyForm.invalid || !this.denyingClaim) {
      this.denyForm.markAllAsTouched();
      return;
    }

    const claim = this.denyingClaim;
    const reason = this.denyForm.value.reason;
    this.actionLoading = true;
    this.actionError = '';

    this.warrantyService.denyClaim(claim.vin, claim.claim_index!, reason).subscribe({
      next: () => {
        this.actionSuccess = `Claim for ${claim.vin} denied.`;
        claim.status = 'denied';
        this.denyingClaim = null;
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
      year: 'numeric', month: 'short', day: 'numeric'
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
