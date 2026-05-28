import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { VehicleService } from './vehicle';
import { environment } from '../../../environments/environment';

describe('VehicleService', () => {
  let service: VehicleService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [VehicleService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(VehicleService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('registerVehicle posts to /vehicle/register', () => {
    const payload = { vin: 'TEST', warranty_years: 3, make: 'Honda', model: 'Civic', year: 2024 };
    service.registerVehicle(payload).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/vehicle/register`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(payload);
    req.flush({ vin: 'TEST' });
  });

  it('getVehicle hits /vehicle/:vin', () => {
    service.getVehicle('1HGCM82633A004352').subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/vehicle/1HGCM82633A004352`);
    expect(req.request.method).toBe('GET');
    req.flush({ vin: '1HGCM82633A004352' });
  });

  it('getMyVehicles hits /vehicle/owner/vehicles (not /my-vehicles)', () => {
    service.getMyVehicles().subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/vehicle/owner/vehicles`);
    expect(req.request.method).toBe('GET');
    req.flush({ vehicles: [], count: 0 });
  });

  it('transferVehicle posts to /vehicle/transfer with correct body', () => {
    service.transferVehicle('VIN123', 'owner@example.com').subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/vehicle/transfer`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ vin: 'VIN123', new_owner_email: 'owner@example.com' });
    req.flush({ message: 'ok' });
  });

  it('getFleet hits /vehicle/fleet with default pagination', () => {
    service.getFleet().subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/vehicle/fleet?page=1&limit=20`);
    expect(req.request.method).toBe('GET');
    req.flush({ vehicles: [], pagination: {} });
  });

  it('getFleet respects custom page and limit', () => {
    service.getFleet(2, 10).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/vehicle/fleet?page=2&limit=10`);
    expect(req.request.method).toBe('GET');
    req.flush({ vehicles: [], pagination: {} });
  });

  it('getManufacturerStats hits /vehicle/stats', () => {
    service.getManufacturerStats().subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/vehicle/stats`);
    expect(req.request.method).toBe('GET');
    req.flush({ total_vehicles: 0 });
  });

  it('getDashboardStats hits /vehicle/dashboard-stats', () => {
    service.getDashboardStats().subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/vehicle/dashboard-stats`);
    expect(req.request.method).toBe('GET');
    req.flush({ total_vehicles: 0, fleet_health_score: 0 });
  });

  it('getPublicVehicle hits /vehicle/public/:vin', () => {
    service.getPublicVehicle('1HGCM82633A004352').subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/vehicle/public/1HGCM82633A004352`);
    expect(req.request.method).toBe('GET');
    req.flush({ vin: '1HGCM82633A004352' });
  });

  it('getActivityFeed hits /vehicle/activity-feed', () => {
    service.getActivityFeed().subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/vehicle/activity-feed`);
    expect(req.request.method).toBe('GET');
    req.flush({ feed: [] });
  });
});
