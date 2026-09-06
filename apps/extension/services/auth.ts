/**
 * AuthService — manages access tokens, refresh tokens, and user profile
 * in chrome.storage.local (with localStorage fallback).
 *
 * Design principles:
 * - Tokens are NEVER exposed to page scripts (stored in extension storage, not cookies)
 * - Silent refresh happens 60 s before access token expiry
 * - All methods are safe to call when the user is not authenticated (return null/false)
 */

import { config } from "../config/env";

// ---------------------------------------------------------------------------
// Storage key constants
// ---------------------------------------------------------------------------

const KEYS = {
  ACCESS_TOKEN: "yt_ai_access_token",
  REFRESH_TOKEN: "yt_ai_refresh_token",
  TOKEN_EXPIRY: "yt_ai_token_expiry", // unix ms
  USER_PROFILE: "yt_ai_user_profile",
} as const;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UserProfile {
  id: string;
  email: string;
  createdAt: string;
}

interface AuthTokenPair {
  accessToken: string;
  refreshToken: string;
  expiresIn: number; // seconds
}

interface AuthApiResponse {
  success: boolean;
  user: UserProfile;
  tokens: AuthTokenPair;
}

interface StoredAuthState {
  accessToken: string | null;
  refreshToken: string | null;
  tokenExpiry: number | null; // unix ms
  userProfile: UserProfile | null;
}

// ---------------------------------------------------------------------------
// Storage helpers (chrome.storage.local → localStorage → memory)
// ---------------------------------------------------------------------------

const _memory: Partial<StoredAuthState> = {};

async function storageGet(keys: string[]): Promise<Record<string, unknown>> {
  if (typeof chrome !== "undefined" && chrome.storage?.local) {
    try {
      return await chrome.storage.local.get(keys);
    } catch {
      // fall through
    }
  }
  const result: Record<string, unknown> = {};
  for (const k of keys) {
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        const v = window.localStorage.getItem(k);
        if (v) result[k] = JSON.parse(v);
      } catch {
        /* ignore */
      }
    } else if (k in _memory) {
      result[k] = _memory[k as keyof typeof _memory];
    }
  }
  return result;
}

async function storageSet(data: Record<string, unknown>): Promise<void> {
  if (typeof chrome !== "undefined" && chrome.storage?.local) {
    try {
      await chrome.storage.local.set(data);
      return;
    } catch {
      // fall through
    }
  }
  for (const [k, v] of Object.entries(data)) {
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        window.localStorage.setItem(k, JSON.stringify(v));
      } catch {
        /* ignore */
      }
    } else {
      (_memory as Record<string, unknown>)[k] = v;
    }
  }
}

async function storageRemove(keys: string[]): Promise<void> {
  if (typeof chrome !== "undefined" && chrome.storage?.local) {
    try {
      await chrome.storage.local.remove(keys);
      return;
    } catch {
      // fall through
    }
  }
  for (const k of keys) {
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        window.localStorage.removeItem(k);
      } catch {
        /* ignore */
      }
    }
    delete (_memory as Record<string, unknown>)[k];
  }
}

// ---------------------------------------------------------------------------
// Refresh threshold: refresh token 60 s before expiry
// ---------------------------------------------------------------------------

const REFRESH_BEFORE_EXPIRY_MS = 60_000;

// ---------------------------------------------------------------------------
// AuthService class
// ---------------------------------------------------------------------------

class AuthService {
  private readonly baseUrl: string;
  private _refreshPromise: Promise<boolean> | null = null;

  constructor(baseUrl: string = config.api.baseUrl) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  // --------------------------------------------------------------------------
  // Read stored state
  // --------------------------------------------------------------------------

  private async _loadState(): Promise<StoredAuthState> {
    const raw = await storageGet([
      KEYS.ACCESS_TOKEN,
      KEYS.REFRESH_TOKEN,
      KEYS.TOKEN_EXPIRY,
      KEYS.USER_PROFILE,
    ]);
    return {
      accessToken: (raw[KEYS.ACCESS_TOKEN] as string) ?? null,
      refreshToken: (raw[KEYS.REFRESH_TOKEN] as string) ?? null,
      tokenExpiry: (raw[KEYS.TOKEN_EXPIRY] as number) ?? null,
      userProfile: (raw[KEYS.USER_PROFILE] as UserProfile) ?? null,
    };
  }

  private async _saveTokens(tokens: AuthTokenPair, profile: UserProfile): Promise<void> {
    const expiryMs = Date.now() + tokens.expiresIn * 1000;
    await storageSet({
      [KEYS.ACCESS_TOKEN]: tokens.accessToken,
      [KEYS.REFRESH_TOKEN]: tokens.refreshToken,
      [KEYS.TOKEN_EXPIRY]: expiryMs,
      [KEYS.USER_PROFILE]: profile,
    });
  }

  private async _clearTokens(): Promise<void> {
    await storageRemove([
      KEYS.ACCESS_TOKEN,
      KEYS.REFRESH_TOKEN,
      KEYS.TOKEN_EXPIRY,
      KEYS.USER_PROFILE,
    ]);
  }

  // --------------------------------------------------------------------------
  // Public API
  // --------------------------------------------------------------------------

  async isAuthenticated(): Promise<boolean> {
    const state = await this._loadState();
    return state.accessToken !== null && state.userProfile !== null;
  }

  async getProfile(): Promise<UserProfile | null> {
    const state = await this._loadState();
    return state.userProfile;
  }

  /**
   * Returns auth headers if the user is authenticated, or {} for anonymous.
   * Silently refreshes the token if it is about to expire.
   */
  async getAuthHeaders(): Promise<Record<string, string>> {
    const state = await this._loadState();
    if (!state.accessToken) return {};

    // Refresh if token expires within threshold
    if (state.tokenExpiry && state.tokenExpiry - Date.now() < REFRESH_BEFORE_EXPIRY_MS) {
      const refreshed = await this.refreshIfNeeded();
      if (refreshed) {
        const fresh = await this._loadState();
        if (fresh.accessToken) {
          return { Authorization: `Bearer ${fresh.accessToken}` };
        }
      }
      // Refresh failed → return anonymous (don't crash)
      return {};
    }

    return { Authorization: `Bearer ${state.accessToken}` };
  }

  /**
   * Attempt a silent token refresh. Returns true if successful.
   * Deduplicates concurrent refresh calls.
   */
  async refreshIfNeeded(): Promise<boolean> {
    if (this._refreshPromise) return this._refreshPromise;

    this._refreshPromise = this._doRefresh().finally(() => {
      this._refreshPromise = null;
    });
    return this._refreshPromise;
  }

  private async _doRefresh(): Promise<boolean> {
    const state = await this._loadState();
    if (!state.refreshToken) return false;

    try {
      const res = await fetch(`${this.baseUrl}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refreshToken: state.refreshToken }),
      });
      if (!res.ok) {
        // Refresh token revoked or expired — clear session
        await this._clearTokens();
        return false;
      }
      const data = (await res.json()) as AuthApiResponse;
      await this._saveTokens(data.tokens, data.user);
      return true;
    } catch {
      return false;
    }
  }

  // --------------------------------------------------------------------------
  // Auth flows
  // --------------------------------------------------------------------------

  async register(email: string, password: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = (await res.json().catch(() => ({}))) as {
        error?: { message?: string; code?: string };
      };
      throw new AuthError(
        err?.error?.message ?? "Registration failed.",
        err?.error?.code ?? "REGISTER_ERROR",
        res.status,
      );
    }
    const data = (await res.json()) as AuthApiResponse;
    await this._saveTokens(data.tokens, data.user);
  }

  async login(email: string, password: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = (await res.json().catch(() => ({}))) as {
        error?: { message?: string; code?: string };
      };
      throw new AuthError(
        err?.error?.message ?? "Login failed.",
        err?.error?.code ?? "LOGIN_ERROR",
        res.status,
      );
    }
    const data = (await res.json()) as AuthApiResponse;
    await this._saveTokens(data.tokens, data.user);
  }

  async logout(): Promise<void> {
    const state = await this._loadState();
    if (state.refreshToken) {
      // Best-effort — ignore network errors
      try {
        await fetch(`${this.baseUrl}/api/v1/auth/logout`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refreshToken: state.refreshToken }),
        });
      } catch {
        /* ignore */
      }
    }
    await this._clearTokens();
  }

  async deleteAccount(): Promise<void> {
    const headers = await this.getAuthHeaders();
    if (!headers.Authorization)
      throw new AuthError("Not authenticated.", "UNAUTHORIZED", 401);

    const res = await fetch(`${this.baseUrl}/api/v1/auth/me`, {
      method: "DELETE",
      headers,
    });
    if (!res.ok) {
      const err = (await res.json().catch(() => ({}))) as {
        error?: { message?: string; code?: string };
      };
      throw new AuthError(
        err?.error?.message ?? "Account deletion failed.",
        err?.error?.code ?? "DELETE_ERROR",
        res.status,
      );
    }
    await this._clearTokens();
  }

  /**
   * Migrate anonymous conversations (created before login) to the authenticated user.
   */
  async migrateSession(sessionId: string): Promise<number> {
    const headers = await this.getAuthHeaders();
    if (!headers.Authorization) return 0;

    try {
      const res = await fetch(`${this.baseUrl}/api/v1/auth/migrate-session`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ sessionId }),
      });
      if (!res.ok) return 0;
      const data = (await res.json()) as { migratedCount?: number };
      return data.migratedCount ?? 0;
    } catch {
      return 0;
    }
  }
}

// ---------------------------------------------------------------------------
// AuthError
// ---------------------------------------------------------------------------

export class AuthError extends Error {
  public readonly code: string;
  public readonly statusCode: number;

  constructor(message: string, code: string, statusCode: number) {
    super(message);
    this.name = "AuthError";
    this.code = code;
    this.statusCode = statusCode;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

// ---------------------------------------------------------------------------
// Singleton
// ---------------------------------------------------------------------------

export const authService = new AuthService();
