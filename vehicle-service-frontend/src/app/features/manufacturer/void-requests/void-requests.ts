import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ServiceService } from '../../../core/services/service';

type StatusFilter = 'open' | 'pending' | 'disputed' | 'resolved' | 'all';

@Component({
  selector: 'app-void-requests',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './void-requests.html',
  styleUrls: ['./void-requests.css'],
})
export class VoidRequestsComponent implements OnInit {
  requests: any[] = [];
  loading = true;
  error = '';
  filter: StatusFilter = 'open';
  voidNotes: { [id: number]: string } = {};
  actionId: number | null = null;

  constructor(private serviceService: ServiceService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.error = '';
    this.serviceService.getVoidRequestsManufacturer().subscribe({
      next: r => {
        this.requests = (r.requests || []).sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.error = 'Failed to load void requests'; this.loading = false; this.cdr.detectChanges(); }
    });
  }

  get filtered(): any[] {
    switch (this.filter) {
      case 'pending':  return this.requests.filter(r => r.status === 'pending');
      case 'disputed': return this.requests.filter(r => r.status === 'disputed');
      case 'resolved': return this.requests.filter(r => r.status === 'approved' || r.status === 'denied');
      case 'open':     return this.requests.filter(r => r.status === 'pending' || r.status === 'disputed');
      default:         return this.requests;
    }
  }

  count(filter: StatusFilter): number {
    switch (filter) {
      case 'pending':  return this.requests.filter(r => r.status === 'pending').length;
      case 'disputed': return this.requests.filter(r => r.status === 'disputed').length;
      case 'resolved': return this.requests.filter(r => r.status === 'approved' || r.status === 'denied').length;
      case 'open':     return this.requests.filter(r => r.status === 'pending' || r.status === 'disputed').length;
      default:         return this.requests.length;
    }
  }

  resolve(id: number, decision: 'approved' | 'denied'): void {
    this.actionId = id;
    this.serviceService.resolveVoidRequest(id, decision, this.voidNotes[id] || '').subscribe({
      next: () => { this.actionId = null; this.load(); },
      error: () => { this.actionId = null; this.cdr.detectChanges(); }
    });
  }

  badgeClass(status: string): string {
    const map: Record<string, string> = {
      pending: 'badge badge-pending',
      disputed: 'badge badge-disputed',
      approved: 'badge badge-denied',
      denied: 'badge badge-approved',
    };
    return map[status] || 'badge';
  }

  statusLabel(status: string): string {
    const map: Record<string, string> = {
      pending: 'Pending Review',
      disputed: 'Disputed by Owner',
      approved: 'Warranty Voided',
      denied: 'Denied — Warranty Valid',
    };
    return map[status] || status;
  }
}
