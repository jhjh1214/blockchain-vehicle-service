import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Subscription } from 'rxjs';
import { AuthService } from '../../../core/services/auth';
import { BlockchainService } from '../../../core/services/blockchain.service';
import { ScManagementService, SCStats } from '../../../core/services/sc-management.service';
import { User } from '../../../core/models/user.model';

@Component({
  selector: 'app-dealer-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.css']
})
export class DashboardComponent implements OnInit, OnDestroy {
  currentUser: User | null = null;
  isConnected: boolean | null = null;
  stats: SCStats | null = null;
  statsLoading = true;
  statsError = false;
  ethRequestLoading = false;
  ethRequestMsg = '';
  private subs = new Subscription();

  constructor(
    private authService: AuthService,
    private blockchain: BlockchainService,
    private scService: ScManagementService,
    private cdr: ChangeDetectorRef
  ) {
    this.currentUser = this.authService.currentUserValue;
  }

  ngOnInit(): void {
    this.subs.add(this.blockchain.connected$.subscribe(v => { this.isConnected = v; this.cdr.detectChanges(); }));
    this.loadStats();
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }

  private loadStats(): void {
    this.scService.getMyStats().subscribe({
      next: s => { this.stats = s; this.statsLoading = false; this.cdr.detectChanges(); },
      error: () => { this.statsLoading = false; this.statsError = true; this.cdr.detectChanges(); }
    });
  }

  requestEth(): void {
    if (this.ethRequestLoading) return;
    this.ethRequestLoading = true;
    this.ethRequestMsg = '';
    this.scService.createEthRequest().subscribe({
      next: r => { this.ethRequestMsg = r.message; this.ethRequestLoading = false; this.cdr.detectChanges(); },
      error: e => { this.ethRequestMsg = e.error?.error || 'Failed to send request'; this.ethRequestLoading = false; this.cdr.detectChanges(); }
    });
  }
}
