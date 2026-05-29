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

  escalateDispute(vin: string, metadataHash: string): Observable<any> {
    return this.http.post(`${environment.apiUrl}/service/escalate-dispute`, {
      vin,
      metadata_hash: metadataHash
    });
  }

  getOwnerHistory(filters?: { status?: string; service_type?: string; date_from?: string; date_to?: string }): Observable<{ service_history: ServiceRecord[]; count: number }> {
    let params: Record<string, string> = {};
    if (filters?.status)       params['status']       = filters.status;
    if (filters?.service_type) params['service_type'] = filters.service_type;
    if (filters?.date_from)    params['date_from']    = filters.date_from;
    if (filters?.date_to)      params['date_to']      = filters.date_to;
    return this.http.get<any>(`${environment.apiUrl}/service/owner/history`, { params });
  }
}