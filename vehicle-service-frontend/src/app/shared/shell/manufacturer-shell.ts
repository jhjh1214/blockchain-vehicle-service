import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../core/services/auth';
import { User } from '../../core/models/user.model';

@Component({
  selector: 'app-manufacturer-shell',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './manufacturer-shell.html',
  styleUrls: ['./manufacturer-shell.css']
})
export class ManufacturerShellComponent implements OnInit {
  currentUser: User | null = null;

  constructor(private authService: AuthService, private router: Router) {}

  ngOnInit(): void {
    this.currentUser = this.authService.currentUserValue;
  }

  get initials(): string {
    const name = this.currentUser?.name || '';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'MF';
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
