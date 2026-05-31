export interface User {
  id: number;
  email: string;
  role: 'MANUFACTURER' | 'SERVICE_CENTER' | 'OWNER';
  name?: string;
  phone?: string;
  city?: string;
  state?: string;
  status?: 'active' | 'pending' | 'suspended';
  blockchain_address: string;
  created_at?: string;
  email_verified?: boolean;
  theme_preference?: 'light' | 'dark';
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
