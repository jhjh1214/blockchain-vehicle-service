import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../core/services/auth';
import { MY_CITIES, MYCity, getStateForCity } from '../../../shared/constants/my-cities';
import { MY_BRANDS } from '../../../shared/constants/my-brands';

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
export class RegisterComponent implements OnInit {
  registerForm: FormGroup;
  loading = false;
  error = '';
  showPassword = false;
  showConfirm  = false;

  roles = [
    { value: 'MANUFACTURER',          label: 'Manufacturer' },
    { value: 'SERVICE_CENTER',         label: 'Authorised Brand Service Centre' },
    { value: 'SERVICE_CENTER_INDEP',   label: 'Independent Workshop' },
  ];

  brands = MY_BRANDS;
  cities: MYCity[] = MY_CITIES;

  get role(): string { return this.f['role'].value; }
  get isManufacturer(): boolean { return this.role === 'MANUFACTURER'; }
  get isAuthSC(): boolean { return this.role === 'SERVICE_CENTER'; }
  get isIndepSC(): boolean { return this.role === 'SERVICE_CENTER_INDEP'; }
  get isSC(): boolean { return this.isAuthSC || this.isIndepSC; }

  onCityChange(): void {
    const city = this.f['city']?.value ?? '';
    this.registerForm.patchValue({ state: getStateForCity(city) });
  }

  requirements = [
    { key: 'minLength',  label: 'At least 8 characters' },
    { key: 'uppercase',  label: 'One uppercase letter (A–Z)' },
    { key: 'lowercase',  label: 'One lowercase letter (a–z)' },
    { key: 'number',     label: 'One number (0–9)' },
    { key: 'special',    label: 'One special character (!@#$%…)' },
  ];

  constructor(private fb: FormBuilder, private router: Router, private authService: AuthService) {
    this.registerForm = this.fb.group({
      email:           ['', [Validators.required, Validators.email]],
      role:            ['SERVICE_CENTER', Validators.required],
      name:            ['', Validators.required],
      ssm_number:      ['', Validators.required],
      brand:           [''],
      phone:           [''],
      city:            [''],
      state:           [''],
      password:        ['', [Validators.required, passwordStrength]],
      confirmPassword: ['', Validators.required],
    }, { validators: passwordMatch });
  }

  ngOnInit(): void {
    this.registerForm.get('role')!.valueChanges.subscribe(() => this._updateValidators());
    this._updateValidators();
  }

  private _updateValidators(): void {
    const brand = this.registerForm.get('brand')!;
    const ssm   = this.registerForm.get('ssm_number')!;
    if (this.isManufacturer) {
      brand.setValidators([Validators.required]);
      ssm.setValidators([Validators.required]);
    } else if (this.isAuthSC) {
      brand.clearValidators();
      ssm.setValidators([Validators.required]);
    } else {
      brand.clearValidators();
      ssm.clearValidators();
    }
    brand.updateValueAndValidity();
    ssm.updateValueAndValidity();
  }

  get f() { return this.registerForm.controls; }
  get passwordErrors(): string[] { return this.f['password'].errors?.['passwordStrength'] ?? []; }
  reqMet(key: string): boolean { return !this.passwordErrors.includes(key); }
  get strength(): number { return 5 - this.passwordErrors.length; }
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
    if (this.registerForm.invalid) { this.registerForm.markAllAsTouched(); return; }
    this.loading = true;
    this.error = '';

    const raw = this.registerForm.value;
    const { confirmPassword, role: rawRole, ...rest } = raw;

    const actualRole = rawRole === 'SERVICE_CENTER_INDEP' ? 'SERVICE_CENTER' : rawRole;
    const isIndependent = rawRole === 'SERVICE_CENTER_INDEP';

    const payload: any = {
      email: rest.email,
      password: rest.password,
      role: actualRole,
      name: rest.name,
      phone: rest.phone ? `+60 ${rest.phone.trim()}` : '',
      is_independent: isIndependent,
    };
    if (rest.ssm_number) payload.ssm_number = rest.ssm_number.toUpperCase().trim();
    if (this.isManufacturer) payload.brand = rest.brand;
    if (this.isSC) {
      payload.city = rest.city || '';
      payload.state = rest.state || '';
    }

    this.authService.register(payload).subscribe({
      next: r => {
        if (r.user.role === 'MANUFACTURER') {
          this.router.navigate(['/manufacturer/dashboard']);
        } else {
          this.router.navigate(['/dealer/dashboard']);
        }
      },
      error: e => {
        this.error = e.error?.error || 'Registration failed. Please try again.';
        this.loading = false;
      }
    });
  }
}
