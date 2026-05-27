import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router, ActivatedRoute, RouterModule } from '@angular/router';
import { AuthService } from '../../../core/services/auth';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './login.html',
  styleUrls: ['./login.css']
})
export class LoginComponent implements OnInit {
  loginForm: FormGroup;
  loading = false;
  error = '';
  lockoutMessage = '';
  showPassword = false;
  returnUrl = '/';

  constructor(
    private formBuilder: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService
  ) {
    const currentUser = this.authService.currentUserValue;
    if (currentUser) {
      if (currentUser.role === 'MANUFACTURER') {
        this.router.navigate(['/manufacturer/dashboard']);
      } else if (currentUser.role === 'SERVICE_CENTER') {
        this.router.navigate(['/dealer/dashboard']);
      }
    }

    this.loginForm = this.formBuilder.group({
      email:      ['', [Validators.required, Validators.email]],
      password:   ['', Validators.required],
      rememberMe: [true]
    });
  }

  ngOnInit(): void {
    this.returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/';
  }

  get f() { return this.loginForm.controls; }

  onSubmit(): void {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.error = '';
    this.lockoutMessage = '';

    const { email, password, rememberMe } = this.loginForm.value;
    this.authService.login({ email, password }, rememberMe).subscribe({
      next: (response) => {
        const user = response.user;
        if (user.role === 'MANUFACTURER') {
          this.router.navigate(['/manufacturer/dashboard']);
        } else if (user.role === 'SERVICE_CENTER') {
          this.router.navigate(['/dealer/dashboard']);
        } else {
          this.error = 'Vehicle owners should use the mobile app.';
          this.authService.logout();
          this.loading = false;
        }
      },
      error: (err) => {
        if (err.status === 423) {
          this.lockoutMessage = err.error?.error || 'Account temporarily locked. Please try again in 15 minutes.';
        } else {
          this.error = err.error?.error || 'Login failed. Please check your credentials.';
        }
        this.loading = false;
      }
    });
  }
}
