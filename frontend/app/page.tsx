'use client'

import { useState, useCallback } from 'react'
import { triggerAnalysis, getJob, streamActivity, CredibilityReport } from '@/lib/api'
import ScoreGauge from '@/components/ScoreGauge'
import TranscriptViewer from '@/components/TranscriptViewer'
import VanishedPromises from '@/components/VanishedPromises'
import SpinReality from '@/components/SpinReality'
import ActivityStream from '@/components/ActivityStream'
import GraphSearch from '@/components/GraphSearch'

type Mode = 'offline' | 'live'

export default function Home() {
  const [company, setCompany] = useState('NMBS')
  const [mode, setMode] = useState<Mode>('offline')
  const [jobId, setJobId] = useState<string | null>(null)
  const [steps, setSteps] = useState<string[]>([])
  const [done, setDone] = useState(false)
  const [finalScore, setFinalScore] = useState<number | undefined>()
  const [report, setReport] = useState<CredibilityReport | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runAnalysis = useCallback(async () => {
    if (!company.trim()) return
    setRunning(true)
    setDone(false)
    setSteps([])
    setReport(null)
    setError(null)
    setJobId(null)
    setFinalScore(undefined)

    try {
      const { job_id } = await triggerAnalysis(company.trim().toUpperCase(), mode)
      setJobId(job_id)

      const stopStream = streamActivity(
        job_id,
        (step) => setSteps((prev) => [...prev, step]),
        async (score) => {
          setDone(true)
          setFinalScore(score)
          setRunning(false)
          // Fetch the full report
          try {
            const job = await getJob(job_id)
            if (job.report) setReport(job.report as CredibilityReport)
          } catch {}
        }
      )

      // Poll as fallback for browsers that don't support SSE well
      const poll = setInterval(async () => {
        try {
          const job = await getJob(job_id)
          if (job.status === 'completed') {
            clearInterval(poll)
            setDone(true)
            setRunning(false)
            if (job.report) setReport(job.report as CredibilityReport)
          } else if (job.status === 'error') {
            clearInterval(poll)
            stopStream()
            setError(job.error || 'Analysis failed')
            setRunning(false)
          }
        } catch {}
      }, 2000)

      // Safety: stop polling after 120s
      setTimeout(() => {
        clearInterval(poll)
        if (running) {
          setRunning(false)
          setError('Analysis timed out. Try again.')
        }
      }, 120_000)
    } catch (e: any) {
      setError(e.message || 'Failed to start analysis')
      setRunning(false)
    }
  }, [company, mode])

  const hedgeDelta = report
    ? report.hedging_density - (report.prior_hedging_density ?? report.hedging_density)
    : null

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Top bar */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-1">
          Management Credibility Engine
        </h1>
        <p className="text-sm text-slate-500">
          Reads earnings calls, diffs the language against prior quarters, cross-checks the narrative against live web signals.
        </p>
      </div>

      {/* Search & trigger */}
      <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 mb-6 flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2 flex-1 min-w-[200px]">
          <label className="text-xs text-slate-500 uppercase tracking-widest whitespace-nowrap">Ticker</label>
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value.toUpperCase())}
            placeholder="NMBS"
            className="flex-1 bg-[#0a0e14] border border-[#1f2937] rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-amber-500/50 uppercase"
            onKeyDown={(e) => e.key === 'Enter' && !running && runAnalysis()}
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500 uppercase tracking-widest">Mode</label>
          <div className="flex rounded-lg overflow-hidden border border-[#1f2937]">
            {(['offline', 'live'] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`text-xs px-3 py-2 transition-colors ${
                  mode === m
                    ? 'bg-amber-500/20 text-amber-400'
                    : 'text-slate-500 hover:text-slate-300 bg-[#0a0e14]'
                }`}
              >
                {m === 'offline' ? 'Offline (demo)' : 'Live (Bright Data)'}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={runAnalysis}
          disabled={running}
          className="px-5 py-2 bg-amber-500 text-black font-semibold text-sm rounded-lg hover:bg-amber-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {running ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-900/40 rounded-xl p-4 mb-6 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Activity stream always visible while running */}
      {steps.length > 0 && (
        <div className="mb-6">
          <ActivityStream steps={steps} done={done} score={finalScore} />
        </div>
      )}

      {report && (
        <>
          {/* Summary banner */}
          <div className="bg-gradient-to-r from-slate-900 to-[#111827] border border-[#1f2937] rounded-xl p-5 mb-6">
            <div className="text-xs text-slate-500 uppercase tracking-widest mb-1">Analysis Summary</div>
            <p className="text-base text-white font-medium">{report.summary}</p>
            <div className="flex gap-4 mt-3 flex-wrap">
              <Chip label="Company" value={report.company} />
              <Chip label="Current" value={report.current_quarter} />
              {report.prior_quarter && <Chip label="Prior" value={report.prior_quarter} />}
              <Chip
                label="Tone"
                value={report.tone}
                color={report.tone === 'confident' ? 'green' : report.tone === 'hedged' ? 'red' : 'amber'}
              />
            </div>
          </div>

          {/* Main grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left column: score + graph */}
            <div className="space-y-6">
              <ScoreGauge
                score={report.score}
                priorScore={report.prior_score}
                breakdown={report.score_breakdown}
              />
              <GraphSearch />
            </div>

            {/* Right columns: transcript + findings */}
            <div className="lg:col-span-2 space-y-6">
              <TranscriptViewer
                company={report.company}
                quarter={report.current_quarter}
                priorQuarter={report.prior_quarter}
                hedgeDelta={hedgeDelta}
              />
              <VanishedPromises
                findings={report.findings}
                priorQuarterData={report.prior_quarter_data}
                currentQuarterData={report.current_quarter_data}
              />
              <SpinReality findings={report.findings} />
            </div>
          </div>
        </>
      )}

      {/* Empty state */}
      {!running && !report && steps.length === 0 && (
        <div className="text-center py-24 text-slate-600">
          <div className="text-4xl mb-4">◉</div>
          <p className="text-sm">Enter a ticker and press <strong className="text-slate-500">Analyze</strong> to start.</p>
          <p className="text-xs mt-1">Default demo: <span className="font-mono text-amber-600">NMBS</span> — preloaded sample data, no API keys needed.</p>
        </div>
      )}
    </div>
  )
}

function Chip({ label, value, color }: { label: string; value: string; color?: string }) {
  const colorClass =
    color === 'green'
      ? 'text-emerald-400'
      : color === 'red'
      ? 'text-red-400'
      : color === 'amber'
      ? 'text-amber-400'
      : 'text-slate-300'
  return (
    <div className="flex items-center gap-1.5 text-xs">
      <span className="text-slate-500">{label}</span>
      <span className={`font-semibold font-mono ${colorClass}`}>{value}</span>
    </div>
  )
}
