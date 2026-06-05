import { Component, OnInit, ChangeDetectorRef, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { VehicleService } from '../../../core/services/vehicle';
import QRCode from 'qrcode';

@Component({
  selector: 'app-fleet',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './fleet.html',
  styleUrls: ['./fleet.css'],
})
export class FleetComponent implements OnInit {
  @ViewChild('handoverQrCanvas') handoverQrCanvas?: ElementRef<HTMLCanvasElement>;

  vehicles: any[] = [];
  pagination: any = null;
  loading = true;
  error = '';
  page = 1;
  readonly limit = 20;

  qrVin: string | null = null;  // non-null = modal open

  reclaimRequests: any[] = [];
  reclaimRequestsLoading = false;
  reclaimActionId: number | null = null;  // which request is being approved/rejected

  constructor(private vehicleService: VehicleService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void { this.load(); this.loadReclaimRequests(); }

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

  showHandoverQr(vin: string): void {
    this.qrVin = vin;
    // Render QR on next tick after modal appears in DOM
    setTimeout(() => {
      const canvas = this.handoverQrCanvas?.nativeElement;
      if (canvas) {
        QRCode.toCanvas(canvas, vin, { width: 220, margin: 2 });
      }
    }, 50);
  }

  closeHandoverQr(): void { this.qrVin = null; }

  loadReclaimRequests(): void {
    this.reclaimRequestsLoading = true;
    this.vehicleService.getReclaimRequests().subscribe({
      next: r => { this.reclaimRequests = r.requests || []; this.reclaimRequestsLoading = false; this.cdr.detectChanges(); },
      error: () => { this.reclaimRequestsLoading = false; this.cdr.detectChanges(); },
    });
  }

  approveReclaim(id: number): void {
    this.reclaimActionId = id;
    this.vehicleService.approveReclaim(id).subscribe({
      next: () => { this.reclaimActionId = null; this.load(); this.loadReclaimRequests(); },
      error: (err) => { this.reclaimActionId = null; alert(err.error?.error || 'Approval failed'); this.cdr.detectChanges(); },
    });
  }

  rejectReclaim(id: number): void {
    this.reclaimActionId = id;
    this.vehicleService.rejectReclaim(id).subscribe({
      next: () => { this.reclaimActionId = null; this.loadReclaimRequests(); },
      error: (err) => { this.reclaimActionId = null; alert(err.error?.error || 'Rejection failed'); this.cdr.detectChanges(); },
    });
  }

  pendingReclaimRequests(): any[] {
    return this.reclaimRequests.filter(r => r.status === 'pending');
  }

  serviceDueLabel(days: number | null, count: number): string {
    if (days === null) return count === 0 ? 'No service yet' : '—';
    if (days === 0)   return 'Today';
    if (days === 1)   return '1 day ago';
    return `${days}d ago`;
  }
}
