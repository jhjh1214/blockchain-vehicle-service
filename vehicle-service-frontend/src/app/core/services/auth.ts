import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { User, LoginRequest, AuthResponse, RegisterRequest } from '../models/user.model';
import { jwtDecode } from 'jwt-decode';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private currentUserSubject: BehaviorSubject<User | null>;
  currentUser: Observable<User | null>;

  constructor(private http: HttpClient) {
    const stored = sessionStorage.getItem('currentUser') || localStorage.getItem('currentUser');
    this.currentUserSubject = new BehaviorSubject<User | null>(
      stored ? JSON.parse(stored) : null
    );
    this.currentUser = this.currentUserSubject.asObservable();
  }

  get currentUserValue(): User | null {
    return this.currentUserSubject.value;
  }

  login(credentials: LoginRequest, rememberMe = true): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/login`, credentials).pipe(
      tap(r => this._storeSession(r, rememberMe))
    );
  }

  register(data: RegisterRequest): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/register`, data).pipe(
      tap(r => this._storeSession(r, true))
    );
  }

  refreshTokens(): Observable<AuthResponse> {
    const refreshToken = sessionStorage.getItem('refresh_token') || localStorage.getItem('refresh_token');
    const remember = !!localStorage.getItem('refresh_token');
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/refresh`, { refresh_token: refreshToken }).pipe(
      tap(r => this._storeSession(r, remember))
    );
  }

  logout(): void {
    const refreshToken = sessionStorage.getItem('refresh_token') || localStorage.getItem('refresh_token');
    if (refreshToken) {
      this.http.post(`${environment.apiUrl}/auth/logout`, { refresh_token: refreshToken }).subscribe();
    }
    ['access_token', 'refresh_token', 'currentUser'].forEach(k => {
      localStorage.removeItem(k);
      sessionStorage.removeItem(k);
    });
    this.currentUserSubject.next(null);
  }

  getToken(): string | null {
    return sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
  }

  isAuthenticated(): boolean {
    const token = this.getToken();
    if (!token) return false;
    try {
      const decoded: any = jwtDecode(token);
      return decoded.exp > Date.now() / 1000;
    } catch {
      return false;
    }
  }

  hasRole(role: string): boolean {
    return this.currentUserValue?.role === role;
  }

  updateProfile(data: { name?: string; phone?: string; city?: string; state?: string }): Observable<{ user: User; message: string }> {
    const remember = !!localStorage.getItem('access_token');
    return this.http.put<{ user: User; message: string }>(`${environment.apiUrl}/auth/profile`, data).pipe(
      tap(r => {
        const store = remember ? localStorage : sessionStorage;
        store.setItem('currentUser', JSON.stringify(r.user));
        this.currentUserSubject.next(r.user);
      })
    );
  }

  changePassword(currentPassword: string, newPassword: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${environment.apiUrl}/auth/change-password`, {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  private _storeSession(r: AuthResponse, remember: boolean): void {
    // Clear both storages to avoid stale tokens in the other one
    ['access_token', 'refresh_token', 'currentUser'].forEach(k => {
      localStorage.removeItem(k);
      sessionStorage.removeItem(k);
    });
    const store = remember ? localStorage : sessionStorage;
    store.setItem('access_token', r.access_token);
    store.setItem('refresh_token', r.refresh_token);
    store.setItem('currentUser', JSON.stringify(r.user));
    this.currentUserSubject.next(r.user);
  }
}
