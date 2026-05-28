import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { VehicleService } from '../../../core/services/vehicle';

@Component({
  selector: 'app-fleet',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './fleet.html',
  styleUrls: ['./fleet.css'],
})
export class FleetComponent implements OnInit {
  vehicles: any[] = [];
  pagination: any = null;
  loading = true;
  error = '';
  page = 1;
  readonly limit = 20;

  constructor(private vehicleService: VehicleService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading = true;
    this.vehicleService.getFleet(this.page, this.limit).subscribe({
      next: r => {
        this.vehicles   = r.vehicles || [];
        this.pagination = r.pagination;
        this.loading    = false;
        this.cdr.detectChanges();
      },
      error: () => { this.error = 'Failed to load fleet'; this.loading = false; this.cdr.detectChanges(); }
    });
  }

  goTo(p: number): void {
    if (p < 1 || (this.pagination && p > this.pagination.pages)) return;
    this.page = p;
    this.load();
  }

  warrantyDate(ts: number): string {
    if (!ts) return '—';
    return new Date(ts * 1000).toLocaleDateString('en-MY', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  isExpired(ts: number): boolean {
    return ts > 0 && ts < Date.now() / 1000;
  }

  serviceDueClass(days: number | null): string {
    if (days === null) return 'service-due-none';
    if (days > 180) return 'service-due-ok';
    if (days > 90)  return 'service-due-warn';
    return 'service-due-alert';
  }

  serviceDueLabel(days: number | null, count: number): string {
    if (days === null) return count === 0 ? 'No service yet' : '—';
    if (days === 0)   return 'Today';
    if (days === 1)   return '1 day ago';
    return `${days}d ago`;
  }
}
