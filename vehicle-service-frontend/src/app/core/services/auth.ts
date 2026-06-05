import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { User, LoginRequest, AuthResponse, RegisterRequest } from '../models/user.model';
import { jwtDecode } from 'jwt-decode';
import { ThemeService } from './theme.service';

const USER_KEY = 'currentUser';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private currentUserSubject: BehaviorSubject<User | null>;
  currentUser: Observable<User | null>;

  constructor(private http: HttpClient, private theme: ThemeService) {
    // Restore user profile from storage for UI state (role, name, email — not a token)
    const stored = sessionStorage.getItem(USER_KEY) || localStorage.getItem(USER_KEY);
    this.currentUserSubject = new BehaviorSubject<User | null>(
      stored ? JSON.parse(stored) : null
    );
    this.currentUser = this.currentUserSubject.asObservable();
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
