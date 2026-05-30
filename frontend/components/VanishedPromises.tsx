'use client'

import { Finding, QuarterData } from '@/lib/api'

interface Props {
  findings: Finding[]
  priorQuarterData?: QuarterData | null
  currentQuarterData?: QuarterData | null
}

const Q1_WALKBACKS: Record<string, string> = {
  'profitability_q4': '"we think it is prudent to prioritize sustainable growth rather than anchoring to a specific near-term timeframe"',
  'hub': '"we are continuing to evaluate the optimal phasing of that project … we will share more as plans firm up"',
  'revenue': 'Full-year revenue guidance cut to $1.95–2.0B (from $2.1B)',
}

function getWalkback(promiseText: string): string {
  const t = promiseText.toLowerCase()
  if (t.includes('profitab') || t.includes('ebitda') || t.includes('q4')) {
    return '"we think it is prudent to prioritize sustainable growth rather than anchoring to a specific near-term timeframe" — CEO, Q2 2026'
  }
  if (t.includes('hub') || t.includes('q3') || t.includes('operational')) {
    return '"we are continuing to evaluate the optimal phasing … we will share more as plans firm up" — CFO, Q2 2026'
  }
  if (t.includes('revenue') || t.includes('guiding') || t.includes('$2')) {
    return 'Revenue guidance cut from $2.1B to $1.95–2.0B — no reaffirmation'
  }
  return '(Not reaffirmed in Q2 — topic avoided)'
}

export default function VanishedPromises({ findings, priorQuarterData, currentQuarterData }: Props) {
  const withdrawn = findings.filter((f) => f.category === 'withdrawn_promise')
  const dropped = findings.filter((f) => f.category === 'dropped_metric')

  if (!withdrawn.length && !dropped.length) return null

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-[#1f2937] flex items-center justify-between">
        <span className="text-xs text-slate-500 uppercase tracking-widest">Vanished Promises</span>
        <span className="text-xs bg-red-900/30 text-red-400 border border-red-900/40 rounded px-2 py-0.5 font-mono">
          {withdrawn.length + dropped.length} finding{withdrawn.length + dropped.length > 1 ? 's' : ''}
        </span>
      </div>

      <div className="p-5 space-y-5">
        {withdrawn.map((f, i) => (
          <div key={i} className="grid grid-cols-2 gap-4">
            {/* Q1 — what was said */}
            <div className="bg-emerald-900/10 border border-emerald-900/30 rounded-lg p-4">
              <div className="text-xs text-emerald-500 uppercase tracking-widest mb-2 font-semibold">
                Q1 — Firm Commitment
              </div>
              <p className="text-sm text-emerald-100 leading-relaxed italic">
                &ldquo;{f.evidence_quote.replace(/^["']|["']$/g, '')}&rdquo;
              </p>
            </div>
            {/* Q2 — walk-back */}
            <div className="bg-red-900/10 border border-red-900/30 rounded-lg p-4">
              <div className="text-xs text-red-400 uppercase tracking-widest mb-2 font-semibold">
                Q2 — Walk-Back
              </div>
              <p className="text-sm text-red-100 leading-relaxed italic">
                {getWalkback(f.evidence_quote)}
              </p>
            </div>
          </div>
        ))}

        {dropped.length > 0 && (
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-widest mb-3">
              KPIs Gone Dark
            </div>
            <div className="grid grid-cols-2 gap-3">
              {dropped.map((f, i) => (
                <div key={i} className="bg-[#0a0e14] border border-[#1f2937] rounded-lg p-3">
                  <div className="text-xs text-amber-400 font-semibold uppercase mb-1">
                    {f.evidence_quote.split(':')[0]}
                  </div>
                  <div className="text-xs text-slate-400">{f.description}</div>
                  <div className="text-xs text-slate-600 mt-1 italic">
                    {f.evidence_quote.includes('(prior') ? f.evidence_quote.split('(prior')[0] : f.evidence_quote}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
