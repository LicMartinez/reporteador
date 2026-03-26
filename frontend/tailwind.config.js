/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "white",
        foreground: "black",
        primary: {
          DEFAULT: "hsl(210, 100%, 50%)",
          foreground: "white"
        },
        card: "hsl(220, 15%, 96%)",
        border: "hsl(220, 10%, 90%)"
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
