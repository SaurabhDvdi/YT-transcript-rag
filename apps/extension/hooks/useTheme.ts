import { useState, useEffect, useCallback } from "react";

export type ThemePreference = "light" | "dark" | "system";

const STORAGE_KEY = "yt_ai_theme";

export function useTheme() {
  const [theme, setThemeState] = useState<ThemePreference>("system");
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("dark");

  const applyTheme = useCallback((pref: ThemePreference) => {
    let resolved: "light" | "dark";
    if (pref === "system") {
      const isSystemDark =
        typeof window !== "undefined" &&
        window.matchMedia &&
        window.matchMedia("(prefers-color-scheme: dark)").matches;
      resolved = isSystemDark ? "dark" : "light";
    } else {
      resolved = pref;
    }

    setResolvedTheme(resolved);

    if (typeof document !== "undefined") {
      const root = document.documentElement;
      if (resolved === "dark") {
        root.classList.add("dark");
        root.classList.remove("light");
      } else {
        root.classList.add("light");
        root.classList.remove("dark");
      }
    }
  }, []);

  // Load initial theme from storage
  useEffect(() => {
    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      chrome.storage.local.get([STORAGE_KEY], (res) => {
        const saved = res[STORAGE_KEY] as ThemePreference | undefined;
        if (saved && (saved === "light" || saved === "dark" || saved === "system")) {
          setThemeState(saved);
          applyTheme(saved);
        } else {
          applyTheme("system");
        }
      });
    } else {
      applyTheme("system");
    }
  }, [applyTheme]);

  // Listen to system preference changes when on 'system'
  useEffect(() => {
    if (theme !== "system" || typeof window === "undefined" || !window.matchMedia) {
      return;
    }

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      applyTheme("system");
    };

    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, [theme, applyTheme]);

  const setTheme = useCallback(
    (newTheme: ThemePreference) => {
      setThemeState(newTheme);
      applyTheme(newTheme);
      if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ [STORAGE_KEY]: newTheme });
      }
    },
    [applyTheme],
  );

  return {
    theme,
    resolvedTheme,
    setTheme,
  };
}
