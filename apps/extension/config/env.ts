/**
 * Centralized extension environment and service configuration.
 * Avoids scattered environment references and hardcoded URLs.
 */
export const config = {
  api: {
    baseUrl: import.meta.env.VITE_API_BASE_URL || "http://localhost:8787",
    timeoutMs: 8000,
  },
} as const;
