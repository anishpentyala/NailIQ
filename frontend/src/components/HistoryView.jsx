import { useEffect, useState } from 'react'
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import Icon from './Icon'
import { getHistory } from '../api'
import { overallStatus, relativeTime } from '../scanStatus'
import { failureReasonMessage } from '../failureReasons'
import { PLACEHOLDER_SCANS } from '../placeholderScans'
import { useI18n, findingName } from '../i18n'

const VERDICT_ICON = { within: 'checkCircle', outside: 'alertTriangle', inconclusive: 'helpCircle' }
const VERDICT_TEXT_KEY = {
  within: 'history.withinRange',
  outside: 'history.outsideRange',
  inconclusive: 'history.inconclusive',
}

const TRACK_NOTE_KEY = { fused: 'history.fusedNote', color_fused: 'history.colorFusedNote' }

// labels whose verdict flipped compared to the previous scan
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

function FindingDetail({ finding }) {
  const { t } = useI18n()
  const noteKey = TRACK_NOTE_KEY[finding.track_used]
  const isInconclusive = finding.verdict === 'inconclusive'

  return (
    <div className="history-finding-body">
      {isInconclusive ? (
        <p className="history-detail-message">{failureReasonMessage(t, finding.failure_reason)}</p>
      ) : (
        <div className="history-detail-grid">
          {finding.value != null && (
            <div className="dashboard-tile">
              <span className="tile-label">
                {finding.unit === 'deg' ? t('history.measuredAngle') : t('history.measuredValue')}
              </span>
              <span className={`tile-value history-tile-value--${finding.verdict}`}>
                {finding.value.toFixed(1)}
                {finding.unit === 'deg' ? '°' : ''}
              </span>
              {finding.label === 'clubbing' && (
                <span className="tile-sub">{t('history.clubbingThreshold')}</span>
              )}
            </div>
          )}
          {finding.confidence != null && (
            <div className="dashboard-tile">
              <span className="tile-label">{t('history.confidenceScore')}</span>
              <div className={`attention-meter history-meter--${finding.verdict}`}>
                <div className="attention-meter-fill" style={{ width: `${Math.round(finding.confidence * 100)}%` }} />
              </div>
              <span className={`tile-value history-tile-value--${finding.verdict}`}>
                {Math.round(finding.confidence * 100)}%
              </span>
            </div>
          )}
        </div>
      )}
      {noteKey && (
        <p className="history-detail-note">
          <Icon name="sparkle" size={14} />
          {t(noteKey)}
        </p>
      )}
    </div>
  )
}

function ScanCard({ scan, previousScan }) {
  const { t, lang } = useI18n()
  const status = overallStatus(scan.findings, t)
  const changed = changedLabels(scan, previousScan)

  return (
    <div className="home-card history-card">
      <div className="history-card-head">
        <div className={`result-icon result-icon--${status.verdict} history-card-icon`}>
          <Icon name={VERDICT_ICON[status.verdict]} size={20} />
        </div>
        <div className="history-card-info">
          <span className="history-card-status">{status.label}</span>
          <span className="history-card-time">{relativeTime(scan.created_at, t, lang)}</span>
        </div>
        {scan.isPlaceholder && <span className="history-example-badge">{t('history.example')}</span>}
        {changed.size > 0 && <span className="history-changed-badge">{t('history.changed')}</span>}
      </div>

      <div className="history-card-body">
        {scan.findings.map((f) => (
          <details key={f.label} className="history-finding-detail">
            <summary className="history-finding-row">
              <span className={`history-finding-dot history-finding-dot--${f.verdict}`} />
              <span className="history-finding-name">{findingName(t, f)}</span>
              <span className={`history-finding-verdict history-finding-verdict--${f.verdict}`}>
                {t(VERDICT_TEXT_KEY[f.verdict])}
              </span>
              {changed.has(f.label) && (
                <span
                  className="history-finding-changed-dot"
                  role="img"
                  aria-label={t('history.changedSinceLast')}
                  title={t('history.changedSinceLast')}
                />
              )}
              <span className="history-finding-chevron"><Icon name="chevronRight" size={14} /></span>
            </summary>
            <FindingDetail finding={f} />
          </details>
        ))}
      </div>
    </div>
  )
}

function AngleTrend({ scans }) {
  const { t, lang } = useI18n()
  const points = scans
    .map((scan) => ({ scan, finding: scan.findings.find((f) => f.label === 'clubbing' && f.value != null) }))
    .filter(({ finding }) => finding)
    .map(({ scan, finding }) => ({
      date: new Date(scan.created_at).toLocaleDateString(lang, { month: 'short', day: 'numeric' }),
      angle: Math.round(finding.value * 10) / 10,
    }))
    .reverse() // put oldest first so the chart reads left-to-right

  if (points.length < 2) return null

  return (
    <section className="home-card history-trend-card">
      <div className="home-card-head">
        <span className="home-card-icon"><Icon name="sparkle" /></span>
        <h3 className="home-card-title">{t('history.trendTitle')}</h3>
      </div>
      <div className="history-trend-chart">
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
            <CartesianGrid stroke="var(--border)" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
            <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} width={36} />
            <Tooltip
              formatter={(value) => [`${value}°`, t('history.trendAngle')]}
              contentStyle={{ borderRadius: 10, border: '1px solid var(--border)', fontSize: 13 }}
            />
            <Line type="monotone" dataKey="angle" stroke="var(--primary)" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="history-trend-note">{t('history.trendNote')}</p>
    </section>
  )
}

export default function HistoryView() {
  const { t } = useI18n()
  const [scans, setScans] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    getHistory()
      .then((data) => {
        if (cancelled) return
        // show example scans if there's no real history yet
        setScans(data.scans.length > 0 ? data.scans : PLACEHOLDER_SCANS)
      })
      .catch(() => { if (!cancelled) setFailed(true) })
    return () => { cancelled = true }
  }, [])

  return (
    <div className="home">
      {failed &&<p className="camera-error" role="alert">{t('history.error')}</p>}

      {!failed && !scans && <p className="result-message" role="status">{t('history.loading')}</p>}

      {!failed && scans && scans.length === 0 && (
        <section className="home-card history-empty">
          <span className="home-card-icon"><Icon name="clipboard" /></span>
          <p className="result-message">{t('history.empty')}</p>
        </section>
      )}

      {!failed && scans && scans.length > 0 && (
        <>
          {scans[0].isPlaceholder && (
            <p className="history-placeholder-note">{t('history.placeholderNote')}</p>
          )}
          <p className="history-rescan-note">{t('history.rescanNote')}</p>
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
