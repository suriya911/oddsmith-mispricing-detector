'use client'

interface Props {
  score: number
  priorScore?: number | null
  breakdown: Record<string, number>
}

function scoreColor(s: number) {
  if (s >= 70) return '#10b981'
  if (s >= 50) return '#f59e0b'
  return '#ef4444'
}

function scoreLabel(s: number) {
  if (s >= 70) return 'CREDIBLE'
  if (s >= 50) return 'CAUTION'
  return 'LOW TRUST'
}

export default function ScoreGauge({ score, priorScore, breakdown }: Props) {
  const r = 80
  const cx = 100
  const cy = 100
  const circumference = Math.PI * r  // half circle
  const arcLength = (score / 100) * circumference
  const color = scoreColor(score)

  // SVG half-circle arc (bottom-open semicircle)
  const startAngle = Math.PI  // 180°
  const endAngle = 0          // 0°

  function polarToXY(angle: number, radius: number) {
    return {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    }
  }

  const scoreAngle = Math.PI - (score / 100) * Math.PI  // maps 0-100 → 180°→0°
  const needleTip = polarToXY(scoreAngle, r - 8)

  const total = Object.values(breakdown).reduce((a, b) => a + b, 0)

  const breakdownLabels: Record<string, string> = {
    withdrawn_promises: 'Withdrawn Promises',
    dropped_metrics: 'Dropped Metrics',
    hedge_increase: 'Hedge Increase',
    spin_vs_reality: 'Spin vs Reality',
    baseline_hedging: 'Baseline Hedging',
    soft_promises: 'Soft Promises',
  }

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-6">
      <div className="text-xs text-slate-500 uppercase tracking-widest mb-4">Credibility Score</div>

      <div className="flex flex-col items-center">
        <svg width="200" height="120" className="overflow-visible">
          {/* Track */}
          <path
            d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
            fill="none"
            stroke="#1f2937"
            strokeWidth="16"
            strokeLinecap="round"
          />
          {/* Score arc */}
          <path
            d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
            fill="none"
            stroke={color}
            strokeWidth="16"
            strokeLinecap="round"
            strokeDasharray={`${(score / 100) * circumference} ${circumference}`}
            style={{ transition: 'stroke-dasharray 1s ease' }}
          />
          {/* Needle */}
          <line
            x1={cx}
            y1={cy}
            x2={needleTip.x}
            y2={needleTip.y}
            stroke="#e2e8f0"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <circle cx={cx} cy={cy} r="4" fill="#e2e8f0" />
          {/* Labels */}
          <text x={cx - r - 4} y={cy + 18} fill="#6b7280" fontSize="10" textAnchor="middle">0</text>
          <text x={cx + r + 4} y={cy + 18} fill="#6b7280" fontSize="10" textAnchor="middle">100</text>
          <text x={cx} y={cy - r - 10} fill="#6b7280" fontSize="10" textAnchor="middle">50</text>
        </svg>

        <div className="text-center -mt-2">
          <div className="text-5xl font-bold tabular-nums" style={{ color }}>
            {score.toFixed(0)}
          </div>
          <div className="text-xs font-semibold tracking-widest mt-1" style={{ color }}>
            {scoreLabel(score)}
          </div>
          {priorScore != null && (
            <div className="text-xs text-slate-500 mt-1">
              Prior quarter:{' '}
              <span className="font-mono" style={{ color: scoreColor(priorScore) }}>
                {priorScore.toFixed(0)}
              </span>
              {' '}
              <span className={score < priorScore ? 'text-red-400' : 'text-emerald-400'}>
                ({score < priorScore ? '▼' : '▲'} {Math.abs(score - priorScore).toFixed(0)} pts)
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Breakdown */}
      {total > 0 && (
        <div className="mt-5 space-y-1.5">
          <div className="text-xs text-slate-500 uppercase tracking-widest mb-2">Point Breakdown</div>
          {Object.entries(breakdown).map(([key, val]) =>
            val > 0 ? (
              <div key={key} className="flex items-center justify-between text-xs">
                <span className="text-slate-400">{breakdownLabels[key] || key}</span>
                <span className="font-mono text-red-400">-{val.toFixed(1)}</span>
              </div>
            ) : null
          )}
          <div className="flex items-center justify-between text-xs border-t border-[#1f2937] pt-1 mt-1">
            <span className="text-slate-400">Total deducted</span>
            <span className="font-mono text-red-400">-{total.toFixed(1)}</span>
          </div>
        </div>
      )}
    </div>
  )
}
