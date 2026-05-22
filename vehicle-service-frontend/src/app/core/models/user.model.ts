export interface User {
  id: number;
  email: string;
  role: 'MANUFACTURER' | 'SERVICE_CENTER' | 'OWNER';
  name: string;
  blockchain_address: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  message: string;
  token: string;
  user: User;
}

export interface RegisterRequest {
  email: string;
  password: string;
  role: string;
  name: string;
  phone?: string;
}
