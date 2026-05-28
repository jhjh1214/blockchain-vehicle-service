import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { ServiceService } from './service';
import { environment } from '../../../environments/environment';

describe('ServiceService', () => {
  let service: ServiceService;
  let httpMock: HttpTestingController;
  const VIN = '1HGCM82633A004352';

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ServiceService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ServiceService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('submitService posts to /service/submit', () => {
    const data = { vin: VIN, service_type: 'Oil Change', service_date: '2024-01-01', mileage: 5000 };
    service.submitService(data).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/service/submit`);
    expect(req.request.method).toBe('POST');
    req.flush({ metadata_hash: '0xabc' });
  });

  it('verifyService posts to /service/verify', () => {
    service.verifyService({ vin: VIN, record_index: 0 }).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/service/verify`);
    expect(req.request.method).toBe('POST');
    req.flush({ message: 'verified' });
  });

  it('disputeService posts to /service/dispute', () => {
    service.disputeService({ vin: VIN, record_index: 0, reason: 'Incorrect' }).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/service/dispute`);
    expect(req.request.method).toBe('POST');
    req.flush({ message: 'disputed' });
  });

  it('getPendingServices hits GET /service/pending/:vin', () => {
    service.getPendingServices(VIN).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/service/pending/${VIN}`);
    expect(req.request.method).toBe('GET');
    req.flush({ vin: VIN, pending_services: [], count: 0 });
  });

  it('getServiceHistory hits GET /service/history/:vin', () => {
    service.getServiceHistory(VIN).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/service/history/${VIN}`);
    expect(req.request.method).toBe('GET');
    req.flush({ vin: VIN, service_history: [], count: 0 });
  });

  it('resolveDispute posts to /service/resolve-dispute with correct body', () => {
    service.resolveDispute(VIN, 2, 1, 'Approved after review').subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/service/resolve-dispute`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      vin: VIN,
      record_index: 2,
      decision: 1,
      resolution_notes: 'Approved after review',
    });
    req.flush({ decision: 'approved' });
  });

  it('submitDisputeResponse posts to /service/dispute-response', () => {
    service.submitDisputeResponse(VIN, '0xhash', 'We checked the car').subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/service/dispute-response`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      vin: VIN,
      metadata_hash: '0xhash',
      rebuttal_notes: 'We checked the car',
    });
    req.flush({ message: 'ok' });
  });
});
