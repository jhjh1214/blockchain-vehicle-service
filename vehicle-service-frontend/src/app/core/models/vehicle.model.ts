export interface Vehicle {
  vin: string;
  make?: string;
  model?: string;
  year?: number;
  registration_status?: 'active' | 'pending' | 'owner_deleted';
  owner: {
    address: string;
    name: string;
    email: string | null;
  };
  warranty: {
    start: number;
    expiry: number;
    is_valid: boolean;
  };
  service_count: number;
  service_hashes?: string[];
}

export interface RegisterVehicleRequest {
  vin: string;
  owner_email?: string;
  warranty_years: number;
  make?: string;
  model?: string;
  year?: number;
}

export interface MyVehicle {
  vin: string;
  make: string;
  model: string;
  year: number;
  warranty_expiry: number;
  is_valid: boolean;
  service_count: number;
}
