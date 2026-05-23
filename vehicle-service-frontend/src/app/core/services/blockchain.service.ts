import { Injectable, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, interval, Subscription } from 'rxjs';
import { map, catchError, switchMap } from 'rxjs/operators';
import { of } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class BlockchainService implements OnDestroy {
  private _connected = new BehaviorSubject<boolean | null>(null);
  connected$ = this._connected.asObservable();

  private pollSub: Subscription;

  constructor(private http: HttpClient) {
    this.check();
    this.pollSub = interval(30_000).pipe(
      switchMap(() => this.fetchStatus())
    ).subscribe(v => this._connected.next(v));
  }

  private check(): void {
    this.fetchStatus().subscribe(v => this._connected.next(v));
  }

  private fetchStatus() {
    return this.http.get<any>(`${environment.apiUrl}/health`).pipe(
      map(res => res?.blockchain?.connected === true),
      catchError(() => of(false))
    );
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
  }
}
