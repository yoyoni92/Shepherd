'use client'
import { signIn } from 'next-auth/react'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const [email, setEmail] = useState('admin@fleetops.io')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const router = useRouter()

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    const res = await signIn('credentials', { email, password, redirect: false })
    if (res?.ok) {
      router.push('/dashboard')
    } else {
      setError('Invalid credentials')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg)' }}>
      <div className="bg-panel border border-line rounded-2xl shadow-2xl" style={{ width: 440, padding: '40px 48px' }}>
        <div className="flex flex-col items-center mb-6">
          <img src="/logo.png" alt="Shepherd" className="w-20 h-20 mb-3" style={{ mixBlendMode: 'lighten' }} />
          <h1 className="text-2xl font-extrabold tracking-tight">Shepherd</h1>
          <p className="text-muted text-xs mt-1">watch over your fleet - Admin Console</p>
        </div>
        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <div>
            <label htmlFor="email" className="block text-[11px] text-slate-400 mb-1">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full bg-panel2 border border-line rounded-lg px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-[11px] text-slate-400 mb-1">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-panel2 border border-line rounded-lg px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-blue-500"
            />
          </div>
          {error && <p className="text-rose-400 text-xs">{error}</p>}
          <button
            type="submit"
            className="bg-blue-600 text-white rounded-lg py-3 font-bold hover:brightness-110 text-sm mt-1"
          >
            Sign in
          </button>
        </form>
        <p className="text-center text-muted text-[10.5px] mt-5">
          Admin access is webapp-login only. Drivers &amp; customers use Telegram.
        </p>
      </div>
    </div>
  )
}
