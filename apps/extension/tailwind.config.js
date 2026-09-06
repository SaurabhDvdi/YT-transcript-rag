/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: [
    "./entrypoints/**/*.{html,ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./utils/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        yt: {
          red: "#FF0000",
          dark: "#0F0F0F",
          card: "#1F1F1F",
          border: "#272727",
          text: "#F1F1F1",
          muted: "#AAAAAA",
        },
        theme: {
          base: "var(--bg-base)",
          surface: "var(--bg-surface)",
          elevated: "var(--bg-elevated)",
          overlay: "var(--bg-overlay)",
          border: "var(--border-subtle)",
          "border-strong": "var(--border-strong)",
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
          brand: "var(--brand-accent)",
          "brand-hover": "var(--brand-accent-hover)",
        },
      },
    },
  },
  plugins: [],
};
