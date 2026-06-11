/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  safelist: [
    // Custom opacity values used in component classes
    { pattern: /bg-(brand|amber|purple|green|blue|red|teal|orange|pink|slate|white|dark)-.+\/(5|10|15|20|25|30|40|50|60|70|80)/ },
    { pattern: /border-(brand|white|slate|green|red|amber|blue|purple)-.+\/(10|15|20|30|40|50|60)/ },
    { pattern: /text-(brand|amber|purple|green|blue|red|teal|orange|pink|slate)-.+/ },
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
          950: '#1e1b4b',
        },
        dark: {
          50:  '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          700: '#334155',
          800: '#1e293b',
          850: '#172033',
          900: '#0f172a',
          950: '#060b18',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      opacity: {
        '8':  '0.08',
        '12': '0.12',
        '15': '0.15',
      },
      backgroundImage: {
        'hero-gradient': 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)',
        'card-gradient': 'linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)',
        'brand-gradient': 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
        'success-gradient': 'linear-gradient(135deg, #059669 0%, #0d9488 100%)',
        'danger-gradient': 'linear-gradient(135deg, #dc2626 0%, #ea580c 100%)',
      },
      boxShadow: {
        'glow': '0 0 20px rgba(99,102,241,0.3)',
        'glow-sm': '0 0 10px rgba(99,102,241,0.2)',
        'card': '0 4px 24px rgba(0,0,0,0.4)',
        'card-hover': '0 8px 40px rgba(0,0,0,0.5)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
        'glow-pulse': 'glowPulse 2s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        glowPulse: {
          '0%, 100%': { boxShadow: '0 0 10px rgba(99,102,241,0.3)' },
          '50%': { boxShadow: '0 0 25px rgba(99,102,241,0.6)' },
        },
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
