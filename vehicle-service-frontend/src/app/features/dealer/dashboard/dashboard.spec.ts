import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError, BehaviorSubject } from 'rxjs';
import { DashboardComponent } from './dashboard';
import { AuthService } from '../../../core/services/auth';
import { BlockchainService } from '../../../core/services/blockchain.service';
import { ScManagementService, SCStats } from '../../../core/services/sc-management.service';

const MOCK_USER = { id: 1, email: 'sc@test.com', role: 'SERVICE_CENTER' as const, name: 'SC', blockchain_address: '0x1' };
const MOCK_STATS: SCStats = { services_submitted: 5, eth_balance: 1.5 };

function makeAuthSpy(user = MOCK_USER) {
  return { currentUserValue: user };
}

function makeBlockchainSpy(connected: boolean | null = true) {
  const subject = new BehaviorSubject<boolean | null>(connected);
  return { connected$: subject.asObservable() };
}

function makeScSpy(stats: SCStats | null = MOCK_STATS, fail = false) {
  return {
    getMyStats: vi.fn().mockReturnValue(
      fail ? throwError(() => new Error('Network error')) : of(stats!)
    ),
  };
}

async function setup(authSpy: any, blockchainSpy: any, scSpy: any) {
  await TestBed.configureTestingModule({
    imports: [DashboardComponent],
    providers: [
      provideRouter([]),
      { provide: AuthService,         useValue: authSpy },
      { provide: BlockchainService,   useValue: blockchainSpy },
      { provide: ScManagementService, useValue: scSpy },
    ],
  }).compileComponents();
}

describe('DealerDashboardComponent', () => {
  it('should create', async () => {
    await setup(makeAuthSpy(), makeBlockchainSpy(), makeScSpy());
    const fixture = TestBed.createComponent(DashboardComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('currentUser is set from AuthService on construction', async () => {
    await setup(makeAuthSpy(), makeBlockchainSpy(), makeScSpy());
    const fixture = TestBed.createComponent(DashboardComponent);
    expect(fixture.componentInstance.currentUser).toEqual(MOCK_USER);
  });

  it('stats are loaded on init and statsLoading becomes false', async () => {
    await setup(makeAuthSpy(), makeBlockchainSpy(), makeScSpy());
    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.componentInstance.ngOnInit();
    expect(fixture.componentInstance.statsLoading).toBe(false);
    expect(fixture.componentInstance.stats).toEqual(MOCK_STATS);
    expect(fixture.componentInstance.statsError).toBe(false);
  });

  it('statsError is true when getMyStats fails', async () => {
    await setup(makeAuthSpy(), makeBlockchainSpy(), makeScSpy(null, true));
    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.componentInstance.ngOnInit();
    expect(fixture.componentInstance.statsLoading).toBe(false);
    expect(fixture.componentInstance.statsError).toBe(true);
    expect(fixture.componentInstance.stats).toBeNull();
  });

  it('isConnected reflects blockchain connection status', async () => {
    await setup(makeAuthSpy(), makeBlockchainSpy(false), makeScSpy());
    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.componentInstance.ngOnInit();
    expect(fixture.componentInstance.isConnected).toBe(false);
  });

  it('isConnected updates when blockchain status changes', async () => {
    const subject = new BehaviorSubject<boolean | null>(false);
    await setup(makeAuthSpy(), { connected$: subject.asObservable() }, makeScSpy());
    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.componentInstance.ngOnInit();
    subject.next(true);
    expect(fixture.componentInstance.isConnected).toBe(true);
  });

  it('ngOnDestroy does not throw', async () => {
    await setup(makeAuthSpy(), makeBlockchainSpy(), makeScSpy());
    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.componentInstance.ngOnInit();
    expect(() => fixture.componentInstance.ngOnDestroy()).not.toThrow();
  });

  it('stats.services_submitted is a number when loaded', async () => {
    await setup(makeAuthSpy(), makeBlockchainSpy(), makeScSpy());
    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.componentInstance.ngOnInit();
    expect(typeof fixture.componentInstance.stats!.services_submitted).toBe('number');
  });
});
