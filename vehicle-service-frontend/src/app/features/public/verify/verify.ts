import { Component, OnInit, AfterViewChecked, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { Title, Meta } from '@angular/platform-browser';
import { ThemeService } from '../../../core/services/theme.service';
import { BaseChartDirective } from 'ng2-charts';
import {
  Chart, ChartData, ChartOptions,
  CategoryScale, LinearScale, LineElement, LineController,
  PointElement, Tooltip, Filler
} from 'chart.js';
import { VehicleService } from '../../../core/services/vehicle';
import { environment } from '../../../../environments/environment';
import QRCode from 'qrcode';

Chart.register(CategoryScale, LinearScale, LineElement, LineController, PointElement, Tooltip, Filler);

@Component({
  selector: 'app-verify',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, BaseChartDirective],
  templateUrl: './verify.html',
  styleUrls: ['./verify.css'],
})
export class VerifyComponent implements OnInit, AfterViewChecked {
  @ViewChild('qrCanvas') qrCanvas!: ElementRef<HTMLCanvasElement>;

  vin = '';
  result: any = null;
  loading = false;
  error = '';
  private qrRendered = false;

  lineChartData: ChartData<'line'> = { labels: [], datasets: [] };
  lineChartOptions: ChartOptions<'line'> = {
    responsive: true,
    plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
    scales: {
      x: { grid: { color: 'rgba(226,232,240,0.8)' }, ticks: { color: '#64748b' } },
      y: { beginAtZero: false, ticks: { color: '#64748b' }, grid: { color: 'rgba(226,232,240,0.8)' } },
    },
  };

  isDark = false;

  constructor(
    private vehicleService: VehicleService,
    private route: ActivatedRoute,
    private titleService: Title,
    private metaService: Meta,
    public theme: ThemeService,
  ) {
    this.theme.dark$.subscribe(v => this.isDark = v);
  }

  toggleTheme(): void { this.theme.toggle(); }

  private setMeta(vin?: string): void {
    if (vin) {
      this.titleService.setTitle(`${vin} — Vehicle History | VehicleChain`);
      this.metaService.updateTag({ name: 'description', content: `Blockchain-verified service history, warranty status, and recall records for vehicle ${vin}.` });
    } else {
      this.titleService.setTitle('Verify Vehicle History — VehicleChain');
      this.metaService.updateTag({ name: 'description', content: 'Free blockchain-verified vehicle history check. See service records, warranty status, and recall history for any registered vehicle.' });
    }
  }

  ngOnInit(): void {
    this.setMeta();
    const paramVin = this.route.snapshot.paramMap.get('vin');
    if (paramVin) {
      this.vin = paramVin.toUpperCase();
      this.lookup();
    }
  }

  ngAfterViewChecked(): void {
    if (this.result && !this.qrRendered && this.qrCanvas?.nativeElement) {
      this.renderQR();
      this.qrRendered = true;
    }
  }

  lookup(): void {
    const v = this.vin.trim().toUpperCase();
    if (!v || v.length !== 17) { this.error = 'Please enter a valid 17-character VIN'; return; }
    this.loading = true;
    this.error = '';
    this.result = null;
    this.qrRendered = false;
    this.vehicleService.getPublicVehicle(v).subscribe({
      next: r => {
        this.result = r;
        this.loading = false;
        this.setMeta(v);
        this.buildMileageChart(r.service_records || []);
      },
      error: e => {
        this.error = e.error?.error || 'Vehicle not found';
        this.loading = false;
      }
    });
  }

  private buildMileageChart(records: any[]): void {
    const pts = records
      .filter(r => r.metadata?.mileage && r.metadata?.service_date)
      .map(r => ({ date: r.metadata.service_date.slice(0, 10), mileage: r.metadata.mileage }))
      .sort((a, b) => a.date.localeCompare(b.date));

    if (pts.length < 2) { this.lineChartData = { labels: [], datasets: [] }; return; }

    this.lineChartData = {
      labels: pts.map(p => p.date),
      datasets: [{
        data:              pts.map(p => p.mileage),
        borderColor:       '#3B82F6',
        backgroundColor:   'rgba(59,130,246,0.08)',
        fill:              true,
        tension:           0.35,
        pointRadius:       4,
        pointBackgroundColor: '#3B82F6',
      }]
    };
  }

  private renderQR(): void {
    const url = `${window.location.origin}/verify/${this.result.vin}`;
    QRCode.toCanvas(this.qrCanvas.nativeElement, url, { width: 160, margin: 2 }, () => {});
  }

  get serviceRecords(): any[] {
    return this.result?.service_records || [];
  }

  get hasMileageChart(): boolean {
    return (this.lineChartData.labels?.length ?? 0) >= 2;
  }

  warrantyDate(ts: number): string {
    if (!ts) return '—';
    return new Date(ts * 1000).toLocaleDateString('en-MY', { year: 'numeric', month: 'long', day: 'numeric' });
  }

  formatDate(val: string): string {
    if (!val) return '—';
    try { return new Date(val).toLocaleDateString('en-MY', { year: 'numeric', month: 'short', day: 'numeric' }); }
    catch { return val.slice(0, 10); }
  }

  exportPdfUrl(): string {
    return `${environment.apiUrl}/vehicle/export/${this.result?.vin}`;
  }
}
