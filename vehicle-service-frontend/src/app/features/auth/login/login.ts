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
  returnUrl = '/';

  constructor(
    private formBuilder: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService
  ) {
    // Check if already logged in
    const currentUser = this.authService.currentUserValue;
    if (currentUser) {
      // Redirect to appropriate dashboard
      if (currentUser.role === 'MANUFACTURER') {
        this.router.navigate(['/manufacturer/dashboard']);
      } else if (currentUser.role === 'SERVICE_CENTER') {
        this.router.navigate(['/dealer/dashboard']);
      }
    }

    this.loginForm = this.formBuilder.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', Validators.required]
    });
  }

  ngOnInit(): void {
    this.returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/';
  }

  get f() { return this.loginForm.controls; }

  onSubmit(): void {
    if (this.loginForm.invalid) {
      return;
    }

    this.loading = true;
    this.error = '';

    this.authService.login(this.loginForm.value).subscribe({
      next: (response) => {
        const user = response.user;
        
        // Route based on role (only MANUFACTURER or SERVICE_CENTER)
        if (user.role === 'MANUFACTURER') {
          this.router.navigate(['/manufacturer/dashboard']);
        } else if (user.role === 'SERVICE_CENTER') {
          this.router.navigate(['/dealer/dashboard']);
        } else {
          // If somehow an OWNER tries to log in via web
          this.error = 'Vehicle owners should use the mobile app. Please download the app from your app store.';
          this.authService.logout();
          this.loading = false;
        }
      },
      error: (error) => {
        this.error = error.error?.error || 'Login failed. Please check your credentials.';
        this.loading = false;
      }
    });
  }
}