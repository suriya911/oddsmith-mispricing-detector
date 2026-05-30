const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Promise_ {
  text: string
  specificity: 'firm' | 'soft'
  metric_or_date: string
}

export interface Metric {
  name: string
  value: string
}

export interface LiveSignal {
  date: string
  source_type: string
  headline: string
  detail: string
  contradicts_claim: string
  source_url: string
}

export interface SpinCheck {
  claim: string
  contradicts: boolean
  explanation: string
  confidence: number
  signal: LiveSignal
}

export interface Finding {
  category: 'withdrawn_promise' | 'dropped_metric' | 'hedge_increase' | 'spin_vs_reality'
  description: string
  evidence_quote: string
  source_url: string
  points_deducted: number
}

export interface QuarterData {
  company: string
  quarter: string
  hedging_density: number
  hedging_markers: string[]
  tone: 'confident' | 'neutral' | 'hedged'
  promises: Promise_[]
  disclosed_metrics: Metric[]
  raw_transcript: string
}

export interface CredibilityReport {
  company: string
  current_quarter: string
  prior_quarter: string | null
  score: number
  prior_score: number | null
  score_delta: number | null
  tone: string
  hedging_density: number
  prior_hedging_density: number | null
  findings: Finding[]
  score_breakdown: Record<string, number>
  summary: string
  current_quarter_data: QuarterData | null
  prior_quarter_data: QuarterData | null
}

export interface JobStatus {
  job_id: string
  status: 'running' | 'completed' | 'error'
  company: string
  report?: CredibilityReport
  error?: string
}

export async function triggerAnalysis(company: string, mode = 'offline'): Promise<{ job_id: string }> {
  const res = await fetch(`${API}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ company, mode }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getReport(company: string): Promise<CredibilityReport> {
  const res = await fetch(`${API}/report/${company}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getJob(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API}/jobs/${jobId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getTranscript(company: string, quarter: string) {
  const res = await fetch(`${API}/transcript/${company}/${quarter}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{
    text: string
    hedging_spans: { start: number; end: number; marker: string }[]
    hedging_density: number
    quarter: string
    company: string
  }>
}

export async function graphSearch(query: string) {
  const res = await fetch(`${API}/graph/search?q=${encodeURIComponent(query)}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ query: string; answer: string }>
}

export function streamActivity(jobId: string, onStep: (step: string) => void, onDone: (score?: number) => void) {
  const es = new EventSource(`${API}/activity/${jobId}`)
  es.onmessage = (e) => {
    const data = JSON.parse(e.data)
    if (data.done) {
      onDone(data.score)
      es.close()
    } else if (data.step) {
      onStep(data.step)
    }
  }
  es.onerror = () => es.close()
  return () => es.close()
}
