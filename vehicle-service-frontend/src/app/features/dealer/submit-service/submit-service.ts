import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { Subscription } from 'rxjs';
import { debounceTime } from 'rxjs/operators';
import { ServiceService } from '../../../core/services/service';

@Component({
  selector: 'app-submit-service',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './submit-service.html',
  styleUrls: ['./submit-service.css']
})
export class SubmitServiceComponent implements OnInit, OnDestroy {
  serviceForm: FormGroup;
  loading = false;
  error = '';
  success = '';
  showAdvanced = false;
  liveHash = '';
  private subs = new Subscription();

  serviceTypes = [
    'Oil Change',
    'Brake Service',
    'Tire Rotation',
    'Engine Repair',
    'Transmission Service',
    'Battery Replacement',
    'Air Filter Replacement',
    'Coolant Flush',
    'General Inspection',
    'Other'
  ];

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private serviceService: ServiceService
  ) {
    this.serviceForm = this.fb.group({
      vin: ['', [Validators.required, Validators.pattern(/^[A-HJ-NPR-Z0-9]{17}$/i)]],
      service_type: ['', Validators.required],
      service_date: ['', Validators.required],
      mileage: ['', [Validators.required, Validators.min(0)]],
      technician_name: [''],
      parts_replaced: [''],
      service_notes: [''],
      ecu_modules: ['']
    });
  }

  ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      if (params['vin']) {
        this.serviceForm.patchValue({ vin: params['vin'] });
      }
    });
    const today = new Date().toISOString().split('T')[0];
    this.serviceForm.patchValue({ service_date: today });

    this.subs.add(
      this.serviceForm.valueChanges.pipe(debounceTime(300)).subscribe(() => {
        this.updateLiveHash();
      })
    );
    this.updateLiveHash();
  }

  ngOnDestroy(): void { this.subs.unsubscribe(); }

  get f() { return this.serviceForm.controls; }

  toggleAdvanced(): void { this.showAdvanced = !this.showAdvanced; }

  private async updateLiveHash(): Promise<void> {
    const v = this.serviceForm.value;
    if (!v.service_type && !v.mileage) { this.liveHash = ''; return; }
    const metadata = {
      ecu_modules: v.ecu_modules ? v.ecu_modules.split(',').map((m: string) => m.trim()).filter(Boolean) : [],
      mileage: v.mileage ? parseInt(v.mileage, 10) : 0,
      parts_replaced: v.parts_replaced || '',
      photos: [],
      service_date: v.service_date ? new Date(v.service_date).toISOString() : '',
      service_notes: v.service_notes || '',
      service_type: v.service_type || '',
      technician_name: v.technician_name || '',
    };
    // Serialize as sorted array of [key, value] pairs — matches Python's json.dumps(sorted(metadata.items()))
    const sorted: [string, unknown][] = Object.entries(metadata).sort(([a], [b]) => a.localeCompare(b));
    const dataStr = JSON.stringify(sorted);
    try {
      const encoder = new TextEncoder();
      const hashBuffer = await crypto.subtle.digest('SHA-256', encoder.encode(dataStr));
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      this.liveHash = '0x' + hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    } catch {
      this.liveHash = '';
    }
  }

  onSubmit(): void {
    if (this.serviceForm.invalid) {
      this.serviceForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.error = '';
    this.success = '';

    const raw = { ...this.serviceForm.value };
    raw.service_date = new Date(raw.service_date).toISOString();
    raw.mileage = parseInt(raw.mileage, 10);
    raw.ecu_modules = raw.ecu_modules
      ? raw.ecu_modules.split(',').map((m: string) => m.trim()).filter(Boolean)
      : [];

    this.serviceService.submitService(raw).subscribe({
      next: (response) => {
        this.success = `Service record submitted. Hash: ${(response.metadata_hash || '').slice(0, 18)}… — Awaiting owner verification.`;
        this.loading = false;
        this.liveHash = '';
        setTimeout(() => {
          this.onReset();
          this.success = '';
        }, 4000);
      },
      error: (err) => {
        this.error = err.error?.error || 'Failed to submit service record.';
        this.loading = false;
      }
    });
  }

  onReset(): void {
    this.serviceForm.reset();
    const today = new Date().toISOString().split('T')[0];
    this.serviceForm.patchValue({ service_date: today });
    this.error = '';
    this.success = '';
    this.liveHash = '';
  }
}
