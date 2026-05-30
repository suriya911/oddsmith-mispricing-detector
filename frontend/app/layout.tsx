import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Oddsmith — Management Credibility Engine',
  description: 'Scores management credibility by diffing earnings call language against prior quarters and live web signals.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-full bg-[#0a0e14] text-slate-200">
        <header className="border-b border-[#1f2937] px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            <span className="font-semibold tracking-tight text-white">Oddsmith</span>
            <span className="text-xs text-slate-500 border border-[#1f2937] rounded px-1.5 py-0.5">
              Management Credibility Engine
            </span>
          </div>
          <div className="text-xs text-slate-500 font-mono">
            Powered by Bright Data · Cognee · AI/ML API
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  )
}
