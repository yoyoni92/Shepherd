import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'

const mockPush = vi.fn()

vi.mock('next-auth/react', () => ({
  signIn: vi.fn(),
  useSession: () => ({ data: null, status: 'unauthenticated' }),
  SessionProvider: ({ children }: { children: React.ReactNode }) => children,
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => '/',
}))

import LoginPage from '@/app/page'
import { signIn } from 'next-auth/react'

describe('T1 - Admin login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockPush.mockClear()
  })

  it('redirects to /dashboard on valid credentials', async () => {
    vi.mocked(signIn).mockResolvedValue({ ok: true, error: null, status: 200, url: '/dashboard' } as never)
    render(<LoginPage />)
    await userEvent.type(screen.getByLabelText(/password/i), 'correct-pass')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/dashboard'))
  })

  it('shows error message on invalid credentials', async () => {
    vi.mocked(signIn).mockResolvedValue({ ok: false, error: 'CredentialsSignin', status: 401, url: null } as never)
    render(<LoginPage />)
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument())
  })

  it('calls signIn with credentials provider', async () => {
    vi.mocked(signIn).mockResolvedValue({ ok: true } as never)
    render(<LoginPage />)
    await userEvent.type(screen.getByLabelText(/password/i), 'secret')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    expect(signIn).toHaveBeenCalledWith('credentials', expect.objectContaining({ password: 'secret', redirect: false }))
  })
})
