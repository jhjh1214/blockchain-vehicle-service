import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-verify-email',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './verify-email.html',
  styleUrls: ['./verify-email.css'],
})
export class VerifyEmailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);

  state: 'loading' | 'success' | 'error' = 'loading';
  message = '';

  ngOnInit(): void {
    const token = this.route.snapshot.queryParamMap.get('token');
    if (!token) {
      this.state = 'error';
      this.message = 'No verification token found in the link.';
      return;
    }
    this.http
      .get<{ message: string }>(`${environment.apiUrl}/auth/verify-email`, { params: { token } })
      .subscribe({
        next: (res) => {
          this.state = 'success';
          this.message = res.message;
        },
        error: (err) => {
          this.state = 'error';
          this.message = err.error?.error ?? 'Verification failed. The link may have expired.';
        },
      });
  }
}
