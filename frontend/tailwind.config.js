/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: "#0B0F17",
          panel: "#131B2A",
          card: "#1B2436",
          border: "#2A364F",
          accent: "#38BDF8",
          warning: "#F59E0B",
          danger: "#EF4444",
          success: "#10B981",
        },
      },
    },
  },
  plugins: [],
};

