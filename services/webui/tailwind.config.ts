import type { Config } from 'tailwindcss'

export default {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './hooks/**/*.ts',
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0b0d14',
        panel: '#10131f',
        panel2: '#0f1218',
        line: '#1e2638',
        muted: '#64748b',
      },
    },
  },
} satisfies Config
