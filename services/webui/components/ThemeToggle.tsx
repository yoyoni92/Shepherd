'use client'
import { useEffect, useState } from 'react'
import { Sun, Moon } from 'lucide-react'

export function ThemeToggle() {
  const [light, setLight] = useState(false)

  // sync with whatever the no-flash script applied
  useEffect(() => setLight(document.documentElement.classList.contains('light')), [])

  const toggle = () => {
    const next = !light
    setLight(next)
    document.documentElement.classList.toggle('light', next)
    try {
      localStorage.setItem('theme', next ? 'light' : 'dark')
    } catch {
      /* storage unavailable */
    }
  }

  return (
    <button
      onClick={toggle}
      aria-label={light ? 'מצב כהה' : 'מצב בהיר'}
      title={light ? 'מצב כהה' : 'מצב בהיר'}
      className="bg-panel2 border border-control rounded-lg w-9 h-9 flex items-center justify-center text-muted cursor-pointer hover:text-ink"
    >
      {light ? <Moon size={17} /> : <Sun size={17} />}
    </button>
  )
}
