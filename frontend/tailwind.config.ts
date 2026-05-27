import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        pitch: "#050814",
        night: "#070d1b",
        panel: "#0f1726",
        panel2: "#162238",
        panel3: "#1e2d49",
        line: "#283956",
        muted: "#91a0b7",
        gold: "#f2c95d",
        foil: "#fff0b0",
        canada: "#ff4358",
        mexico: "#24d47e",
        usa: "#4f8cff",
      },
      boxShadow: {
        foil: "0 0 0 1px rgba(242,201,93,.28), 0 24px 80px rgba(0,0,0,.42)",
        glow: "0 0 40px rgba(79,140,255,.18)",
        card: "0 18px 55px rgba(0,0,0,.34)",
      },
      borderRadius: {
        sticker: "1.35rem",
      },
      keyframes: {
        sheen: {
          "0%": { transform: "translateX(-120%) rotate(12deg)" },
          "100%": { transform: "translateX(220%) rotate(12deg)" },
        },
      },
      animation: {
        sheen: "sheen 2.8s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
