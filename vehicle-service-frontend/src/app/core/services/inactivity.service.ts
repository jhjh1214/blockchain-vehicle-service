import { Injectable, NgZone, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { AuthService } from './auth';

const TIMEOUT_MS = 30 * 60 * 1000;   // 30 minutes
const WARNING_MS = 25 * 60 * 1000;   // warn at 25 minutes (5 min before logout)

@Injectable({ providedIn: 'root' })
export class InactivityService implements OnDestroy {
  readonly showWarning$ = new Subject<boolean>();

  private logoutTimer?: ReturnType<typeof setTimeout>;
  private warningTimer?: ReturnType<typeof setTimeout>;
  private readonly activityEvents = ['mousemove', 'keydown', 'click', 'touchstart'] as const;
  private boundReset = this._reset.bind(this);
  private active = false;

  constructor(
    private auth: AuthService,
    private router: Router,
    private zone: NgZone,
  ) {}

  start(): void {
    if (this.active) return;
    this.active = true;
    this.activityEvents.forEach(e => document.addEventListener(e, this.boundReset, { passive: true }));
    this._schedule();
  }

  stop(): void {
    if (!this.active) return;
    this.active = false;
    this.activityEvents.forEach(e => document.removeEventListener(e, this.boundReset));
    this._clearTimers();
    this.showWarning$.next(false);
  }

  dismissWarning(): void {
    this._reset();
  }

  private _reset(): void {
    this._clearTimers();
    this.showWarning$.next(false);
    this._schedule();
  }

  private _schedule(): void {
    this.zone.runOutsideAngular(() => {
      this.warningTimer = setTimeout(() => {
        this.zone.run(() => this.showWarning$.next(true));
      }, WARNING_MS);

      this.logoutTimer = setTimeout(() => {
        this.zone.run(() => {
          this.stop();
          this.auth.logout();
          this.router.navigate(['/login'], { queryParams: { reason: 'inactivity' } });
        });
      }, TIMEOUT_MS);
    });
  }

  private _clearTimers(): void {
    clearTimeout(this.warningTimer);
    clearTimeout(this.logoutTimer);
  }

  ngOnDestroy(): void {
    this.stop();
  }
}
