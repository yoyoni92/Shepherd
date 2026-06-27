import { redirect } from 'next/navigation'
import { cookies } from 'next/headers'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { Shell } from '@/components/Shell'
import { parseActAs, ACT_AS_STATE_COOKIE } from '@/lib/actAs'

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/')

  // Read act-as state server-side so the nav/banner render correctly on first paint
  // (no hydration flash). Only a system admin can act-as.
  const actAs =
    session.user.role === 'admin'
      ? parseActAs((await cookies()).get(ACT_AS_STATE_COOKIE)?.value)
      : null

  return <Shell actAs={actAs}>{children}</Shell>
}
