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
        // Primary: electric sky-blue — broadcast signal
        primary: {
          50:  '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        // Accent: fuchsia — AI commentary / DJ voice
        accent: {
          400: '#e879f9',
          500: '#d946ef',
          600: '#c026d3',
          900: '#1a0520',
        },
        // Surface: deep cool blue-black
        surface: {
          DEFAULT:     '#07070f',
          card:        '#0d0d1a',
          elevated:    '#131327',
          border:      '#1a1a32',
          borderStrong:'#252545',
        },
      },
      fontFamily: {
        sans:    ['Manrope', 'system-ui', 'sans-serif'],
        display: ['Syne', 'system-ui', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      animation: {
        'fade-in':        'fadeIn 0.5s ease-in-out',
        'slide-up':       'slideUp 0.3s ease-out',
        'slide-in-bottom':'slideInBottom 0.3s ease-out',
        'pulse-slow':     'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%':   { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)',    opacity: '1' },
        },
        slideInBottom: {
          '0%':   { transform: 'translateY(100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)',    opacity: '1' },
        },
      },
      boxShadow: {
        'glow-primary': '0 0 20px rgba(56,189,248,0.15), 0 0 60px rgba(56,189,248,0.06)',
        'glow-accent':  '0 0 20px rgba(232,121,249,0.15), 0 0 60px rgba(232,121,249,0.06)',
        'glow-sm':      '0 0 10px rgba(56,189,248,0.25)',
        'artwork':      '0 0 50px rgba(14,165,233,0.18), 0 0 100px rgba(14,165,233,0.06)',
      },
    },
  },
  plugins: [],
}
