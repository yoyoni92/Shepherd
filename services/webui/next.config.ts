import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
  // ponytail: serve the (already-small) logo as-is; avoids needing sharp in the standalone runner
  images: { unoptimized: true },
}

export default nextConfig
