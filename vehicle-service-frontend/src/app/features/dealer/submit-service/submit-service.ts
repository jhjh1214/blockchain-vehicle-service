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
  vinPrefilled = false;
  selectedPhotos: File[] = [];
  photoPreviews: string[] = [];
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
        this.serviceForm.patchValue({ vin: params['vin'].toUpperCase() });
        this.serviceForm.get('vin')?.disable();
        this.vinPrefilled = true;
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

  onPhotosSelected(event: Event): void {
    const files = (event.target as HTMLInputElement).files;
    if (!files) return;
    const remaining = 5 - this.selectedPhotos.length;
    Array.from(files).slice(0, remaining).forEach(file => {
      const reader = new FileReader();
      reader.onload = (e) => this.photoPreviews.push(e.target?.result as string);
      reader.readAsDataURL(file);
      this.selectedPhotos.push(file);
    });
    (event.target as HTMLInputElement).value = '';
  }

  removePhoto(index: number): void {
    this.selectedPhotos.splice(index, 1);
    this.photoPreviews.splice(index, 1);
  }

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

    const raw = { ...this.serviceForm.getRawValue() };
    raw.service_date = new Date(raw.service_date).toISOString();
    raw.mileage = parseInt(raw.mileage, 10);
    const ecuArr = raw.ecu_modules
      ? raw.ecu_modules.split(',').map((m: string) => m.trim()).filter(Boolean)
      : [];

    let payload: FormData | Record<string, unknown>;
    if (this.selectedPhotos.length > 0) {
      const fd = new FormData();
      fd.append('vin', raw.vin);
      fd.append('service_type', raw.service_type);
      fd.append('service_date', raw.service_date);
      fd.append('mileage', String(raw.mileage));
      fd.append('technician_name', raw.technician_name || '');
      fd.append('parts_replaced', raw.parts_replaced || '');
      fd.append('service_notes', raw.service_notes || '');
      fd.append('ecu_modules', JSON.stringify(ecuArr));
      this.selectedPhotos.forEach(f => fd.append('photos', f, f.name));
      payload = fd;
    } else {
      payload = { ...raw, ecu_modules: ecuArr };
    }

    this.serviceService.submitService(payload).subscribe({
      next: (response) => {
        const photoNote = this.selectedPhotos.length > 0 ? ` ${this.selectedPhotos.length} photo(s) attached.` : '';
        this.success = `Service record submitted. Hash: ${(response.metadata_hash || '').slice(0, 18)}…${photoNote} — Awaiting owner verification.`;
        this.loading = false;
        this.liveHash = '';
        setTimeout(() => {
          this.onReset();
          this.success = '';
        }, 5000);
      },
      error: (err) => {
        this.error = err.error?.error || 'Failed to submit service record.';
        this.loading = false;
      }
    });
  }

  onReset(): void {
    this.serviceForm.reset();
    if (this.vinPrefilled) {
      const vin = this.serviceForm.get('vin')?.value;
      this.serviceForm.get('vin')?.disable();
      this.serviceForm.patchValue({ vin });
    }
    const today = new Date().toISOString().split('T')[0];
    this.serviceForm.patchValue({ service_date: today });
    this.error = '';
    this.success = '';
    this.liveHash = '';
    this.selectedPhotos = [];
    this.photoPreviews = [];
  }
}
