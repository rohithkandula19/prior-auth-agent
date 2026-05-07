import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111111",
        body: "#3f3f3f",
        soft: "#6b6b6b",
        rule: "#e8e6df",
        line: "#e8e6df",
        paper: "#f6f4ee",
        canvas: "#fbfaf6",
        approved: "#1f7a4d",
        denied: "#b3261e",
        pending: "#a86b00",
        wash: {
          policy: "#fce8b1",
          chart: "#bfe9c8",
        },
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "'SF Pro Text'",
          "Inter",
          "sans-serif",
        ],
        display: [
          "ui-serif",
          "'New York'",
          "'Iowan Old Style'",
          "Georgia",
          "serif",
        ],
        mono: ["ui-monospace", "'SF Mono'", "'JetBrains Mono'", "monospace"],
      },
      letterSpacing: {
        tightest: "-0.04em",
      },
      boxShadow: {
        card: "0 1px 0 rgba(17,17,17,0.04)",
      },
    },
  },
  plugins: [],
};

export default config;
