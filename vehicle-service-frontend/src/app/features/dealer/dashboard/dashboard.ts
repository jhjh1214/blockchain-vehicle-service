import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Subscription } from 'rxjs';
import { AuthService } from '../../../core/services/auth';
import { BlockchainService } from '../../../core/services/blockchain.service';
import { User } from '../../../core/models/user.model';

@Component({
  selector: 'app-dealer-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.css']
})
export class DashboardComponent implements OnInit, OnDestroy {
  currentUser: User | null = null;
  isConnected: boolean | null = null;
  private subs = new Subscription();

  constructor(private authService: AuthService, private blockchain: BlockchainService) {
    this.currentUser = this.authService.currentUserValue;
  }

  ngOnInit(): void {
    this.subs.add(this.blockchain.connected$.subscribe(v => this.isConnected = v));
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }
}
