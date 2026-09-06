/**
 * AuthPanel — optional Login / Register form shown in the extension sidebar.
 * The panel is dismissible: clicking "Continue without signing in" closes it.
 * Anonymous usage continues to work in full when dismissed.
 */

import React, { useState } from "react";
import type { UseAuthReturn } from "../hooks/useAuth";

type AuthTab = "login" | "register";

interface AuthPanelProps {
  auth: UseAuthReturn;
  onDismiss: () => void;
}

export const AuthPanel: React.FC<AuthPanelProps> = ({ auth, onDismiss }) => {
  const [tab, setTab] = useState<AuthTab>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    auth.clearError();

    if (tab === "register") {
      if (password !== confirmPassword) {
        setLocalError("Passwords do not match.");
        return;
      }
      if (password.length < 8) {
        setLocalError("Password must be at least 8 characters.");
        return;
      }
    }

    try {
      if (tab === "login") {
        await auth.login(email.trim(), password);
      } else {
        await auth.register(email.trim(), password);
      }
      // Success: parent (App.tsx) will re-render with authenticated state
    } catch {
      // Error is already set in auth.error via the hook
    }
  };

  const displayError = localError ?? auth.error;

  return (
    <div
      id="auth-panel"
      className="rounded-xl bg-zinc-900/80 border border-zinc-700/60 p-4 space-y-4 shadow-lg"
      role="region"
      aria-label="Authentication"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100">
            {tab === "login" ? "Sign In" : "Create Account"}
          </h2>
          <p className="text-[11px] text-zinc-400 mt-0.5">
            Save your conversations across devices
          </p>
        </div>
        {/* Tab switcher */}
        <div className="flex bg-zinc-800 rounded-lg p-0.5 text-[11px] font-medium">
          <button
            id="auth-tab-login"
            type="button"
            onClick={() => {
              setTab("login");
              setLocalError(null);
              auth.clearError();
            }}
            className={`px-2.5 py-1 rounded-md transition-colors ${
              tab === "login"
                ? "bg-zinc-700 text-zinc-100"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Sign In
          </button>
          <button
            id="auth-tab-register"
            type="button"
            onClick={() => {
              setTab("register");
              setLocalError(null);
              auth.clearError();
            }}
            className={`px-2.5 py-1 rounded-md transition-colors ${
              tab === "register"
                ? "bg-zinc-700 text-zinc-100"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Register
          </button>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Email */}
        <div>
          <label
            htmlFor="auth-email"
            className="block text-[11px] font-medium text-zinc-400 mb-1"
          >
            Email
          </label>
          <input
            id="auth-email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
          />
        </div>

        {/* Password */}
        <div>
          <label
            htmlFor="auth-password"
            className="block text-[11px] font-medium text-zinc-400 mb-1"
          >
            Password
          </label>
          <input
            id="auth-password"
            type="password"
            required
            autoComplete={tab === "login" ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
          />
        </div>

        {/* Confirm password (register only) */}
        {tab === "register" && (
          <div>
            <label
              htmlFor="auth-confirm"
              className="block text-[11px] font-medium text-zinc-400 mb-1"
            >
              Confirm Password
            </label>
            <input
              id="auth-confirm"
              type="password"
              required
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
            />
          </div>
        )}

        {/* Error */}
        {displayError && (
          <div
            role="alert"
            className="text-[11px] text-red-400 bg-red-950/30 border border-red-900/40 rounded-lg px-3 py-2"
          >
            {displayError}
          </div>
        )}

        {/* Submit */}
        <button
          id="auth-submit"
          type="submit"
          disabled={auth.isLoading}
          className="w-full py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-zinc-900"
        >
          {auth.isLoading
            ? tab === "login"
              ? "Signing in…"
              : "Creating account…"
            : tab === "login"
              ? "Sign In"
              : "Create Account"}
        </button>
      </form>

      {/* Dismiss */}
      <button
        id="auth-dismiss"
        type="button"
        onClick={onDismiss}
        className="w-full text-center text-[11px] text-zinc-500 hover:text-zinc-300 transition-colors py-1"
      >
        Continue without signing in →
      </button>
    </div>
  );
};
