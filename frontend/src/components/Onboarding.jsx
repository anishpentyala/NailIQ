import { useEffect, useRef, useState } from 'react'
import Icon from './Icon'
import { useI18n } from '../i18n'
import { CONDITION_ICONS, signNameParts } from '../conditions'
import { markOnboarded } from '../onboardingState'
import nailPhoto from '../assets/onboarding-nail.webp'

// A handful of example signs (deliberately not the full list). Anchors are fractions of the fingertip-up photo;
// they are illustration spots for the intro, not detections.
const IMG_W = 900
const IMG_H = 1820
const IMG_AR = IMG_W / IMG_H
const SIGNS = [
  { key: 'koilonychia', x: 0.3, y: 0.27, group: 'shape' },
  { key: 'leukonychia', x: 0.6, y: 0.34, group: 'color' },
  { key: 'pitting', x: 0.38, y: 0.4, group: 'shape' },
  { key: 'cyanosis', x: 0.5, y: 0.47, group: 'color' },
]

// Camera path, in terms of which point of the photo sits on the fixed scan line (REF_Y of the screen): zoom in to the
// fingertip (intro), glide DOWN the finger through the signs (travel), pull back out (outro).
const REF_Y = 0.4
const FOCUS_X = 0.49
const START = { s: 0.85, cy: 0.385 }
const TOP = { s: 1.9, cy: 0.22 }
const BOTTOM = { s: 1.9, cy: 0.52 }
const END = { s: 0.8, cy: 0.45 }
const NEAR_WINDOW = 0.045 // how close (photo fraction) a point must be to the scan line to light up

const ease = (x) => x * x * (3 - 2 * x)
const lerp = (a, b, t) => a + (b - a) * t
const clamp01 = (x) => Math.min(1, Math.max(0, x))

// The example nail photo with the sign points drawn over it (SVG in the photo's own coordinates).
function NailPhoto({ near, mode }) {
  return (
    <div className="ob-nail">
      <img className="ob-nail-img" src={nailPhoto} alt="" draggable="false" />
      <svg className="ob-nail-overlay" viewBox={`0 0 ${IMG_W} ${IMG_H}`} aria-hidden="true">
        <defs>
          <radialGradient id="obZone">
            <stop offset="0" stopColor="#3ddbb3" stopOpacity="0.5" />
            <stop offset="1" stopColor="#3ddbb3" stopOpacity="0" />
          </radialGradient>
        </defs>
        {SIGNS.map((p) => (
          <g
            key={p.key}
            className={`ob-point ${near[p.key] > 0.6 ? 'is-active' : ''}`}
            style={{ '--near': mode === 'none' ? 0 : near[p.key] }}
            transform={`translate(${p.x * IMG_W} ${p.y * IMG_H})`}
          >
            <circle className="ob-point-zone" r="120" fill="url(#obZone)" />
            <circle className="ob-point-ring" r="40" />
            <circle className="ob-point-core" r="17" />
          </g>
        ))}
      </svg>
    </div>
  )
}

export default function Onboarding({ onDone }) {
  const { t } = useI18n()
  const scrollerRef = useRef(null)
  const [size, setSize] = useState({ W: 390, H: 844 })
  const [y, setY] = useState(0) // scroll position in px
  const reduced = typeof document !== 'undefined' && document.documentElement.classList.contains('a11y-reduce-motion')

  const intro = size.H * 0.5
  const travel = size.H * 0.95
  const outro = size.H * 0.5
  const total = intro + travel + outro

  useEffect(() => {
    const el = scrollerRef.current
    if (!el) return
    const measure = () => setSize({ W: el.clientWidth, H: el.clientHeight })
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    const el = scrollerRef.current
    if (!el) return
    const onScroll = () => setY(Math.min(total, Math.max(0, el.scrollTop)))
    onScroll()
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [total])

  // continuous camera: no steps, so scrolling reads as moving down the finger
  let s
  let cy
  if (y < intro) {
    const u = ease(y / intro)
    s = lerp(START.s, TOP.s, u)
    cy = lerp(START.cy, TOP.cy, u)
  } else if (y < intro + travel) {
    const u = (y - intro) / travel
    s = TOP.s
    cy = lerp(TOP.cy, BOTTOM.cy, u)
  } else {
    const u = ease((y - intro - travel) / outro)
    s = lerp(BOTTOM.s, END.s, u)
    cy = lerp(BOTTOM.cy, END.cy, u)
  }
  const phase = y < intro * 0.55 ? 'welcome' : y < intro + travel + outro * 0.25 ? 'signs' : 'photos'
  const mode = phase === 'welcome' ? 'all' : phase === 'photos' ? 'none' : 'focus'

  const near = {}
  SIGNS.forEach((p) => {
    near[p.key] = mode === 'all' ? 0.55 : clamp01(1 - Math.abs(cy - p.y) / NEAR_WINDOW)
  })
  const current = SIGNS.reduce((best, p) => (Math.abs(cy - p.y) < Math.abs(cy - best.y) ? p : best), SIGNS[0])

  // put photo point (FOCUS_X, cy) on the scan line, scaled about the camera box center
  const Wc = size.H * IMG_AR
  const dx = -s * (FOCUS_X * Wc - Wc / 2)
  const dy = REF_Y * size.H - size.H / 2 - s * (cy * size.H - size.H / 2)
  const scanOpacity = phase === 'signs' ? 1 : phase === 'welcome' ? clamp01((y / intro) * 1.4) * 0.6 : 0.2

  const finish = () => {
    markOnboarded()
    onDone()
  }

  const name = signNameParts(t(`findingNames.${current.key}`))

  return (
    <div className="onboarding" role="dialog" aria-modal="true" aria-label={t('onboarding.label')}>
      <div className="ob-scroller" ref={scrollerRef} tabIndex={0}>
        <div className="ob-track" style={{ height: size.H + total }}>
          <div className="ob-sticky" style={{ height: size.H }}>
            <div className="ob-stage">
              <div
                className="ob-camera"
                style={{
                  width: Wc,
                  height: size.H,
                  left: (size.W - Wc) / 2,
                  transform: `translate(${dx}px, ${dy}px) scale(${s})`,
                }}
              >
                <NailPhoto near={near} mode={mode} />
              </div>
              <div className="ob-reticle" style={{ top: `${REF_Y * 100}%`, opacity: reduced ? 0.4 : scanOpacity }} aria-hidden="true">
                <span /><span />
              </div>
              <span className="ob-example">{t('onboarding.example')}</span>
            </div>

            <div className="ob-top">
              <div className="ob-progress" aria-hidden="true"><span style={{ width: `${(y / total) * 100}%` }} /></div>
              {phase !== 'photos' && (
                <button type="button" className="ob-skip" onClick={finish}>{t('onboarding.skip')}</button>
              )}
            </div>

            <div className="ob-panel" aria-live="polite">
              <div className="ob-card" key={phase === 'signs' ? current.key : phase}>
                {phase === 'signs' ? (
                  <>
                    <span className="ob-kicker">
                      <Icon name={CONDITION_ICONS[current.key]} size={14} /> {t(`onboarding.${current.group}Title`)}
                    </span>
                    <h2 className="ob-title">{name.term}</h2>
                    <p className="ob-text">{t(`conditions.${current.key}.summary`)}</p>
                  </>
                ) : (
                  <>
                    <h2 className="ob-title">{t(`onboarding.${phase}Title`)}</h2>
                    <p className="ob-text">{t(`onboarding.${phase}Text`)}</p>
                  </>
                )}
                {phase === 'welcome' && (
                  <p className="ob-hint"><Icon name="chevronRight" size={14} className="rot-down" /> {t('onboarding.scrollHint')}</p>
                )}
                {phase === 'photos' && (
                  <>
                    <p className="ob-fine">{t('app.disclaimer')}</p>
                    <button type="button" className="primary-btn ob-start" onClick={finish}>{t('onboarding.start')}</button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
