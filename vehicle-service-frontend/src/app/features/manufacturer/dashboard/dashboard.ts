import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Subscription } from 'rxjs';
import { AuthService } from '../../../core/services/auth';
import { BlockchainService } from '../../../core/services/blockchain.service';
import { VehicleService, ManufacturerStats } from '../../../core/services/vehicle';
import { User } from '../../../core/models/user.model';

@Component({
  selector: 'app-manufacturer-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.css']
})
export class ManufacturerDashboardComponent implements OnInit, OnDestroy {
  currentUser: User | null = null;
  isConnected: boolean | null = null;
  stats: ManufacturerStats | null = null;
  statsLoading = true;
  statsError = false;
  private subs = new Subscription();

  constructor(
    private authService: AuthService,
    private blockchain: BlockchainService,
    private vehicleService: VehicleService,
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
    this.vehicleService.getManufacturerStats().subscribe({
      next: s => { this.stats = s; this.statsLoading = false; this.cdr.detectChanges(); },
      error: () => { this.statsLoading = false; this.statsError = true; this.cdr.detectChanges(); }
    });
  }
}
