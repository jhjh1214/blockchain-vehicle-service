import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface ServiceCenter {
  id: number;
  email: string;
  name: string;
  phone: string;
  city: string;
  state: string;
  status: 'active' | 'pending' | 'suspended';
  blockchain_address: string;
  eth_balance: number | null;
  created_at: string;
}

export interface SCListResponse {
  items: ServiceCenter[];
  pagination: { page: number; limit: number; total: number; pages: number };
}

export interface FundResult {
  message: string;
  new_balance?: number;
  results?: { id: number; name: string; status: string; error?: string }[];
}

@Injectable({ providedIn: 'root' })
export class ScManagementService {
  private base = `${environment.apiUrl}/sc`;

  constructor(private http: HttpClient) {}

  getServiceCenters(filters: {
    city?: string; state?: string; status?: string; search?: string;
    page?: number; limit?: number;
  } = {}): Observable<SCListResponse> {
    let params = new HttpParams();
    if (filters.city)   params = params.set('city',   filters.city);
    if (filters.state)  params = params.set('state',  filters.state);
    if (filters.status) params = params.set('status', filters.status);
    if (filters.search) params = params.set('search', filters.search);
    if (filters.page)   params = params.set('page',   filters.page.toString());
    if (filters.limit)  params = params.set('limit',  filters.limit.toString());
    return this.http.get<SCListResponse>(`${this.base}/service-centers`, { params });
  }

  getServiceCenter(id: number): Observable<ServiceCenter> {
    return this.http.get<ServiceCenter>(`${this.base}/service-centers/${id}`);
  }

  activate(id: number): Observable<{ message: string; sc: ServiceCenter }> {
    return this.http.post<{ message: string; sc: ServiceCenter }>(
      `${this.base}/service-centers/${id}/activate`, {}
    );
  }

  suspend(id: number): Observable<{ message: string; sc: ServiceCenter }> {
    return this.http.post<{ message: string; sc: ServiceCenter }>(
      `${this.base}/service-centers/${id}/suspend`, {}
    );
  }

  fund(id: number, amountEth: number): Observable<FundResult> {
    return this.http.post<FundResult>(
      `${this.base}/service-centers/${id}/fund`, { amount_eth: amountEth }
    );
  }

  fundAll(amountEth: number): Observable<FundResult> {
    return this.http.post<FundResult>(`${this.base}/fund-all`, { amount_eth: amountEth });
  }
}
