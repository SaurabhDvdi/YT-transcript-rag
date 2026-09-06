/**
 * useAuth — React hook wrapping AuthService for use in extension components.
 * Provides reactive auth state (user, isAuthenticated, isLoading, error)
 * and actions (login, register, logout).
 */

import { useState, useEffect, useCallback } from "react";
import { authService, type UserProfile, AuthError } from "../services/auth";
import { getOrCreateSessionId } from "../services/session";

interface AuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: UserProfile | null;
  error: string | null;
}

interface AuthActions {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  deleteAccount: () => Promise<void>;
  clearError: () => void;
}

export type UseAuthReturn = AuthState & AuthActions;

export function useAuth(): UseAuthReturn {
  const [state, setState] = useState<AuthState>({
    isLoading: true,
    isAuthenticated: false,
    user: null,
    error: null,
  });

  // Load initial auth state from storage on mount
  useEffect(() => {
    let cancelled = false;
    authService.getProfile().then((profile) => {
      if (cancelled) return;
      setState({
        isLoading: false,
        isAuthenticated: profile !== null,
        user: profile,
        error: null,
      });
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      await authService.login(email, password);
      const profile = await authService.getProfile();
      setState({ isLoading: false, isAuthenticated: true, user: profile, error: null });

      // Auto-migrate anonymous conversations on first login
      try {
        const sessionId = await getOrCreateSessionId();
        await authService.migrateSession(sessionId);
      } catch {
        // Non-critical — migration failure doesn't affect login success
      }
    } catch (err) {
      const msg =
        err instanceof AuthError ? err.message : "Login failed. Please try again.";
      setState((prev) => ({ ...prev, isLoading: false, error: msg }));
      throw err;
    }
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      await authService.register(email, password);
      const profile = await authService.getProfile();
      setState({ isLoading: false, isAuthenticated: true, user: profile, error: null });
    } catch (err) {
      const msg =
        err instanceof AuthError ? err.message : "Registration failed. Please try again.";
      setState((prev) => ({ ...prev, isLoading: false, error: msg }));
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      await authService.logout();
      setState({ isLoading: false, isAuthenticated: false, user: null, error: null });
    } catch {
      setState((prev) => ({ ...prev, isLoading: false }));
    }
  }, []);

  const deleteAccount = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      await authService.deleteAccount();
      setState({ isLoading: false, isAuthenticated: false, user: null, error: null });
    } catch (err) {
      const msg = err instanceof AuthError ? err.message : "Account deletion failed.";
      setState((prev) => ({ ...prev, isLoading: false, error: msg }));
      throw err;
    }
  }, []);

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  return { ...state, login, register, logout, deleteAccount, clearError };
}
