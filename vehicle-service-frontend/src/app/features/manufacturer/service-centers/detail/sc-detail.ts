import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ScManagementService, ServiceCenter } from '../../../../core/services/sc-management.service';

@Component({
  selector: 'app-sc-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './sc-detail.html',
  styleUrls: ['./sc-detail.css'],
})
export class ScDetailComponent implements OnInit {
  sc: ServiceCenter | null = null;
  loading = true;
  error = '';

  actionLoading = false;
  actionMsg = '';
  actionError = '';

  fundAmount = 0.5;
  showFundPanel = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private scService: ScManagementService,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.scService.getServiceCenter(id).subscribe({
      next: sc => { this.sc = sc; this.loading = false; },
      error: () => { this.error = 'Service center not found'; this.loading = false; },
    });
  }

  activate(): void {
    if (!this.sc) return;
    this.actionLoading = true;
    this.actionMsg = '';
    this.actionError = '';
    this.scService.activate(this.sc.id).subscribe({
      next: r => {
        this.sc = r.sc;
        this.actionMsg = r.message;
        this.actionLoading = false;
      },
      error: e => {
        this.actionError = e.error?.error || 'Action failed';
        this.actionLoading = false;
      }
    });
  }

  suspend(): void {
    if (!this.sc) return;
    this.actionLoading = true;
    this.actionMsg = '';
    this.actionError = '';
    this.scService.suspend(this.sc.id).subscribe({
      next: r => {
        this.sc = r.sc;
        this.actionMsg = r.message;
        this.actionLoading = false;
      },
      error: e => {
        this.actionError = e.error?.error || 'Action failed';
        this.actionLoading = false;
      }
    });
  }

  fund(): void {
    if (!this.sc) return;
    this.actionLoading = true;
    this.actionMsg = '';
    this.actionError = '';
    this.scService.fund(this.sc.id, this.fundAmount).subscribe({
      next: r => {
        this.actionMsg = r.message;
        if (this.sc && r.new_balance !== undefined) {
          this.sc = { ...this.sc, eth_balance: r.new_balance };
        }
        this.showFundPanel = false;
        this.actionLoading = false;
      },
      error: e => {
        this.actionError = e.error?.error || 'Funding failed';
        this.actionLoading = false;
      }
    });
  }

  get statusClass(): string {
    const map: Record<string, string> = { active: 'sc-status-active', pending: 'sc-status-pending', suspended: 'sc-status-suspended' };
    return map[this.sc?.status ?? ''] ?? '';
  }

  get statusLabel(): string {
    const map: Record<string, string> = { active: 'Active', pending: 'Pending Approval', suspended: 'Suspended' };
    return map[this.sc?.status ?? ''] ?? '';
  }

  get shortAddress(): string {
    const a = this.sc?.blockchain_address ?? '';
    return a ? `${a.slice(0, 8)}…${a.slice(-6)}` : '';
  }

  goBack(): void {
    this.router.navigate(['/manufacturer/service-centers']);
  }
}
