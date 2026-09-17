/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        studio: {
          bg: "#090C10",
          card: "#121622",
          border: "#1F2937",
          accent: "#6366F1",
          gold: "#FFDD00"
        }
      }
    },
  },
  plugins: [],
}
