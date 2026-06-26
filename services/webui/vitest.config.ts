import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    exclude: ['e2e/**', 'node_modules/**'],
    // Client base points straight at the mocked host (the Next proxy is bypassed in unit tests).
    env: {
      NEXT_PUBLIC_FLEET_BASE: 'http://localhost:8000',
    },
    coverage: {
      provider: 'v8',
      include: ['lib/**', 'hooks/**'],
      // ponytail: NextAuth config + cn() styling helper — not business logic
      exclude: ['lib/auth.ts', 'lib/utils.ts'],
      thresholds: { lines: 85, functions: 85, branches: 85, statements: 85 },
    },
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, '.') },
  },
})
