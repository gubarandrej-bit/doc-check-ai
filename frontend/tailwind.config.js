/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: { 950: '#07090f', 900: '#0b1020', 850: '#11182b', 800: '#1a2238', 700: '#243049' },
        accent: { 400: '#38bdf8', 500: '#0ea5e9', 600: '#0284c7' },
      },
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
}