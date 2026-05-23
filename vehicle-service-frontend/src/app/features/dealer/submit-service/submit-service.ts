import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { ServiceService } from '../../../core/services/service';

@Component({
  selector: 'app-submit-service',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './submit-service.html',
  styleUrls: ['./submit-service.css']
})
export class SubmitServiceComponent implements OnInit {
  serviceForm: FormGroup;
  loading = false;
  error = '';
  success = '';

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
  }

  get f() { return this.serviceForm.controls; }

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
  }
}
