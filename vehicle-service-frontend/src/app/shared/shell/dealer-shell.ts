import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, NavigationStart, NavigationEnd, NavigationCancel, NavigationError } from '@angular/router';
import { Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';
import { AuthService } from '../../core/services/auth';
import { BlockchainService } from '../../core/services/blockchain.service';
import { ThemeService } from '../../core/services/theme.service';
import { User } from '../../core/models/user.model';

@Component({
  selector: 'app-dealer-shell',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dealer-shell.html',
  styleUrls: ['./dealer-shell.css']
})
export class DealerShellComponent implements OnInit, OnDestroy {
  currentUser: User | null = null;
  isConnected: boolean | null = null;
  isDark = false;
  sidebarOpen = false;
  routeLoading = false;

  private subs = new Subscription();

  constructor(
    private authService: AuthService,
    private router: Router,
    private blockchain: BlockchainService,
    private theme: ThemeService
  ) {}

  ngOnInit(): void {
    this.currentUser = this.authService.currentUserValue;
    this.subs.add(this.blockchain.connected$.subscribe(v => this.isConnected = v));
    this.subs.add(this.theme.dark$.subscribe(v => this.isDark = v));
    this.subs.add(
      this.router.events.subscribe(e => {
        if (e instanceof NavigationStart) this.routeLoading = true;
        if (e instanceof NavigationEnd || e instanceof NavigationCancel || e instanceof NavigationError) this.routeLoading = false;
      })
    );
  }

  get initials(): string {
    const src = this.currentUser?.name || this.currentUser?.email || '';
    return src.split(/[\s@.]/).filter(Boolean).map(s => s[0]).join('').toUpperCase().slice(0, 2) || 'SC';
  }

  toggleTheme(): void { this.theme.toggle(); }
  toggleSidebar(): void { this.sidebarOpen = !this.sidebarOpen; }
  closeSidebar(): void { this.sidebarOpen = false; }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }
}
