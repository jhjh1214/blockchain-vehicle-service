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
}