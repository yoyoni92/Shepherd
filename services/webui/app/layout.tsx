import type { Metadata } from 'next'
import { Assistant } from 'next/font/google'
import './globals.css'
import { Providers } from '@/components/Providers'

const assistant = Assistant({
  subsets: ['hebrew', 'latin'],
  weight: ['400', '500', '600', '700', '800'],
  variable: '--font-assistant',
})

export const metadata: Metadata = {
  title: 'ניהול צי רכב',
  description: 'קונסולת ניהול צי רכב',
}

// Apply the saved theme before paint to avoid a flash (dark is the default).
const themeScript = `(function(){try{if(localStorage.getItem('theme')==='light'){document.documentElement.classList.add('light')}}catch(e){}})()`

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="he" dir="rtl" className={assistant.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
