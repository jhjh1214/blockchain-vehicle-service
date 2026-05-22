import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { AuthService } from '../../../core/services/auth';
import { User } from '../../../core/models/user.model';

@Component({
  selector: 'app-manufacturer-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.css']
})
export class ManufacturerDashboardComponent {
  currentUser: User | null = null;

  constructor(private authService: AuthService) {
    this.currentUser = this.authService.currentUserValue;
  }
}
