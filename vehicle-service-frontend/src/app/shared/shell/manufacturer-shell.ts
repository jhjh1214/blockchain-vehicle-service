import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, NavigationStart, NavigationEnd, NavigationCancel, NavigationError } from '@angular/router';
import { Subscription } from 'rxjs';
import { AuthService } from '../../core/services/auth';
import { BlockchainService } from '../../core/services/blockchain.service';
import { ThemeService } from '../../core/services/theme.service';
import { InactivityService } from '../../core/services/inactivity.service';
import { User } from '../../core/models/user.model';

@Component({
  selector: 'app-manufacturer-shell',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './manufacturer-shell.html',
  styleUrls: ['./manufacturer-shell.css']
})
export class ManufacturerShellComponent implements OnInit, OnDestroy {
  currentUser: User | null = null;
  isConnected: boolean | null = null;
  isDark = false;
  sidebarOpen = false;
  routeLoading = false;
  showInactivityWarning = false;

  private subs = new Subscription();

  constructor(
    private authService: AuthService,
    private router: Router,
    private blockchain: BlockchainService,
    private theme: ThemeService,
    readonly inactivity: InactivityService,
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
    this.subs.add(this.inactivity.showWarning$.subscribe(v => this.showInactivityWarning = v));
    this.inactivity.start();
  }

  get initials(): string {
    const src = this.currentUser?.name || this.currentUser?.email || '';
    return src.split(/[\s@.]/).filter(Boolean).map(s => s[0]).join('').toUpperCase().slice(0, 2) || 'MF';
  }

  toggleTheme(): void { this.theme.toggle(); }
  toggleSidebar(): void { this.sidebarOpen = !this.sidebarOpen; }
  closeSidebar(): void { this.sidebarOpen = false; }

  logout(): void {
    this.inactivity.stop();
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  ngOnDestroy(): void {
    this.inactivity.stop();
    this.subs.unsubscribe();
  }
}
