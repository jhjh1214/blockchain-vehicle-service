import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
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
import { VehicleService, DashboardStats, ActivityItem } from '../../../core/services/vehicle';
import { ThemeService } from '../../../core/services/theme.service';
import { ScManagementService } from '../../../core/services/sc-management.service';
import { ServiceService } from '../../../core/services/service';
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
  imports: [CommonModule, FormsModule, RouterModule, BaseChartDirective],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.css']
})
export class ManufacturerDashboardComponent implements OnInit, OnDestroy {
  currentUser: User | null = null;
  isConnected: boolean | null = null;
  stats: DashboardStats | null = null;
  statsLoading = true;
  statsError = false;
  activityFeed: ActivityItem[] = [];
  activityLoading = true;
  exportLoading = false;
  showRecallModal = false;
  recallTitle = '';
  recallMessage = '';
  recallVinStart = '';
  recallVinEnd = '';
  recallSending = false;
  recallResult: { sent: number; recall_id?: number } | null = null;
  recallError = '';
  recalls: any[] = [];
  recallsLoading = false;
  ethRequestsCount = 0;
  ethRequests: any[] = [];
  ethRequestsLoading = false;
  voidRequests: any[] = [];
  private subs = new Subscription();

  pieChartData: ChartData<'pie'> = { labels: [], datasets: [{ data: [] }] };
  pieChartOptions: ChartOptions<'pie'> = this.buildPieOptions(false);

  warrantyChartData: ChartData<'doughnut'> = {
    labels: ['Active', 'Expired / No Warranty'],
    datasets: [{ data: [0, 0], backgroundColor: ['#1D9E75', '#E5E7EB'] }]
  };
  warrantyChartOptions: ChartOptions<'doughnut'> = this.buildDoughnutOptions(false);

  lineChartData: ChartData<'line'> = { labels: [], datasets: [] };
  lineChartOptions: ChartOptions<'line'> = this.buildLineOptions(false);

  barChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  barChartOptions: ChartOptions<'bar'> = this.buildBarOptions(false);

  constructor(
    private authService: AuthService,
    private blockchain: BlockchainService,
    private vehicleService: VehicleService,
    private themeService: ThemeService,
    private scService: ScManagementService,
    private serviceService: ServiceService,
    private cdr: ChangeDetectorRef
  ) {
    this.currentUser = this.authService.currentUserValue;
  }

  ngOnInit(): void {
    this.subs.add(this.blockchain.connected$.subscribe(v => {
      this.isConnected = v;
      this.cdr.detectChanges();
    }));
    this.subs.add(this.themeService.dark$.subscribe(isDark => {
      this.applyTheme(isDark);
      this.cdr.detectChanges();
    }));
    this.loadStats();
    this.loadActivityFeed();
    this.loadRecalls();
    this.loadEthRequests();
    this.loadVoidRequests();
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }

  private applyTheme(isDark: boolean): void {
    this.pieChartOptions      = this.buildPieOptions(isDark);
    this.warrantyChartOptions = this.buildDoughnutOptions(isDark);
    this.lineChartOptions     = this.buildLineOptions(isDark);
    this.barChartOptions      = this.buildBarOptions(isDark);
    if (this.stats) this.buildCharts(this.stats, isDark);
  }

  private scaleColors(isDark: boolean) {
    return {
      grid:   { color: isDark ? 'rgba(30,41,59,0.7)' : 'rgba(226,232,240,0.8)' },
      ticks:  { color: isDark ? '#94a3b8' : '#64748b' },
      border: { color: isDark ? '#1e293b' : '#e2e8f0' },
    };
  }

  private tooltipStyle(isDark: boolean) {
    return {
      backgroundColor: isDark ? '#1e293b' : '#ffffff',
      titleColor:      isDark ? '#f1f5f9' : '#0f172a',
      bodyColor:       isDark ? '#94a3b8' : '#374151',
      borderColor:     isDark ? '#334155' : '#e2e8f0',
      borderWidth:     1,
      padding:         10,
    };
  }

  private legendStyle(isDark: boolean) {
    return { color: isDark ? '#cbd5e1' : '#374151', font: { size: 12 as const } };
  }

  private buildPieOptions(isDark: boolean): ChartOptions<'pie'> {
    return {
      responsive: true,
      plugins: {
        legend:  { position: 'bottom', labels: this.legendStyle(isDark) },
        tooltip: this.tooltipStyle(isDark),
      },
    };
  }

  private buildDoughnutOptions(isDark: boolean): ChartOptions<'doughnut'> {
    return {
      responsive: true,
      cutout: '65%',
      plugins: {
        legend:  { position: 'bottom', labels: this.legendStyle(isDark) },
        tooltip: this.tooltipStyle(isDark),
      },
    };
  }

  private buildLineOptions(isDark: boolean): ChartOptions<'line'> {
    const sc = this.scaleColors(isDark);
    return {
      responsive: true,
      plugins: {
        legend:  { display: false },
        tooltip: this.tooltipStyle(isDark),
      },
      scales: {
        x: { grid: sc.grid, ticks: sc.ticks, border: sc.border },
        y: { beginAtZero: true, ticks: { ...sc.ticks, stepSize: 1 }, grid: sc.grid, border: sc.border },
      },
    };
  }

  private buildBarOptions(isDark: boolean): ChartOptions<'bar'> {
    const sc = this.scaleColors(isDark);
    return {
      responsive: true,
      plugins: {
        legend:  { display: false },
        tooltip: this.tooltipStyle(isDark),
      },
      scales: {
        x: { grid: { display: false }, ticks: sc.ticks, border: sc.border },
        y: { beginAtZero: true, ticks: { ...sc.ticks, stepSize: 1 }, grid: sc.grid, border: sc.border },
      },
    };
  }

  refresh(): void {
    this.statsLoading = true;
    this.activityLoading = true;
    this.statsError = false;
    this.loadStats();
    this.loadActivityFeed();
  }

  private loadStats(): void {
    this.vehicleService.getDashboardStats().subscribe({
      next: s => {
        this.stats = s;
        this.statsLoading = false;
        this.buildCharts(s, this.themeService.isDark);
        this.cdr.detectChanges();
      },
      error: () => {
        this.vehicleService.getManufacturerStats().subscribe({
          next: s  => { this.stats = s as DashboardStats; this.statsLoading = false; this.cdr.detectChanges(); },
          error: () => { this.statsLoading = false; this.statsError = true; this.cdr.detectChanges(); }
        });
      }
    });
  }

  private loadActivityFeed(): void {
    this.vehicleService.getActivityFeed().subscribe({
      next: res  => { this.activityFeed = res.feed || []; this.activityLoading = false; this.cdr.detectChanges(); },
      error: ()  => { this.activityLoading = false; this.cdr.detectChanges(); }
    });
  }

  activityIcon(type: string): string {
    if (type === 'registration')   return 'M8.25 18.75a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 0 1-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 0 0-3.213-9.193 2.056 2.056 0 0 0-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 0 0-10.026 0 1.106 1.106 0 0 0-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12';
    if (type === 'warranty_claim') return 'M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z';
    return 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z';
  }

  activityColor(type: string): string {
    if (type === 'registration')   return '#3B82F6';
    if (type === 'warranty_claim') return '#10B981';
    return '#F59E0B';
  }

  activityLabel(type: string): string {
    if (type === 'registration')   return 'Vehicle Registered';
    if (type === 'warranty_claim') return 'Warranty Claim';
    return 'Service Disputed';
  }

  formatActivityTime(ts: string | null): string {
    if (!ts) return '—';
    try {
      const d    = new Date(ts);
      const now  = new Date();
      const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
      if (diff < 60)    return 'just now';
      if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
      if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
      return `${Math.floor(diff / 86400)}d ago`;
    } catch { return '—'; }
  }

  openRecallModal(): void {
    this.showRecallModal = true;
    this.recallTitle = '';
    this.recallMessage = '';
    this.recallVinStart = '';
    this.recallVinEnd = '';
    this.recallResult = null;
    this.recallError = '';
  }

  closeRecallModal(): void {
    this.showRecallModal = false;
  }

  sendRecall(): void {
    if (!this.recallTitle.trim() || !this.recallMessage.trim()) return;
    this.recallSending = true;
    this.recallResult = null;
    this.recallError = '';
    const vinStart = this.recallVinStart.trim().toUpperCase() || undefined;
    const vinEnd = this.recallVinEnd.trim().toUpperCase() || undefined;
    this.vehicleService.sendRecall(this.recallTitle.trim(), this.recallMessage.trim(), vinStart, vinEnd).subscribe({
      next: res => {
        this.recallSending = false;
        this.recallResult = res;
        this.loadRecalls();
        this.cdr.detectChanges();
      },
      error: () => {
        this.recallSending = false;
        this.recallError = 'Failed to send recall notice. Please try again.';
        this.cdr.detectChanges();
      }
    });
  }

  loadRecalls(): void {
    this.recallsLoading = true;
    this.vehicleService.getRecalls('active').subscribe({
      next: r => { this.recalls = r.recalls; this.recallsLoading = false; this.cdr.detectChanges(); },
      error: () => { this.recallsLoading = false; this.cdr.detectChanges(); }
    });
  }

  closeRecall(id: number): void {
    this.vehicleService.closeRecall(id).subscribe({
      next: () => { this.loadRecalls(); this.cdr.detectChanges(); },
      error: () => {}
    });
  }

  loadEthRequests(): void {
    this.ethRequestsLoading = true;
    this.scService.getEthRequests().subscribe({
      next: r => {
        this.ethRequests = r.requests;
        this.ethRequestsCount = r.count;
        this.ethRequestsLoading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.ethRequestsLoading = false; this.cdr.detectChanges(); }
    });
  }

  dismissEthRequest(id: number): void {
    this.scService.dismissEthRequest(id).subscribe({
      next: () => { this.loadEthRequests(); this.cdr.detectChanges(); },
      error: () => {}
    });
  }

  loadVoidRequests(): void {
    this.serviceService.getVoidRequestsManufacturer().subscribe({
      next: r => { this.voidRequests = (r.requests || []).filter(x => x.status === 'pending' || x.status === 'disputed'); this.cdr.detectChanges(); },
      error: () => {}
    });
  }

  exportAuditReport(): void {
    this.exportLoading = true;
    this.vehicleService.getFleetExport().subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const _nd = new Date();
        const _ds = `${_nd.getFullYear()}-${String(_nd.getMonth()+1).padStart(2,'0')}-${String(_nd.getDate()).padStart(2,'0')}`;
        a.download = `VehicleChain_Fleet_Audit_${_ds}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        this.exportLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.exportLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  private buildCharts(s: DashboardStats, isDark: boolean): void {
    const expiredColor = isDark ? '#334155' : '#E5E7EB';

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

    const active  = s.active_warranties ?? 0;
    const expired = Math.max(0, (s.total_vehicles ?? 0) - active);
    this.warrantyChartData = {
      labels: ['Active', 'Expired / No Warranty'],
      datasets: [{ data: [active, expired], backgroundColor: ['#1D9E75', expiredColor] }]
    };

    if (s.warranty_claim_trend?.length) {
      this.lineChartData = {
        labels: s.warranty_claim_trend.map(p => p.month),
        datasets: [{
          data:               s.warranty_claim_trend.map(p => p.count),
          borderColor:        '#3B82F6',
          backgroundColor:    isDark ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.08)',
          fill:               true,
          tension:            0.35,
          pointRadius:        4,
          pointBackgroundColor: '#3B82F6',
        }]
      };
    }

    if (s.top_service_centers?.length) {
      this.barChartData = {
        labels: s.top_service_centers.map(sc => sc.label),
        datasets: [{
          data:            s.top_service_centers.map(sc => sc.submissions),
          backgroundColor: s.top_service_centers.map(sc => sc.flagged ? '#EF4444' : '#1D9E75'),
          borderRadius:    4,
        }]
      };
    }
  }
}
