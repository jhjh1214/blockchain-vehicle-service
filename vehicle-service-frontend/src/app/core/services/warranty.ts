import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface WarrantyStatus {
  vin: string;
  valid: boolean;
  reason: string;
  warranty_expiry: number;
  days_remaining: number;
}

export interface WarrantyClaim {
  vin: string;
  claim_details_hash: string;
  timestamp: number;
  claimant: string;
  status: 'pending' | 'approved' | 'denied';
  resolution_notes_hash: string | null;
  metadata?: {
    issue_description: string;
    photos: string[];
  };
}

@Injectable({
  providedIn: 'root'
})
export class WarrantyService {
  constructor(private http: HttpClient) { }

  checkWarranty(vin: string): Observable<WarrantyStatus> {
    return this.http.get<WarrantyStatus>(`${environment.apiUrl}/warranty/check/${vin}`);
  }

  submitClaim(vin: string, issueDescription: string, photos?: string[]): Observable<any> {
    return this.http.post(`${environment.apiUrl}/warranty/submit-claim`, {
      vin,
      issue_description: issueDescription,
      photos: photos || []
    });
  }

  getClaims(vin: string): Observable<{ vin: string; claims: WarrantyClaim[]; count: number }> {
    return this.http.get<any>(`${environment.apiUrl}/warranty/claims/${vin}`);
  }

  approveClaim(vin: string, claimIndex: number): Observable<any> {
    return this.http.post(`${environment.apiUrl}/warranty/approve-claim`, {
      vin,
      claim_index: claimIndex
    });
  }

  denyClaim(vin: string, claimIndex: number, reason: string): Observable<any> {
    return this.http.post(`${environment.apiUrl}/warranty/deny-claim`, {
      vin,
      claim_index: claimIndex,
      reason
    });
  }
}
