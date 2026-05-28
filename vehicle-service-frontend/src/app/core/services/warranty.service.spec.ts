import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { WarrantyService } from './warranty';
import { environment } from '../../../environments/environment';

describe('WarrantyService', () => {
  let service: WarrantyService;
  let httpMock: HttpTestingController;
  const VIN = '1HGCM82633A004352';

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [WarrantyService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(WarrantyService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('checkWarranty hits GET /warranty/check/:vin', () => {
    service.checkWarranty(VIN).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/warranty/check/${VIN}`);
    expect(req.request.method).toBe('GET');
    req.flush({ vin: VIN, valid: true });
  });

  it('submitClaim posts to /warranty/submit-claim with correct body', () => {
    service.submitClaim(VIN, 'Engine noise', ['photo1.jpg']).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/warranty/submit-claim`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      vin: VIN,
      issue_description: 'Engine noise',
      photos: ['photo1.jpg'],
    });
    req.flush({ claim_hash: '0xabc' });
  });

  it('submitClaim sends empty photos array when omitted', () => {
    service.submitClaim(VIN, 'Noise').subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/warranty/submit-claim`);
    expect(req.request.body.photos).toEqual([]);
    req.flush({ claim_hash: '0xabc' });
  });

  it('getClaims hits GET /warranty/claims/:vin', () => {
    service.getClaims(VIN).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/warranty/claims/${VIN}`);
    expect(req.request.method).toBe('GET');
    req.flush({ vin: VIN, claims: [], count: 0 });
  });

  it('approveClaim posts to /warranty/approve-claim with correct body', () => {
    service.approveClaim(VIN, 2).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/warranty/approve-claim`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ vin: VIN, claim_index: 2 });
    req.flush({ message: 'approved' });
  });

  it('denyClaim posts to /warranty/deny-claim with vin, index and reason', () => {
    service.denyClaim(VIN, 1, 'Outside scope').subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/warranty/deny-claim`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ vin: VIN, claim_index: 1, reason: 'Outside scope' });
    req.flush({ message: 'denied' });
  });
});
