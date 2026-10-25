import { useEffect, useState } from 'react'
import Icon from './Icon'
import { getHistory } from '../api'
import { relativeTime } from '../scanStatus'
import { useI18n } from '../i18n'
import { CONDITION_KEYS, CONDITION_ICONS, signNameParts } from '../conditions'
import nailPhoto from '../assets/onboarding-nail.webp'

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

// The sign "radar": the example nail photo in the middle with a glowing point per sign, and a chip for each sign beside
// it joined to its point by a curved line. Coordinates are in a 350x480 box that scales with the card. The points are
// illustration spots on the example nail (where each sign tends to show), not detections. Each chip shows the sign's
// verdict from the latest scan, in the same three verdicts as everywhere else.
const BOX_W = 350
const BOX_H = 480
const PHOTO = { x: 110, y: 150, w: 130, h: 263 } // the finger photo's rectangle inside the box
const CHIP_W = 108
const CHIP_H = 62
// Chips hug the left and right edges of the card and are spread unevenly from top to bottom (uneven gaps and small
// sideways offsets on purpose). Within a side they keep the same top-to-bottom order as their points on the nail, so the
// connecting lines never cross.
const RIGHT_X = BOX_W - CHIP_W
const RADAR = [
  { key: 'onycholysis', side: 'L', x: 0, y: 14, at: { x: 0.5, y: 0.255 } },
  { key: 'koilonychia', side: 'L', x: 6, y: 124, at: { x: 0.4, y: 0.29 } },
  { key: 'leukonychia', side: 'L', x: 0, y: 246, at: { x: 0.45, y: 0.35 } },
  { key: 'cyanosis', side: 'L', x: 10, y: 372, at: { x: 0.41, y: 0.43 } },
  { key: 'onychogryphosis', side: 'R', x: RIGHT_X, y: 48, at: { x: 0.6, y: 0.265 } },
  { key: 'splinter_hemorrhages', side: 'R', x: RIGHT_X - 8, y: 160, at: { x: 0.58, y: 0.32 } },
  { key: 'pitting', side: 'R', x: RIGHT_X, y: 276, at: { x: 0.56, y: 0.38 } },
  { key: 'beaus_lines', side: 'R', x: RIGHT_X - 4, y: 398, at: { x: 0.54, y: 0.46 } },
].filter((r) => CONDITION_KEYS.includes(r.key))
const STATUS_KEY = { within: 'history.withinRange', outside: 'history.outsideRange', inconclusive: 'history.inconclusive' }

function SignRadar({ scans }) {
  const { t } = useI18n()
  const [active, setActive] = useState(null)
  const verdictOf = (key) => (scans.length > 0 ? scans[0].findings.find((f) => f.label === key)?.verdict ?? null : null)

  return (
    <div className="radar" style={{ aspectRatio: `${BOX_W} / ${BOX_H}` }}>
      <img className="radar-photo" src={nailPhoto} alt="" draggable="false" style={{
        left: `${(PHOTO.x / BOX_W) * 100}%`, top: `${(PHOTO.y / BOX_H) * 100}%`, width: `${(PHOTO.w / BOX_W) * 100}%`,
      }} />
      <svg className="radar-lines" viewBox={`0 0 ${BOX_W} ${BOX_H}`} aria-hidden="true">
        <defs>
          <radialGradient id="radarGlow">
            <stop offset="0" stopColor="#3ddbb3" stopOpacity="0.55" />
            <stop offset="1" stopColor="#3ddbb3" stopOpacity="0" />
          </radialGradient>
        </defs>
        {RADAR.map((r, i) => {
          const px = PHOTO.x + r.at.x * PHOTO.w
          const py = PHOTO.y + r.at.y * PHOTO.h
          const x0 = r.side === 'L' ? r.x + CHIP_W : r.x
          const y0 = r.y + CHIP_H / 2
          const xm = (x0 + px) / 2
          const tone = verdictOf(r.key) ?? 'none'
          return (
            <g key={r.key} className={`radar-link radar-link--${tone} ${active === r.key ? 'is-active' : ''}`} style={{ '--i': i }}>
              <path className="radar-line" pathLength="1" d={`M ${x0} ${y0} C ${xm} ${y0} ${xm} ${py} ${px} ${py}`} />
              <circle className="radar-halo" cx={px} cy={py} r="15" fill="url(#radarGlow)" />
              <circle className="radar-dot" cx={px} cy={py} r="3.6" />
            </g>
          )
        })}
      </svg>
      {RADAR.map((r, i) => {
        const { term } = signNameParts(t(`findingNames.${r.key}`))
        const latest = verdictOf(r.key)
        const tone = latest ?? 'none'
        return (
          <button
            key={r.key}
            type="button"
            aria-pressed={active === r.key}
            className={`radar-chip radar-chip--${tone} ${active === r.key ? 'is-active' : ''}`}
            style={{
              left: `${(r.x / BOX_W) * 100}%`,
              top: `${(r.y / BOX_H) * 100}%`,
              width: `${(CHIP_W / BOX_W) * 100}%`,
              height: `${(CHIP_H / BOX_H) * 100}%`,
              '--i': i,
            }}
            onClick={() => setActive((a) => (a === r.key ? null : r.key))}
          >
            <span className="radar-chip-icon"><Icon name={CONDITION_ICONS[r.key]} size={14} /></span>
            <span className="radar-chip-term">{term}</span>
            <span className="radar-chip-status">{latest ? t(STATUS_KEY[latest]) : t('home.notScanned')}</span>
          </button>
        )
      })}
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
    getHistory(1)
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

        <SignRadar scans={scans} />

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
