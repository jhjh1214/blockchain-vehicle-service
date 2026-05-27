import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Subscription } from 'rxjs';
import { BaseChartDirective } from 'ng2-charts';
import {
  Chart, ChartData, ChartOptions,
  CategoryScale, LinearScale, BarElement, BarController,
  LineElement, LineController, PointElement,
  ArcElement, PieController, DoughnutController,
  Tooltip, Legend, Filler
} from 'chart.js';
import { AuthService } from '../../../core/services/auth';
import { BlockchainService } from '../../../core/services/blockchain.service';
import { VehicleService, DashboardStats } from '../../../core/services/vehicle';
import { User } from '../../../core/models/user.model';

Chart.register(
  CategoryScale, LinearScale,
  BarElement, BarController,
  LineElement, LineController, PointElement, Filler,
  ArcElement, PieController, DoughnutController,
  Tooltip, Legend
);

@Component({
  selector: 'app-manufacturer-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, BaseChartDirective],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.css']
})
export class ManufacturerDashboardComponent implements OnInit, OnDestroy {
  currentUser: User | null = null;
  isConnected: boolean | null = null;
  stats: DashboardStats | null = null;
  statsLoading = true;
  statsError = false;
  private subs = new Subscription();

  pieChartData: ChartData<'pie'> = { labels: [], datasets: [{ data: [] }] };
  pieChartOptions: ChartOptions<'pie'> = {
    responsive: true,
    plugins: { legend: { position: 'bottom' } }
  };

  warrantyChartData: ChartData<'doughnut'> = {
    labels: ['Active', 'Expired'],
    datasets: [{ data: [0, 0], backgroundColor: ['#1D9E75', '#E5E7EB'] }]
  };
  warrantyChartOptions: ChartOptions<'doughnut'> = {
    responsive: true,
    cutout: '65%',
    plugins: { legend: { position: 'bottom' } }
  };

  lineChartData: ChartData<'line'> = { labels: [], datasets: [] };
  lineChartOptions: ChartOptions<'line'> = {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
  };

  barChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  barChartOptions: ChartOptions<'bar'> = {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
  };

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
    this.vehicleService.getDashboardStats().subscribe({
      next: s => {
        this.stats = s;
        this.statsLoading = false;
        this.buildCharts(s);
        this.cdr.detectChanges();
      },
      error: () => {
        // Fall back to basic stats if extended endpoint unavailable
        this.vehicleService.getManufacturerStats().subscribe({
          next: s => { this.stats = s as DashboardStats; this.statsLoading = false; this.cdr.detectChanges(); },
          error: () => { this.statsLoading = false; this.statsError = true; this.cdr.detectChanges(); }
        });
      }
    });
  }

  private buildCharts(s: DashboardStats): void {
    // Pie: service type distribution
    if (s.service_type_distribution) {
      const entries = Object.entries(s.service_type_distribution);
      this.pieChartData = {
        labels: entries.map(([k]) => k),
        datasets: [{
          data: entries.map(([, v]) => v),
          backgroundColor: [
            '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
            '#8B5CF6', '#06B6D4', '#F97316', '#84CC16', '#EC4899', '#6B7280'
          ]
        }]
      };
    }

    // Doughnut: warranty coverage
    const active  = s.active_warranties  ?? 0;
    const expired = (s.total_vehicles ?? 0) - active;
    this.warrantyChartData = {
      labels: ['Active', 'Expired / No Warranty'],
      datasets: [{ data: [active, Math.max(0, expired)], backgroundColor: ['#1D9E75', '#E5E7EB'] }]
    };

    // Line: warranty claim trend (last 6 months)
    if (s.warranty_claim_trend?.length) {
      this.lineChartData = {
        labels: s.warranty_claim_trend.map(p => p.month),
        datasets: [{
          data: s.warranty_claim_trend.map(p => p.count),
          borderColor: '#3B82F6',
          backgroundColor: 'rgba(59,130,246,0.1)',
          fill: true,
          tension: 0.35,
          pointRadius: 4,
          pointBackgroundColor: '#3B82F6',
        }]
      };
    }

    // Bar: top service centres by submissions
    if (s.top_service_centers?.length) {
      this.barChartData = {
        labels: s.top_service_centers.map(sc => sc.label),
        datasets: [{
          data: s.top_service_centers.map(sc => sc.submissions),
          backgroundColor: s.top_service_centers.map(sc =>
            sc.flagged ? '#EF4444' : '#1D9E75'
          ),
          borderRadius: 4,
        }]
      };
    }
  }
}
