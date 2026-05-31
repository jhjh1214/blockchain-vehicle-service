import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, Subscription, interval } from 'rxjs';
import { switchMap, catchError, startWith } from 'rxjs/operators';
import { of } from 'rxjs';
import { VehicleService } from './vehicle';
import { ServiceService } from './service';

const POLL_MS = 30_000;

@Injectable({ providedIn: 'root' })
export class NotificationBadgeService implements OnDestroy {
  private _warrantyBadge = new BehaviorSubject<number>(0);
  private _disputeBadge  = new BehaviorSubject<number>(0);

  readonly warrantyBadge$ = this._warrantyBadge.asObservable();
  readonly disputeBadge$  = this._disputeBadge.asObservable();

  private sub = new Subscription();

  constructor(
    private vehicleService: VehicleService,
    private serviceService: ServiceService,
  ) {}

  startManufacturer(): void {
    this.sub.add(
      interval(POLL_MS).pipe(
        startWith(0),
        switchMap(() => this.vehicleService.getDashboardStats().pipe(catchError(() => of(null)))),
      ).subscribe(stats => {
        if (stats) {
          this._warrantyBadge.next(stats.warranty_claims ?? 0);
        }
      })
    );
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
  }

  stop(): void {
    this.sub.unsubscribe();
    this.sub = new Subscription();
    this._warrantyBadge.next(0);
    this._disputeBadge.next(0);
  }

  ngOnDestroy(): void {
    this.stop();
  }
}
