/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#fef7ee',
          100: '#fdedd3',
          200: '#fad7a5',
          300: '#f6ba6d',
          400: '#f09433',
          500: '#ec7711',
          600: '#dd5f07',
          700: '#b74608',
          800: '#93380e',
          900: '#76300f',
        },
        pirate: {
          50: '#f7f3f0',
          100: '#eee4dd',
          200: '#dbc6b8',
          300: '#c3a089',
          400: '#a7785a',
          500: '#965f3e',
          600: '#855034',
          700: '#6f422c',
          800: '#5c3627',
          900: '#4c2e22',
        },
      },
      fontFamily: {
        pirate: ['Cinzel', 'serif'],
        modern: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'wave': 'wave 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        wave: {
          '0%, 100%': { transform: 'scaleX(1)' },
          '50%': { transform: 'scaleX(1.1)' },
        },
      },
    },
  },
  plugins: [],
}