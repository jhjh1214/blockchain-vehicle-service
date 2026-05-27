import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Vehicle, RegisterVehicleRequest, MyVehicle } from '../models/vehicle.model';

@Injectable({
  providedIn: 'root'
})
export class VehicleService {
  constructor(private http: HttpClient) { }

  registerVehicle(data: RegisterVehicleRequest): Observable<any> {
    return this.http.post(`${environment.apiUrl}/vehicle/register`, data);
  }

  getVehicle(vin: string): Observable<Vehicle> {
    return this.http.get<Vehicle>(`${environment.apiUrl}/vehicle/${vin}`);
  }

  getMyVehicles(): Observable<{ vehicles: MyVehicle[], count: number }> {
    return this.http.get<{ vehicles: MyVehicle[], count: number }>(`${environment.apiUrl}/vehicle/my-vehicles`);
  }

  transferVehicle(vin: string, newOwnerEmail: string): Observable<any> {
    return this.http.post(`${environment.apiUrl}/vehicle/transfer`, {
      vin,
      new_owner_email: newOwnerEmail
    });
  }

  getFleet(page = 1, limit = 20): Observable<any> {
    return this.http.get(`${environment.apiUrl}/vehicle/fleet?page=${page}&limit=${limit}`);
  }

  getManufacturerStats(): Observable<ManufacturerStats> {
    return this.http.get<ManufacturerStats>(`${environment.apiUrl}/vehicle/stats`);
  }

  getDashboardStats(): Observable<DashboardStats> {
    return this.http.get<DashboardStats>(`${environment.apiUrl}/vehicle/dashboard-stats`);
  }

  getPublicVehicle(vin: string): Observable<any> {
    return this.http.get(`${environment.apiUrl}/vehicle/public/${vin}`);
  }

  getActivityFeed(): Observable<{ feed: ActivityItem[] }> {
    return this.http.get<{ feed: ActivityItem[] }>(`${environment.apiUrl}/vehicle/activity-feed`);
  }
}

export interface ManufacturerStats {
  total_vehicles: number;
  sc_total: number;
  sc_active: number;
  sc_pending: number;
  warranty_claims: number;
}

export interface ClaimTrendPoint { month: string; count: number; }
export interface TopSC { label: string; address: string; submissions: number; disputed: number; dispute_rate: number; flagged: boolean; }

export interface DashboardStats extends ManufacturerStats {
  active_warranties: number;
  services_this_month: number;
  service_type_distribution: Record<string, number>;
  warranty_claim_trend: ClaimTrendPoint[];
  top_service_centers: TopSC[];
}

export interface ActivityItem {
  type: 'registration' | 'warranty_claim' | 'dispute';
  vin: string;
  description: string;
  timestamp: string | null;
}