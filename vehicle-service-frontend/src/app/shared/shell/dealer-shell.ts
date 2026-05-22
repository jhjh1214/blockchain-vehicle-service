import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../core/services/auth';
import { User } from '../../core/models/user.model';

@Component({
  selector: 'app-dealer-shell',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dealer-shell.html',
  styleUrls: ['./dealer-shell.css']
})
export class DealerShellComponent implements OnInit {
  currentUser: User | null = null;

  constructor(private authService: AuthService, private router: Router) {}

  ngOnInit(): void {
    this.currentUser = this.authService.currentUserValue;
  }

  get initials(): string {
    const name = this.currentUser?.name || '';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'SC';
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
