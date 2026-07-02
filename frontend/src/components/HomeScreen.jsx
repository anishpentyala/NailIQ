import { useEffect, useState } from 'react'
import Icon from './Icon'
import { getHistory } from '../api'
import { overallStatus, relativeTime } from '../scanStatus'

const TIPS = [
  'Good lighting and a plain background make your scan far more accurate.',
  'Healthy nails are usually smooth, with a slight even curve and no deep grooves.',
  'Nail changes develop slowly — checking now and then helps you notice a trend.',
  'Rest your finger against an edge to keep the side-profile photo steady and sharp.',
  'Remove nail polish before scanning so the nail surface is visible.',
  'One odd-looking nail is rarely a concern on its own — patterns across nails matter more.',
  'Frame just one finger, filling most of the frame, for the clearest read.',
]

function tipOfTheDay() {
  const start = new Date(new Date().getFullYear(), 0, 0)
  const dayOfYear = Math.floor((Date.now() - start) / 86_400_000)
  return TIPS[dayOfYear % TIPS.length]
}

function HeroArt() {
  return (
    <svg
      className="hero-art"
      viewBox="0 0 320 190"
      role="img"
      aria-label="Illustration of a phone scanning a fingernail"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="phoneGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#3f9a85" />
          <stop offset="1" stopColor="#245f51" />
        </linearGradient>
      </defs>
      {/* soft background blob */}
      <ellipse cx="160" cy="120" rx="135" ry="62" fill="rgba(47,125,107,0.12)" />
      <circle cx="58" cy="48" r="6" fill="rgba(47,125,107,0.2)" />
      <circle cx="270" cy="38" r="9" fill="rgba(47,125,107,0.18)" />

      {/* phone with shield */}
      <rect x="196" y="36" width="86" height="120" rx="16" fill="url(#phoneGrad)" />
      <rect x="206" y="46" width="66" height="100" rx="10" fill="#ffffff" opacity="0.95" />
      <path
        d="M239 70 l20 7 v14 c0 13 -9 21 -20 26 c-11 -5 -20 -13 -20 -26 v-14 z"
        fill="#3f9a85"
        opacity="0.25"
      />
      <path d="M231 96 l6 6 l12 -14" fill="none" stroke="#245f51" strokeWidth="4"
        strokeLinecap="round" strokeLinejoin="round" />

      {/* hand / finger pointing up with a nail */}
      <rect x="92" y="70" width="46" height="92" rx="22" fill="#f3c9a8" />
      <rect x="98" y="58" width="34" height="46" rx="16" fill="#f6d6bb" />
      <rect x="103" y="62" width="24" height="22" rx="9" fill="#fbeee2"
        stroke="#e3b793" strokeWidth="2" />

      {/* magnifying glass over the nail */}
      <circle cx="116" cy="74" r="30" fill="rgba(255,255,255,0.35)"
        stroke="#245f51" strokeWidth="5" />
      <line x1="138" y1="96" x2="158" y2="118" stroke="#245f51"
        strokeWidth="7" strokeLinecap="round" />

      {/* sparkles */}
      <path d="M168 48 l3 8 l8 3 l-8 3 l-3 8 l-3 -8 l-8 -3 l8 -3 z" fill="#3f9a85" />
      <path d="M60 110 l2 6 l6 2 l-6 2 l-2 6 l-2 -6 l-6 -2 l6 -2 z" fill="#3f9a85" opacity="0.7" />
    </svg>
  )
}

const VERDICT_ICON = { within: 'checkCircle', outside: 'alertTriangle', inconclusive: 'helpCircle' }

// The home-screen analogue of "today's UV index": a glanceable status from your
// most recent scan, pulled from the same /history data HistoryView already
// renders, so it costs no new backend work. Fails quietly (no card) on error --
// this is a nice-to-have on the landing screen, not something worth an error banner.
function LastScanCard({ onViewHistory }) {
  const [scans, setScans] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    getHistory()
      .then((data) => { if (!cancelled) setScans(data.scans) })
      .catch(() => { if (!cancelled) setFailed(true) })
    return () => { cancelled = true }
  }, [])

  if (failed || scans === null) return null

  if (scans.length === 0) {
    return (
      <button type="button" className="home-card home-last-scan home-last-scan--empty" onClick={onViewHistory}>
        <span className="home-card-icon"><Icon name="clipboard" /></span>
        <div className="home-last-scan-info">
          <span className="home-last-scan-status">No scans yet</span>
          <span className="home-last-scan-time">Your first result will show up here.</span>
        </div>
      </button>
    )
  }

  const latest = scans[0]
  const findings = latest.findings
  const status = overallStatus(findings)

  const conclusive = findings.filter((f) => f.verdict !== 'inconclusive')
  const meanConf =
    conclusive.length > 0
      ? conclusive.reduce((s, f) => s + (f.confidence ?? 0), 0) / conclusive.length
      : null

  // The two most tell-tale measured values, if we have them -- prefer the
  // geometry findings (they carry a real number, not just a verdict).
  const stats = findings.filter((f) => f.value != null).slice(0, 2)

  return (
    <button type="button" className="home-assessment" onClick={onViewHistory}>
      <div className="home-assessment-head">
        <span className="home-assessment-eyebrow">Latest assessment</span>
        {meanConf != null && (
          <span className={`home-assessment-confidence home-assessment-confidence--${status.verdict}`}>
            {Math.round(meanConf * 100)}% confidence
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
              <span className="home-assessment-stat-label">{f.display_name}</span>
              <span className="home-assessment-stat-value">
                {f.value.toFixed(1)}
                {f.unit === 'deg' ? '°' : ''}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="home-assessment-footer">
        <span><Icon name="clipboard" size={13} /> Scan ID: NIQ-{latest.id}</span>
        <span>{relativeTime(latest.created_at)}</span>
      </div>
    </button>
  )
}

export default function HomeScreen({ onStartScan, onViewHistory }) {
  return (
    <div className="home">
      <h1 className="home-title">Home</h1>

      <section className="home-hero">
        <HeroArt />
        <h2 className="home-hero-title">Spot nail changes worth a doctor&rsquo;s look</h2>
        <p className="home-hero-text">
          Some nail signs of anemia, heart, lung, and liver conditions show up early &mdash; but
          develop too slowly to notice on your own. Two quick photos check for thirteen of them.
        </p>
        <button type="button" className="primary-btn home-cta" onClick={onStartScan}>
          Start a scan
        </button>
      </section>

      <LastScanCard onViewHistory={onViewHistory} />

      <section className="home-card">
        <div className="home-card-head">
          <span className="home-card-icon"><Icon name="clipboard" /></span>
          <h3 className="home-card-title">How it works</h3>
        </div>
        <ol className="home-steps">
          <li>
            <span className="step-num">1</span>
            <div>
              <strong>Side profile</strong>
              <p>Finger sideways, nail facing the camera.</p>
            </div>
          </li>
          <li>
            <span className="step-num">2</span>
            <div>
              <strong>Top down</strong>
              <p>Look straight down at the nail surface.</p>
            </div>
          </li>
          <li>
            <span className="step-num">3</span>
            <div>
              <strong>Get your read</strong>
              <p>A clear, non-diagnostic result for each sign.</p>
            </div>
          </li>
        </ol>
      </section>

      <section className="home-card">
        <div className="home-card-head">
          <span className="home-card-icon"><Icon name="search" /></span>
          <h3 className="home-card-title">What NailIQ screens for</h3>
        </div>
        <div className="home-screen-rows">
          <div className="screen-row">
            <span className="screen-emoji"><Icon name="finger" /></span>
            <div>
              <strong>Digital clubbing</strong>
              <p>The angle where the nail meets the skin.</p>
            </div>
          </div>
          <div className="screen-row">
            <span className="screen-emoji"><Icon name="spoon" /></span>
            <div>
              <strong>Koilonychia</strong>
              <p>Spoon-shaped curve of the nail plate.</p>
            </div>
          </div>
          <div className="screen-row">
            <span className="screen-emoji"><Icon name="sparkle" /></span>
            <div>
              <strong>Leukonychia</strong>
              <p>White spots or discoloration on the nail.</p>
            </div>
          </div>
          <div className="screen-row">
            <span className="screen-emoji"><Icon name="pulse" /></span>
            <div>
              <strong>Melanonychia</strong>
              <p>A dark band running down the nail.</p>
            </div>
          </div>
          <div className="screen-row">
            <span className="screen-emoji"><Icon name="eye" /></span>
            <div>
              <strong>Terry's nails</strong>
              <p>Mostly-white nail with a darker band at the tip.</p>
            </div>
          </div>
          <div className="screen-row">
            <span className="screen-emoji"><Icon name="pulse" /></span>
            <div>
              <strong>Beau's lines</strong>
              <p>Grooves running across the nail surface.</p>
            </div>
          </div>
          <div className="screen-row">
            <span className="screen-emoji"><Icon name="pulse" /></span>
            <div>
              <strong>Splinter hemorrhages</strong>
              <p>Tiny dark streaks beneath the nail.</p>
            </div>
          </div>
          <div className="screen-row">
            <span className="screen-emoji"><Icon name="search" /></span>
            <div>
              <strong>Pitting</strong>
              <p>Small dents or pinpricks in the nail surface.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="home-card home-tip">
        <div className="home-card-head">
          <span className="home-card-icon home-card-icon--accent"><Icon name="sparkle" /></span>
          <h3 className="home-card-title">Daily tip</h3>
        </div>
        <p className="home-tip-text">{tipOfTheDay()}</p>
      </section>
    </div>
  )
}
