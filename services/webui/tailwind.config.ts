import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './hooks/**/*.ts'],
  theme: {
    extend: {
      colors: {
        // Surfaces
        bg: '#0b0d14',
        panel: '#0f1218',
        panel2: '#10131f',
        raised: '#0c0f17',
        // Borders
        line: '#1a2030', // panel border
        control: '#1e2638', // control border
        divider: '#14181f',
        // Text
        ink: '#e2e8f0',
        muted: '#94a3b8',
        faint: '#64748b',
        dim: '#475569',
        // Accents
        accent: '#60a5fa',
        success: '#34d399',
        warning: '#fbbf24',
        danger: '#f87171',
        orange: '#fb923c',
        purple: '#a78bfa',
        pink: '#f472b6',
        cyan: '#7dd3fc',
      },
      fontFamily: {
        sans: ['var(--font-assistant)', 'system-ui', 'sans-serif'],
      },
      keyframes: {
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'none' },
        },
      },
      animation: {
        'fade-up': 'fadeUp .3s ease',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
} satisfies Config
