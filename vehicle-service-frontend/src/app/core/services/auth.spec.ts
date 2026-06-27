import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { AuthService } from './auth';
import { environment } from '../../../environments/environment';

const MOCK_USER = { id: 1, email: 'test@example.com', role: 'MANUFACTURER', name: 'Test', blockchain_address: '0x1' };
const MOCK_RESPONSE = { access_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjo5OTk5OTk5OTk5fQ.mock', refresh_token: 'refresh123', user: MOCK_USER };

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();

    TestBed.configureTestingModule({
      providers: [AuthService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    sessionStorage.clear();
    localStorage.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('currentUserValue is null when no stored session', () => {
    expect(service.currentUserValue).toBeNull();
  });

  it('isAuthenticated returns false when no token', () => {
    expect(service.isAuthenticated()).toBe(false);
  });

  it('getToken returns null when nothing stored', () => {
    expect(service.getToken()).toBeNull();
  });

  it('login posts to correct URL', () => {
    service.login({ email: 'a@b.com', password: 'pass' }).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/auth/login`);
    expect(req.request.method).toBe('POST');
    req.flush(MOCK_RESPONSE);
  });

  it('login stores tokens in localStorage when rememberMe=true', () => {
    service.login({ email: 'a@b.com', password: 'pass' }, true).subscribe();
    httpMock.expectOne(`${environment.apiUrl}/auth/login`).flush(MOCK_RESPONSE);
    expect(localStorage.getItem('access_token')).toBe(MOCK_RESPONSE.access_token);
    expect(localStorage.getItem('refresh_token')).toBe(MOCK_RESPONSE.refresh_token);
  });

  it('login stores tokens in sessionStorage when rememberMe=false', () => {
    service.login({ email: 'a@b.com', password: 'pass' }, false).subscribe();
    httpMock.expectOne(`${environment.apiUrl}/auth/login`).flush(MOCK_RESPONSE);
    expect(sessionStorage.getItem('access_token')).toBe(MOCK_RESPONSE.access_token);
    expect(localStorage.getItem('access_token')).toBeNull();
  });

  it('login updates currentUserValue', () => {
    service.login({ email: 'a@b.com', password: 'pass' }).subscribe();
    httpMock.expectOne(`${environment.apiUrl}/auth/login`).flush(MOCK_RESPONSE);
    expect(service.currentUserValue).toEqual(MOCK_USER);
  });

  it('logout clears all stored tokens', () => {
    localStorage.setItem('access_token', 'tok');
    localStorage.setItem('refresh_token', 'ref');
    service.logout();
    // logout fires a POST but we don't need to flush it for the storage assertions
    httpMock.expectOne(`${environment.apiUrl}/auth/logout`).flush({});
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  it('logout sets currentUserValue to null', () => {
    service.login({ email: 'a@b.com', password: 'pass' }).subscribe();
    httpMock.expectOne(`${environment.apiUrl}/auth/login`).flush(MOCK_RESPONSE);
    service.logout();
    httpMock.expectOne(`${environment.apiUrl}/auth/logout`).flush({});
    expect(service.currentUserValue).toBeNull();
  });

  it('hasRole returns true for matching role', () => {
    service.login({ email: 'a@b.com', password: 'pass' }).subscribe();
    httpMock.expectOne(`${environment.apiUrl}/auth/login`).flush(MOCK_RESPONSE);
    expect(service.hasRole('MANUFACTURER')).toBe(true);
  });

  it('hasRole returns false for non-matching role', () => {
    service.login({ email: 'a@b.com', password: 'pass' }).subscribe();
    httpMock.expectOne(`${environment.apiUrl}/auth/login`).flush(MOCK_RESPONSE);
    expect(service.hasRole('OWNER')).toBe(false);
  });

  it('hasRole returns false when not logged in', () => {
    expect(service.hasRole('MANUFACTURER')).toBe(false);
  });

  it('register posts to correct URL', () => {
    service.register({ email: 'a@b.com', password: 'pass', role: 'MANUFACTURER' }).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/auth/register`);
    expect(req.request.method).toBe('POST');
    req.flush(MOCK_RESPONSE);
  });

  it('refreshTokens posts to correct URL', () => {
    sessionStorage.setItem('refresh_token', 'old-refresh');
    service.refreshTokens().subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/auth/refresh`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body.refresh_token).toBe('old-refresh');
    req.flush(MOCK_RESPONSE);
  });

  it('changePassword posts to correct URL with correct body', () => {
    service.changePassword('old', 'new123!').subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/auth/change-password`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body.current_password).toBe('old');
    expect(req.request.body.new_password).toBe('new123!');
    req.flush({ message: 'ok' });
  });

  describe('cross-tab session guard', () => {
    // The auth cookie is shared across every tab of this browser. If a different
    // account logs in (or out) in another tab, this tab's cookie silently swaps
    // too, even though it still renders the old account's UI — these guard
    // against that by reloading the moment the mismatch is detected.
    let reloadSpy: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      reloadSpy = vi.fn();
      vi.stubGlobal('location', { ...window.location, reload: reloadSpy });
    });

    afterEach(() => {
      vi.unstubAllGlobals();
    });

    it('reloads when another tab logs in as a different user (storage event)', () => {
      sessionStorage.setItem('currentUser', JSON.stringify(MOCK_USER));
      const otherUser = { ...MOCK_USER, id: 999, email: 'other@example.com' };
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'currentUser',
        newValue: JSON.stringify(otherUser),
      }));
      expect(reloadSpy).toHaveBeenCalled();
      expect(sessionStorage.getItem('currentUser')).toBeNull();
    });

    it('does not reload when the storage event is for the same user', () => {
      service.login({ email: 'a@b.com', password: 'pass' }).subscribe();
      httpMock.expectOne(`${environment.apiUrl}/auth/login`).flush(MOCK_RESPONSE);
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'currentUser',
        newValue: JSON.stringify(MOCK_USER),
      }));
      expect(reloadSpy).not.toHaveBeenCalled();
    });

    it('ignores storage events for unrelated keys', () => {
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'some_other_key',
        newValue: 'whatever',
      }));
      expect(reloadSpy).not.toHaveBeenCalled();
    });
  });
});
