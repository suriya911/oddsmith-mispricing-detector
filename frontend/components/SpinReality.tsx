'use client'

import { Finding } from '@/lib/api'

interface Props {
  findings: Finding[]
}

const SOURCE_TYPE_LABELS: Record<string, string> = {
  news: 'NEWS',
  jobs: 'JOBS',
  filing: 'SEC FILING',
  reviews: 'GLASSDOOR',
}

function sourceTypeColor(type: string) {
  switch (type) {
    case 'news': return 'text-blue-400 bg-blue-900/20 border-blue-900/40'
    case 'jobs': return 'text-purple-400 bg-purple-900/20 border-purple-900/40'
    case 'filing': return 'text-amber-400 bg-amber-900/20 border-amber-900/40'
    case 'reviews': return 'text-pink-400 bg-pink-900/20 border-pink-900/40'
    default: return 'text-slate-400 bg-slate-900/20 border-slate-700'
  }
}

function extractSignalInfo(finding: Finding) {
  const pipe = finding.evidence_quote.split(' | Signal: ')
  const claim = pipe[0].replace('Claim: "', '').replace(/"$/, '')
  const signal = pipe[1] || finding.description
  return { claim, signal }
}

export default function SpinReality({ findings }: Props) {
  const spinFindings = findings.filter((f) => f.category === 'spin_vs_reality')
  if (!spinFindings.length) return null

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-[#1f2937] flex items-center justify-between">
        <span className="text-xs text-slate-500 uppercase tracking-widest">Spin vs Reality</span>
        <span className="text-xs text-slate-500">Powered by Bright Data</span>
      </div>

      <div className="p-5 space-y-4">
        {spinFindings.map((f, i) => {
          const { claim, signal } = extractSignalInfo(f)
          return (
            <div key={i} className="grid grid-cols-2 gap-4">
              {/* Left: Management claim */}
              <div className="bg-[#0a0e14] border border-[#1f2937] rounded-lg p-4">
                <div className="text-xs text-slate-500 uppercase tracking-widest mb-2">
                  Management Said
                </div>
                <p className="text-sm text-slate-300 leading-relaxed italic">&ldquo;{claim}&rdquo;</p>
              </div>
              {/* Right: Live signal */}
              <div className="bg-red-950/20 border border-red-900/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="text-xs text-slate-500 uppercase tracking-widest">Reality</div>
                  <span className={`text-xs px-1.5 py-0.5 rounded border font-semibold ${
                    sourceTypeColor(
                      spinFindings[i].evidence_quote.toLowerCase().includes('job')
                        ? 'jobs'
                        : spinFindings[i].evidence_quote.toLowerCase().includes('glassdoor')
                        ? 'reviews'
                        : spinFindings[i].evidence_quote.toLowerCase().includes('contractor') ||
                          spinFindings[i].evidence_quote.toLowerCase().includes('sec')
                        ? 'filing'
                        : 'news'
                    )
                  }`}>
                    {spinFindings[i].evidence_quote.toLowerCase().includes('job')
                      ? 'JOBS'
                      : spinFindings[i].evidence_quote.toLowerCase().includes('glassdoor')
                      ? 'GLASSDOOR'
                      : spinFindings[i].evidence_quote.toLowerCase().includes('contractor')
                      ? 'SEC FILING'
                      : 'NEWS'}
                  </span>
                </div>
                <p className="text-sm text-red-300 font-medium leading-relaxed">{signal}</p>
                {f.source_url && f.source_url.startsWith('http') && (
                  <a
                    href={f.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-400 hover:text-blue-300 underline mt-2 inline-block"
                  >
                    View source →
                  </a>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
