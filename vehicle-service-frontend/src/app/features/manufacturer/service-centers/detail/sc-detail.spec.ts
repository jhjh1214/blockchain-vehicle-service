import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of, Subject } from 'rxjs';
import { ScDetailComponent } from './sc-detail';
import { ScManagementService, ServiceCenter } from '../../../../core/services/sc-management.service';

const PENDING_SC: ServiceCenter = {
  id: 5, email: 'sc@test.com', name: 'Pending Workshop', phone: '0123456789',
  city: 'KL', state: 'Selangor', status: 'pending',
  blockchain_address: '0x' + '9'.repeat(40), eth_balance: 0.01,
  created_at: new Date().toISOString(),
};

function makeScSpy(sc: ServiceCenter = PENDING_SC) {
  return {
    getServiceCenter: vi.fn().mockReturnValue(of(sc)),
    activate: vi.fn(),
    suspend: vi.fn(),
    fund: vi.fn(),
  };
}

async function setup(scSpy: any = makeScSpy()) {
  await TestBed.configureTestingModule({
    imports: [ScDetailComponent],
    providers: [
      { provide: ScManagementService, useValue: scSpy },
      {
        provide: ActivatedRoute,
        useValue: { snapshot: { paramMap: convertToParamMap({ id: '5' }) } },
      },
    ],
  }).compileComponents();
  const fixture = TestBed.createComponent(ScDetailComponent);
  fixture.componentInstance.ngOnInit();
  return fixture.componentInstance;
}

describe('ScDetailComponent', () => {
  it('loads the service centre on init', async () => {
    const cmp = await setup();
    expect(cmp.sc).toEqual(PENDING_SC);
    expect(cmp.loading).toBe(false);
  });

  it('fund() does not toggle actionLoading — only its own fundLoading flag', async () => {
    const fundSubject = new Subject<any>();
    const scSpy = makeScSpy();
    scSpy.fund.mockReturnValue(fundSubject.asObservable());
    const cmp = await setup(scSpy);

    cmp.fund();
    expect(cmp.fundLoading).toBe(true);
    expect(cmp.actionLoading).toBe(false);

    fundSubject.next({ message: 'Sent 0.5 ETH', new_balance: 0.51 });
    expect(cmp.fundLoading).toBe(false);
  });

  it('activate() does not toggle fundLoading — only its own actionLoading flag', async () => {
    const activateSubject = new Subject<any>();
    const scSpy = makeScSpy();
    scSpy.activate.mockReturnValue(activateSubject.asObservable());
    const cmp = await setup(scSpy);

    cmp.activate();
    expect(cmp.actionLoading).toBe(true);
    expect(cmp.fundLoading).toBe(false);

    activateSubject.next({ message: 'Activated', sc: { ...PENDING_SC, status: 'active' } });
    expect(cmp.actionLoading).toBe(false);
  });

  it('regression: fund panel stays usable while an activate request is still in flight', async () => {
    // Previously both actions shared a single `actionLoading` flag, so opening the
    // fund panel while activate() was still pending disabled the Send button and
    // collapsed its label to just a bare spinner.
    const activateSubject = new Subject<any>();
    const scSpy = makeScSpy();
    scSpy.activate.mockReturnValue(activateSubject.asObservable());
    const cmp = await setup(scSpy);

    cmp.activate();
    expect(cmp.actionLoading).toBe(true);

    cmp.showFundPanel = true;
    expect(cmp.fundLoading).toBe(false);
    expect(cmp.fundAmount).toBe(0.5);
  });
});
