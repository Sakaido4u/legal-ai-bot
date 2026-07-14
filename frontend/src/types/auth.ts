// Auth request/response shapes used by authService and login/register pages.

export interface AuthUser {
  id: string
  name: string
  email: string
  avatar?: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  name: string
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

export interface RegisterResponse {
  access_token: string
  token_type: string
  user: AuthUser
}
