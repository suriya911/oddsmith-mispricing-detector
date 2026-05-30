'use client'

import { useState } from 'react'
import { graphSearch } from '@/lib/api'

export default function GraphSearch() {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setAnswer('')
    try {
      const res = await graphSearch(query)
      setAnswer(res.answer)
    } catch {
      setAnswer('Query failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-[#1f2937]">
        <span className="text-xs text-slate-500 uppercase tracking-widest">
          Ask the Graph — Powered by Cognee
        </span>
      </div>
      <div className="p-5">
        <form onSubmit={submit} className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='e.g. "What did NMBS stop disclosing?"'
            className="flex-1 bg-[#0a0e14] border border-[#1f2937] rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-amber-500/50"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-lg text-sm hover:bg-amber-500/30 transition-colors disabled:opacity-50"
          >
            {loading ? '…' : 'Ask'}
          </button>
        </form>
        {answer && (
          <div className="mt-4 bg-[#0a0e14] border border-[#1f2937] rounded-lg p-4 text-sm text-slate-300 font-mono whitespace-pre-wrap">
            {answer}
          </div>
        )}
      </div>
    </div>
  )
}
