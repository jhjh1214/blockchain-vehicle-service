export interface ServiceRecord {
  vin: string;
  record_index: number;
  metadata_hash: string;
  timestamp: number;
  service_center: string;
  verified: boolean;
  disputed: boolean;
  dispute_reason: string;
  metadata?: ServiceMetadata;
  // Owner-enriched fields (only on owner pending list)
  make?: string;
  model?: string;
  year?: number;
}

export interface ServiceMetadata {
  service_type: string;
  service_date: string;
  mileage: number;
  parts_replaced: string;
  technician_name: string;
  service_notes: string;
  photos: string[];
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
