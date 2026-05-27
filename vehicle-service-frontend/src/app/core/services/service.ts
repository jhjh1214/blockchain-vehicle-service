import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { 
  ServiceRecord, 
  SubmitServiceRequest, 
  VerifyServiceRequest,
  DisputeServiceRequest 
} from '../models/service.model';

@Injectable({
  providedIn: 'root'
})
export class ServiceService {
  constructor(private http: HttpClient) { }

  submitService(data: SubmitServiceRequest | FormData | Record<string, unknown>): Observable<any> {
    return this.http.post(`${environment.apiUrl}/service/submit`, data);
  }

  verifyService(data: VerifyServiceRequest): Observable<any> {
    return this.http.post(`${environment.apiUrl}/service/verify`, data);
  }

  disputeService(data: DisputeServiceRequest): Observable<any> {
    return this.http.post(`${environment.apiUrl}/service/dispute`, data);
  }

  getPendingServices(vin: string): Observable<{ vin: string, pending_services: ServiceRecord[], count: number }> {
    return this.http.get<any>(`${environment.apiUrl}/service/pending/${vin}`);
  }

  getServiceHistory(vin: string): Observable<{ vin: string, service_history: ServiceRecord[], count: number }> {
    return this.http.get<any>(`${environment.apiUrl}/service/history/${vin}`);
  }

  resolveDispute(vin: string, recordIndex: number, decision: number, resolutionNotes: string): Observable<any> {
    return this.http.post(`${environment.apiUrl}/service/resolve-dispute`, {
      vin,
      record_index: recordIndex,
      decision,
      resolution_notes: resolutionNotes
    });
  }

  submitDisputeResponse(vin: string, metadataHash: string, rebuttalNotes: string): Observable<any> {
    return this.http.post(`${environment.apiUrl}/service/dispute-response`, {
      vin,
      metadata_hash: metadataHash,
      rebuttal_notes: rebuttalNotes
    });
  }
}