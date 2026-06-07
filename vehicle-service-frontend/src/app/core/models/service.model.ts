export interface ServiceRecord {
  vin: string;
  record_index: number;
  metadata_hash: string;
  timestamp: number;
  service_center: string;
  verified: boolean;
  disputed: boolean;
  dispute_reason: string;
  // Flat service fields (returned by backend _flatten_owner_record)
  service_type?: string;
  service_date?: string;
  mileage?: number;
  technician_name?: string;
  parts_replaced?: string;
  service_notes?: string;
  photos?: string[];
  ecu_modules?: string[];
  rebuttal_notes?: string;
  rebuttal_submitted_at?: string;
  escalated?: boolean;
  escalated_at?: string;
  // Owner-enriched fields
  make?: string;
  model?: string;
  year?: number;
  status?: string;
  // Legacy nested shape (may still appear in some endpoints)
  metadata?: ServiceMetadata;
}

export interface ServiceMetadata {
  service_type: string;
  service_date: string;
  mileage: number;
  parts_replaced: string;
  technician_name: string;
  service_notes: string;
  photos: string[];
  rebuttal_notes?: string;
  rebuttal_submitted_at?: string;
  escalated?: boolean;
  escalated_at?: string;
}

export interface SubmitServiceRequest {
  vin: string;
  service_type: string;
  service_date: string;
  mileage: number;
  parts_replaced?: string;
  technician_name?: string;
  service_notes?: string;
  photos?: string[];
  ecu_modules?: string[];
}

export interface VerifyServiceRequest {
  vin: string;
  record_index: number;
}

export interface DisputeServiceRequest {
  vin: string;
  record_index: number;
  reason: string;
}
