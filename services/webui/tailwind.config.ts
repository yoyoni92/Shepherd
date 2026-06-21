import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './hooks/**/*.ts'],
  theme: {
    extend: {
      colors: {
        // Surfaces (theme-driven via CSS vars; see globals.css)
        bg: 'var(--bg)',
        panel: 'var(--panel)',
        panel2: 'var(--panel2)',
        raised: 'var(--raised)',
        // Borders
        line: 'var(--line)',
        control: 'var(--control)',
        divider: 'var(--divider)',
        // Text
        ink: 'var(--ink)',
        muted: 'var(--muted)',
        faint: 'var(--faint)',
        dim: 'var(--dim)',
        // Accents
        accent: 'var(--accent)',
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
