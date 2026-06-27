import { withAuth } from 'next-auth/middleware'
import { NextResponse } from 'next/server'
import { isRouteAllowed } from '@/lib/routeAccess'

export default withAuth(
  function middleware(req) {
    // Hard-gate by role before the page loads; backend 403 stays the final backstop.
    const role = req.nextauth.token?.role as string | undefined
    if (role && !isRouteAllowed(req.nextUrl.pathname, role)) {
      return NextResponse.redirect(new URL('/dashboard', req.url))
    }
    return NextResponse.next()
  },
  { callbacks: { authorized: ({ token }) => !!token } },
)

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/vehicles/:path*',
    '/drivers/:path*',
    '/customers/:path*',
    '/events/:path*',
    '/accidents/:path*',
    '/attendance/:path*',
    '/upload/:path*',
    '/bot/:path*',
    '/maintenance-types/:path*',
    '/companies/:path*',
    '/access/:path*',
    '/health/:path*',
    '/config/:path*',
  ],
}
