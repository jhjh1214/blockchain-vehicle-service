import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError, BehaviorSubject, Subject } from 'rxjs';
import { ManufacturerDashboardComponent } from './dashboard';
import { AuthService } from '../../../core/services/auth';
import { BlockchainService } from '../../../core/services/blockchain.service';
import { VehicleService, DashboardStats } from '../../../core/services/vehicle';
import { ThemeService } from '../../../core/services/theme.service';
import { ScManagementService } from '../../../core/services/sc-management.service';
import { ServiceService } from '../../../core/services/service';

const MOCK_USER = {
  id: 1, email: 'mfr@test.com',
  role: 'MANUFACTURER' as const,
  name: 'Honda Corp', blockchain_address: '0x1',
};

const MOCK_STATS: DashboardStats = {
  total_vehicles: 10,
  sc_total: 5,
  sc_active: 3,
  sc_pending: 2,
  warranty_claims: 1,
  active_warranties: 8,
  services_this_month: 4,
  service_type_distribution: { 'Oil Change': 2, 'Tire Rotation': 2 },
  warranty_claim_trend: [],
  top_service_centers: [],
  fleet_health_score: 75,
  manufacturer_eth_balance: 1.5,
};

const MOCK_STATS_NO_PENDING: DashboardStats = { ...MOCK_STATS, sc_pending: 0 };

function makeAuthSpy(user = MOCK_USER) {
  return { currentUserValue: user };
}

function makeBlockchainSpy(connected: boolean | null = true) {
  const subject = new BehaviorSubject<boolean | null>(connected);
  return { connected$: subject.asObservable() };
}

function makeVehicleSpy(stats: DashboardStats | null = MOCK_STATS, fail = false) {
  return {
    getDashboardStats: vi.fn().mockReturnValue(
      fail ? throwError(() => new Error('Network error')) : of(stats!)
    ),
    getManufacturerStats: vi.fn().mockReturnValue(of(stats!)),
    getActivityFeed: vi.fn().mockReturnValue(of({ feed: [] })),
    getFleetExport: vi.fn().mockReturnValue(of(new Blob())),
    getRecalls: vi.fn().mockReturnValue(of({ recalls: [] })),
  };
}

function makeThemeSpy(isDark = false) {
  const subject = new BehaviorSubject<boolean>(isDark);
  return { dark$: subject.asObservable(), isDark };
}

function makeScManagementSpy() {
  return {
    getEthRequests: vi.fn().mockReturnValue(of({ requests: [], count: 0 })),
  };
}

function makeServiceSpy() {
  return {
    getVoidRequestsManufacturer: vi.fn().mockReturnValue(of({ requests: [] })),
  };
}

async function setup(
  authSpy: any = makeAuthSpy(),
  blockchainSpy: any = makeBlockchainSpy(),
  vehicleSpy: any = makeVehicleSpy(),
  themeSpy: any = makeThemeSpy(),
  scSpy: any = makeScManagementSpy(),
  serviceSpy: any = makeServiceSpy(),
) {
  await TestBed.configureTestingModule({
    imports: [ManufacturerDashboardComponent],
    providers: [
      provideRouter([]),
      { provide: AuthService,      useValue: authSpy },
      { provide: BlockchainService, useValue: blockchainSpy },
      { provide: VehicleService,   useValue: vehicleSpy },
      { provide: ThemeService,     useValue: themeSpy },
      { provide: ScManagementService, useValue: scSpy },
      { provide: ServiceService,   useValue: serviceSpy },
    ],
  }).compileComponents();
}

describe('ManufacturerDashboardComponent', () => {
  it('should create', async () => {
    await setup();
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('currentUser is set from AuthService on construction', async () => {
    await setup();
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    expect(fixture.componentInstance.currentUser).toEqual(MOCK_USER);
  });

  it('stats are loaded on init and statsLoading becomes false', async () => {
    await setup();
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    fixture.componentInstance.ngOnInit();
    expect(fixture.componentInstance.statsLoading).toBe(false);
    expect(fixture.componentInstance.stats).toEqual(MOCK_STATS);
    expect(fixture.componentInstance.statsError).toBe(false);
  });

  it('statsError is true when getDashboardStats and getManufacturerStats both fail', async () => {
    const vehicleSpy = {
      ...makeVehicleSpy(),
      getDashboardStats:    vi.fn().mockReturnValue(throwError(() => new Error('fail'))),
      getManufacturerStats: vi.fn().mockReturnValue(throwError(() => new Error('fail'))),
    };
    await setup(makeAuthSpy(), makeBlockchainSpy(), vehicleSpy);
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    fixture.componentInstance.ngOnInit();
    expect(fixture.componentInstance.statsLoading).toBe(false);
    expect(fixture.componentInstance.statsError).toBe(true);
  });

  it('isConnected reflects blockchain connection status', async () => {
    await setup(makeAuthSpy(), makeBlockchainSpy(false));
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    fixture.componentInstance.ngOnInit();
    expect(fixture.componentInstance.isConnected).toBe(false);
  });

  it('isConnected updates when blockchain status changes', async () => {
    const subject = new BehaviorSubject<boolean | null>(false);
    await setup(makeAuthSpy(), { connected$: subject.asObservable() });
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    fixture.componentInstance.ngOnInit();
    subject.next(true);
    expect(fixture.componentInstance.isConnected).toBe(true);
  });

  it('ngOnDestroy does not throw', async () => {
    await setup();
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    fixture.componentInstance.ngOnInit();
    expect(() => fixture.componentInstance.ngOnDestroy()).not.toThrow();
  });

  // --- sc_pending / pending SC approval banner ---

  it('stats.sc_pending is a number when loaded', async () => {
    await setup();
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    fixture.componentInstance.ngOnInit();
    expect(typeof fixture.componentInstance.stats!.sc_pending).toBe('number');
  });

  it('stats.sc_pending is 2 from mock data', async () => {
    await setup();
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    fixture.componentInstance.ngOnInit();
    expect(fixture.componentInstance.stats!.sc_pending).toBe(2);
  });

  it('stats.sc_pending is 0 when no pending SCs', async () => {
    await setup(makeAuthSpy(), makeBlockchainSpy(), makeVehicleSpy(MOCK_STATS_NO_PENDING));
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    fixture.componentInstance.ngOnInit();
    expect(fixture.componentInstance.stats!.sc_pending).toBe(0);
  });

  it('banner condition: sc_pending > 0 is true when there are pending SCs', async () => {
    await setup();
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    fixture.componentInstance.ngOnInit();
    const stats = fixture.componentInstance.stats!;
    expect(stats.sc_pending > 0).toBe(true);
  });

  it('banner condition: sc_pending > 0 is false when there are no pending SCs', async () => {
    await setup(makeAuthSpy(), makeBlockchainSpy(), makeVehicleSpy(MOCK_STATS_NO_PENDING));
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    fixture.componentInstance.ngOnInit();
    const stats = fixture.componentInstance.stats!;
    expect(stats.sc_pending > 0).toBe(false);
  });

  it('stats.fleet_health_score is a number', async () => {
    await setup();
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    fixture.componentInstance.ngOnInit();
    expect(typeof fixture.componentInstance.stats!.fleet_health_score).toBe('number');
  });

  it('stats.manufacturer_eth_balance is a number or null', async () => {
    await setup();
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    fixture.componentInstance.ngOnInit();
    const bal = fixture.componentInstance.stats!.manufacturer_eth_balance;
    expect(bal === null || typeof bal === 'number').toBe(true);
  });

  it('refresh reloads stats', async () => {
    const vehicleSpy = makeVehicleSpy();
    await setup(makeAuthSpy(), makeBlockchainSpy(), vehicleSpy);
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    fixture.componentInstance.ngOnInit();
    fixture.componentInstance.refresh();
    expect(vehicleSpy.getDashboardStats).toHaveBeenCalledTimes(2);
  });

  it('activityIcon returns a path string for known types', async () => {
    await setup();
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    expect(fixture.componentInstance.activityIcon('registration')).toContain('M');
    expect(fixture.componentInstance.activityIcon('warranty_claim')).toContain('M');
    expect(fixture.componentInstance.activityIcon('dispute')).toContain('M');
  });

  it('activityLabel returns expected labels', async () => {
    await setup();
    const { activityLabel } = TestBed.createComponent(ManufacturerDashboardComponent).componentInstance;
    expect(activityLabel('registration')).toBe('Vehicle Registered');
    expect(activityLabel('warranty_claim')).toBe('Warranty Claim');
    expect(activityLabel('other')).toBe('Service Disputed');
  });

  it('formatActivityTime returns "just now" for recent timestamps', async () => {
    await setup();
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    const now = new Date().toISOString();
    expect(fixture.componentInstance.formatActivityTime(now)).toBe('just now');
  });

  it('formatActivityTime returns "—" for null', async () => {
    await setup();
    const fixture = TestBed.createComponent(ManufacturerDashboardComponent);
    expect(fixture.componentInstance.formatActivityTime(null)).toBe('—');
  });
});
