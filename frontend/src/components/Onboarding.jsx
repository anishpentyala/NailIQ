import { useEffect, useMemo, useRef, useState } from 'react'
import Icon from './Icon'
import { useI18n } from '../i18n'
import { CONDITION_ICONS, signNameParts } from '../conditions'
import { markOnboarded } from '../onboardingState'

// Where on a healthy nail each sign is looked for (SVG units of the 240x420 drawing). Illustration anchors for the
// intro, not detections.
const POINTS = {
  onychogryphosis: { x: 120, y: 50 },
  onycholysis: { x: 152, y: 66 },
  splinter_hemorrhages: { x: 94, y: 78 },
  leukonychia: { x: 142, y: 104 },
  pitting: { x: 102, y: 118 },
  cyanosis: { x: 120, y: 152 },
  koilonychia: { x: 78, y: 150 },
  beaus_lines: { x: 134, y: 178 },
}

const SHAPE_SIGNS = ['koilonychia', 'pitting', 'beaus_lines', 'onychogryphosis']

// scroll steps: welcome, one per sign (top of the nail to the bottom), then the closing screen
const STEPS = [
  { id: 'welcome' },
  ...['onychogryphosis', 'onycholysis', 'splinter_hemorrhages', 'leukonychia', 'pitting', 'cyanosis', 'koilonychia', 'beaus_lines']
    .map((sign) => ({ id: sign, sign })),
  { id: 'photos' },
]

const NAIL_CENTER = { x: 120, y: 140 }
const ease = (x) => x * x * (3 - 2 * x)
const lerp = (a, b, t) => a + (b - a) * t

// A drawn (not photographed) healthy nail: skin, nail plate, lunula, cuticle fold, gloss. Illustration only.
function NailArt({ activeSign, mode }) {
  const nail = 'M76 74C76 54 96 44 120 44S164 54 164 74V188C164 222 146 238 120 238S76 222 76 188Z'
  return (
    <svg className="ob-nail" viewBox="0 0 240 420" role="img" aria-hidden="true">
      <defs>
        <linearGradient id="obSkin" x1="0" x2="1">
          <stop offset="0" stopColor="#a9694a" />
          <stop offset="0.28" stopColor="#cf9170" />
          <stop offset="0.5" stopColor="#dca584" />
          <stop offset="0.72" stopColor="#cf9170" />
          <stop offset="1" stopColor="#a9694a" />
        </linearGradient>
        <linearGradient id="obPad" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#000" stopOpacity="0.25" />
          <stop offset="0.25" stopColor="#000" stopOpacity="0" />
          <stop offset="1" stopColor="#3a1a10" stopOpacity="0.35" />
        </linearGradient>
        <linearGradient id="obNail" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#f6d5ca" />
          <stop offset="0.3" stopColor="#efbcae" />
          <stop offset="1" stopColor="#e3978c" />
        </linearGradient>
        <linearGradient id="obGloss" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0.55" />
          <stop offset="0.5" stopColor="#fff" stopOpacity="0.08" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <radialGradient id="obLunula" cx="0.5" cy="1" r="0.8">
          <stop offset="0" stopColor="#fbe9e2" stopOpacity="0.95" />
          <stop offset="1" stopColor="#fbe9e2" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="obScan" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#3ddbb3" stopOpacity="0" />
          <stop offset="0.5" stopColor="#3ddbb3" stopOpacity="0.55" />
          <stop offset="1" stopColor="#3ddbb3" stopOpacity="0" />
        </linearGradient>
        <radialGradient id="obZone">
          <stop offset="0" stopColor="#3ddbb3" stopOpacity="0.45" />
          <stop offset="1" stopColor="#3ddbb3" stopOpacity="0" />
        </radialGradient>
        <filter id="obBlur"><feGaussianBlur stdDeviation="3" /></filter>
        <clipPath id="obNailClip"><path d={nail} /></clipPath>
      </defs>

      {/* finger */}
      <path d="M52 420V122C52 54 82 20 120 20S188 54 188 122V420Z" fill="url(#obSkin)" />
      <path d="M52 420V122C52 54 82 20 120 20S188 54 188 122V420Z" fill="url(#obPad)" />
      <ellipse cx="120" cy="30" rx="44" ry="10" fill="#fff" opacity="0.12" filter="url(#obBlur)" />
      <g fill="none" stroke="#6b3420" strokeOpacity="0.28" strokeLinecap="round" strokeWidth="2">
        <path d="M74 318C100 326 140 326 166 318" />
        <path d="M80 330C104 336 136 336 160 330" strokeOpacity="0.18" />
        <path d="M70 378C98 388 142 388 170 378" />
      </g>

      {/* nail fold shadow, plate, ridges, lunula, free edge, gloss, scan line */}
      <path d={nail} fill="#5a2a1c" opacity="0.4" filter="url(#obBlur)" transform="translate(0 2) scale(1.02) translate(-2.4 -2)" />
      <path d={nail} fill="url(#obNail)" />
      <g clipPath="url(#obNailClip)">
        <g stroke="#fff" strokeOpacity="0.09" strokeWidth="2">
          <path d="M96 50V230" /><path d="M110 46V234" /><path d="M124 46V234" /><path d="M138 48V232" /><path d="M152 52V228" />
        </g>
        <ellipse cx="120" cy="238" rx="38" ry="26" fill="url(#obLunula)" />
        <rect x="70" y="44" width="100" height="16" fill="#fff" opacity="0.4" />
        <path d="M76 74C76 54 96 44 120 44S164 54 164 74" fill="none" stroke="#fff" strokeOpacity="0.55" strokeWidth="3" />
        <path d="M82 60L112 40 138 40 96 150Z" fill="url(#obGloss)" />
        <rect className="ob-scan" x="70" y="40" width="100" height="46" fill="url(#obScan)" />
      </g>
      <path d={nail} fill="none" stroke="#7a3a2a" strokeOpacity="0.45" strokeWidth="2" />
      <path d="M74 214C86 246 154 246 166 214C162 236 150 252 120 252S78 236 74 214Z" fill="#cf9170" />
      <path d="M74 214C86 246 154 246 166 214" fill="none" stroke="#7a3a2a" strokeOpacity="0.4" strokeWidth="1.5" />

      {/* points: the active sign glows with a soft zone; the rest stay dim */}
      {Object.entries(POINTS).map(([key, p]) => {
        const active = activeSign === key
        const dim = mode === 'none' || (mode === 'focus' && !active)
        return (
          <g key={key} className={`ob-point ${active ? 'is-active' : ''} ${dim ? 'is-dim' : ''}`} transform={`translate(${p.x} ${p.y})`}>
            <circle className="ob-point-zone" r="26" fill="url(#obZone)" />
            <circle className="ob-point-ring" r="9" />
            <circle className="ob-point-core" r="4.2" />
          </g>
        )
      })}
    </svg>
  )
}

// Camera pose for a step so that `focus` (SVG units) lands at the target spot of a W x H stage. The transform is
// applied about the camera box center, so d = target - center - s * R(r) * (focus - center).
function poseFor(step, index, W, H) {
  const Wc = (H * 240) / 420
  const toLocal = (pt) => ({ x: (pt.x / 240) * Wc - Wc / 2, y: (pt.y / 420) * H - H / 2 })
  let focus = NAIL_CENTER
  let s = 0.85
  let r = 0
  let tx = 0.5
  let ty = 0.36
  if (step.sign) {
    focus = POINTS[step.sign]
    const side = index % 2 === 0 ? 1 : -1
    s = 1.7
    r = 9 * side
    tx = 0.5 + 0.14 * -side // finger swings left/right as you scroll
    ty = 0.32
  } else if (step.id === 'photos') {
    s = 0.7
    ty = 0.34
  }
  const p = toLocal(focus)
  const rad = (r * Math.PI) / 180
  const rx = Math.cos(rad) * p.x - Math.sin(rad) * p.y
  const ry = Math.sin(rad) * p.x + Math.cos(rad) * p.y
  return { s, r, dx: tx * W - W / 2 - s * rx, dy: ty * H - H / 2 - s * ry }
}

export default function Onboarding({ onDone }) {
  const { t } = useI18n()
  const scrollerRef = useRef(null)
  const [size, setSize] = useState({ W: 390, H: 844 })
  const [f, setF] = useState(0) // fractional step index driven by scroll
  const reduced = typeof document !== 'undefined' && document.documentElement.classList.contains('a11y-reduce-motion')
  const stepPx = Math.max(300, size.H * 0.5)
  const last = STEPS.length - 1

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
    const onScroll = () => setF(Math.min(last, Math.max(0, el.scrollTop / stepPx)))
    onScroll()
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [stepPx, last])

  const poses = useMemo(() => STEPS.map((s, i) => poseFor(s, i, size.W, size.H)), [size.W, size.H])
  const i = reduced ? Math.round(f) : Math.min(Math.floor(f), last - 1)
  const k = reduced ? 0 : ease(f - i)
  const a = poses[i]
  const b = poses[reduced ? i : Math.min(i + 1, last)]
  const cam = { s: lerp(a.s, b.s, k), r: lerp(a.r, b.r, k), dx: lerp(a.dx, b.dx, k), dy: lerp(a.dy, b.dy, k) }
  const stepIdx = Math.min(last, Math.round(f))
  const step = STEPS[stepIdx]
  const mode = step.id === 'welcome' ? 'all' : step.id === 'photos' ? 'none' : 'focus'
  const Wc = (size.H * 240) / 420

  const finish = () => {
    markOnboarded()
    onDone()
  }

  const name = step.sign ? signNameParts(t(`findingNames.${step.sign}`)) : null
  const group = step.sign ? (SHAPE_SIGNS.includes(step.sign) ? 'shape' : 'color') : null

  return (
    <div className="onboarding" role="dialog" aria-modal="true" aria-label={t('onboarding.label')}>
      <div className="ob-scroller" ref={scrollerRef} tabIndex={0}>
        <div className="ob-track" style={{ height: size.H + stepPx * last }}>
          <div className="ob-sticky" style={{ height: size.H }}>
            <div className="ob-stage">
              <div
                className="ob-camera"
                style={{
                  width: Wc,
                  height: size.H,
                  left: (size.W - Wc) / 2,
                  transform: `translate(${cam.dx}px, ${cam.dy}px) rotate(${cam.r}deg) scale(${cam.s})`,
                }}
              >
                <NailArt activeSign={step.sign ?? null} mode={mode} />
              </div>
              <span className="ob-example">{t('onboarding.example')}</span>
            </div>

            <div className="ob-top">
              <div className="ob-progress" aria-hidden="true"><span style={{ width: `${(f / last) * 100}%` }} /></div>
              {stepIdx < last && (
                <button type="button" className="ob-skip" onClick={finish}>{t('onboarding.skip')}</button>
              )}
            </div>

            <div className="ob-panel" aria-live="polite">
              <div className="ob-card" key={step.id}>
                {step.sign ? (
                  <>
                    <span className="ob-kicker">
                      <Icon name={CONDITION_ICONS[step.sign]} size={14} /> {t(`onboarding.${group}Title`)}
                    </span>
                    <h2 className="ob-title">{name.term}</h2>
                    <p className="ob-text">{t(`conditions.${step.sign}.summary`)}</p>
                  </>
                ) : (
                  <>
                    <h2 className="ob-title">{t(`onboarding.${step.id}Title`)}</h2>
                    <p className="ob-text">{t(`onboarding.${step.id}Text`)}</p>
                  </>
                )}
                {step.id === 'welcome' && (
                  <p className="ob-hint"><Icon name="chevronRight" size={14} className="rot-down" /> {t('onboarding.scrollHint')}</p>
                )}
                {step.id === 'photos' && (
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
