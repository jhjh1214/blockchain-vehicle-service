import { Component, OnInit } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ServiceService } from '../../../core/services/service';
import { ServiceRecord } from '../../../core/models/service.model';
import { VehicleService } from '../../../core/services/vehicle';

@Component({
  selector: 'app-dealer-disputes',
  standalone: true,
  imports: [CommonModule, DatePipe, FormsModule],
  templateUrl: './disputes.html',
  styleUrl: './disputes.css'
})
export class DealerDisputesComponent implements OnInit {
  loading = true;
  error = '';
  rebuttalSuccess = '';
  escalateSuccess = '';
  escalateError = '';
  disputedRecords: ServiceRecord[] = [];

  rebuttalRecord: ServiceRecord | null = null;
  rebuttalText = '';
  rebuttalLoading = false;
  rebuttalError = '';
  escalatingRecord: ServiceRecord | null = null;

  threadOpen: { [key: string]: boolean } = {};
  threadMessages: { [key: string]: any[] } = {};
  threadLoading: { [key: string]: boolean } = {};
  threadInput: { [key: string]: string } = {};
  threadSending: { [key: string]: boolean } = {};
  threadError: { [key: string]: string } = {};

  recalls: any[] = [];
  recallsLoading = false;
  recallMarkLoading: { [key: number]: boolean } = {};

  constructor(private serviceService: ServiceService, private vehicleService: VehicleService) {}

  ngOnInit(): void {
    this.load();
    this.loadRecalls();
  }

  loadRecalls(): void {
    this.recallsLoading = true;
    this.vehicleService.getRecalls('active').subscribe({
      next: r => { this.recalls = r.recalls; this.recallsLoading = false; },
      error: () => { this.recallsLoading = false; }
    });
  }

  markRecallServicedForVin(recallId: number, vin: string): void {
    this.recallMarkLoading[recallId] = true;
    this.vehicleService.markRecallServiced(recallId, vin).subscribe({
      next: () => {
        this.recallMarkLoading[recallId] = false;
        this.loadRecalls();
      },
      error: () => { this.recallMarkLoading[recallId] = false; }
    });
  }

  load(): void {
    this.loading = true;
    this.error = '';
    this.serviceService.getCenterPending().subscribe({
      next: (data) => {
        this.disputedRecords = (data.pending_services || [])
          .filter((r: any) => r.status === 'disputed');
        this.loading = false;
      },
      error: (err) => {
        this.error = err.error?.error || 'Failed to load disputed records';
        this.loading = false;
      }
    });
  }

  threadKey(vin: string, recordIndex: number): string {
    return `${vin}-${recordIndex}`;
  }

  toggleThread(vin: string, recordIndex: number): void {
    const key = this.threadKey(vin, recordIndex);
    this.threadOpen[key] = !this.threadOpen[key];
    if (this.threadOpen[key] && !this.threadMessages[key]) {
      this.loadThread(vin, recordIndex);
    }
  }

  loadThread(vin: string, recordIndex: number): void {
    const key = this.threadKey(vin, recordIndex);
    this.threadLoading[key] = true;
    this.serviceService.getDisputeMessages(vin, recordIndex).subscribe({
      next: (res) => {
        this.threadMessages[key] = res.messages || [];
        this.threadLoading[key] = false;
      },
      error: () => { this.threadLoading[key] = false; }
    });
  }

  sendThreadMessage(vin: string, recordIndex: number): void {
    const key = this.threadKey(vin, recordIndex);
    const text = (this.threadInput[key] || '').trim();
    if (!text || this.threadSending[key]) return;
    this.threadSending[key] = true;
    this.threadError[key] = '';
    this.threadInput[key] = '';
    this.serviceService.postDisputeMessage(vin, recordIndex, text).subscribe({
      next: () => {
        this.threadSending[key] = false;
        this.loadThread(vin, recordIndex);
      },
      error: (e: any) => {
        this.threadSending[key] = false;
        this.threadInput[key] = text;
        this.threadError[key] = e.error?.error || 'Failed to send message. Please try again.';
      }
    });
  }

  senderLabel(msg: any): string {
    if (msg.sender_role === 'OWNER') return 'Owner';
    if (msg.sender_role === 'MANUFACTURER') return msg.sender_name || 'Manufacturer';
    return 'You';
  }

  openRebuttal(record: ServiceRecord): void {
    this.rebuttalRecord = record;
    this.rebuttalText = '';
    this.rebuttalSuccess = '';
    this.rebuttalError = '';
  }

  cancelRebuttal(): void {
    this.rebuttalRecord = null;
  }

  submitRebuttal(): void {
    if (!this.rebuttalRecord || !this.rebuttalText.trim()) return;
    this.rebuttalLoading = true;
    this.rebuttalError = '';
    this.serviceService.submitDisputeResponse(
      this.rebuttalRecord.vin,
      this.rebuttalRecord.metadata_hash,
      this.rebuttalText.trim()
    ).subscribe({
      next: () => {
        this.rebuttalSuccess = 'Rebuttal submitted. The manufacturer will review it before making a decision.';
        this.rebuttalRecord = null;
        this.rebuttalLoading = false;
        this.load();
      },
      error: (err: any) => {
        this.rebuttalError = err.error?.error || 'Failed to submit rebuttal';
        this.rebuttalLoading = false;
      }
    });
  }

  escalateDispute(record: ServiceRecord): void {
    this.escalatingRecord = record;
    this.escalateSuccess = '';
    this.escalateError = '';
    this.serviceService.escalateDispute(record.vin, record.metadata_hash).subscribe({
      next: () => {
        this.escalateSuccess = 'Dispute escalated to manufacturer for priority review.';
        this.escalatingRecord = null;
        this.load();
      },
      error: (err: any) => {
        this.escalateError = err.error?.error || 'Failed to escalate dispute';
        this.escalatingRecord = null;
      }
    });
  }

  formatDate(iso: string): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-MY', { year: 'numeric', month: 'short', day: 'numeric' });
  }
}
