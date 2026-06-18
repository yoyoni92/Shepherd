import { withAuth } from 'next-auth/middleware'

export default withAuth({ callbacks: { authorized: ({ token }) => !!token } })

export const config = {
  matcher: ['/dashboard/:path*', '/chat/:path*', '/assistant/:path*', '/upload/:path*', '/config/:path*', '/review/:path*'],
}
