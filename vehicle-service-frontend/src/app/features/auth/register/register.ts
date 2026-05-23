import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../core/services/auth';

function passwordStrength(control: AbstractControl): ValidationErrors | null {
  const v: string = control.value || '';
  const errors: string[] = [];
  if (v.length < 8)                             errors.push('minLength');
  if (!/[A-Z]/.test(v))                         errors.push('uppercase');
  if (!/[a-z]/.test(v))                         errors.push('lowercase');
  if (!/\d/.test(v))                            errors.push('number');
  if (!/[!@#$%^&*()\-_=+\[\]{};':"\\|,.<>/?`~]/.test(v)) errors.push('special');
  return errors.length ? { passwordStrength: errors } : null;
}

function passwordMatch(g: AbstractControl): ValidationErrors | null {
  return g.get('password')?.value === g.get('confirmPassword')?.value
    ? null : { mismatch: true };
}

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './register.html',
  styleUrls: ['./register.css']
})
export class RegisterComponent {
  registerForm: FormGroup;
  loading = false;
  error = '';
  showPassword = false;
  showConfirm  = false;

  roles = [
    { value: 'MANUFACTURER',   label: 'Manufacturer' },
    { value: 'SERVICE_CENTER', label: 'Service Center' },
  ];

  requirements = [
    { key: 'minLength',  label: 'At least 8 characters' },
    { key: 'uppercase',  label: 'One uppercase letter (A–Z)' },
    { key: 'lowercase',  label: 'One lowercase letter (a–z)' },
    { key: 'number',     label: 'One number (0–9)' },
    { key: 'special',    label: 'One special character (!@#$%…)' },
  ];

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private authService: AuthService
  ) {
    this.registerForm = this.fb.group({
      email:           ['', [Validators.required, Validators.email]],
      role:            ['SERVICE_CENTER', Validators.required],
      password:        ['', [Validators.required, passwordStrength]],
      confirmPassword: ['', Validators.required],
    }, { validators: passwordMatch });
  }

  get f() { return this.registerForm.controls; }

  get passwordErrors(): string[] {
    return this.f['password'].errors?.['passwordStrength'] ?? [];
  }

  reqMet(key: string): boolean {
    return !this.passwordErrors.includes(key);
  }

  get strength(): number {
    return 5 - this.passwordErrors.length;
  }

  get strengthLabel(): string {
    const s = this.strength;
    if (s <= 1) return 'Very weak';
    if (s === 2) return 'Weak';
    if (s === 3) return 'Fair';
    if (s === 4) return 'Good';
    return 'Strong';
  }

  get strengthClass(): string {
    const s = this.strength;
    if (s <= 1) return 'strength-1';
    if (s === 2) return 'strength-2';
    if (s === 3) return 'strength-3';
    if (s === 4) return 'strength-4';
    return 'strength-5';
  }

  onSubmit(): void {
    if (this.registerForm.invalid) {
      this.registerForm.markAllAsTouched();
      return;
    }
    this.loading = true;
    this.error   = '';

    const { confirmPassword, ...userData } = this.registerForm.value;
    this.authService.register(userData).subscribe({
      next: r => {
        if (r.user.role === 'MANUFACTURER') {
          this.router.navigate(['/manufacturer/dashboard']);
        } else {
          this.router.navigate(['/dealer/dashboard']);
        }
      },
      error: e => {
        this.error   = e.error?.error || 'Registration failed. Please try again.';
        this.loading = false;
      }
    });
  }
}
