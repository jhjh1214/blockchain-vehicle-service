import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule, FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth';
import { User } from '../../../core/models/user.model';
import { MY_CITIES, getStateForCity } from '../../../shared/constants/my-cities';

function passwordStrength(control: AbstractControl): ValidationErrors | null {
  const v: string = control.value || '';
  if (!v) return null;
  const errors: string[] = [];
  if (v.length < 8)                              errors.push('minLength');
  if (!/[A-Z]/.test(v))                          errors.push('uppercase');
  if (!/[a-z]/.test(v))                          errors.push('lowercase');
  if (!/\d/.test(v))                             errors.push('number');
  if (!/[!@#$%^&*()\-_=+\[\]{};':"\\|,.<>/?`~]/.test(v)) errors.push('special');
  return errors.length ? { passwordStrength: errors } : null;
}

function passwordMatch(g: AbstractControl): ValidationErrors | null {
  return g.get('newPassword')?.value === g.get('confirmPassword')?.value
    ? null : { mismatch: true };
}

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule],
  templateUrl: './profile.html',
})
export class ProfileComponent implements OnInit {
  currentUser: User | null = null;
  profileForm: FormGroup;
  pwForm: FormGroup;

  profileSaving = false;
  profileSuccess = '';
  profileError   = '';

  pwSaving  = false;
  pwSuccess = '';
  pwError   = '';

  showCurrentPw = false;
  showNewPw     = false;
  showConfirmPw = false;

  deleteConfirmText = '';
  deletePassword = '';
  deleteLoading = false;
  deleteError = '';
  showDeleteZone = false;

  cities = MY_CITIES;

  get initials(): string {
    const n = this.currentUser?.name || this.currentUser?.email || '?';
    return n.split(' ').map(p => p[0]).join('').toUpperCase().slice(0, 2);
  }

  get isServiceCenter(): boolean {
    return this.currentUser?.role === 'SERVICE_CENTER';
  }

  get isManufacturer(): boolean {
    return this.currentUser?.role === 'MANUFACTURER';
  }

  constructor(private fb: FormBuilder, private authService: AuthService, private router: Router) {
    this.profileForm = this.fb.group({
      name:  [''],
      phone: [''],
      city:  [''],
      state: [''],
    });
    this.pwForm = this.fb.group({
      currentPassword: ['', Validators.required],
      newPassword:     ['', [Validators.required, passwordStrength]],
      confirmPassword: ['', Validators.required],
    }, { validators: passwordMatch });
  }

  ngOnInit(): void {
    this.currentUser = this.authService.currentUserValue;
    if (this.currentUser) {
      this.profileForm.patchValue({
        name:  this.currentUser.name  || '',
        phone: this.currentUser.phone || '',
        city:  this.currentUser.city  || '',
        state: this.currentUser.state || '',
      });
    }
  }

  onCityChange(): void {
    const city = this.profileForm.get('city')?.value ?? '';
    this.profileForm.patchValue({ state: getStateForCity(city) });
  }

  saveProfile(): void {
    this.profileSaving = true;
    this.profileSuccess = '';
    this.profileError   = '';
    const v = this.profileForm.value;
    this.authService.updateProfile({ name: v.name, phone: v.phone, city: v.city, state: v.state }).subscribe({
      next: () => {
        this.profileSaving = false;
        this.profileSuccess = 'Profile updated successfully';
        this.currentUser = this.authService.currentUserValue;
      },
      error: e => {
        this.profileSaving = false;
        this.profileError = e.error?.error || 'Failed to update profile';
      }
    });
  }

  changePassword(): void {
    if (this.pwForm.invalid) { this.pwForm.markAllAsTouched(); return; }
    this.pwSaving = true;
    this.pwSuccess = '';
    this.pwError   = '';
    const v = this.pwForm.value;
    this.authService.changePassword(v.currentPassword, v.newPassword).subscribe({
      next: () => {
        this.pwSaving = false;
        this.pwSuccess = 'Password changed. Please log in again on other devices.';
        this.pwForm.reset();
      },
      error: e => {
        this.pwSaving = false;
        this.pwError = e.error?.error || 'Failed to change password';
      }
    });
  }

  get pwErrors(): string[] {
    return this.pwForm.get('newPassword')?.errors?.['passwordStrength'] ?? [];
  }
  reqMet(key: string): boolean { return !this.pwErrors.includes(key); }

  requirements = [
    { key: 'minLength', label: 'At least 8 characters' },
    { key: 'uppercase', label: 'One uppercase letter' },
    { key: 'lowercase', label: 'One lowercase letter' },
    { key: 'number',    label: 'One number' },
    { key: 'special',  label: 'One special character' },
  ];

  deleteAccount(): void {
    if (this.deleteConfirmText !== 'DELETE' || !this.deletePassword || this.deleteLoading) return;
    this.deleteLoading = true;
    this.deleteError = '';
    this.authService.deleteAccount(this.deletePassword).subscribe({
      next: () => {
        this.authService.logout();
        this.router.navigate(['/login']);
      },
      error: (e) => {
        this.deleteError = e.error?.error || 'Failed to delete account';
        this.deleteLoading = false;
      }
    });
  }
}
