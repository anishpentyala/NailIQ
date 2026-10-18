import { useEffect, useState } from 'react'
import Icon from './Icon'
import { getHistory } from '../api'
import { overallStatus, relativeTime } from '../scanStatus'
import { useI18n, findingName } from '../i18n'

function tipOfTheDay(tips) {
  const start = new Date(new Date().getFullYear(), 0, 0)
  const dayOfYear = Math.floor((Date.now() - start) / 86_400_000)
  return tips[dayOfYear % tips.length]
}

// Colors come from CSS classes, not presentation attributes: var() only
// resolves inside CSS declarations, so fill="var(--primary)" would be ignored
// and the illustration would stay light-mode green on a dark surface.
function HeroArt({ label }) {
  return (
    <svg
      className="hero-art"
      viewBox="0 0 320 190"
      role="img"
      aria-label={label}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="phoneGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" className="hero-grad-a" />
          <stop offset="1" className="hero-grad-b" />
        </linearGradient>
      </defs>
      {/* soft background blob */}
      <ellipse cx="160" cy="120" rx="135" ry="62" className="hero-blob" />
      <circle cx="58" cy="48" r="6" className="hero-dot" />
      <circle cx="270" cy="38" r="9" className="hero-dot" />

      {/* phone with shield */}
      <rect x="196" y="36" width="86" height="120" rx="16" fill="url(#phoneGrad)" />
      <rect x="206" y="46" width="66" height="100" rx="10" className="hero-screen" />
      <path
        d="M239 70 l20 7 v14 c0 13 -9 21 -20 26 c-11 -5 -20 -13 -20 -26 v-14 z"
        className="hero-shield"
      />
      <path d="M231 96 l6 6 l12 -14" fill="none" stroke="currentColor" strokeWidth="4"
        strokeLinecap="round" strokeLinejoin="round" />

      {/* hand / finger pointing up with a nail */}
      <rect x="92" y="70" width="46" height="92" rx="22" className="hero-skin-1" />
      <rect x="98" y="58" width="34" height="46" rx="16" className="hero-skin-2" />
      <rect x="103" y="62" width="24" height="22" rx="9" className="hero-skin-3 hero-nail"
        strokeWidth="2" />

      {/* magnifying glass over the nail */}
      <circle cx="116" cy="74" r="30" className="hero-lens"
        stroke="currentColor" strokeWidth="5" />
      <line x1="138" y1="96" x2="158" y2="118" stroke="currentColor"
        strokeWidth="7" strokeLinecap="round" />

      {/* sparkles */}
      <path d="M168 48 l3 8 l8 3 l-8 3 l-3 8 l-3 -8 l-8 -3 l8 -3 z" className="hero-spark" />
      <path d="M60 110 l2 6 l6 2 l-6 2 l-2 6 l-2 -6 l-6 -2 l6 -2 z" className="hero-spark"
        opacity="0.7" />
    </svg>
  )
}

const VERDICT_ICON = { within: 'checkCircle', outside: 'alertTriangle', inconclusive: 'helpCircle' }

// Summary of the most recent scan, promoted to sit right under the hero.
function AssessmentCard({ scan, onViewHistory }) {
  const { t, lang } = useI18n()
  const findings = scan.findings
  const status = overallStatus(findings, t)

  const conclusive = findings.filter((f) => f.verdict !== 'inconclusive')
  const meanConf =
    conclusive.length > 0
      ? conclusive.reduce((s, f) => s + (f.confidence ?? 0), 0) / conclusive.length
      : null

  // just grab the first couple findings that have an actual measured value
  const stats = findings.filter((f) => f.value != null).slice(0, 2)

  return (
    <button type="button" className="home-assessment" onClick={onViewHistory}>
      <div className="home-assessment-head">
        <span className="home-assessment-eyebrow">{t('home.latestAssessment')}</span>
        {meanConf != null && (
          <span className={`home-assessment-confidence home-assessment-confidence--${status.verdict}`}>
            {t('home.confidencePct', { pct: Math.round(meanConf * 100) })}
          </span>
        )}
      </div>

      <div className="home-assessment-status">
        <span className={`result-icon result-icon--${status.verdict} home-assessment-icon`}>
          <Icon name={VERDICT_ICON[status.verdict]} size={18} />
        </span>
        {status.label}
      </div>

      {stats.length > 0 && (
        <div className="home-assessment-stats">
          {stats.map((f) => (
            <div className="home-assessment-stat" key={f.label}>
              <span className="home-assessment-stat-label">{findingName(t, f)}</span>
              <span className="home-assessment-stat-value">
                {f.value.toFixed(1)}
                {f.unit === 'deg' ? '°' : ''}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="home-assessment-footer">
        <span><Icon name="clipboard" size={13} /> {t('home.scanId')}: NIQ-{scan.id}</span>
        <span>{relativeTime(scan.created_at, t, lang)}</span>
      </div>
    </button>
  )
}

function EmptyScanCard({ onViewHistory }) {
  const { t } = useI18n()
  return (
    <button type="button" className="home-last-scan" onClick={onViewHistory}>
      <span className="info-icon"><Icon name="clipboard" /></span>
      <div className="home-last-scan-info">
        <span className="home-last-scan-status">{t('home.noScans')}</span>
        <span className="home-last-scan-time">{t('home.firstResult')}</span>
      </div>
    </button>
  )
}

const WHY_ROWS = [
  { key: 'anemia', icon: 'droplet' },
  { key: 'organs', icon: 'pulse' },
  { key: 'baseline', icon: 'history' },
]

const SCREEN_ROWS = [
  { key: 'clubbing', icon: 'finger' },
  { key: 'koilonychia', icon: 'spoon' },
  { key: 'leukonychia', icon: 'sparkle' },
  { key: 'melanonychia', icon: 'pulse' },
  { key: 'pallor', icon: 'info' },
  { key: 'cyanosis', icon: 'sparkle' },
  { key: 'terrys_nails', icon: 'eye' },
  { key: 'lindsays_nails', icon: 'clipboard' },
  { key: 'onycholysis', icon: 'finger' },
  { key: 'beaus_lines', icon: 'pulse' },
  { key: 'muehrckes_lines', icon: 'clipboard' },
  { key: 'splinter_hemorrhages', icon: 'pulse' },
  { key: 'pitting', icon: 'search' },
  { key: 'onychogryphosis', icon: 'finger' },
]

const COLLAPSED_ROW_COUNT = 4

export default function HomeScreen({ onStartScan, onViewHistory }) {
  const { t } = useI18n()
  // 'loading' renders a fixed-height skeleton so the page doesn't jump once
  // history arrives; 'error' degrades to showing nothing at all.
  const [scanState, setScanState] = useState('loading')
  const [latest, setLatest] = useState(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    let cancelled = false
    getHistory(1)
      .then((data) => {
        if (cancelled) return
        if (data.scans.length === 0) {
          setScanState('empty')
        } else {
          setLatest(data.scans[0])
          setScanState('ready')
        }
      })
      .catch(() => { if (!cancelled) setScanState('error') })
    return () => { cancelled = true }
  }, [])

  const visibleRows = expanded ? SCREEN_ROWS : SCREEN_ROWS.slice(0, COLLAPSED_ROW_COUNT)

  return (
    <div className="home">
      <section className={`home-hero ${scanState === 'ready' ? 'home-hero--compact' : ''}`}>
        <HeroArt label={t('home.heroAlt')} />
        <h2 className="home-hero-title">{t('home.heroTitle')}</h2>
        <p className="home-hero-text">{t('home.heroText')}</p>
        <button type="button" className="primary-btn home-cta" onClick={onStartScan}>
          {t('home.cta')}
        </button>
      </section>

      {scanState === 'loading' && <div className="home-assessment-skeleton" aria-hidden="true" />}
      {scanState === 'ready' && <AssessmentCard scan={latest} onViewHistory={onViewHistory} />}
      {scanState === 'empty' && <EmptyScanCard onViewHistory={onViewHistory} />}

      <section className="home-group">
        <h2 className="info-group-title">{t('home.howItWorks')}</h2>
        <ol className="info-group home-steps">
          {['side', 'top', 'read'].map((step, i) => (
            <li className="info-card info-card--static" key={step}>
              <span className="step-num">{i + 1}</span>
              <div className="info-row-text">
                <strong>{t(`home.steps.${step}.title`)}</strong>
                <p>{t(`home.steps.${step}.text`)}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="home-group">
        <h2 className="info-group-title">{t('home.screensFor')}</h2>
        <div className="info-group">
          {visibleRows.map(({ key, icon }) => (
            <div className="info-card info-card--static" key={key}>
              <span className="info-icon"><Icon name={icon} /></span>
              <div className="info-row-text">
                <strong>{t(`home.rows.${key}.name`)}</strong>
                <p>{t(`home.rows.${key}.text`)}</p>
              </div>
            </div>
          ))}
          <button
            type="button"
            className="info-card list-expander"
            aria-expanded={expanded}
            onClick={() => setExpanded((v) => !v)}
          >
            <span className="info-name">
              {expanded ? t('home.showLess') : t('home.showAll', { n: SCREEN_ROWS.length })}
            </span>
            <span className="info-chevron"><Icon name="chevronRight" size={18} /></span>
          </button>
        </div>
      </section>

      <section className="home-group">
        <h2 className="info-group-title">{t('home.whyTitle')}</h2>
        <div className="info-group">
          {WHY_ROWS.map(({ key, icon }) => (
            <div className="info-card info-card--static" key={key}>
              <span className="info-icon"><Icon name={icon} /></span>
              <div className="info-row-text">
                <strong>{t(`home.whyRows.${key}.name`)}</strong>
                <p>{t(`home.whyRows.${key}.text`)}</p>
              </div>
            </div>
          ))}
        </div>
        <p className="home-group-footnote">{t('home.whoFor')}</p>
      </section>

      <section className="home-tip">
        <span className="home-card-icon home-card-icon--accent"><Icon name="sparkle" /></span>
        <div className="info-row-text">
          <strong>{t('home.dailyTip')}</strong>
          <p>{tipOfTheDay(t('home.tips'))}</p>
        </div>
      </section>

      <p className="home-group-footnote home-disclaimer">{t('app.disclaimer')}</p>
    </div>
  )
}
