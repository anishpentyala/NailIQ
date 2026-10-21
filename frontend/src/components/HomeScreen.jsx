import { useEffect, useState } from 'react'
import Icon from './Icon'
import { getHistory } from '../api'
import { relativeTime } from '../scanStatus'
import { useI18n } from '../i18n'
import { CONDITION_KEYS, CONDITION_ICONS, signNameParts } from '../conditions'

function tipOfTheDay(tips) {
  const start = new Date(new Date().getFullYear(), 0, 0)
  const dayOfYear = Math.floor((Date.now() - start) / 86_400_000)
  return tips[dayOfYear % tips.length]
}

const WHY_ROWS = [
  { key: 'anemia', icon: 'droplet' },
  { key: 'organs', icon: 'pulse' },
  { key: 'baseline', icon: 'history' },
]

const DOT_SCANS = 6

// One dashboard card per sign: its verdict in the latest scan, plus a dot per recent scan (oldest -> newest) so a
// change over time is visible at a glance. Dots carry the same three verdicts as everywhere else, never a score.
function SignTile({ signKey, scans, index }) {
  const { t } = useI18n()
  const verdictOf = (scan) => scan.findings.find((f) => f.label === signKey)?.verdict ?? null
  const latest = scans.length > 0 ? verdictOf(scans[0]) : null
  const dots = scans.slice(0, DOT_SCANS).map(verdictOf).reverse()
  const { label, term } = signNameParts(t(`findingNames.${signKey}`))
  const tone = latest ?? 'none'

  return (
    <div className={`dash-tile dash-tile--${tone}`} style={{ '--finding-delay': `${index * 45}ms` }}>
      <span className="dash-tile-icon"><Icon name={CONDITION_ICONS[signKey]} size={16} /></span>
      <span className="dash-tile-label">{label}</span>
      <span className="dash-tile-term">{term}</span>
      <span className="dash-tile-status">{latest ? t(`verdict.${latest}.label`) : t('home.notScanned')}</span>
      <span className="dash-tile-dots" aria-hidden="true">
        {dots.map((v, i) => (
          <i key={i} className={`dot dot--${v ?? 'none'}`} />
        ))}
      </span>
    </div>
  )
}

export default function HomeScreen({ onStartScan }) {
  const { t, lang } = useI18n()
  // 'loading' keeps the grid a stable height so the page doesn't jump once history arrives; 'error' degrades to
  // the not-scanned-yet state.
  const [scanState, setScanState] = useState('loading')
  const [scans, setScans] = useState([])

  useEffect(() => {
    let cancelled = false
    getHistory(DOT_SCANS)
      .then((data) => {
        if (cancelled) return
        setScans(data.scans)
        setScanState(data.scans.length === 0 ? 'empty' : 'ready')
      })
      .catch(() => { if (!cancelled) setScanState('error') })
    return () => { cancelled = true }
  }, [])

  return (
    <div className="home">
      <section className="home-dash">
        <header className="home-dash-head">
          <p className="home-dash-hello">{t('home.greeting')}</p>
          <h2 className="home-dash-title">{t('home.howNails')}</h2>
          <p className="home-dash-sub">{t('home.heroText')}</p>
        </header>

        <div className="dash-grid">
          {CONDITION_KEYS.map((key, i) => (
            <SignTile key={key} signKey={key} scans={scans} index={i} />
          ))}
        </div>

        <p className="home-dash-last">
          {scanState === 'ready'
            ? t('home.lastScan', { when: relativeTime(scans[0].created_at, t, lang) })
            : scanState === 'loading'
              ? ' '
              : t('home.noScans')}
        </p>
        <button type="button" className="primary-btn home-cta" onClick={onStartScan}>
          {t('home.cta')}
        </button>
        <p className="home-not-yet">{t('home.notYet')}</p>
      </section>

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
