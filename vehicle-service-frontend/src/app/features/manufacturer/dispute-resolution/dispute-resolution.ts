import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Subscription, interval } from 'rxjs';
import { ServiceService } from '../../../core/services/service';

const THREAD_POLL_MS = 5_000;

interface DisputedRecord {
  record_index: number;
  vin: string;
  metadata_hash: string;
  timestamp: number;
  disputed: boolean;
  escalated?: boolean;
  escalated_at?: string;
  dispute_reason?: string;
  service_type?: string;
  service_date?: string;
  mileage?: number;
  technician_name?: string;
  parts_replaced?: string;
  service_notes?: string;
  rebuttal_notes?: string;
  rebuttal_submitted_at?: string;
}

@Component({
  selector: 'app-dispute-resolution',
  standalone: true,
  imports: [CommonModule, DatePipe, FormsModule, ReactiveFormsModule],
  templateUrl: './dispute-resolution.html',
  styleUrl: './dispute-resolution.css'
})
export class DisputeResolutionComponent implements OnInit, OnDestroy {
  searchForm: FormGroup;
  resolveForm: FormGroup;

  loading = false;
  actionLoading = false;
  error = '';
  actionSuccess = '';
  actionError = '';

  /** 'all' = aggregate view across every VIN; 'vin' = a specific VIN search result. */
  viewMode: 'all' | 'vin' = 'all';
  currentVin = '';
  disputedRecords: DisputedRecord[] = [];
  resolvingIndex: number | null = null;
  resolvingDecision: 'approve' | 'reject' | 'modify' | null = null;

  threadOpen: { [key: string]: boolean } = {};
  threadMessages: { [key: string]: any[] } = {};
  threadLoading: { [key: string]: boolean } = {};
  threadInput: { [key: string]: string } = {};
  threadSending: { [key: string]: boolean } = {};
  private threadPollSub?: Subscription;

  constructor(private fb: FormBuilder, private serviceService: ServiceService) {
    this.searchForm = this.fb.group({
      vin: ['', [Validators.required, Validators.pattern(/^[A-HJ-NPR-Z0-9]{17}$/i)]]
    });
    this.resolveForm = this.fb.group({
      resolution_notes: ['', Validators.required]
    });
  }

  ngOnInit(): void {
    this.loadAllDisputes();
    this.threadPollSub = interval(THREAD_POLL_MS).subscribe(() => this.pollOpenThreads());
  }

  ngOnDestroy(): void {
    this.threadPollSub?.unsubscribe();
  }

  private pollOpenThreads(): void {
    for (const key of Object.keys(this.threadOpen)) {
      if (!this.threadOpen[key]) continue;
      const [vin, recordIndexStr] = key.split('-');
      this.loadThread(vin, Number(recordIndexStr), true);
    }
  }

  loadAllDisputes(): void {
    this.viewMode = 'all';
    this.loading = true;
    this.error = '';
    this.actionSuccess = '';
    this.actionError = '';
    this.resolvingIndex = null;
    this.currentVin = '';
    this.serviceService.getMfrDisputedServices().subscribe({
      next: (res) => {
        this.disputedRecords = res.disputed_services || [];
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

  loadThread(vin: string, recordIndex: number, silent = false): void {
    const key = this.threadKey(vin, recordIndex);
    if (!silent) this.threadLoading[key] = true;
    this.serviceService.getDisputeMessages(vin, recordIndex).subscribe({
      next: (res) => {
        this.threadMessages[key] = res.messages || [];
        if (!silent) this.threadLoading[key] = false;
      },
      error: () => { if (!silent) this.threadLoading[key] = false; }
    });
  }

  sendThreadMessage(vin: string, recordIndex: number): void {
    const key = this.threadKey(vin, recordIndex);
    const text = (this.threadInput[key] || '').trim();
    if (!text || this.threadSending[key]) return;
    this.threadSending[key] = true;
    this.threadInput[key] = '';
    this.serviceService.postDisputeMessage(vin, recordIndex, text).subscribe({
      next: () => {
        this.threadSending[key] = false;
        this.loadThread(vin, recordIndex);
      },
      error: () => {
        this.threadSending[key] = false;
        this.threadInput[key] = text;
      }
    });
  }

  onThreadEnter(event: Event, vin: string, recordIndex: number): void {
    const ke = event as KeyboardEvent;
    if (!ke.shiftKey) {
      event.preventDefault();
      this.sendThreadMessage(vin, recordIndex);
    }
  }

  senderLabel(msg: any): string {
    if (msg.sender_role === 'OWNER') return 'Owner';
    if (msg.sender_role === 'MANUFACTURER') return msg.sender_name || 'Manufacturer';
    return msg.sender_name || 'Service Centre';
  }

  get f() { return this.searchForm.controls; }

  onSearch(): void {
    if (this.searchForm.invalid) {
      this.searchForm.markAllAsTouched();
      return;
    }
    const vin = this.searchForm.value.vin.toUpperCase();
    this.viewMode = 'vin';
    this.loading = true;
    this.error = '';
    this.actionSuccess = '';
    this.actionError = '';
    this.disputedRecords = [];
    this.resolvingIndex = null;
    this.currentVin = vin;

    this.serviceService.getPendingServices(vin).subscribe({
      next: (res) => {
        this.disputedRecords = this.flattenAndFilterDisputed(res.pending_services, vin);
        this.loading = false;
      },
      error: (err) => {
        this.error = err.error?.error || 'Failed to load pending services';
        this.loading = false;
      }
    });
  }

  /** /service/pending/:vin nests metadata and uses the on-chain VIN hash, not the plain
   * VIN, in its `vin` field — flatten to the same shape the aggregate endpoint returns. */
  private flattenAndFilterDisputed(records: any[], vin: string): DisputedRecord[] {
    return (records || [])
      .map((r: any, i: number) => ({
        ...r,
        vin,
        record_index: i,
        service_type: r.metadata?.service_type,
        service_date: r.metadata?.service_date,
        mileage: r.metadata?.mileage,
        technician_name: r.metadata?.technician_name,
        parts_replaced: r.metadata?.parts_replaced,
        service_notes: r.metadata?.service_notes,
        rebuttal_notes: r.metadata?.rebuttal_notes,
        rebuttal_submitted_at: r.metadata?.rebuttal_submitted_at,
      }))
      .filter((r: any) => r.disputed);
  }

  startResolve(index: number, decision: 'approve' | 'reject' | 'modify'): void {
    this.resolvingIndex = index;
    this.resolvingDecision = decision;
    this.resolveForm.reset();
    this.actionError = '';
  }

  cancelResolve(): void {
    this.resolvingIndex = null;
    this.resolvingDecision = null;
  }

  confirmResolve(): void {
    if (this.resolveForm.invalid) {
      this.resolveForm.markAllAsTouched();
      return;
    }
    if (this.resolvingIndex === null || !this.resolvingDecision) return;

    const record = this.disputedRecords[this.resolvingIndex];
    const decision = this.resolvingDecision === 'approve' ? 1 : this.resolvingDecision === 'reject' ? 2 : 3;
    const notes = this.resolveForm.value.resolution_notes;

    this.actionLoading = true;
    this.actionError = '';
    this.actionSuccess = '';

    this.serviceService.resolveDispute(record.vin, record.metadata_hash, decision, notes).subscribe({
      next: () => {
        const label = this.resolvingDecision === 'approve' ? 'approved' : this.resolvingDecision === 'reject' ? 'rejected' : 'flagged for modification';
        this.actionSuccess = `Dispute ${label} successfully for ${record.service_type || 'record'}.`;
        this.resolvingIndex = null;
        this.resolvingDecision = null;
        this.actionLoading = false;
        // Re-fetch from chain: swap-and-pop removal shifts indices so local state is stale
        this.refreshDisputed();
      },
      error: (err) => {
        this.actionError = err.error?.error || 'Failed to resolve dispute';
        this.actionLoading = false;
      }
    });
  }

  private refreshDisputed(): void {
    if (this.viewMode === 'all') {
      this.loadAllDisputes();
      return;
    }
    const vin = this.currentVin;
    this.serviceService.getPendingServices(vin).subscribe({
      next: (res) => {
        this.disputedRecords = this.flattenAndFilterDisputed(res.pending_services, vin);
      },
      error: () => {}
    });
  }

  formatDate(ts: number): string {
    if (!ts) return '—';
    return new Date(ts * 1000).toLocaleDateString('en-MY', {
      day: '2-digit', month: 'short', year: 'numeric'
    });
  }

  formatDateTime(val: string): string {
    if (!val) return '—';
    return new Date(val).toLocaleDateString('en-MY', {
      day: '2-digit', month: 'short', year: 'numeric'
    });
  }
}
