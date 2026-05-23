export interface User {
  id: number;
  email: string;
  role: 'MANUFACTURER' | 'SERVICE_CENTER' | 'OWNER';
  name?: string;
  blockchain_address: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  message?: string;
  access_token: string;
  refresh_token: string;
  user: User;
}

// Keep legacy alias so existing components compile without changes
export type LoginResponse = AuthResponse;

export interface RegisterRequest {
  email: string;
  password: string;
  role: string;
}
