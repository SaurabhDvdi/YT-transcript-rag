/**
 * Auth types for user authentication and session management.
 */

export interface UserProfile {
  id: string;
  email: string;
  createdAt: string;
}

export interface AuthTokenPair {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
}

export interface AuthResponse {
  success: boolean;
  user: UserProfile;
  tokens: AuthTokenPair;
  requestId?: string;
}

export interface ProfileResponse {
  success: boolean;
  user: UserProfile;
  requestId?: string;
}

export interface LogoutResponse {
  success: boolean;
  requestId?: string;
}

export interface DeleteAccountResponse {
  success: boolean;
  message: string;
  requestId?: string;
}

export interface MigrateSessionRequest {
  sessionId: string;
}

export interface MigrateSessionResponse {
  success: boolean;
  migratedCount: number;
  requestId?: string;
}
