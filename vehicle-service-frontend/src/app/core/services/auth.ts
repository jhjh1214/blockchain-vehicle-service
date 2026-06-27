import { Injectable, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, Subscription, interval, of } from 'rxjs';
import { tap, filter, switchMap, catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { User, LoginRequest, AuthResponse, RegisterRequest } from '../models/user.model';
import { jwtDecode } from 'jwt-decode';
import { ThemeService } from './theme.service';

const USER_KEY = 'currentUser';
// How often to re-verify the live session against the locally cached profile.
// The auth cookie is shared across every tab of this browser, so logging into
// a different account in another tab silently swaps the cookie under this tab
// too — this catches that drift even when "remember me" was off (sessionStorage
// writes don't fire cross-tab `storage` events, so the listener alone can't).
const SESSION_CHECK_MS = 15_000;

@Injectable({ providedIn: 'root' })
export class AuthService implements OnDestroy {
  private currentUserSubject: BehaviorSubject<User | null>;
  currentUser: Observable<User | null>;
  private readonly _storageListener = (event: StorageEvent) => this._onStorageEvent(event);
  private _sessionWatchSub?: Subscription;

  constructor(private http: HttpClient, private theme: ThemeService) {
    // Restore user profile from storage for UI state (role, name, email — not a token)
    const stored = sessionStorage.getItem(USER_KEY) || localStorage.getItem(USER_KEY);
    this.currentUserSubject = new BehaviorSubject<User | null>(
      stored ? JSON.parse(stored) : null
    );
    this.currentUser = this.currentUserSubject.asObservable();

    window.addEventListener('storage', this._storageListener);
    this._startSessionWatch();
  }

  ngOnDestroy(): void {
    window.removeEventListener('storage', this._storageListener);
    this._sessionWatchSub?.unsubscribe();
  }

  /** Fast path: fires instantly in other tabs when a tab using "remember me" logs in/out. */
  private _onStorageEvent(event: StorageEvent): void {
    if (event.key !== USER_KEY) return;
    const current = this.currentUserSubject.value;
    const incoming: User | null = event.newValue ? JSON.parse(event.newValue) : null;
    if ((incoming?.id ?? null) !== (current?.id ?? null)) {
      this._onSessionMismatch();
    }
  }

  /** Fallback path: catches the case where the other tab didn't use "remember me". */
  private _startSessionWatch(): void {
    this._sessionWatchSub = interval(SESSION_CHECK_MS).pipe(
      filter(() => this.isAuthenticated()),
      switchMap(() => this.http.get<User>(`${environment.apiUrl}/auth/me`, { withCredentials: true }).pipe(
        catchError(() => of(null))
      )),
    ).subscribe(serverUser => {
      const local = this.currentUserSubject.value;
      if (serverUser && local && serverUser.id !== local.id) {
        this._onSessionMismatch();
      }
    });
  }

  /**
   * The shared auth cookie now belongs to a different account than what this tab
   * is rendering — reload to resync. Only this tab's own sessionStorage is cleared;
   * localStorage is left untouched since it may hold another tab's valid
   * "remember me" session that this tab must not destroy.
   */
  private _onSessionMismatch(): void {
    sessionStorage.removeItem(USER_KEY);
    window.location.reload();
  }

  get currentUserValue(): User | null {
    return this.currentUserSubject.value;
  }

  login(credentials: LoginRequest, rememberMe = true): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(
      `${environment.apiUrl}/auth/login`,
      { ...credentials, remember_me: rememberMe },
      { withCredentials: true }
    ).pipe(
      tap(r => this._storeSession(r, rememberMe))
    );
  }

  register(data: RegisterRequest): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/register`, data, { withCredentials: true }).pipe(
      tap(r => this._storeSession(r, true))
    );
  }

  refreshTokens(): Observable<AuthResponse> {
    // Cookie is sent automatically — no body needed
    const remember = !!localStorage.getItem(USER_KEY);
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/refresh`, {}, { withCredentials: true }).pipe(
      tap(r => this._storeSession(r, remember))
    );
  }

  logout(): void {
    // Backend clears cookies; we clear local user state
    this.http.post(`${environment.apiUrl}/auth/logout`, {}, { withCredentials: true }).subscribe();
    [USER_KEY].forEach(k => {
      localStorage.removeItem(k);
      sessionStorage.removeItem(k);
    });
    // Also clear any legacy token keys from old storage format
    ['access_token', 'refresh_token'].forEach(k => {
      localStorage.removeItem(k);
      sessionStorage.removeItem(k);
    });
    this.currentUserSubject.next(null);
  }

  /**
   * Returns the access token from the JWT cookie indirectly — only available
   * via the response body on login/refresh. Returns null for web (cookie-based);
   * Flutter uses its own token storage and never calls this.
   */
  getToken(): string | null {
    return null; // Web uses HttpOnly cookies — no JS access to token
  }

  isAuthenticated(): boolean {
    // Auth is proven by the HttpOnly cookie; UI reflects login state via stored user profile
    return this.currentUserSubject.value !== null;
  }

  hasRole(role: string): boolean {
    return this.currentUserValue?.role === role;
  }

  updateProfile(data: { name?: string; phone?: string; city?: string; state?: string; theme_preference?: string }): Observable<{ user: User; message: string }> {
    const remember = !!localStorage.getItem(USER_KEY);
    return this.http.put<{ user: User; message: string }>(`${environment.apiUrl}/auth/profile`, data, { withCredentials: true }).pipe(
      tap(r => {
        const store = remember ? localStorage : sessionStorage;
        store.setItem(USER_KEY, JSON.stringify(r.user));
        this.currentUserSubject.next(r.user);
      })
    );
  }

  changePassword(currentPassword: string, newPassword: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${environment.apiUrl}/auth/change-password`, {
      current_password: currentPassword,
      new_password: newPassword,
    }, { withCredentials: true });
  }

  resendVerification(): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${environment.apiUrl}/auth/resend-verification`, {}, { withCredentials: true });
  }

  deleteAccount(password: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${environment.apiUrl}/auth/account`, {
      body: { password },
      withCredentials: true,
    });
  }

  private _storeSession(r: AuthResponse, remember: boolean): void {
    // Only store the user profile (role, name, email) — NOT tokens
    // Tokens live in HttpOnly cookies set by the backend
    [USER_KEY].forEach(k => {
      localStorage.removeItem(k);
      sessionStorage.removeItem(k);
    });
    const store = remember ? localStorage : sessionStorage;
    store.setItem(USER_KEY, JSON.stringify(r.user));
    this.currentUserSubject.next(r.user);
    if (r.user?.theme_preference) {
      this.theme.applyUserPreference(r.user.theme_preference);
    }
  }
}
