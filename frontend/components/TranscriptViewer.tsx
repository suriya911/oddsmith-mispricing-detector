'use client'

import { useState, useEffect } from 'react'
import { getTranscript } from '@/lib/api'

interface Props {
  company: string
  quarter: string
  priorQuarter?: string | null
  hedgeDelta?: number | null
}

interface HedgeSpan {
  start: number
  end: number
  marker: string
}

function renderWithHighlights(text: string, spans: HedgeSpan[]) {
  if (!spans.length) return <span className="whitespace-pre-wrap">{text}</span>

  const sorted = [...spans].sort((a, b) => a.start - b.start)
  const parts: React.ReactNode[] = []
  let cursor = 0

  for (const span of sorted) {
    if (span.start < cursor) continue
    if (span.start > cursor) {
      parts.push(
        <span key={cursor} className="whitespace-pre-wrap">
          {text.slice(cursor, span.start)}
        </span>
      )
    }
    parts.push(
      <mark key={span.start} className="hedge-mark">
        {text.slice(span.start, span.end)}
      </mark>
    )
    cursor = span.end
  }
  if (cursor < text.length) {
    parts.push(
      <span key={cursor} className="whitespace-pre-wrap">
        {text.slice(cursor)}
      </span>
    )
  }
  return <>{parts}</>
}

export default function TranscriptViewer({ company, quarter, priorQuarter, hedgeDelta }: Props) {
  const [current, setCurrent] = useState<any>(null)
  const [prior, setPrior] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState<'current' | 'prior'>('current')

  useEffect(() => {
    setLoading(true)
    const promises = [getTranscript(company, quarter).then(setCurrent)]
    if (priorQuarter) promises.push(getTranscript(company, priorQuarter).then(setPrior))
    Promise.allSettled(promises).finally(() => setLoading(false))
  }, [company, quarter, priorQuarter])

  const active = view === 'current' ? current : prior

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#1f2937]">
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500 uppercase tracking-widest">Transcript</span>
          {hedgeDelta != null && Math.abs(hedgeDelta) > 0.02 && (
            <span className={`text-xs font-mono px-2 py-0.5 rounded ${
              hedgeDelta > 0 ? 'bg-red-900/40 text-red-400' : 'bg-emerald-900/40 text-emerald-400'
            }`}>
              {hedgeDelta > 0 ? '▲' : '▼'} Hedging {hedgeDelta > 0 ? '+' : ''}{(hedgeDelta * 100).toFixed(1)}% QoQ
            </span>
          )}
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => setView('current')}
            className={`text-xs px-3 py-1 rounded transition-colors ${
              view === 'current'
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {quarter}
          </button>
          {priorQuarter && (
            <button
              onClick={() => setView('prior')}
              className={`text-xs px-3 py-1 rounded transition-colors ${
                view === 'prior'
                  ? 'bg-slate-700/50 text-slate-300 border border-slate-600'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {priorQuarter}
            </button>
          )}
        </div>
      </div>

      {loading && (
        <div className="p-6 text-slate-500 text-sm text-center">Loading transcript…</div>
      )}

      {!loading && active && (
        <div className="p-5 max-h-[420px] overflow-y-auto">
          <div className="flex items-center gap-3 mb-3">
            <span className={`text-xs px-2 py-0.5 rounded font-mono ${
              active.hedging_density < 0.15
                ? 'bg-emerald-900/40 text-emerald-400'
                : active.hedging_density < 0.30
                ? 'bg-amber-900/40 text-amber-400'
                : 'bg-red-900/40 text-red-400'
            }`}>
              Hedge density: {(active.hedging_density * 100).toFixed(1)}%
            </span>
            <span className="text-xs text-slate-500">
              Highlighted in <span className="text-red-400">red</span>
            </span>
          </div>
          <div className="text-sm text-slate-300 leading-relaxed font-mono">
            {renderWithHighlights(active.text, active.hedging_spans)}
          </div>
        </div>
      )}
    </div>
  )
}
