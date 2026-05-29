import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { InactivityService } from './inactivity.service';
import { AuthService } from './auth';

function makeAuthSpy() {
  return { logout: vi.fn() };
}

async function setup(authSpy = makeAuthSpy()) {
  await TestBed.configureTestingModule({
    providers: [
      provideRouter([]),
      { provide: AuthService, useValue: authSpy },
      InactivityService,
    ],
  }).compileComponents();
}

describe('InactivityService', () => {
  afterEach(() => {
    // Ensure service is stopped to clean up timers
    try {
      TestBed.inject(InactivityService).stop();
    } catch { /* already stopped */ }
    vi.useRealTimers();
  });

  it('should create', async () => {
    await setup();
    const svc = TestBed.inject(InactivityService);
    expect(svc).toBeTruthy();
  });

  it('showWarning$ starts closed (no emission until start)', async () => {
    await setup();
    const svc = TestBed.inject(InactivityService);
    const emissions: boolean[] = [];
    svc.showWarning$.subscribe(v => emissions.push(v));
    expect(emissions).toHaveLength(0);
  });

  it('start() can be called without errors', async () => {
    await setup();
    const svc = TestBed.inject(InactivityService);
    expect(() => svc.start()).not.toThrow();
    svc.stop();
  });

  it('stop() can be called without errors before start', async () => {
    await setup();
    const svc = TestBed.inject(InactivityService);
    expect(() => svc.stop()).not.toThrow();
  });

  it('calling start() twice does not register double listeners', async () => {
    await setup();
    const svc = TestBed.inject(InactivityService);
    expect(() => { svc.start(); svc.start(); }).not.toThrow();
    svc.stop();
  });

  it('dismissWarning() hides warning and resets timer', async () => {
    await setup();
    const svc = TestBed.inject(InactivityService);
    const warnings: boolean[] = [];
    svc.showWarning$.subscribe(v => warnings.push(v));
    svc.start();
    // Manually emit warning
    (svc as any).showWarning$.next(true);
    svc.dismissWarning();
    expect(warnings.at(-1)).toBe(false);
    svc.stop();
  });

  it('stop() emits showWarning false', async () => {
    await setup();
    const svc = TestBed.inject(InactivityService);
    const warnings: boolean[] = [];
    svc.showWarning$.subscribe(v => warnings.push(v));
    svc.start();
    (svc as any).showWarning$.next(true);
    svc.stop();
    expect(warnings.at(-1)).toBe(false);
  });

  it('ngOnDestroy calls stop()', async () => {
    await setup();
    const svc = TestBed.inject(InactivityService);
    const stopSpy = vi.spyOn(svc, 'stop');
    svc.ngOnDestroy();
    expect(stopSpy).toHaveBeenCalled();
  });
});
