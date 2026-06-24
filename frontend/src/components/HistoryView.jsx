import { useEffect, useState } from 'react'
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import Icon from './Icon'
import { getHistory } from '../api'

const VERDICT_ICON = { within: 'checkCircle', outside: 'alertTriangle', inconclusive: 'helpCircle' }
const VERDICT_TEXT = { within: 'Within range', outside: 'Outside range', inconclusive: 'Inconclusive' }

function relativeTime(isoString) {
  const minutes = Math.round((Date.now() - new Date(isoString).getTime()) / 60_000)
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days}d ago`
  return new Date(isoString).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

// One status for the whole scan: worst verdict wins, but it's still only ever
// within/outside/inconclusive -- never a named condition or a risk score.
function overallStatus(findings) {
  const outsideCount = findings.filter((f) => f.verdict === 'outside').length
  if (outsideCount > 0) {
    return { verdict: 'outside', label: `${outsideCount} outside typical range` }
  }
  if (findings.some((f) => f.verdict === 'within')) {
    return { verdict: 'within', label: 'All within typical range' }
  }
  return { verdict: 'inconclusive', label: "Couldn't analyze this scan" }
}

// Labels whose verdict flipped vs. the previous (older) scan -- this is the
// "any new differences" signal the history view exists to surface.
function changedLabels(scan, previousScan) {
  const changed = new Set()
  if (!previousScan) return changed
  const prevByLabel = new Map(previousScan.findings.map((f) => [f.label, f.verdict]))
  for (const f of scan.findings) {
    const prevVerdict = prevByLabel.get(f.label)
    if (prevVerdict && prevVerdict !== f.verdict) changed.add(f.label)
  }
  return changed
}

function ScanCard({ scan, previousScan }) {
  const status = overallStatus(scan.findings)
  const changed = changedLabels(scan, previousScan)

  return (
    <div className="home-card history-card">
      <div className="history-card-head">
        <div className={`result-icon result-icon--${status.verdict} history-card-icon`}>
          <Icon name={VERDICT_ICON[status.verdict]} size={20} />
        </div>
        <div className="history-card-info">
          <span className="history-card-status">{status.label}</span>
          <span className="history-card-time">{relativeTime(scan.created_at)}</span>
        </div>
        {changed.size > 0 && <span className="history-changed-badge">Changed</span>}
      </div>

      <div className="history-card-body">
        {scan.findings.map((f) => (
          <div key={f.label} className="history-finding-row">
            <span className={`history-finding-dot history-finding-dot--${f.verdict}`} />
            <span className="history-finding-name">{f.display_name}</span>
            <span className={`history-finding-verdict history-finding-verdict--${f.verdict}`}>
              {VERDICT_TEXT[f.verdict]}
            </span>
            {changed.has(f.label) && (
              <span className="history-finding-changed-dot" aria-label="Changed since last scan" title="Changed since last scan" />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function AngleTrend({ scans }) {
  const points = scans
    .map((scan) => ({ scan, finding: scan.findings.find((f) => f.label === 'clubbing' && f.value != null) }))
    .filter(({ finding }) => finding)
    .map(({ scan, finding }) => ({
      date: new Date(scan.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      angle: Math.round(finding.value * 10) / 10,
    }))
    .reverse() // scans arrive newest-first; the trend reads left-to-right oldest-first

  if (points.length < 2) return null

  return (
    <section className="home-card history-trend-card">
      <div className="home-card-head">
        <span className="home-card-icon"><Icon name="sparkle" /></span>
        <h3 className="home-card-title">Clubbing angle over time</h3>
      </div>
      <div className="history-trend-chart">
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
            <CartesianGrid stroke="var(--border)" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
            <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} width={36} />
            <Tooltip
              formatter={(value) => [`${value}°`, 'Angle']}
              contentStyle={{ borderRadius: 10, border: '1px solid var(--border)', fontSize: 13 }}
            />
            <Line type="monotone" dataKey="angle" stroke="var(--primary)" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="history-trend-note">
        This tracks the measured angle only, not a diagnosis. Share this trend with a
        doctor if you have concerns.
      </p>
    </section>
  )
}

export default function HistoryView() {
  const [scans, setScans] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    getHistory()
      .then((data) => { if (!cancelled) setScans(data.scans) })
      .catch(() => { if (!cancelled) setError("Couldn't load your scan history. Is the backend running?") })
    return () => { cancelled = true }
  }, [])

  return (
    <div className="home">
      <h1 className="home-title">History</h1>

      {error && <p className="camera-error">{error}</p>}

      {!error && !scans && <p className="result-message">Loading your past scans…</p>}

      {!error && scans && scans.length === 0 && (
        <section className="home-card history-empty">
          <span className="home-card-icon"><Icon name="clipboard" /></span>
          <p className="result-message">
            No scans yet. Your past results will show up here so you can track changes over time.
          </p>
        </section>
      )}

      {!error && scans && scans.length > 0 && (
        <>
          <AngleTrend scans={scans} />
          <div className="history-list">
            {scans.map((scan, i) => (
              <ScanCard key={scan.id} scan={scan} previousScan={scans[i + 1]} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
