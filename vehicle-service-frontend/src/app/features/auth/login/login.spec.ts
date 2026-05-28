import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { of, throwError, BehaviorSubject } from 'rxjs';
import { LoginComponent } from './login';
import { AuthService } from '../../../core/services/auth';
import { BlockchainService } from '../../../core/services/blockchain.service';

const MANUFACTURER_USER = { id: 1, email: 'mfr@test.com', role: 'MANUFACTURER' as const, name: 'Mfr', blockchain_address: '0x1' };
const SC_USER            = { id: 2, email: 'sc@test.com',  role: 'SERVICE_CENTER' as const, name: 'SC', blockchain_address: '0x2' };
const OWNER_USER         = { id: 3, email: 'own@test.com', role: 'OWNER' as const, name: 'Own', blockchain_address: '0x3' };

function makeBlockchainSpy() {
  const subject = new BehaviorSubject<boolean | null>(null);
  return { connected$: subject.asObservable() };
}

function makeAuthSpy(user: any = null) {
  return {
    currentUserValue: user,
    login: vi.fn().mockReturnValue(of({ access_token: 'tok', refresh_token: 'ref', user })),
    logout: vi.fn(),
    hasRole: (r: string) => user?.role === r,
  };
}

describe('LoginComponent', () => {
  async function setup(authSpy: any) {
    await TestBed.configureTestingModule({
      imports: [LoginComponent, ReactiveFormsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([
          { path: 'manufacturer/dashboard', component: LoginComponent },
          { path: 'dealer/dashboard',       component: LoginComponent },
        ]),
        { provide: AuthService,       useValue: authSpy },
        { provide: BlockchainService, useValue: makeBlockchainSpy() },
      ],
    }).compileComponents();
    const router = TestBed.inject(Router);
    await router.initialNavigation();
    return router;
  }

  it('should create', async () => {
    await setup(makeAuthSpy(null));
    const fixture = TestBed.createComponent(LoginComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('redirects MANUFACTURER to /manufacturer/dashboard on construction', async () => {
    const authSpy = makeAuthSpy(MANUFACTURER_USER);
    const router = await setup(authSpy);
    const navSpy = vi.spyOn(router, 'navigate');
    TestBed.createComponent(LoginComponent);
    expect(navSpy).toHaveBeenCalledWith(['/manufacturer/dashboard']);
  });

  it('redirects SERVICE_CENTER to /dealer/dashboard on construction', async () => {
    const authSpy = makeAuthSpy(SC_USER);
    const router = await setup(authSpy);
    const navSpy = vi.spyOn(router, 'navigate');
    TestBed.createComponent(LoginComponent);
    expect(navSpy).toHaveBeenCalledWith(['/dealer/dashboard']);
  });

  it('does not redirect when no user is logged in', async () => {
    const router = await setup(makeAuthSpy(null));
    const navSpy = vi.spyOn(router, 'navigate');
    TestBed.createComponent(LoginComponent);
    expect(navSpy).not.toHaveBeenCalled();
  });

  it('form is invalid when empty', async () => {
    await setup(makeAuthSpy(null));
    const fixture = TestBed.createComponent(LoginComponent);
    expect(fixture.componentInstance.loginForm.invalid).toBe(true);
  });

  it('form is valid with email and password', async () => {
    await setup(makeAuthSpy(null));
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.componentInstance.loginForm.setValue({ email: 'a@b.com', password: 'pass123', rememberMe: true });
    expect(fixture.componentInstance.loginForm.valid).toBe(true);
  });

  it('login success for MANUFACTURER navigates to /manufacturer/dashboard', async () => {
    const authSpy = makeAuthSpy(null);
    authSpy.login = vi.fn().mockReturnValue(
      of({ access_token: 'tok', refresh_token: 'ref', user: MANUFACTURER_USER })
    );
    const router = await setup(authSpy);
    const navSpy = vi.spyOn(router, 'navigate');
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.componentInstance.loginForm.setValue({ email: 'mfr@test.com', password: 'pass', rememberMe: true });
    fixture.componentInstance.onSubmit();
    expect(navSpy).toHaveBeenCalledWith(['/manufacturer/dashboard']);
  });

  it('login success for SERVICE_CENTER navigates to /dealer/dashboard', async () => {
    const authSpy = makeAuthSpy(null);
    authSpy.login = vi.fn().mockReturnValue(
      of({ access_token: 'tok', refresh_token: 'ref', user: SC_USER })
    );
    const router = await setup(authSpy);
    const navSpy = vi.spyOn(router, 'navigate');
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.componentInstance.loginForm.setValue({ email: 'sc@test.com', password: 'pass', rememberMe: true });
    fixture.componentInstance.onSubmit();
    expect(navSpy).toHaveBeenCalledWith(['/dealer/dashboard']);
  });

  it('OWNER login sets error message directing to mobile app', async () => {
    const authSpy = makeAuthSpy(null);
    authSpy.login = vi.fn().mockReturnValue(
      of({ access_token: 'tok', refresh_token: 'ref', user: OWNER_USER })
    );
    await setup(authSpy);
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.componentInstance.loginForm.setValue({ email: 'own@test.com', password: 'pass', rememberMe: true });
    fixture.componentInstance.onSubmit();
    expect(fixture.componentInstance.error).toContain('mobile app');
    expect(authSpy.logout).toHaveBeenCalled();
  });

  it('login error sets error message', async () => {
    const authSpy = makeAuthSpy(null);
    authSpy.login = vi.fn().mockReturnValue(
      throwError(() => ({ status: 401, error: { error: 'Invalid credentials' } }))
    );
    await setup(authSpy);
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.componentInstance.loginForm.setValue({ email: 'a@b.com', password: 'wrong', rememberMe: true });
    fixture.componentInstance.onSubmit();
    expect(fixture.componentInstance.error).toBe('Invalid credentials');
  });

  it('lockout error (423) sets lockoutMessage', async () => {
    const authSpy = makeAuthSpy(null);
    authSpy.login = vi.fn().mockReturnValue(
      throwError(() => ({ status: 423, error: { error: 'Account locked' } }))
    );
    await setup(authSpy);
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.componentInstance.loginForm.setValue({ email: 'a@b.com', password: 'pass', rememberMe: true });
    fixture.componentInstance.onSubmit();
    expect(fixture.componentInstance.lockoutMessage).toBe('Account locked');
    expect(fixture.componentInstance.error).toBe('');
  });

  it('onSubmit does nothing when form is invalid', async () => {
    const authSpy = makeAuthSpy(null);
    await setup(authSpy);
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.componentInstance.onSubmit();
    expect(authSpy.login).not.toHaveBeenCalled();
  });
});
