'use client'

import { useEffect, useRef } from 'react'

interface Props {
  steps: string[]
  done: boolean
  score?: number
}

export default function ActivityStream({ steps, done, score }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [steps.length])

  return (
    <div className="bg-[#0a0e14] border border-[#1f2937] rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#1f2937]">
        <span className="text-xs text-slate-500 uppercase tracking-widest">Live Agent Activity</span>
        <span className={`flex items-center gap-1.5 text-xs ${done ? 'text-emerald-400' : 'text-amber-400'}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${done ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'}`} />
          {done ? 'Complete' : 'Running'}
        </span>
      </div>
      <div className="p-4 max-h-64 overflow-y-auto font-mono text-xs space-y-1">
        {steps.map((step, i) => (
          <div key={i} className="flex gap-2">
            <span className="text-slate-600 select-none shrink-0">{String(i + 1).padStart(2, '0')}</span>
            <span className={step.startsWith('[') ? 'text-amber-400' : 'text-slate-400'}>{step}</span>
          </div>
        ))}
        {!done && steps.length > 0 && (
          <div className="flex gap-2 text-slate-600">
            <span className="select-none shrink-0">&gt;&gt;</span>
            <span className="animate-pulse">▊</span>
          </div>
        )}
        {done && score != null && (
          <div className="mt-2 text-emerald-400 font-semibold">
            ✓ Analysis complete — Score: {score.toFixed(0)}/100
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
