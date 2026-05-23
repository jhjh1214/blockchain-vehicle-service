import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../core/services/auth';

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

  roles = [
    { value: 'MANUFACTURER', label: 'Manufacturer' },
    { value: 'SERVICE_CENTER', label: 'Service Center' }
    //OWNER - mobile app only
  ];

  constructor(
    private formBuilder: FormBuilder,
    private router: Router,
    private authService: AuthService
  ) {
    //allow registration even if logged in elsewhere
    this.registerForm = this.formBuilder.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', Validators.required],
      role: ['SERVICE_CENTER', Validators.required]
    }, {
      validator: this.passwordMatchValidator
    });
  }

  ngOnInit(): void { }

  passwordMatchValidator(g: FormGroup) {
    return g.get('password')?.value === g.get('confirmPassword')?.value
      ? null : { 'mismatch': true };
  }

  get f() { return this.registerForm.controls; }

  onSubmit(): void {
    if (this.registerForm.invalid) {
      return;
    }

    this.loading = true;
    this.error = '';

    const { confirmPassword, ...userData } = this.registerForm.value;

    this.authService.register(userData).subscribe({
      next: (response) => {
        const user = response.user;
        
        // Route based on role (only MANUFACTURER or SERVICE_CENTER)
        if (user.role === 'MANUFACTURER') {
          this.router.navigate(['/manufacturer/dashboard']);
        } else if (user.role === 'SERVICE_CENTER') {
          this.router.navigate(['/dealer/dashboard']);
        } else {
          // Fallback - should never happen 
          this.error = 'Invalid role. Please contact administrator.';
          this.loading = false;
        }
      },
      error: (error) => {
        this.error = error.error?.error || 'Registration failed. Please try again.';
        this.loading = false;
      }
    });
  }
}