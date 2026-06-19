'use client'
import { signIn } from 'next-auth/react'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Truck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export default function LoginPage() {
  const [email, setEmail] = useState('admin@fleet.co.il')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const router = useRouter()

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    const res = await signIn('credentials', { email, password, redirect: false })
    if (res?.ok) router.push('/dashboard')
    else setError('פרטי התחברות שגויים')
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-6"
      style={{
        background:
          'radial-gradient(1100px 600px at 50% -10%,rgba(59,130,246,.10),transparent 60%),#0b0d14',
      }}
    >
      <div className="w-full" style={{ maxWidth: 420 }}>
        <div className="flex items-center gap-3 justify-center mb-7">
          <div
            className="flex items-center justify-center"
            style={{
              width: 46,
              height: 46,
              borderRadius: 12,
              background: 'linear-gradient(135deg,#3b82f6,#1d4ed8)',
              boxShadow: '0 8px 24px rgba(59,130,246,.35)',
            }}
          >
            <Truck size={26} color="#fff" />
          </div>
          <div className="text-right">
            <div className="text-[19px] font-extrabold" style={{ letterSpacing: '-.3px' }}>
              שפרד - ניהול צי רכב
            </div>
            <div className="text-[12px] text-faint" style={{ letterSpacing: '.5px' }}>
              FLEET MANAGEMENT
            </div>
          </div>
        </div>

        <form
          onSubmit={handleLogin}
          className="bg-panel border border-line"
          style={{ borderRadius: 16, padding: '30px 28px', boxShadow: '0 24px 60px rgba(0,0,0,.45)' }}
        >
          <div className="text-[20px] font-bold mb-1">כניסת מנהל מערכת</div>
          <div className="text-[13px] text-faint mb-6">התחבר/י לקונסולת הניהול</div>

          <label htmlFor="email" className="block text-[12.5px] font-semibold text-muted mb-[7px]">
            דוא״ל
          </label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full mb-[18px] ltr text-left"
          />

          <label htmlFor="password" className="block text-[12.5px] font-semibold text-muted mb-[7px]">
            סיסמה
          </label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full mb-[22px] ltr text-left"
          />

          {error && <p className="text-danger text-xs mb-3">{error}</p>}

          <Button type="submit" variant="primary" size="lg" className="w-full">
            כניסה למערכת
          </Button>

          <div className="flex items-center gap-2 mt-[18px] justify-center text-[12px] text-dim">
            <span className="w-1.5 h-1.5 rounded-full bg-success" />
            מחובר לשרת · גישת מנהל בלבד
          </div>
        </form>
        <div className="text-center text-[11.5px] mt-[18px]" style={{ color: '#334155' }}>
          © 2026 YoniD Ops · גרסה 1.0
        </div>
      </div>
    </div>
  )
}
