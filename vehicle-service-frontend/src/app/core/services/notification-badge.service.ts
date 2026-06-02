import { Injectable, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Subscription, interval, Observable } from 'rxjs';
import { switchMap, catchError, startWith } from 'rxjs/operators';
import { of } from 'rxjs';
import { VehicleService } from './vehicle';
import { ServiceService } from './service';
import { environment } from '../../../environments/environment';

const POLL_MS = 30_000;

@Injectable({ providedIn: 'root' })
export class NotificationBadgeService implements OnDestroy {
  private _warrantyBadge = new BehaviorSubject<number>(0);
  private _disputeBadge  = new BehaviorSubject<number>(0);
  private _notifCount    = new BehaviorSubject<number>(0);

  readonly warrantyBadge$ = this._warrantyBadge.asObservable();
  readonly disputeBadge$  = this._disputeBadge.asObservable();
  readonly notifCount$    = this._notifCount.asObservable();

  private sub = new Subscription();

  constructor(
    private vehicleService: VehicleService,
    private serviceService: ServiceService,
    private http: HttpClient,
  ) {}

  startManufacturer(): void {
    this.sub.add(
      interval(POLL_MS).pipe(
        startWith(0),
        switchMap(() => this.vehicleService.getDashboardStats().pipe(catchError(() => of(null)))),
      ).subscribe(stats => {
        if (stats) this._warrantyBadge.next(stats.warranty_claims ?? 0);
      })
    );
    this._pollNotifCount();
  }

  startDealer(): void {
    this.sub.add(
      interval(POLL_MS).pipe(
        startWith(0),
        switchMap(() => this.serviceService.getCenterPending().pipe(catchError(() => of(null)))),
      ).subscribe(res => {
        if (res) {
          const disputedCount = (res.pending_services ?? []).filter((r: any) => r.disputed).length;
          this._disputeBadge.next(disputedCount);
        }
      })
    );
    this._pollNotifCount();
  }

  private _pollNotifCount(): void {
    this.sub.add(
      interval(POLL_MS).pipe(
        startWith(0),
        switchMap(() =>
          this.http.get<{ unread: number }>(`${environment.apiUrl}/notifications/count`)
            .pipe(catchError(() => of(null)))
        ),
      ).subscribe(res => {
        if (res) this._notifCount.next(res.unread ?? 0);
      })
    );
  }

  getNotifications(limit = 20): Observable<{ notifications: any[] }> {
    return this.http.get<{ notifications: any[] }>(
      `${environment.apiUrl}/notifications?limit=${limit}`
    );
  }

  markAllRead(): Observable<any> {
    return this.http.post(`${environment.apiUrl}/notifications/read-all`, {});
  }

  markRead(id: number): Observable<any> {
    return this.http.post(`${environment.apiUrl}/notifications/${id}/read`, {});
  }

  refreshCount(): void {
    this.http.get<{ unread: number }>(`${environment.apiUrl}/notifications/count`)
      .pipe(catchError(() => of(null)))
      .subscribe(res => { if (res) this._notifCount.next(res.unread ?? 0); });
  }

  stop(): void {
    this.sub.unsubscribe();
    this.sub = new Subscription();
    this._warrantyBadge.next(0);
    this._disputeBadge.next(0);
    this._notifCount.next(0);
  }

  ngOnDestroy(): void {
    this.stop();
  }
}
