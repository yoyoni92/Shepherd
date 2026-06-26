import { withAuth } from 'next-auth/middleware'

export default withAuth({ callbacks: { authorized: ({ token }) => !!token } })

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/vehicles/:path*',
    '/drivers/:path*',
    '/missions/:path*',
    '/attendance/:path*',
    '/config/:path*',
  ],
}
