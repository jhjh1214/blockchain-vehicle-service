import { TestBed } from '@angular/core/testing';
import { provideRouter, Router, ActivatedRoute } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { ResetPasswordComponent } from './reset-password';
import { environment } from '../../../../environments/environment';

function makeActivatedRoute(token: string | null) {
  return {
    snapshot: {
      queryParamMap: {
        get: (key: string) => (key === 'token' ? token : null),
      },
    },
  };
}

async function setup(token: string | null = 'valid-reset-token') {
  await TestBed.configureTestingModule({
    imports: [ResetPasswordComponent, ReactiveFormsModule],
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      provideRouter([{ path: 'login', component: ResetPasswordComponent }]),
      { provide: ActivatedRoute, useValue: makeActivatedRoute(token) },
    ],
  }).compileComponents();
}

describe('ResetPasswordComponent', () => {
  it('should create', async () => {
    await setup();
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('reads token from query params on ngOnInit', async () => {
    await setup('my-secret-token');
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    fixture.componentInstance.ngOnInit();
    expect(fixture.componentInstance.token).toBe('my-secret-token');
  });

  it('sets error message when token is missing', async () => {
    await setup(null);
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    fixture.componentInstance.ngOnInit();
    expect(fixture.componentInstance.error).toBeTruthy();
    expect(fixture.componentInstance.token).toBe('');
  });

  it('form is invalid when empty', async () => {
    await setup();
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    fixture.componentInstance.ngOnInit();
    expect(fixture.componentInstance.form.invalid).toBe(true);
  });

  it('form is invalid when passwords do not match', async () => {
    await setup();
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    fixture.componentInstance.ngOnInit();
    fixture.componentInstance.form.setValue({
      new_password: 'Password123!',
      confirm_password: 'Different123!',
    });
    expect(fixture.componentInstance.form.hasError('mismatch')).toBe(true);
  });

  it('form is valid when passwords match and meet min length', async () => {
    await setup();
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    fixture.componentInstance.ngOnInit();
    fixture.componentInstance.form.setValue({
      new_password: 'Password123!',
      confirm_password: 'Password123!',
    });
    expect(fixture.componentInstance.form.valid).toBe(true);
  });

  it('form is invalid when new_password is too short', async () => {
    await setup();
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    fixture.componentInstance.ngOnInit();
    fixture.componentInstance.form.setValue({
      new_password: 'short',
      confirm_password: 'short',
    });
    expect(fixture.componentInstance.f['new_password'].hasError('minlength')).toBe(true);
  });

  it('does not submit when form is invalid', async () => {
    await setup();
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    fixture.componentInstance.ngOnInit();
    // form is empty / invalid
    fixture.componentInstance.onSubmit();
    expect(fixture.componentInstance.loading).toBe(false);
    expect(fixture.componentInstance.done).toBe(false);
  });

  it('does not submit when token is missing', async () => {
    await setup(null);
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    fixture.componentInstance.ngOnInit();
    fixture.componentInstance.form.setValue({
      new_password: 'Password123!',
      confirm_password: 'Password123!',
    });
    fixture.componentInstance.onSubmit();
    expect(fixture.componentInstance.loading).toBe(false);
  });

  it('sets done=true and loading=false on successful reset', async () => {
    await setup('valid-token');
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    fixture.componentInstance.ngOnInit();
    fixture.componentInstance.form.setValue({
      new_password: 'NewPass123!',
      confirm_password: 'NewPass123!',
    });

    const http = TestBed.inject(HttpTestingController);
    fixture.componentInstance.onSubmit();

    const req = http.expectOne(`${environment.apiUrl}/auth/reset-password`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ token: 'valid-token', new_password: 'NewPass123!' });
    req.flush({ message: 'Password reset successfully.' });

    expect(fixture.componentInstance.done).toBe(true);
    expect(fixture.componentInstance.loading).toBe(false);
    http.verify();
  });

  it('sets error and loading=false on failed reset', async () => {
    await setup('valid-token');
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    fixture.componentInstance.ngOnInit();
    fixture.componentInstance.form.setValue({
      new_password: 'NewPass123!',
      confirm_password: 'NewPass123!',
    });

    const http = TestBed.inject(HttpTestingController);
    fixture.componentInstance.onSubmit();

    const req = http.expectOne(`${environment.apiUrl}/auth/reset-password`);
    req.flush({ error: 'Invalid or expired reset link.' }, { status: 400, statusText: 'Bad Request' });

    expect(fixture.componentInstance.done).toBe(false);
    expect(fixture.componentInstance.loading).toBe(false);
    expect(fixture.componentInstance.error).toBeTruthy();
    http.verify();
  });

  it('shows generic error message when server returns no error field', async () => {
    await setup('valid-token');
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    fixture.componentInstance.ngOnInit();
    fixture.componentInstance.form.setValue({
      new_password: 'NewPass123!',
      confirm_password: 'NewPass123!',
    });

    const http = TestBed.inject(HttpTestingController);
    fixture.componentInstance.onSubmit();

    const req = http.expectOne(`${environment.apiUrl}/auth/reset-password`);
    req.flush({}, { status: 500, statusText: 'Internal Server Error' });

    expect(fixture.componentInstance.error).toBe('Something went wrong. Please try again.');
    http.verify();
  });

  it('goToLogin navigates to /login', async () => {
    await setup();
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    const router = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    fixture.componentInstance.goToLogin();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });

  it('showPw is false by default', async () => {
    await setup();
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    expect(fixture.componentInstance.showPw).toBe(false);
  });

  it('loading is false by default', async () => {
    await setup();
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    expect(fixture.componentInstance.loading).toBe(false);
  });

  it('done is false by default', async () => {
    await setup();
    const fixture = TestBed.createComponent(ResetPasswordComponent);
    expect(fixture.componentInstance.done).toBe(false);
  });
});
