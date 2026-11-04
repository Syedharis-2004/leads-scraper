/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark theme palette
        ink: {
          50: '#f6f7f9',
          100: '#eceef2',
          200: '#d4d8e0',
          300: '#a8b0c0',
          400: '#7884a0',
          500: '#525e7a',
          600: '#3d4660',
          700: '#2a3148',
          800: '#1c2138',
          900: '#131829',
          950: '#0b0f1c',
        },
        teal: {
          50: '#effcf8',
          100: '#cbf7ec',
          200: '#97edda',
          300: '#5cdcc4',
          400: '#2bc0a8',
          500: '#14a08f',
          600: '#0d8076',
          700: '#0e6760',
          800: '#10524e',
          900: '#114542',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
